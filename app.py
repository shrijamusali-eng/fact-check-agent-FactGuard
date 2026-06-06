import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os
from dotenv import load_dotenv
from tavily import TavilyClient

# 1. Load environment variables
load_dotenv()

# 2. Retrieve API Keys safely from Streamlit Secrets or local .env
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
TAVILY_API_KEY = st.secrets.get("TAVILY_API_KEY", os.getenv("TAVILY_API_KEY"))

# 3. Configure API Clients
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("Missing Gemini API Key. Please check your Streamlit Advanced Settings Secrets.")

if TAVILY_API_KEY:
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
else:
    st.error("Missing Tavily API Key. Please check your Streamlit Advanced Settings Secrets.")

# --- HELPER FUNCTIONS ---

def extract_text_from_pdf(uploaded_file):
    """Extracts raw text from an uploaded PDF file stream."""
    text = ""
    try:
        file_bytes = uploaded_file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()
    except Exception as e:
        st.error(f"Error reading PDF file: {e}")
    return text

def extract_claims(text):
    """Identifies distinct factual claims from the text block using Gemini."""
    if not GEMINI_API_KEY:
        return []
        
    prompt = f"""
    Analyze the following text and extract a list of up to 4 main objective, factual statements or claims.
    Return ONLY the claims, one per line. Do not number them, use bullet points, or add extra introductory text.
    
    Text:
    {text}
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        claims = [line.strip() for line in response.text.split("\n") if line.strip()]
        return claims
    except Exception as e:
        st.error(f"Error extracting claims: {e}")
        return []

# --- STREAMLIT UI ---

st.title("Fact Check Agent")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file is not None:
    with st.spinner("Extracting text from PDF..."):
        extracted_text = extract_text_from_pdf(uploaded_file)
        
    if extracted_text.strip():
        st.success("PDF uploaded successfully!")
        
        with st.expander("View Extracted PDF Text"):
            st.write(extracted_text)
            
        # Extract Claims
        with st.spinner("Isolating key factual claims..."):
            claims = extract_claims(extracted_text)
            
        if claims:
            st.subheader("Claims Found")
            for c in claims:
                st.write(f"- {c}")
                
            st.markdown("---")
            st.subheader("Fact Check Results")
            
            # --- BATCH SEARCH ENGINE PROCESSING ---
            bundled_evidence_prompt = ""
            
            with st.spinner("Searching the live web for evidence..."):
                for i, claim in enumerate(claims, 1):
                    st.write(f"🔍 Gathering data for claim {i}/{len(claims)}: *{claim}*")
                    try:
                        search_result = tavily_client.search(query=claim, max_results=2)
                        search_context = "\n".join([res.get("content", "") for res in search_result.get("results", [])])
                        
                        bundled_evidence_prompt += f"""
                        ---
                        CLAIM #{i}: {claim}
                        WEB EVIDENCE FOUND: {search_context}
                        """
                    except Exception as e:
                        bundled_evidence_prompt += f"\n---\nCLAIM #{i}: {claim}\nWEB EVIDENCE: Could not fetch data ({e})"
            
            # --- SINGLE BATCH LLM VERIFICATION CALL ---
            with st.spinner("Analyzing all evidence and generating verdicts..."):
                final_verification_prompt = f"""
                You are an expert fact-checker. Analyze each claim against its corresponding web evidence data.
                
                DATA TO ANALYZE:
                {bundled_evidence_prompt}
                
                For each claim block, output your verdict strictly using this exact marker format:
                
                [CLAIM_START]
                ### Claim: [Write the original claim here]
                Verdict: [Write either VERIFIED, INACCURATE, or FALSE]
                Reason: [Provide a concise 1-2 sentence explanation based on the web evidence]
                [CLAIM_END]
                """
                
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    final_response = model.generate_content(final_verification_prompt)
                    report_text = final_response.text

                    # Calculate Document Trust Score Metrics
                    trust_score = 100
                    false_count = report_text.count("Verdict: FALSE")
                    inaccurate_count = report_text.count("Verdict: INACCURATE")

                    trust_score -= false_count * 20
                    trust_score -= inaccurate_count * 10
                    trust_score = max(trust_score, 0)

                    st.metric(
                        label="📄 Overall Document Trust Score",
                        value=f"{trust_score}/100",
                        delta=f"-{100 - trust_score} pts" if trust_score < 100 else "Perfect Balance"
                    )
                    st.markdown("---")

                    # Parse and display color indicators
                    claim_blocks = report_text.split("[CLAIM_START]")
                    for block in claim_blocks:
                        if "[CLAIM_END]" in block:
                            clean_block = block.split("[CLAIM_END]")[0].strip()
                            
                            if "Verdict: FALSE" in clean_block:
                                st.error(clean_block)
                            elif "Verdict: INACCURATE" in clean_block:
                                st.warning(clean_block)
                            else:
                                st.success(clean_block)

                except Exception as e:
                    st.error(f"Gemini Analysis Error during batch verification: {e}")
        else:
            st.warning("No clear factual statements could be parsed from this PDF layout.")
    else:
        st.error("The uploaded PDF could not be read properly.") 