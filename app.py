import os
import re
import json
import time
import fitz  # PyMuPDF
import pdfplumber
import streamlit as st
from dotenv import load_dotenv
from tavily import TavilyClient
import google.generativeai as genai

# ─────────────────────────────────────────────
# ENV & API SETUP
# ─────────────────────────────────────────────
load_dotenv()

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
TAVILY_API_KEY = st.secrets.get("TAVILY_API_KEY", os.getenv("TAVILY_API_KEY", ""))

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash-lite") if GEMINI_API_KEY else None
tavily = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

# ─────────────────────────────────────────────
# PAGE CONFIG & GLOBAL STYLES
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="FactGuard – Truth Layer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --bg: #0b0d12;
    --surface: #13161f;
    --border: #1e2330;
    --accent: #4fffb0;
    --accent2: #7c6aff;
    --warn: #ffcc44;
    --danger: #ff4d6d;
    --text: #e8eaf0;
    --muted: #6b7280;
    --verified-bg: #0a2318;
    --warn-bg: #1f1800;
    --danger-bg: #1f0010;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { background: var(--surface) !important; }

.block-container {
    padding: 2rem 3rem !important;
    max-width: 1100px !important;
}

/* ── HERO ── */
.hero {
    text-align: center;
    padding: 3.5rem 1rem 2.5rem;
    position: relative;
}
.hero-badge {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--accent);
    border: 1px solid var(--accent);
    padding: 4px 14px;
    border-radius: 20px;
    margin-bottom: 1.2rem;
}
.hero h1 {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2.4rem, 5vw, 4rem);
    font-weight: 800;
    line-height: 1.1;
    margin: 0 0 0.8rem;
    background: linear-gradient(135deg, #e8eaf0 0%, var(--accent) 60%, var(--accent2) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero p {
    font-size: 1.05rem;
    color: var(--muted);
    max-width: 520px;
    margin: 0 auto;
    line-height: 1.7;
}

/* ── UPLOAD ZONE ── */
[data-testid="stFileUploader"] {
    background: var(--surface) !important;
    border: 1.5px dashed var(--border) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    transition: border-color 0.2s;
}
[data-testid="stFileUploader"]:hover { border-color: var(--accent) !important; }

/* Fix: "Drop a PDF here" and file size hint text → black so visible on light dropzone */
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploaderDropzoneInstructions"] p {
    color: #111111 !important;
}
/* Fix: upload cloud/arrow icon → black */
[data-testid="stFileUploaderDropzoneInstructions"] svg {
    fill: #111111 !important;
    stroke: #111111 !important;
}
/* Fix: "Browse files" button text and border → black */
[data-testid="stFileUploaderDropzone"] button {
    color: #111111 !important;
    border-color: #333333 !important;
}

/* ── DIVIDER ── */
.section-divider {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin: 2rem 0 1.5rem;
}
.section-divider .label {
    font-family: 'Syne', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--muted);
    white-space: nowrap;
}
.section-divider .line {
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* ── SCORE CARD ── */
.score-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.6rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 2rem;
    flex-wrap: wrap;
    gap: 1rem;
}
.score-number {
    font-family: 'Syne', sans-serif;
    font-size: 3.5rem;
    font-weight: 800;
    line-height: 1;
}
.score-label {
    font-size: 0.78rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-top: 4px;
    font-family: 'DM Mono', monospace;
}
.score-pills {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
}
.pill {
    font-family: 'DM Mono', monospace;
    font-size: 0.75rem;
    padding: 4px 12px;
    border-radius: 20px;
    border: 1px solid;
}
.pill-v { color: var(--accent); border-color: var(--accent); background: rgba(79,255,176,0.07); }
.pill-i { color: var(--warn); border-color: var(--warn); background: rgba(255,204,68,0.07); }
.pill-f { color: var(--danger); border-color: var(--danger); background: rgba(255,77,109,0.07); }

