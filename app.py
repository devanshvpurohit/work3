import streamlit as st
import google.generativeai as genai
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import uuid
import json

# Load environment variables
load_dotenv()
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-flash")

# Simulated storage for version control and calendar events
CONTRACTS_DB = {}
EVENTS_DB = []

st.set_page_config(page_title="📜 LEXIGUARD359", layout="wide")
st.markdown("""
    <style>
    .big-font { font-size:22px !important; }
    .highlight { background-color: #ffe4b5; padding: 0.5em; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚖️ LEXIGUARD359: AI-Powered Compliance & Risk Management")
st.markdown("""
    <p class='big-font'>Ensuring Legal Compliance & Risk Mitigation with AI-Powered Contract Analysis.</p>
    <hr>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📄 Upload Legal Contract (.pdf/.txt)", type=["txt", "pdf"])

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
    You are an AI legal assistant. Extract and structure the following:
    1. **Compliance Summary**: Overall compliance assessment.
    2. **Clause Risk Heatmap**: Identify high-risk clauses and highlight them.
    3. **Risk Trends Overview**: Show trends based on prior analyses.
    4. **Category-wise Clause Risk Analysis**: Break down risks by clause categories (e.g., termination, liability, exclusivity).
    Return the results in structured JSON format.

    Contract:
    {text}
    """
    response = model.generate_content(prompt)
    try:
        return json.loads(response.text)  # Ensure structured JSON output
    except json.JSONDecodeError:
        return {"error": "Invalid response format from AI model."}

def add_to_calendar(title, expiry_date):
    EVENTS_DB.append({"event": title, "date": expiry_date})
    st.success(f"📅 Alert set for {title} expiring on {expiry_date}")

def simulate_risk_score(analysis):
    high_risk_clauses = len([clause for clause in analysis.get("Clause Risk Heatmap", []) if clause["risk_level"] == "high"])
    return min(100, 50 + high_risk_clauses * 10)

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

        st.subheader("📜 Compliance Summary")
        st.markdown(f"<div class='highlight'>{analysis.get('Compliance Summary', 'No summary available.')}</div>", unsafe_allow_html=True)

        st.subheader("🔥 Clause Risk Heatmap")
        for clause in analysis.get("Clause Risk Heatmap", []):
            st.warning(f"⚠️ {clause['clause']}: {clause['risk_level']}")

        st.subheader("📊 Risk Trends Overview")
        st.line_chart([simulate_risk_score(a["analysis"]) for a in CONTRACTS_DB.values()])

        st.subheader("📌 Category-wise Clause Risk Analysis")
        for category, risks in analysis.get("Category-wise Clause Risk Analysis", {}).items():
            st.write(f"### {category}")
            for risk in risks:
                st.write(f"- {risk}")

        # Risk Score
        risk_score = simulate_risk_score(analysis)
        st.metric(label="⚠️ Legal Risk Score", value=f"{risk_score}%")

        # Set Alert
        expiry_input = st.date_input("📆 Enter License Expiry Date to Schedule Alert")
        if st.button("Set Renewal Alert"):
            add_to_calendar(uploaded_file.name, expiry_input)

        # Version control view
        st.subheader("🗂️ Version Control")
        for cid, data in CONTRACTS_DB.items():
            st.markdown(f"**Version ID**: `{cid}` | ⏰ Uploaded at: `{data['timestamp']}`")
            with st.expander("View Analysis"):
                st.code(json.dumps(data["analysis"], indent=2), language="json")

# Calendar View
st.sidebar.subheader("📅 Upcoming Expiry Alerts")
for event in EVENTS_DB:
    st.sidebar.warning(f"🔔 {event['event']} → {event['date']}")
