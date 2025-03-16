import streamlit as st
import google.generativeai as genai
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import uuid

# Load environment variables
load_dotenv()
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-pro")

# Simulated storage for version control and calendar events
CONTRACTS_DB = {}
EVENTS_DB = []

st.set_page_config(page_title="📺 Aha Rights Manager AI", layout="wide")
st.markdown("""
    <style>
    .big-font { font-size:22px !important; }
    .highlight { background-color: #ffe4b5; padding: 0.5em; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎬 Aha AI Rights & Licensing Manager")
st.markdown("""
    <p class='big-font'>Empowering content compliance with AI — Analyze, Track, and Alert with Ease.</p>
    <hr>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📄 Upload Licensing Contract (.pdf/.txt)", type=["txt", "pdf"])

# Filters
with st.sidebar:
    st.header("🔎 Search & Filter")
    party_filter = st.text_input("Filter by Party")
    region_filter = st.text_input("Filter by Region")
    type_filter = st.selectbox("Contract Type", ["All", "Original", "Exclusive", "Acquisition"])
    date_filter = st.date_input("Filter by Start Date")

def extract_text(file):
    if file.name.endswith(".txt"):
        return file.read().decode("utf-8")
    elif file.name.endswith(".pdf"):
        pdf = PdfReader(file)
        return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    return ""

def analyze_contract(text):
    prompt = f"""
    You are an AI contract assistant for Aha OTT. 
    Extract the following from the contract:
    - Title
    - Parties Involved
    - License Duration, Start and Expiry Date
    - Regions granted
    - Type (Original, Exclusive, Acquisition)
    - Exclusivity
    - Termination Conditions
    - Risky Clauses or Compliance Flags
    Return the result in bullet format.

    Contract:
    {text}
    """
    response = model.generate_content(prompt)
    return response.text

def add_to_calendar(title, expiry_date):
    EVENTS_DB.append({"event": title, "date": expiry_date})
    st.success(f"📅 Alert set for {title} expiring on {expiry_date}")

def simulate_risk_score(analysis):
    return 87 if "termination" in analysis.lower() else 45

if uploaded_file:
    with st.spinner("🔍 Analyzing contract..."):
        contract_text = extract_text(uploaded_file)
        analysis = analyze_contract(contract_text)
        contract_id = str(uuid.uuid4())
        CONTRACTS_DB[contract_id] = {
            "text": contract_text,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }

        st.subheader("📑 Clause-Based Analysis")
        st.markdown(f"<div class='highlight'>{analysis}</div>", unsafe_allow_html=True)

        # Risk Score
        risk_score = simulate_risk_score(analysis)
        st.metric(label="⚖️ Legal Risk Score", value=f"{risk_score}%")

        # Set Alert
        expiry_input = st.date_input("📆 Enter License Expiry Date to Schedule Alert")
        if st.button("Set Renewal Alert"):
            add_to_calendar(uploaded_file.name, expiry_input)

        # Version control view
        st.subheader("🗂️ Version Control")
        for cid, data in CONTRACTS_DB.items():
            st.markdown(f"**Version ID**: `{cid}` | ⏰ Uploaded at: `{data['timestamp']}`")
            with st.expander("View Analysis"):
                st.code(data["analysis"], language="markdown")

# Calendar View
st.sidebar.subheader("📅 Upcoming Expiry Alerts")
for event in EVENTS_DB:
    st.sidebar.warning(f"🔔 {event['event']} → {event['date']}")