/* ── CLAIM CARD ── */
.claim-card {
    border-radius: 12px;
    border: 1px solid var(--border);
    margin-bottom: 1.2rem;
    overflow: hidden;
    transition: border-color 0.2s;
}
.claim-card:hover { border-color: #2e3448; }

.claim-header {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: 1.1rem 1.4rem;
}
.claim-index {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    color: var(--muted);
    min-width: 2rem;
    padding-top: 3px;
}
.claim-text {
    font-size: 0.97rem;
    font-weight: 500;
    line-height: 1.5;
    flex: 1;
    color: var(--text);
}
.verdict-chip {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    padding: 4px 10px;
    border-radius: 6px;
    white-space: nowrap;
    margin-top: 2px;
}
.chip-v { background: rgba(79,255,176,0.12); color: var(--accent); border: 1px solid var(--accent); }
.chip-i { background: rgba(255,204,68,0.12); color: var(--warn); border: 1px solid var(--warn); }
.chip-f { background: rgba(255,77,109,0.12); color: var(--danger); border: 1px solid var(--danger); }

.claim-body {
    padding: 0.6rem 1.4rem 1.1rem 1.4rem;
    border-top: 1px solid var(--border);
}
.detail-row {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    align-items: flex-start;
}
.detail-key {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    min-width: 80px;
    padding-top: 2px;
}
.detail-val {
    font-size: 0.88rem;
    color: #c8cadc;
    line-height: 1.55;
    flex: 1;
}
.real-fact-val {
    color: var(--accent);
    font-weight: 500;
}

/* ── TEXT PREVIEW ── */
.text-preview {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
    color: var(--muted);
    line-height: 1.65;
    white-space: pre-wrap;
    max-height: 220px;
    overflow-y: auto;
}

/* ── SECTION STATS ── */
.section-stat-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.8rem;
    flex-wrap: wrap;
}
.stat-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.4rem;
    flex: 1;
    min-width: 130px;
}
.stat-box .num {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    line-height: 1;
}
.stat-box .lbl {
    font-size: 0.72rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-family: 'DM Mono', monospace;
    margin-top: 4px;
}

/* ── SPINNERS ── */
.stSpinner > div { border-top-color: var(--accent) !important; }

