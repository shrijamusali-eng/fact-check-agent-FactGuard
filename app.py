import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os
from dotenv import load_dotenv
from tavily import TavilyClient
import time

# 1. Load environment variables (Local development fallback)
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
        # Read the file bytes directly from Streamlit's file uploader
        file_bytes = uploaded_file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()
    except Exception as e:
        st.error(f"Error reading PDF file: {e}")
    return text

def extract_claims(text):
    """Uses Gemini to identify distinct factual claims from the text block."""
    if not GEMINI_API_KEY:
        return []
        
    prompt = f"""
    Analyze the following text and extract a list of up to 5 main objective, factual, verifiable statements or claims.
    Return ONLY the claims, one per line. Do not number them or add extra text.
    
    Text:
    {text}
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        # Split by newlines and filter out empty strings
        claims = [line.strip() for line in response.text.split("\n") if line.strip()]
        return claims
    except Exception as e:
        st.error(f"Error extracting claims: {e}")
        return []

def verify_claim(claim):
    """Validates a singular claim using Tavily Search data and Gemini analysis."""
    if not GEMINI_API_KEY or not TAVILY_API_KEY:
        return "Verification setup incomplete."

    # Step A: Gather context via web search
    try:
        search_result = tavily_client.search(query=claim, max_results=3)
        search_context = "\n".join([res.get("content", "") for res in search_result.get("results", [])])
    except Exception as e:
        search_context = f"Could not pull live web data due to search error: {e}"

    # Step B: Pass context to Gemini for final verdict reporting
    verification_prompt = f"""
    You are an expert Fact-Checking Agent.
    Verify the validity of the given 'Claim' using the provided 'Web Search Context'.
    
    Your final answer must begin strictly with one of these three prefixes:
    - Verdict: TRUE
    - Verdict: FALSE
    - Verdict: INACCURATE
    
    Followed by a clear, one or two-sentence factual explanation supporting the conclusion.
    
    Claim: {claim}
    Web Search Context: {search_context}
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(verification_prompt)
        return response.text.strip()
    except Exception as e:
        # Pass the raw exception error up so we can inspect it safely
        raise e

# --- STREAMLIT UI ---

st.title("Fact Check Agent")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file is not None:
    # 1. Parse PDF document layout
    with st.spinner("Extracting text from PDF..."):
        extracted_text = extract_text_from_pdf(uploaded_file)
        
    if extracted_text.strip():
        st.success("PDF uploaded successfully!")
        
        with st.expander("View Extxtracted PDF Text"):
            st.write(extracted_text)
            
        # 2. Extract Claims via LLM
        with st.spinner("Isolating key factual claims..."):
            claims = extract_claims(extracted_text)
            
        if claims:
            st.subheader("Claims Found")
            for c in claims:
                st.write(f"- {c}")
                
            st.markdown("---")
            st.subheader("Fact Check Results")
            
            # 3. Step-by-step verification with sequential timing delays
            for index, claim in enumerate(claims):
                st.markdown(f"🔍 **Checking:** *{claim}*")
                
                try:
                    # Run the verification engine
                    result = verify_claim(claim)
                    
                    # Highlight responses dynamically using native alert boxes
                    if "Verdict: TRUE" in result:
                        st.success(result)
                    elif "Verdict: FALSE" in result:
                        st.error(result)
                    elif "Verdict: INACCURATE" in result:
                        st.warning(result)
                    else:
                        st.info(result)
                        
                except Exception as e:
                    st.error(f"Gemini Analysis Error: {e}")
                
                # Rate-limiting guardrail loop implementation
                if index < len(claims) - 1:
                    # Sleep for 3 seconds between requests to protect the API quota
                    time.sleep(3)
        else:
            st.warning("No explicit factual claims could be parsed from this text layout.")
    else:
        st.error("The uploaded PDF appears empty or unreadable.")