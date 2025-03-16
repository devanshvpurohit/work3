import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
import pandas as pd
import PyPDF2
import plotly.express as px
import streamlit_authenticator as stauth
from datetime import datetime
import yaml
import gspread
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

# Load env variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash"")

# Streamlit config
st.set_page_config(page_title="Aha! Rights Manager", layout="wide")
st.title("🎬 Aha! Content Rights Compliance Dashboard")

# --- Authentication Setup ---
with open("credentials.yaml") as file:
    config = yaml.safe_load(file)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

name, auth_status, username = authenticator.login("Login", "main")

if auth_status:
    authenticator.logout("Logout", "sidebar")

    # --- Connect to Google Sheet ---
    @st.cache_resource
    def connect_gsheet():
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gspread-cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("AhaContractLogs").sheet1
        return sheet

    sheet = connect_gsheet()

    # --- Upload Contract ---
    uploaded_file = st.file_uploader("📁 Upload Licensing Contract (.txt or .pdf)", type=["txt", "pdf"])
    contract_text = ""

    if uploaded_file:
        if uploaded_file.name.endswith(".txt"):
            contract_text = uploaded_file.read().decode("utf-8")
        elif uploaded_file.name.endswith(".pdf"):
            reader = PyPDF2.PdfReader(uploaded_file)
            for page in reader.pages:
                contract_text += page.extract_text()

        st.subheader("📄 Contract Preview")
        st.text_area("Raw Text", contract_text[:3000], height=250)

        if st.button("🧠 Analyze Contract"):
            with st.spinner("Calling Gemini..."):
                prompt = f"""
You are an AI assistant helping an OTT platform (Aha). Analyze the contract below and extract:
- Agreement type
- Duration with dates
- Territory
- Rights granted
- Termination & renewal
- Compliance risks
Return output in bullet format with key alerts.

Contract:
"""
{contract_text}
"""
"""
                result = model.generate_content(prompt)
                st.success("✅ Analysis Complete")
                st.markdown(result.text)

                # Renewal dates
                renewal_prompt = f"Extract any dates (like end/renewal/expiry) in YYYY-MM-DD format only from:\n{contract_text}"
                dates = model.generate_content(renewal_prompt).text
                st.info(f"📅 Dates Mentioned: {dates}")

                # Clause search
                st.markdown("---")
                st.subheader("🔍 Search for Specific Clauses")
                query = st.text_input("Enter a clause to search (e.g., 'termination')")
                if query:
                    matches = [line for line in contract_text.split('\n') if query.lower() in line.lower()]
                    if matches:
                        st.success(f"Found {len(matches)} matching clauses")
                        for m in matches:
                            st.markdown(f"- {m.strip()}")
                    else:
                        st.warning("No matching clauses found.")

                # Summary pie chart
                st.markdown("---")
                st.subheader("📊 Contract Visual Summary")
                labels = ["Exclusive", "Non-Exclusive", "Streaming", "Download", "Theatrical", "Worldwide", "India Only"]
                data = {"Clause": labels, "Count": [1 if label.lower() in contract_text.lower() else 0 for label in labels]}
                df = pd.DataFrame(data)
                fig = px.pie(df[df["Count"] > 0], names="Clause", values="Count", title="Content Rights Summary")
                st.plotly_chart(fig)

                # Log to Google Sheets
                existing_data = pd.DataFrame(sheet.get_all_records())
                new_row = {
                    "Filename": uploaded_file.name,
                    "Uploaded By": name,
                    "Upload Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Agreement Type": "Exclusive" if "exclusive" in contract_text.lower() else "Non-Exclusive",
                    "Territory": "India" if "india" in contract_text.lower() else "Worldwide",
                    "Rights": ", ".join([r for r in ["streaming", "download", "theatrical"] if r in contract_text.lower()]),
                    "Renewal Dates": dates.strip(),
                    "Gemini Summary": result.text.strip()
                }
                updated_df = existing_data.append(new_row, ignore_index=True)
                set_with_dataframe(sheet, updated_df)
                st.success("📊 Analysis stored in Google Sheet!")

    # --- Sidebar Log Viewer ---
    if st.sidebar.checkbox("📜 View & Filter Contract Log"):
        sheet = connect_gsheet()
        log_df = pd.DataFrame(sheet.get_all_records())

        contract_filter = st.sidebar.text_input("🔍 Filter by filename")
        date_filter = st.sidebar.date_input("📅 Uploaded after", value=datetime(2024, 1, 1))

        if contract_filter:
            log_df = log_df[log_df["Filename"].str.contains(contract_filter, case=False)]

        if "Upload Date" in log_df.columns:
            log_df["Upload Date"] = pd.to_datetime(log_df["Upload Date"])
            log_df = log_df[log_df["Upload Date"] >= pd.to_datetime(date_filter)]

        st.subheader("🧾 Filtered Contracts Log")
        st.dataframe(log_df, use_container_width=True)

        # Auto-expiry
        st.subheader("⚠️ Expired or Expiring Contracts")
        def parse_date(d):
            try:
                return pd.to_datetime(d)
            except:
                return None

        log_df["RenewalDateParsed"] = log_df["Renewal Dates"].apply(parse_date)
        today = pd.to_datetime("today")
        expiring_soon = log_df[log_df["RenewalDateParsed"].notnull() & (log_df["RenewalDateParsed"] <= today + pd.Timedelta(days=30))]

        if not expiring_soon.empty:
            st.warning("These contracts are expiring soon or already expired:")
            st.dataframe(expiring_soon[["Filename", "Renewal Dates", "Upload Date"]])
        else:
            st.success("✅ No contracts expiring in the next 30 days.")

        st.sidebar.markdown("---")
        st.sidebar.download_button(
            "⬇️ Download Log as CSV",
            data=log_df.to_csv(index=False),
            file_name="aha_contract_logs.csv",
            mime="text/csv"
        )

elif auth_status is False:
    st.error("Incorrect username or password.")
elif auth_status is None:
    st.warning("Please enter your credentials.")
