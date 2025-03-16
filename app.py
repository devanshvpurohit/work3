import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import pandas as pd
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import PyPDF2
import yaml
import streamlit_authenticator as stauth
import plotly.express as px

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Load authentication config
with open("credentials.yaml") as file:
    config = yaml.safe_load(file)

authenticator = stauth.Authenticate(
    config["credentials"], config["cookie"]["name"],
    config["cookie"]["key"], config["cookie"]["expiry_days"]
)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")
elif authentication_status:

    st.sidebar.title(f"Welcome, {name}")
    authenticator.logout("Logout", "sidebar")

    st.title("📺 Aha Content Rights & Licensing AI")

    # Connect to Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("gspread-cred.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("YOUR_SHEET_ID").sheet1  # Replace with your actual Sheet ID

    # Initialize Gemini Model
    model = genai.GenerativeModel("gemini-pro")

    def extract_text_from_pdf(file):
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text

    def analyze_contract(text, model):
        prompt = f"Analyze the following contract:\n\n{text}\n\nHighlight key clauses, renewal terms, rights granted, restrictions, and expiration dates."
        result = model.generate_content(prompt)
        return result.text

    def log_to_sheet(filename, analysis, upload_date):
        sheet.append_row([filename, analysis, upload_date])

    def get_sheet_data():
        data = sheet.get_all_records()
        return pd.DataFrame(data)

    st.subheader("Upload Contract")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")

    if uploaded_file:
        text = extract_text_from_pdf(uploaded_file)
        analysis = analyze_contract(text, model)
        st.subheader("📄 AI Contract Analysis")
        st.write(analysis)

        if st.button("Save to Log"):
            today = datetime.date.today().strftime("%Y-%m-%d")
            log_to_sheet(uploaded_file.name, analysis, today)
            st.success("Logged to Google Sheets ✅")

    st.subheader("📚 Contract History")

    df = get_sheet_data()

    # Search and filters
    with st.expander("🔍 Search / Filter"):
        name_filter = st.text_input("Filter by Filename")
        date_filter = st.date_input("Filter by Upload Date", value=None)

        if name_filter:
            df = df[df["filename"].str.contains(name_filter, case=False)]
        if date_filter:
            df = df[df["upload_date"] == date_filter.strftime("%Y-%m-%d")]

    # Auto-expiry tagging (example logic)
    df["Status"] = df["analysis"].apply(lambda x: "⚠️ Expired" if "expired" in x.lower() else "✅ Active")

    st.dataframe(df)

    st.download_button("📥 Export Log to CSV", df.to_csv(index=False), file_name="contract_log.csv")

    # Visual summary
    st.subheader("📊 Summary Visualization")
    status_counts = df["Status"].value_counts().reset_index()
    fig = px.pie(status_counts, names="index", values="Status", title="Contract Status Overview")
    st.plotly_chart(fig)
