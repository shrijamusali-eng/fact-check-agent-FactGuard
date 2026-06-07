import os
import re
import json
import time
import io
import fitz          # PyMuPDF
import pdfplumber
import streamlit as st
from dotenv import load_dotenv
from tavily import TavilyClient
from groq import Groq

# ─────────────────────────────────────────────────────────────
# ENV & API SETUP
# ─────────────────────────────────────────────────────────────
load_dotenv()

GROQ_API_KEY   = st.secrets.get("GROQ_API_KEY",   os.getenv("GROQ_API_KEY",   ""))
TAVILY_API_KEY = st.secrets.get("TAVILY_API_KEY",  os.getenv("TAVILY_API_KEY", ""))

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
tavily      = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

# Groq free-tier model fallback chain
# llama-3.3-70b-versatile  → best quality, ~6 k TPM free
# llama3-70b-8192          → solid fallback
# llama3-8b-8192           → fastest / lightest, last resort
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
]


# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
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
    --bg:         #0b0d12;
    --surface:    #13161f;
    --border:     #1e2330;
    --accent:     #4fffb0;
    --accent2:    #7c6aff;
    --warn:       #ffcc44;
    --danger:     #ff4d6d;
    --text:       #e8eaf0;
    --muted:      #6b7280;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color:      var(--text) !important;
    font-family: 'DM Sans', sans-serif;
}
[data-testid="stHeader"]  { background: transparent !important; }
[data-testid="stSidebar"] { background: var(--surface) !important; }
.block-container          { padding: 2rem 3rem !important; max-width: 1100px !important; }

