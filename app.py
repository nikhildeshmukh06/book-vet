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
if 'current_report' not in st.session_state:
    st.session_state.current_report = None
if 'current_img_id' not in st.session_state:
    st.session_state.current_img_id = ""

# --- APP UI ---
st.set_page_config(page_title="Samaira's Books", page_icon="📚")

# SIDEBAR
with st.sidebar:
    st.header(f"📚 Stack ({len(st.session_state.history)})")
    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()
    
    if st.session_state.history:
        text_data = "SAMAIRA'S BOOK LIST:\n\n"
        for b in st.session_state.history:
            text_data += f"- {b['title']} ({b['verdict']})\n"
        st.download_button("📥 Save List", text_data, "samaira_books.txt")

    for book in st.session_state.history:
        emoji = "✅" if "Green" in book['verdict'] else "⚠️"
        if "Red" in book['verdict']: emoji = "❌"
        with st.expander(f"{emoji} {book['title']}"):
            st.caption(book['author'])
            st.write(book['one_line_verdict'])

# MAIN PAGE
st.title("📚 Can Samaira read this book?")

col1, col2 = st.columns([2,1])
with col2:
    target_age = st.number_input("Age", 5, 18, 12)

img_file = st.camera_input(f"Scan book cover")

if img_file:
    image = Image.open(img_file)
    
    report_container = st.container()
    
    # LOGIC CHECK
    should_analyze = False
    if st.session_state.current_img_id != img_file.file_id:
        should_analyze = True
    elif st.session_state.current_report is None:
        should_analyze = True

    if should_analyze:
        with st.spinner("Checking for positive themes..."):
            try:
                # UPDATED PROMPT: Asks for "Positive Content" and "Highlights"
                prompt = f"""
                Analyze this book cover. The reader is a {target_age}-year-old girl named Samaira.
                
                Return valid JSON:
                {{
                    "title": "Title",
                    "author": "Author",
                    "series": "Series Info (e.g. Book 2 of 5)",
                    "verdict": "Green/Yellow/Red",
                    "one_line_verdict": "Short summary decision.",
                    "positive_highlights": "One clear sentence highlighting the best themes (e.g. 'Promotes bravery and friendship').",
                    "ratings": {{ 
                        "violence": "0-5", 
                        "sex": "0-5", 
                        "language": "0-5", 
                        "positive_content": "0-5" 
                    }},
                    "details": "Detailed parents guide.",
                    "plot": "Plot summary."
                }}
                """
                response = model.generate_content([prompt, image])
                
                try:
                    raw_text = response.text
                except ValueError:
                    st.error("🚨 Google blocked this image (Safety Filter).")
                    st.stop()

                clean_text = raw_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_text)
                
                st.session_state.current_report = data
                st.session_state.current_img_id = img_file.file_id
                
                if not any(b['title'] == data['title'] for b in st.session_state.history):
                    st.session_state.history.append(data)
                    
            except Exception as e:
                st.error(f"Error reading book: {e}")
                st.stop()

    # --- DISPLAY REPORT ---
    if st.session_state.current_report:
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
                st.write(f"**Summary:** {data['one_line_verdict']}")

            # NEW SECTION: THE GOOD STUFF
            st.success(f"**🌟 The Good Stuff:** {data['positive_highlights']}")

            st.markdown("### 📊 Ratings")
            col_a, col_b = st.columns(2)
            with col_a:
                # RENAMED CATEGORY
                st.write(f"**Positive Content:** {data['ratings']['positive_content']}/5")
                st.progress(int(data['ratings']['positive_content'])/5)
                st.write(f"**Language:** {data['ratings']['language']}/5")
                st.progress(int(data['ratings']['language'])/5)
            with col_b:
                st.write(f"**Violence:** {data['ratings']['violence']}/5")
                st.progress(int(data['ratings']['violence'])/5)
                st.write(f"**Sex/Romance:** {data['ratings']['sex']}/5")
                st.progress(int(data['ratings']['sex'])/5)
            
            st.markdown("### 📝 Details")
            st.write(data["details"])

        # --- CHAT FEATURE ---
        st.divider()
        st.subheader("💬 Ask about this book")
        user_question = st.text_input("Example: 'Is it scary?' or 'Is there swearing?'")
        
        if user_question:
            with st.spinner("Checking..."):
                chat_prompt = f"You are analyzing the book '{data['title']}' for Samaira ({target_age}). The parent asks: {user_question}. Answer briefly and honestly."
                chat_response = model.generate_content([chat_prompt, image])
                st.write(f"**Answer:** {chat_response.text}")
