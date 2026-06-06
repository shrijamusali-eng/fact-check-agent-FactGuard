import os
import fitz  # PyMuPDF
import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv
from tavily import TavilyClient

# Load environment variables
load_dotenv()

# Configure APIs
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# USING FLASH-LITE: Optimized for fast, multi-line structural extraction on the free tier
model = genai.GenerativeModel("gemini-2.5-flash-lite")
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Streamlit UI
st.title("Fact Check Agent")

pdf = st.file_uploader("Upload PDF", type=["pdf"])

if pdf:
    st.success("PDF uploaded successfully!")

    # Read PDF
    doc = fitz.open(stream=pdf.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()

    st.subheader("Extracted Text")
    st.write(text[:2000])  # Previews the first 2000 characters safely

    # Step 1: Extract claims using Gemini (1st API Call)
    with st.spinner("Finding claims..."):
        prompt = f"""
        Analyze the following text and extract up to 5-7 key factual claims that can be verified. 
        Return them ONLY as a plain list of bullet points (one per line). Do not include introductory text.
        TEXT:
        {text[:8000]} 
        """
        try:
            response = model.generate_content(prompt)
            claims_text = response.text
        except Exception as e:
            st.error(f"Error during claim extraction: {e}")
            claims_text = ""

    if claims_text:
        st.subheader("Claims Found")
        st.write(claims_text)

        # Process individual lines cleanly
        raw_claims = claims_text.split("\n")
        cleaned_claims = []
        for c in raw_claims:
            cleaned = c.replace("•", "").replace("-", "").replace("*", "").strip()
            if len(cleaned) > 10:
                cleaned_claims.append(cleaned)

        st.subheader("Fact Check Results")

        # Step 2: Gather all search evidence via Tavily first
        bundled_evidence_prompt = ""
        
        with st.spinner("Searching the web for evidence..."):
            for i, claim in enumerate(cleaned_claims, 1):
                st.write(f"🔍 Gathering web data for claim {i}/{len(cleaned_claims)}: *{claim}*")
                try:
                    search_result = tavily.search(query=claim, max_results=2)
                    
                    # Append to our final prompt structure
                    bundled_evidence_prompt += f"""
                    ---
                    CLAIM #{i}: {claim}
                    WEB EVIDENCE FOUND: {search_result}
                    """
                except Exception as e:
                    bundled_evidence_prompt += f"""
                    ---
                    CLAIM #{i}: {claim}
                    WEB EVIDENCE FOUND: Could not fetch search results.
                    """

        # Step 3: Send ALL claims and evidence to Gemini in ONE single final batch call (2nd API Call)
        with st.spinner("Analyzing all evidence and generating verdicts..."):
            final_verification_prompt = f"""
            You are an expert fact-checker. You are given a list of claims and corresponding web search evidence.
            Analyze each claim against its web evidence and provide a verdict.
            
            DATA:
            {bundled_evidence_prompt}
            
            For each claim, determine:
            VERIFIED
            INACCURATE
            FALSE

            Definitions:
            VERIFIED = Web evidence strongly supports the claim.
            INACCURATE = Claim is partially true or outdated.
            FALSE = Claim is contradicted by evidence.

            Output exactly using this marker syntax so the UI can parse it:
            [CLAIM_START]
            ### Claim: {claim}
            Verdict: [VERIFIED, INACCURATE, or FALSE]
            Reason: [Provide a short, clear 2-3 sentence explanation based strictly on the provided web evidence]
            [CLAIM_END]
            """
            
            try:
                final_response = model.generate_content(final_verification_prompt)
                report_text = final_response.text

                # --- 3. IMPROVEMENT: CALCULATE DOCUMENT TRUST SCORE ---
                trust_score = 100
                false_count = report_text.count("Verdict: FALSE")
                inaccurate_count = report_text.count("Verdict: INACCURATE")

                trust_score -= false_count * 20
                trust_score -= inaccurate_count * 10
                trust_score = max(trust_score, 0)

                # Display product metrics block
                st.metric(
                    label="📄 Document Trust Score",
                    value=f"{trust_score}/100",
                    delta=f"-{100 - trust_score} pts" if trust_score < 100 else "Perfect"
                )
                st.markdown("---")

                # --- 1. IMPROVEMENT: PARSE & APPLY VERDICT COLORS ---
                # Split the raw payload into individual verified claim strings
                claim_blocks = report_text.split("[CLAIM_START]")
                
                for block in claim_blocks:
                    if "[CLAIM_END]" in block:
                        clean_block = block.split("[CLAIM_END]")[0].strip()
                        
                        # Apply conditional color wrappers depending on inner values
                        if "Verdict: FALSE" in clean_block:
                            st.error(clean_block)
                        elif "Verdict: INACCURATE" in clean_block:
                            st.warning(clean_block)
                        else:
                            st.success(clean_block)

            except Exception as e:
                st.error(f"Gemini Analysis Error: {e}")