/* HERO */
.hero { text-align:center; padding:3.5rem 1rem 2.5rem; }
.hero-badge {
    display:inline-block; font-family:'DM Mono',monospace; font-size:0.7rem;
    letter-spacing:0.2em; text-transform:uppercase; color:var(--accent);
    border:1px solid var(--accent); padding:4px 14px; border-radius:20px; margin-bottom:1.2rem;
}
.hero h1 {
    font-family:'Syne',sans-serif; font-size:clamp(2.4rem,5vw,4rem); font-weight:800;
    line-height:1.1; margin:0 0 0.8rem;
    background:linear-gradient(135deg,#e8eaf0 0%,var(--accent) 60%,var(--accent2) 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.hero p { font-size:1.05rem; color:var(--muted); max-width:520px; margin:0 auto; line-height:1.7; }

/* UPLOAD ZONE */
[data-testid="stFileUploader"] {
    background:var(--surface) !important; border:1.5px dashed var(--border) !important;
    border-radius:12px !important; padding:1rem !important; transition:border-color 0.2s;
}
[data-testid="stFileUploader"]:hover { border-color:var(--accent) !important; }
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploaderDropzoneInstructions"] p { color:#111 !important; }
[data-testid="stFileUploaderDropzoneInstructions"] svg { fill:#111 !important; stroke:#111 !important; }
[data-testid="stFileUploaderDropzone"] button { color:#111 !important; border-color:#333 !important; }

/* DIVIDER */
.section-divider { display:flex; align-items:center; gap:0.8rem; margin:2rem 0 1.5rem; }
.section-divider .label {
    font-family:'Syne',sans-serif; font-size:0.75rem; font-weight:700;
    letter-spacing:0.15em; text-transform:uppercase; color:var(--muted); white-space:nowrap;
}
.section-divider .line { flex:1; height:1px; background:var(--border); }

/* SCORE CARD */
.score-card {
    background:var(--surface); border:1px solid var(--border); border-radius:14px;
    padding:1.6rem 2rem; display:flex; align-items:center;
    justify-content:space-between; margin-bottom:2rem; flex-wrap:wrap; gap:1rem;
}
.score-number { font-family:'Syne',sans-serif; font-size:3.5rem; font-weight:800; line-height:1; }
.score-label  { font-size:0.78rem; letter-spacing:0.12em; text-transform:uppercase; color:var(--muted); margin-top:4px; font-family:'DM Mono',monospace; }
.score-pills  { display:flex; gap:0.6rem; flex-wrap:wrap; }
.pill         { font-family:'DM Mono',monospace; font-size:0.75rem; padding:4px 12px; border-radius:20px; border:1px solid; }
.pill-v       { color:var(--accent);  border-color:var(--accent);  background:rgba(79,255,176,0.07); }
.pill-i       { color:var(--warn);    border-color:var(--warn);    background:rgba(255,204,68,0.07); }
.pill-f       { color:var(--danger);  border-color:var(--danger);  background:rgba(255,77,109,0.07); }

/* CLAIM CARD */
.claim-card { border-radius:12px; border:1px solid var(--border); margin-bottom:1.2rem; overflow:hidden; transition:border-color 0.2s; }
.claim-card:hover { border-color:#2e3448; }
.claim-header { display:flex; align-items:flex-start; gap:1rem; padding:1.1rem 1.4rem; }
.claim-index  { font-family:'DM Mono',monospace; font-size:0.7rem; color:var(--muted); min-width:2rem; padding-top:3px; }
.claim-text   { font-size:0.97rem; font-weight:500; line-height:1.5; flex:1; color:var(--text); }
.verdict-chip { font-family:'DM Mono',monospace; font-size:0.68rem; font-weight:700; letter-spacing:0.1em; padding:4px 10px; border-radius:6px; white-space:nowrap; margin-top:2px; }
.chip-v { background:rgba(79,255,176,0.12);  color:var(--accent);  border:1px solid var(--accent); }
.chip-i { background:rgba(255,204,68,0.12);  color:var(--warn);    border:1px solid var(--warn); }
.chip-f { background:rgba(255,77,109,0.12);  color:var(--danger);  border:1px solid var(--danger); }
.claim-body   { padding:0.6rem 1.4rem 1.1rem; border-top:1px solid var(--border); }
.detail-row   { display:flex; gap:0.5rem; margin-bottom:0.5rem; align-items:flex-start; }
.detail-key   { font-family:'DM Mono',monospace; font-size:0.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.08em; min-width:80px; padding-top:2px; }
.detail-val   { font-size:0.88rem; color:#c8cadc; line-height:1.55; flex:1; }
.real-fact-val { color:var(--accent); font-weight:500; }

/* TEXT PREVIEW */
.text-preview {
    background:var(--surface); border:1px solid var(--border); border-radius:10px;
    padding:1.2rem 1.4rem; font-family:'DM Mono',monospace; font-size:0.82rem;
    color:var(--muted); line-height:1.65; white-space:pre-wrap; max-height:220px; overflow-y:auto;
}

/* STAT BOX */
.stat-box { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:1rem 1.4rem; flex:1; min-width:130px; }
.stat-box .num { font-family:'Syne',sans-serif; font-size:1.8rem; font-weight:700; line-height:1; }
.stat-box .lbl { font-size:0.72rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.1em; font-family:'DM Mono',monospace; margin-top:4px; }

/* QUOTA BANNER */
.quota-info { background:#0d1a2a; border:1px solid #1a4a7a; border-radius:10px; padding:0.9rem 1.3rem; margin-bottom:1rem; }

/* BUTTONS & MISC */
.stSpinner > div { border-top-color:var(--accent) !important; }
.stButton > button {
    background:var(--accent) !important; color:#000 !important;
    font-family:'Syne',sans-serif !important; font-weight:700 !important;
    border:none !important; border-radius:8px !important; padding:0.55rem 1.6rem !important;
    cursor:pointer !important; transition:opacity 0.2s !important;
}
.stButton > button:hover { opacity:0.85 !important; }
[data-testid="stExpander"] { background:#0e1017 !important; border:1px solid var(--border) !important; border-radius:8px !important; }
.stSuccess, .stWarning, .stError { display:none !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def section_divider(label: str):
    st.markdown(f"""
    <div class="section-divider">
      <span class="line"></span><span class="label">{label}</span><span class="line"></span>
    </div>""", unsafe_allow_html=True)


def groq_generate(prompt: str, label: str = "Groq") -> str:
    """
    Walk GROQ_MODELS fallback chain.
    - 429 / rate-limit → back off 10s then retry same model once, then move on
    - Other errors     → try next model immediately
    """
    if not groq_client:
        raise RuntimeError("No Groq API key configured.")

    for model_name in GROQ_MODELS:
        for attempt in range(2):
            try:
                response = groq_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4000,
                    temperature=0.1,
                )
                return response.choices[0].message.content.strip()

            except Exception as e:
                err_str = str(e).lower()

                is_rate_limit = "429" in err_str or "rate" in err_str or "limit" in err_str
                is_unavailable = "503" in err_str or "500" in err_str or "model" in err_str

                if is_rate_limit and attempt == 0:
                    st.toast(f"⏳ Rate-limited on {model_name} — waiting 10s…", icon="⚠️")
                    time.sleep(10)
                    continue  # retry same model after backoff

                elif is_unavailable or is_rate_limit:
                    st.toast(f"⚡ {model_name} unavailable — trying next model…", icon="⚠️")
                    break  # next model

                else:
                    raise

    raise RuntimeError(
        "⚠️ All Groq models are unavailable right now.\n\n"
        "**Likely cause:** free-tier TPM quota exhausted.\n\n"
        "**Fix options:**\n"
        "1. **Wait 1 minute** — Groq TPM limits reset per minute\n"
        "2. Reduce the claim cap in the sidebar (fewer claims = fewer tokens)\n"
        "3. Try again — Groq recovers very quickly"
    )


def extract_text_pymupdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages_text = []
    for page_num, page in enumerate(doc, 1):
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))
        page_text = f"\n[PAGE {page_num}]\n"
        page_text += " ".join(b[4].strip() for b in blocks if b[4].strip())
        pages_text.append(page_text)
    return "\n\n".join(pages_text)


def extract_tables_pdfplumber(file_bytes: bytes) -> list[str]:
    tables = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    rows = [
                        " | ".join(str(cell or "").strip() for cell in row)
                        for row in table if row
                    ]
                    tables.append("\n".join(rows))
    except Exception:
        pass
    return tables


def extract_claims(text: str, table_context: str) -> list[dict]:
    prompt = f"""
You are a meticulous fact-extraction expert. Extract ALL verifiable factual claims from the text.

A verifiable claim includes: statistics/percentages, named dates/years, financial figures,
named companies/products with attributed facts, technical specs, rankings with specific numbers.

INSTRUCTIONS:
1. Extract EVERY such claim — target 8–14 if present.
2. Identify section/topic area for each claim.
3. Identify type: STATISTIC | DATE | FINANCIAL | TECHNICAL | RANKING | OTHER
4. Return ONLY a valid JSON array. No markdown, no backticks, no preamble.

FORMAT:
[
  {{"claim": "exact claim text", "section": "section label", "type": "STATISTIC"}},
  ...
]

DOCUMENT TEXT:
{text[:10000]}

TABLE DATA (if any):
{table_context[:2000]}
"""
    try:
        raw = groq_generate(prompt, label="Claim extraction")
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
        raw = re.sub(r"```$",         "", raw, flags=re.MULTILINE).strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except RuntimeError as e:
        st.error(str(e))
    except Exception as e:
        st.error(f"Claim extraction error: {e}")
    return []


def tavily_search(query: str, max_results: int = 4) -> list[dict]:
    if not tavily:
        return [{"title": "Tavily not configured", "snippet": "No TAVILY_API_KEY set.", "url": ""}]
    try:
        result = tavily.search(query=query, max_results=max_results)
        return [
            {
                "title":   r.get("title", ""),
                "snippet": r.get("content", "")[:400],
                "url":     r.get("url", ""),
            }
            for r in result.get("results", [])
        ]
    except Exception as e:
        return [{"title": "Search Error", "snippet": str(e), "url": ""}]


def verify_batch(claims_with_evidence: list[dict]) -> list[dict]:
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
- "reason": 2–3 sentence explanation grounded in the evidence
- "real_fact": if INACCURATE or FALSE, write the correct value from evidence. If VERIFIED, write "N/A".

VERDICTS:
- VERIFIED   : Evidence strongly supports the claim.
- INACCURATE : Partially true, outdated, or wrong numbers.
- FALSE      : Directly contradicted or entirely unsupported.

Return ONLY a JSON array. No markdown, no extra text, no preamble.

CLAIMS AND EVIDENCE:
{bundle}
"""
    try:
        raw = groq_generate(prompt, label="Verdict generation")
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
        raw = re.sub(r"```$",         "", raw, flags=re.MULTILINE).strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except RuntimeError as e:
        st.error(str(e))
    except Exception as e:
        st.error(f"Verification error: {e}")
    return []


def render_claim_card(idx: int, claim_obj: dict, verdict_obj: dict):
    verdict   = verdict_obj.get("verdict",   "FALSE").upper()
    reason    = verdict_obj.get("reason",    "—")
    real_fact = verdict_obj.get("real_fact", "N/A")
    section   = claim_obj.get("section", "")
    ctype     = claim_obj.get("type", "")
    sources   = claim_obj.get("sources", [])

    chip_class  = {"VERIFIED": "chip-v", "INACCURATE": "chip-i"}.get(verdict, "chip-f")
    card_border = {"VERIFIED": "border-color:#1a3d2b;", "INACCURATE": "border-color:#3d2e00;"}.get(verdict, "border-color:#3d0015;")

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
    if ctype:
        meta_tags += f'<span class="pill" style="font-size:0.65rem;margin-top:2px;color:var(--muted);border-color:var(--border)">{ctype}</span>'

    st.markdown(f"""
    <div class="claim-card" style="{card_border}">
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
                st.markdown(
                    f"**{j}. [{s.get('title','Source')}]({s.get('url','')})**  \n"
                    f"<span style='font-size:0.83rem;color:#7a8099'>{s.get('snippet','')}</span>",
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <div class="hero-badge">⬡ AI-Powered Truth Layer</div>
  <h1>FactGuard</h1>
  <p>Upload any PDF. We extract every verifiable claim, cross-reference it against live web data,
     and flag exactly what's wrong — with the correct facts.</p>
</div>
""", unsafe_allow_html=True)

# ── API key guard
missing = []
if not GROQ_API_KEY:   missing.append("GROQ_API_KEY")
if not TAVILY_API_KEY: missing.append("TAVILY_API_KEY")
if missing:
    st.markdown(f"""
    <div style="background:#1f0a00;border:1px solid #7a3800;border-radius:10px;padding:1rem 1.4rem;margin-bottom:1.5rem">
      <span style="color:#ff8844;font-family:'DM Mono',monospace;font-size:0.85rem">
        ⚠ Missing API keys: <b>{', '.join(missing)}</b><br>
        Add them to <code>.streamlit/secrets.toml</code> or your environment.
      </span>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── Sidebar settings
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    max_claims = st.slider(
        "Max claims to verify",
        min_value=3, max_value=20, value=10,
        help="Lower this if you hit rate limits. Each claim = 1 Tavily search + tokens.",
    )
    st.markdown("""
    <div class="quota-info">
      <span style="color:#5ba3d9;font-family:'DM Mono',monospace;font-size:0.75rem">
        <b>Groq free tier</b><br>
        llama-3.3-70b → primary ✓<br>
        llama3-70b    → fallback ✓<br>
        llama3-8b     → last resort ✓<br>
        Auto-fallback on 429 ✓<br>
        Resets every minute
      </span>
    </div>""", unsafe_allow_html=True)

# ── Upload
section_divider("Upload Document")
pdf_file = st.file_uploader(
    "Drop a PDF here or click to browse",
    type=["pdf"],
    help="Any PDF with factual claims — reports, marketing docs, whitepapers.",
)

if pdf_file:
    file_bytes = pdf_file.read()

    # ── STEP 1: Extract text
    section_divider("Document Parsing")
    with st.spinner("Extracting text with layout-aware parsing…"):
        full_text     = extract_text_pymupdf(file_bytes)
        tables        = extract_tables_pdfplumber(file_bytes)
        table_context = "\n\n".join(tables) if tables else ""

    col1, col2, col3 = st.columns(3)
    word_count = len(full_text.split())
    with col1:
        st.markdown(f'<div class="stat-box"><div class="num" style="color:var(--accent)">{word_count:,}</div><div class="lbl">Words Extracted</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-box"><div class="num" style="color:var(--accent2)">{len(tables)}</div><div class="lbl">Tables Found</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-box"><div class="num" style="color:#c8aaff">{len(full_text):,}</div><div class="lbl">Characters</div></div>', unsafe_allow_html=True)

    with st.expander("📄 Preview extracted text"):
        preview = full_text[:3000] + ("…" if len(full_text) > 3000 else "")
        st.markdown(f'<div class="text-preview">{preview}</div>', unsafe_allow_html=True)

    if table_context:
        with st.expander("📊 Preview extracted tables"):
            st.markdown(f'<div class="text-preview">{table_context[:2000]}</div>', unsafe_allow_html=True)

    # ── STEP 2: Extract claims
    section_divider("Claim Extraction")
    with st.spinner("Identifying all verifiable claims…"):
        raw_claims = extract_claims(full_text, table_context)

    if not raw_claims:
        st.markdown("""
        <div style="background:#1f0a00;border:1px solid #7a3800;border-radius:10px;padding:1rem 1.4rem">
          <span style="color:#ff8844;font-size:0.88rem">
            No verifiable claims could be extracted. The document may lack specific statistics,
            dates, or figures.
          </span>
        </div>""", unsafe_allow_html=True)
        st.stop()

    # Cap to avoid blowing quota
    if len(raw_claims) > max_claims:
        st.markdown(f"""
        <div style="background:#0d1a2a;border:1px solid #1a4a7a;border-radius:10px;padding:0.8rem 1.2rem;margin-bottom:0.5rem">
          <span style="color:#5ba3d9;font-family:'DM Mono',monospace;font-size:0.8rem">
            ℹ Found {len(raw_claims)} claims — verifying top {max_claims} to stay within quota.
            Adjust the cap in the sidebar ↙
          </span>
        </div>""", unsafe_allow_html=True)
        raw_claims = raw_claims[:max_claims]

    st.markdown(f"""
    <div style="background:rgba(79,255,176,0.05);border:1px solid rgba(79,255,176,0.2);border-radius:10px;padding:0.9rem 1.3rem;margin-bottom:0.5rem">
      <span style="color:var(--accent);font-family:'DM Mono',monospace;font-size:0.82rem">
        ✓ Isolated <b>{len(raw_claims)}</b> verifiable claims across
        <b>{len(set(c.get('section','') for c in raw_claims))}</b> topic sections
      </span>
    </div>""", unsafe_allow_html=True)

    with st.expander(f"🗂 Preview all {len(raw_claims)} extracted claims"):
        for i, c in enumerate(raw_claims, 1):
            st.markdown(f"**#{i:02d}** `{c.get('type','?')}` · *{c.get('section','')}*  \n{c['claim']}")
            st.divider()

    # ── STEP 3: Web search
    section_divider("Live Web Verification")
    progress_bar = st.progress(0, text="Initialising web search…")

    claims_with_evidence = []
    for i, claim_obj in enumerate(raw_claims):
        query = claim_obj["claim"][:120]
        progress_bar.progress(
            i / len(raw_claims),
            text=f"🔍 Searching claim {i+1}/{len(raw_claims)}: *{query[:70]}…*",
        )
        sources = tavily_search(query, max_results=4)
        claims_with_evidence.append({**claim_obj, "sources": sources})
        time.sleep(0.3)

    progress_bar.progress(1.0, text="✓ Web evidence collected for all claims")

    # ── STEP 4: Batch verdict
    with st.spinner("Analysing evidence and generating verdicts…"):
        verdicts = verify_batch(claims_with_evidence)

    if not verdicts:
        st.error(
            "Verdict generation failed — likely a rate-limit issue. "
            "Try reducing the claim cap in the sidebar, wait a minute, then retry."
        )
        st.stop()

    verdict_map: dict[int, dict] = {}
    for v in verdicts:
        try:
            verdict_map[int(v["index"])] = v
        except (KeyError, ValueError, TypeError):
            pass

    # ── STEP 5: Trust score
    verified_count   = sum(1 for v in verdicts if v.get("verdict","").upper() == "VERIFIED")
    inaccurate_count = sum(1 for v in verdicts if v.get("verdict","").upper() == "INACCURATE")
    false_count      = sum(1 for v in verdicts if v.get("verdict","").upper() == "FALSE")
    trust_score      = max(0, 100 - (false_count * 20) - (inaccurate_count * 10))
    score_color = (
        "var(--accent)"  if trust_score >= 75 else
        "var(--warn)"    if trust_score >= 45 else
        "var(--danger)"
    )

    section_divider("Verification Report")
    st.markdown(f"""
    <div class="score-card">
      <div>
        <div class="score-number" style="color:{score_color}">
          {trust_score}<span style="font-size:1.5rem;color:var(--muted)">/100</span>
        </div>
        <div class="score-label">Document Trust Score</div>
      </div>
      <div class="score-pills">
        <span class="pill pill-v">✓ {verified_count} Verified</span>
        <span class="pill pill-i">⚠ {inaccurate_count} Inaccurate</span>
        <span class="pill pill-f">✗ {false_count} False</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── STEP 6: Group by section
    sections: dict[str, list] = {}
    for i, claim_obj in enumerate(claims_with_evidence, 1):
        sec = claim_obj.get("section", "General")
        if sec not in sections:
            sections[sec] = []
        vobj = verdict_map.get(i, {"verdict": "FALSE", "reason": "Could not verify.", "real_fact": "N/A"})
        sections[sec].append((i, claim_obj, vobj))

    for sec_name, items in sections.items():
        sec_verified = sum(1 for _, _, v in items if v.get("verdict","").upper() == "VERIFIED")
        sec_total    = len(items)
        sec_pct      = int(sec_verified / sec_total * 100) if sec_total else 0

        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
                    background:var(--surface);border:1px solid var(--border);
                    border-radius:10px;padding:0.7rem 1.2rem;margin:1.2rem 0 0.5rem">
          <span style="font-family:'Syne',sans-serif;font-weight:700;font-size:1rem">{sec_name}</span>
          <span style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted)">
            {sec_verified}/{sec_total} verified · {sec_pct}% accuracy
          </span>
        </div>""", unsafe_allow_html=True)

        for idx, claim_obj, verdict_obj in items:
            render_claim_card(idx, claim_obj, verdict_obj)

    # ── Footer
    st.markdown(f"""
    <div style="text-align:center;margin-top:3rem;padding-top:2rem;border-top:1px solid var(--border)">
      <p style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted)">
        FactGuard · Powered by Groq + Tavily · {len(raw_claims)} claims scanned · Trust Score {trust_score}/100
      </p>
    </div>""", unsafe_allow_html=True)