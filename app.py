import streamlit as st
import google.generativeai as genai

# 🔹 Quick Fix: Hardcode the API key (Not recommended for production)
API_KEY = "AIzaSyAW_b4mee9l8eP931cqd9xqErHV34f7OEw"

# Configure Gemini API
genai.configure(api_key=API_KEY)

# Define the model (using Gemini 1.5 Flash)
model = genai.GenerativeModel("gemini-1.5-flash")

def get_cricket_stats(player_name):
    prompt = (
        f"Provide a detailed cricket statistics summary for {player_name}. "
        "Include:\n- Batting average\n- Bowling average\n- Total runs\n- Total wickets\n"
        "Format it as a cricket card with key stats and major achievements."
    )
    try:
        response = model.generate_content(prompt)
        return response.text if response else "No data available."
    except Exception as e:
        return f"⚠️ Error fetching stats: {str(e)}"

# Streamlit UI
st.title("🏏 Cricket Player Stats Viewer")

player_name = st.text_input("Enter Player Name:")

if st.button("Get Stats") and player_name:
    stats = get_cricket_stats(player_name)
    st.markdown(f"### 📊 Stats for {player_name}")
    st.write(stats)