/* ── BUTTONS ── */
.stButton > button {
    background: var(--accent) !important;
    color: #000 !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.55rem 1.6rem !important;
    cursor: pointer !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* ── EXPANDER ── */
[data-testid="stExpander"] {
    background: #0e1017 !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

/* Streamlit green/yellow/red overrides */
.stSuccess, .stWarning, .stError { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def section_divider(label: str):
    st.markdown(f"""
    <div class="section-divider">
      <span class="line"></span>
      <span class="label">{label}</span>
      <span class="line"></span>
    </div>
    """, unsafe_allow_html=True)


def extract_text_pymupdf(file_bytes: bytes) -> str:
    """Extract full text using PyMuPDF with block-level ordering."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages_text = []
    for page_num, page in enumerate(doc, 1):
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))  # top-to-bottom, left-to-right
        page_text = f"\n[PAGE {page_num}]\n"
        page_text += " ".join(b[4].strip() for b in blocks if b[4].strip())
        pages_text.append(page_text)
    return "\n\n".join(pages_text)


def extract_tables_pdfplumber(file_bytes: bytes) -> list[str]:
    """Extract any tabular data as plain text rows."""
    tables = []
    try:
        import io
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    rows = [" | ".join(str(cell or "").strip() for cell in row) for row in table if row]
                    tables.append("\n".join(rows))
    except Exception:
        pass
    return tables


def gemini_extract_claims(text: str, table_context: str) -> list[dict]:
    """
    Ask Gemini to extract ALL verifiable claims with their section context.
    Returns a list of {claim, section, type}.
    """
    prompt = f"""
You are a meticulous fact-extraction expert. Your job is to extract ALL verifiable factual claims from the text below.

A verifiable claim is any specific assertion that includes:
- Statistics or percentages (e.g., "market grew 45%")
- Named dates or years (e.g., "launched in 2022")
- Financial figures (e.g., "$4.5 billion revenue")
- Named companies, products, or people with attributed facts
- Technical specifications or benchmarks
- Rankings or comparisons with specific numbers
- Any statement that can be cross-checked against public data

INSTRUCTIONS:
1. Extract EVERY such claim you find — do not skip any. Target 8–14 claims if the document has them.
2. For each claim, also identify which section/topic area it belongs to (e.g., "Market Size", "Company Performance", "Product Feature").
3. Identify the type: STATISTIC | DATE | FINANCIAL | TECHNICAL | RANKING | OTHER
4. Return ONLY a valid JSON array. No markdown, no backticks.

FORMAT (strict):
[
  {{"claim": "exact claim text from document", "section": "section or topic label", "type": "STATISTIC"}},
  ...
]

DOCUMENT TEXT:
{text[:10000]}

TABLE DATA (if any):
{table_context[:2000]}
"""
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # Strip any accidental markdown fences
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
        raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        st.error(f"Claim extraction error: {e}")
    return []


def tavily_search(query: str, max_results: int = 4) -> list[dict]:
    """Search Tavily and return list of {title, snippet, url}."""
    try:
        result = tavily.search(query=query, max_results=max_results)
        sources = []
        for r in result.get("results", []):
            sources.append({
                "title": r.get("title", ""),
                "snippet": r.get("content", "")[:400],
                "url": r.get("url", ""),
            })
        return sources
    except Exception as e:
        return [{"title": "Search Error", "snippet": str(e), "url": ""}]


def gemini_verify_batch(claims_with_evidence: list[dict]) -> list[dict]:
    """
    Send all claims + evidence to Gemini in one call.
    Returns list of {index, verdict, reason, real_fact}.
    """
    bundle = ""
    for i, item in enumerate(claims_with_evidence, 1):
        evidence_text = "\n".join(
            f"  [{j}] {s['title']}: {s['snippet']}" 
            for j, s in enumerate(item["sources"], 1)
        ) or "  No sources found."
        bundle += f"""
---
CLAIM #{i}: {item['claim']}
SECTION: {item.get('section', 'Unknown')}
TYPE: {item.get('type', 'OTHER')}
WEB EVIDENCE:
{evidence_text}
"""

    prompt = f"""
You are a senior fact-checker. Evaluate each claim against its web evidence.

For each claim output a JSON object with:
- "index": claim number (integer)
- "verdict": one of "VERIFIED", "INACCURATE", "FALSE"
- "reason": 2–3 sentence explanation grounded strictly in the evidence
- "real_fact": if INACCURATE or FALSE, write the correct value/stat from the evidence. If VERIFIED, write "N/A".

VERDICTS:
- VERIFIED: Evidence strongly supports the claim as stated.
- INACCURATE: Claim is partially true, outdated, or uses wrong numbers.
- FALSE: Claim is directly contradicted or entirely unsupported by evidence.

Return ONLY a JSON array of objects. No markdown, no extra text.

CLAIMS AND EVIDENCE:
{bundle}
"""
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
        raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        st.error(f"Gemini verification error: {e}")
    return []


def render_claim_card(idx: int, claim_obj: dict, verdict_obj: dict):
    verdict = verdict_obj.get("verdict", "FALSE").upper()
    reason = verdict_obj.get("reason", "—")
    real_fact = verdict_obj.get("real_fact", "N/A")
    section = claim_obj.get("section", "")
    claim_type = claim_obj.get("type", "")
    sources = claim_obj.get("sources", [])

    chip_class = {"VERIFIED": "chip-v", "INACCURATE": "chip-i"}.get(verdict, "chip-f")
    card_style = ""
    if verdict == "VERIFIED":
        card_style = "border-color:#1a3d2b;"
    elif verdict == "INACCURATE":
        card_style = "border-color:#3d2e00;"
    else:
        card_style = "border-color:#3d0015;"

    real_fact_html = ""
    if real_fact and real_fact.upper() not in ("N/A", "", "NA"):
        real_fact_html = f"""
        <div class="detail-row">
          <span class="detail-key">Real Fact</span>
          <span class="detail-val real-fact-val">↳ {real_fact}</span>
        </div>"""

    meta_tags = ""
    if section:
        meta_tags += f'<span class="pill pill-v" style="font-size:0.65rem;margin-top:2px">{section}</span> '
    if claim_type:
        meta_tags += f'<span class="pill" style="font-size:0.65rem;margin-top:2px;color:var(--muted);border-color:var(--border)">{claim_type}</span>'

    st.markdown(f"""
    <div class="claim-card" style="{card_style}">
      <div class="claim-header">
        <span class="claim-index">#{idx:02d}</span>
        <div style="flex:1">
          <div class="claim-text">{claim_obj['claim']}</div>
          <div style="margin-top:6px">{meta_tags}</div>
        </div>
        <span class="verdict-chip {chip_class}">{verdict}</span>
      </div>
      <div class="claim-body">
        <div class="detail-row">
          <span class="detail-key">Analysis</span>
          <span class="detail-val">{reason}</span>
        </div>
        {real_fact_html}
      </div>
    </div>
    """, unsafe_allow_html=True)

    if sources:
        with st.expander(f"🌐 View {len(sources)} web source(s) for claim #{idx}"):
            for j, s in enumerate(sources, 1):
                url = s.get("url", "")
                title = s.get("title", "Source")
                snippet = s.get("snippet", "")
                st.markdown(
                    f"**{j}. [{title}]({url})**  \n"
                    f"<span style='font-size:0.83rem;color:#7a8099'>{snippet}</span>",
                    unsafe_allow_html=True
                )


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────

# HERO
st.markdown("""
<div class="hero">
  <div class="hero-badge">⬡ AI-Powered Truth Layer</div>
  <h1>FactGuard</h1>
  <p>Upload any PDF. We extract every verifiable claim, cross-reference it against live web data, and flag exactly what's wrong — with the correct facts.</p>
</div>
""", unsafe_allow_html=True)

# API KEY GUARD
missing = []
if not GEMINI_API_KEY:
    missing.append("GEMINI_API_KEY")
if not TAVILY_API_KEY:
    missing.append("TAVILY_API_KEY")
if missing:
    st.markdown(f"""
    <div style="background:#1f0a00;border:1px solid #7a3800;border-radius:10px;padding:1rem 1.4rem;margin-bottom:1.5rem">
      <span style="color:#ff8844;font-family:'DM Mono',monospace;font-size:0.85rem">
        ⚠ Missing API keys: <b>{', '.join(missing)}</b><br>
        Add them to <code>.streamlit/secrets.toml</code> or your environment.
      </span>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# UPLOAD
section_divider("Upload Document")
pdf_file = st.file_uploader(
    "Drop a PDF here or click to browse",
    type=["pdf"],
    help="Any PDF with factual claims — reports, marketing docs, whitepapers."
)

if pdf_file:
    file_bytes = pdf_file.read()

    # ── STEP 1: EXTRACT TEXT ──────────────────
    section_divider("Document Parsing")
    with st.spinner("Extracting text with layout-aware parsing…"):
        full_text = extract_text_pymupdf(file_bytes)
        tables = extract_tables_pdfplumber(file_bytes)
        table_context = "\n\n".join(tables) if tables else ""

    col1, col2, col3 = st.columns(3)
    word_count = len(full_text.split())
    with col1:
        st.markdown(f"""
        <div class="stat-box">
          <div class="num" style="color:var(--accent)">{word_count:,}</div>
          <div class="lbl">Words Extracted</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-box">
          <div class="num" style="color:var(--accent2)">{len(tables)}</div>
          <div class="lbl">Tables Found</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        char_count = len(full_text)
        st.markdown(f"""
        <div class="stat-box">
          <div class="num" style="color:#c8aaff">{char_count:,}</div>
          <div class="lbl">Characters</div>
        </div>""", unsafe_allow_html=True)

    with st.expander("📄 Preview extracted text"):
        st.markdown(f'<div class="text-preview">{full_text[:3000]}{"..." if len(full_text) > 3000 else ""}</div>',
                    unsafe_allow_html=True)

    if table_context:
        with st.expander("📊 Preview extracted tables"):
            st.markdown(f'<div class="text-preview">{table_context[:2000]}</div>', unsafe_allow_html=True)

    # ── STEP 2: EXTRACT CLAIMS ─────────────────
    section_divider("Claim Extraction")
    with st.spinner("Identifying all verifiable claims…"):
        raw_claims = gemini_extract_claims(full_text, table_context)

    if not raw_claims:
        st.markdown("""
        <div style="background:#1f0a00;border:1px solid #7a3800;border-radius:10px;padding:1rem 1.4rem">
          <span style="color:#ff8844;font-size:0.88rem">
            No verifiable claims could be extracted. The document may lack specific statistics, dates, or figures.
          </span>
        </div>""", unsafe_allow_html=True)
        st.stop()

    st.markdown(f"""
    <div style="background:rgba(79,255,176,0.05);border:1px solid rgba(79,255,176,0.2);border-radius:10px;padding:0.9rem 1.3rem;margin-bottom:0.5rem">
      <span style="color:var(--accent);font-family:'DM Mono',monospace;font-size:0.82rem">
        ✓ Isolated <b>{len(raw_claims)}</b> verifiable claims across <b>{len(set(c.get('section','') for c in raw_claims))}</b> topic sections
      </span>
    </div>
    """, unsafe_allow_html=True)

    # Show extracted claims preview
    with st.expander(f"🗂 Preview all {len(raw_claims)} extracted claims"):
        for i, c in enumerate(raw_claims, 1):
            st.markdown(
                f"**#{i:02d}** `{c.get('type','?')}` · *{c.get('section','')}*  \n"
                f"{c['claim']}",
            )
            st.divider()

    # ── STEP 3: WEB SEARCH ────────────────────
    section_divider("Live Web Verification")
    progress_bar = st.progress(0, text="Initialising web search…")

    claims_with_evidence = []
    for i, claim_obj in enumerate(raw_claims):
        query = claim_obj["claim"][:120]  # Tavily query cap
        progress_bar.progress(
            (i) / len(raw_claims),
            text=f"🔍 Searching web for claim {i+1}/{len(raw_claims)}: *{query[:70]}…*"
        )
        sources = tavily_search(query, max_results=4)
        enriched = {**claim_obj, "sources": sources}
        claims_with_evidence.append(enriched)
        time.sleep(0.4)  # polite rate limiting

    progress_bar.progress(1.0, text="✓ Web evidence collected for all claims")

    # ── STEP 4: BATCH GEMINI VERDICT ─────────
    with st.spinner("Analysing evidence and generating verdicts…"):
        verdicts = gemini_verify_batch(claims_with_evidence)

    # Build verdict lookup by index
    verdict_map: dict[int, dict] = {}
    for v in verdicts:
        try:
            verdict_map[int(v["index"])] = v
        except (KeyError, ValueError, TypeError):
            pass

    # ── STEP 5: TRUST SCORE ───────────────────
    verified_count = sum(1 for v in verdicts if v.get("verdict", "").upper() == "VERIFIED")
    inaccurate_count = sum(1 for v in verdicts if v.get("verdict", "").upper() == "INACCURATE")
    false_count = sum(1 for v in verdicts if v.get("verdict", "").upper() == "FALSE")

    trust_score = max(0, 100 - (false_count * 20) - (inaccurate_count * 10))
    score_color = (
        "var(--accent)" if trust_score >= 75
        else "var(--warn)" if trust_score >= 45
        else "var(--danger)"
    )

    section_divider("Verification Report")

    st.markdown(f"""
    <div class="score-card">
      <div>
        <div class="score-number" style="color:{score_color}">{trust_score}<span style="font-size:1.5rem;color:var(--muted)">/100</span></div>
        <div class="score-label">Document Trust Score</div>
      </div>
      <div class="score-pills">
        <span class="pill pill-v">✓ {verified_count} Verified</span>
        <span class="pill pill-i">⚠ {inaccurate_count} Inaccurate</span>
        <span class="pill pill-f">✗ {false_count} False</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── STEP 6: GROUPED OUTPUT BY SECTION ─────
    sections: dict[str, list] = {}
    for i, claim_obj in enumerate(claims_with_evidence, 1):
        sec = claim_obj.get("section", "General")
        if sec not in sections:
            sections[sec] = []
        verdict_obj = verdict_map.get(i, {"verdict": "FALSE", "reason": "Could not verify.", "real_fact": "N/A"})
        sections[sec].append((i, claim_obj, verdict_obj))

    for sec_name, items in sections.items():
        # Section header
        sec_verified = sum(1 for _, _, v in items if v.get("verdict", "").upper() == "VERIFIED")
        sec_total = len(items)
        sec_pct = int(sec_verified / sec_total * 100) if sec_total else 0

        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
                    background:var(--surface);border:1px solid var(--border);
                    border-radius:10px;padding:0.7rem 1.2rem;margin:1.2rem 0 0.5rem">
          <span style="font-family:'Syne',sans-serif;font-weight:700;font-size:1rem">{sec_name}</span>
          <span style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted)">
            {sec_verified}/{sec_total} verified · {sec_pct}% accuracy
          </span>
        </div>
        """, unsafe_allow_html=True)

        for idx, claim_obj, verdict_obj in items:
            render_claim_card(idx, claim_obj, verdict_obj)

    # ── FOOTER ────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center;margin-top:3rem;padding-top:2rem;border-top:1px solid var(--border)">
      <p style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted)">
        FactGuard · Powered by Gemini + Tavily · {len(raw_claims)} claims scanned · Trust Score {trust_score}/100
      </p>
    </div>
    """, unsafe_allow_html=True)