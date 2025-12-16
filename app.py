import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# --- SETUP ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Missing API Key. Please add it to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- SESSION STATE ---
if 'history' not in st.session_state:
    st.session_state.history = []

# --- APP UI ---
# This sets the browser tab name
st.set_page_config(page_title="Samaira's Books", page_icon="📚")

# SIDEBAR: BOOKSHELF
with st.sidebar:
    st.header(f"📚 Stack ({len(st.session_state.history)})")
    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()
    
    # Download Button
    if st.session_state.history:
        text_data = "SAMAIRA'S BOOK LIST:\n\n"
        for b in st.session_state.history:
            text_data += f"- {b['title']} ({b['verdict']})\n"
        st.download_button("📥 Save List", text_data, "samaira_books.txt")

    # List items
    for book in st.session_state.history:
        emoji = "✅" if "Green" in book['verdict'] else "⚠️"
        if "Red" in book['verdict']: emoji = "❌"
        with st.expander(f"{emoji} {book['title']}"):
            st.caption(book['author'])
            st.write(book['one_line_verdict'])

# MAIN PAGE
# --- UPDATED TITLE HERE ---
st.title("📚 Can Samaira read this book?")

col1, col2 = st.columns([2,1])
with col2:
    # Default is 12, but you can change it if needed
    target_age = st.number_input("Age", 5, 18, 12)

# Camera Input
img_file = st.camera_input(f"Scan book cover")

if img_file:
    image = Image.open(img_file)
    
    # We use a container so we can display the chat cleanly below the report
    report_container = st.container()
    
    # LOGIC: Only run the heavy AI analysis if we haven't already done it for this specific photo
    # This prevents the app from "re-reading" the book every time you type a chat message.
    if "current_img_id" not in st.session_state or st.session_state.current_img_id != img_file.file_id:
        with st.spinner("Checking if this is good for Samaira..."):
            try:
                prompt = f"""
                Analyze this book cover. The reader is a {target_age}-year-old girl named Samaira.
                
                Return valid JSON:
                {{
                    "title": "Title",
                    "author": "Author",
                    "series": "Series Info (e.g. Book 2 of 5)",
                    "verdict": "Green/Yellow/Red",
                    "one_line_verdict": "Short summary decision.",
                    "ratings": {{ "violence": "0-5", "sex": "0-5", "language": "0-5", "role_models": "0-5" }},
                    "details": "Detailed parents guide.",
                    "plot": "Plot summary."
                }}
                """
                response = model.generate_content([prompt, image])
                raw_text = response.text.replace("```json", "").replace("```", "").
