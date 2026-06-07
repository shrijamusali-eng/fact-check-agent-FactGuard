# fact-check-agent-FactGuard
# 🔍 FactGuard – AI-Powered PDF Fact Verification

FactGuard is an AI-powered fact-checking platform that analyzes PDF documents, extracts factual claims, and verifies them against live web data.

Using Groq's LLMs and Tavily Search, FactGuard identifies misleading, inaccurate, or unsupported information and provides evidence-backed verification results.

---

## 🚀 Features

### 📄 PDF Analysis

* Extract text from PDF documents
* Preserve document structure and layout
* Extract tabular data for verification

### 🧠 AI Claim Extraction

Automatically identifies:

* Statistics and percentages
* Dates and years
* Financial figures
* Technical specifications
* Rankings and measurable facts

### 🌐 Live Web Verification

* Searches the web using Tavily Search
* Collects supporting evidence
* Cross-checks claims against current information

### ✅ Intelligent Fact Checking

Each claim is classified as:

* VERIFIED
* INACCURATE
* FALSE

For every claim, FactGuard provides:

* Verification verdict
* Explanation
* Supporting evidence
* Corrected information when applicable

### 📊 Trust Score

Generates an overall trust score for the uploaded document based on verification results.

---

## 🛠 Tech Stack

### Frontend

* Streamlit

### AI Engine

* Groq API
* Llama 3.3 70B
* Llama 3 70B
* Llama 3 8B

### Search Engine

* Tavily Search API

### PDF Processing

* PyMuPDF
* pdfplumber

### Environment Management

* python-dotenv

---

## 📦 Installation

### Clone the Repository

```bash
git clone https://github.com/yourusername/factguard.git
cd factguard
```

### Create Virtual Environment

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
```

---

## ▶️ Run the Application

```bash
streamlit run app.py
```

---

## 📋 How It Works

1. Upload a PDF document.
2. FactGuard extracts all verifiable claims.
3. Tavily searches the web for supporting evidence.
4. Groq LLM evaluates each claim.
5. A verification report is generated.
6. The system calculates a document trust score.

---
## Live Demo

🚀 **Try FactGuard here:**  
[FactGuard Live App](https://fact-check-agent-factguard-hicm9bpgcpahfzstuvupww.streamlit.app)

## 📊 Example Output

Document Trust Score: 82/100

* ✓ 8 Verified Claims
* ⚠ 2 Inaccurate Claims
* ✗ 1 False Claim

Each result includes:

* Claim text
* Verification verdict
* Explanation
* Evidence sources
* Corrected fact (if required)

---

## 📁 Project Structure

```text
factguard/
│
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
│
└── assets/
    └── screenshot.png
```

---

## 🔮 Future Enhancements

* Export verification reports as PDF
* Multi-document comparison
* Source credibility scoring
* Historical fact tracking
* Batch document verification
* Advanced citation analysis

---

## 👩‍💻 Author

Shrija Musali

Electronics Engineer | Product Management Enthusiast | AI & Digital Trust Solutions

---

## 📄 License

MIT License
