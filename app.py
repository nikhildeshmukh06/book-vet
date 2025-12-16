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
st.set_page_config(page_title="Book Vet", page_icon="📚")

# SIDEBAR: BOOKSHELF
with st.sidebar:
    st.header(f"📚 Stack ({len(st.session_state.history)})")
    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()
    
    # Download Button
    if st.session_state.history:
        text_data = "MY BOOK LIST:\n\n"
        for b in st.session_state.history:
            text_data += f"- {b['title']} ({b['verdict']})\n"
        st.download_button("📥 Save List", text_data, "books.txt")

    # List items
    for book in st.session_state.history:
        emoji = "✅" if "Green" in book['verdict'] else "⚠️"
        if "Red" in book['verdict']: emoji = "❌"
        with st.expander(f"{emoji} {book['title']}"):
            st.caption(book['author'])
            st.write(book['one_line_verdict'])

# MAIN PAGE
st.title("📚 Parent Pal: Scanner")

col1, col2 = st.columns([2,1])
with col2:
    target_age = st.number_input("Age", 5, 18, 12)

# Camera Input
img_file = st.camera_input(f"Scan book for {target_age}-year-old")

if img_file:
    image = Image.open(img_file)
    
    # We use a container so we can display the chat cleanly below the report
    report_container = st.container()
    
    # Only run the heavy analysis if we haven't already done it for this specific image ID
    # (Streamlit reruns the whole script when you type in the chat box, so we need to cache the result)
    # We use the file ID to check if it's the same photo
    
    if "current_img_id" not in st.session_state or st.session_state.current_img_id != img_file.file_id:
        with st.spinner("Analyzing..."):
            try:
                prompt = f"""
                Analyze this book cover. Reader: {target_age}-year-old.
                
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
                raw_text = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(raw_text)
                
                # Save to session state so we don't re-analyze when chatting
                st.session_state.current_report = data
                st.session_state.current_img_id = img_file.file_id
                
                # Add to history if unique
                if not any(b['title'] == data['title'] for b in st.session_state.history):
                    st.session_state.history.append(data)
                    
            except Exception as e:
                st.error("Could not read cover. Please try again.")
                st.stop()

    # --- DISPLAY REPORT (From Memory) ---
    data = st.session_state.current_report
    
    with report_container:
        st.divider()
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(image, width=120, caption="Scanned")
        with c2:
            color = "green" if "Green" in data["verdict"] else "orange"
            if "Red" in data["verdict"]: color = "red"
            st.markdown(f":{color}[**VERDICT: {data['verdict']}**]")
            st.subheader(data["title"])
            st.caption(f"{data['author']} | {data['series']}")
            st.info(data["one_line_verdict"])

        st.markdown("### 📊 Ratings")
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**Violence:** {data['ratings']['violence']}/5")
            st.progress(int(data['ratings']['violence'])/5)
            st.write(f"**Language:** {data['ratings']['language']}/5")
            st.progress(int(data['ratings']['language'])/5)
        with col_b:
            st.write(f"**Role Models:** {data['ratings']['role_models']}/5")
            st.progress(int(data['ratings']['role_models'])/5)
            st.write(f"**Sex/Romance:** {data['ratings']['sex']}/5")
            st.progress(int(data['ratings']['sex'])/5)
            
        st.markdown("### 📝 Details")
        st.write(data["details"])

    # --- CHAT FEATURE ---
    st.divider()
    st.subheader("💬 Chat with this book")
    user_question = st.text_input("Ask a specific question (e.g. 'Is it scary?', 'Does the dog die?')")
    
    if user_question:
        with st.spinner("Asking the book..."):
            # We send the original image + the specific question
            chat_prompt = f"You are analyzing the book '{data['title']}' for a {target_age}-year-old. The parent asks: {user_question}. Answer briefly and honestly."
            chat_response = model.generate_content([chat_prompt, image])
            st.write(f"**Answer:** {chat_response.text}")
