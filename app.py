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
# CHANGE THIS LINE:
model = genai.GenerativeModel('gemini-flash-latest')

# --- SESSION STATE ---
if 'history' not in st.session_state:
    st.session_state.history = []
if 'current_results' not in st.session_state:
    st.session_state.current_results = None
if 'current_img_id' not in st.session_state:
    st.session_state.current_img_id = ""

# --- APP UI ---
st.set_page_config(page_title="Samaira's Library", page_icon="📚")

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
st.title("📚 Can Samaira read these?")
st.caption("Tip: You can take a photo of multiple books at once!")

col1, col2 = st.columns([2,1])
with col2:
    target_age = st.number_input("Age", 5, 18, 12)

img_file = st.camera_input(f"Scan books")

if img_file:
    image = Image.open(img_file)
    results_container = st.container()
    
    # LOGIC: Run AI only if new photo
    if st.session_state.current_img_id != img_file.file_id:
        with st.spinner("Analyzing all books in the photo..."):
            try:
                # UPDATED PROMPT: HANDLES MULTIPLE BOOKS
                prompt = f"""
                Look at this image. It may contain one book or MULTIPLE books.
                The reader is a {target_age}-year-old girl named Samaira.
                
                I need you to identify EVERY book visible in the image.
                
                Return a valid JSON object with this structure:
                {{
                    "books": [
                        {{
                            "title": "Title",
                            "author": "Author",
                            "verdict": "Green/Yellow/Red",
                            "one_line_verdict": "Short summary decision.",
                            "negative_highlights": "One sentence warning (if any).",
                            "positive_highlights": "One sentence highlights.",
                            "ratings": {{ "violence": "0-5", "sex": "0-5", "language": "0-5", "positive_content": "0-5" }},
                            "details": "Details parents guide."
                        }}
                    ],
                    "best_pick": {{
                        "title": "Title of the most appropriate book for her age",
                        "reason": "Why this is the winner compared to the others."
                    }}
                }}
                """
                response = model.generate_content([prompt, image])
                
                try:
                    clean_text = response.text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_text)
                except:
                    st.error("Could not read the books. Try getting closer.")
                    st.stop()

                # Save to memory
                st.session_state.current_results = data
                st.session_state.current_img_id = img_file.file_id
                
                # Add all found books to history (avoiding dupes)
                for book in data['books']:
                    if not any(b['title'] == book['title'] for b in st.session_state.history):
                        st.session_state.history.append(book)
                    
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

    # --- DISPLAY RESULTS ---
    if st.session_state.current_results:
        data = st.session_state.current_results
        books = data.get("books", [])
        best = data.get("best_pick", {})

        with results_container:
            st.divider()
            
            # 1. SHOW THE WINNER (Only if more than 1 book)
            if len(books) > 1:
                st.markdown("### 🏆 The Top Pick")
                st.success(f"**{best['title']}** is the best choice because: {best['reason']}")
                st.divider()

            # 2. SHOW EACH BOOK CARD
            st.subheader(f"Found {len(books)} Books:")
            
            for i, book in enumerate(books):
                # Color logic
                color = "green" if "Green" in book["verdict"] else "orange"
                if "Red" in book["verdict"]: color = "red"
                
                # Create a visual card for each book
                with st.expander(f"{i+1}. {book['title']} ({book['verdict']})", expanded=True):
                    st.markdown(f":{color}[**VERDICT: {book['verdict']}**]")
                    st.caption(f"By {book['author']}")
                    
                    if book.get("negative_highlights"):
                        st.error(f"⚠️ {book['negative_highlights']}")
                    st.success(f"🌟 {book['positive_highlights']}")
                    
                    # Mini ratings grid
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Positive", f"{book['ratings']['positive_content']}/5")
                    c2.metric("Violence", f"{book['ratings']['violence']}/5")
                    c3.metric("Lang", f"{book['ratings']['language']}/5")
                    c4.metric("Romance", f"{book['ratings']['sex']}/5")
                    
                    st.write(f"**Details:** {book['details']}")

        # --- CHAT FEATURE (Global) ---
        st.divider()
        st.subheader("💬 Ask about these books")
        user_question = st.text_input("Example: 'Which one is funniest?'")
        
        if user_question:
            with st.spinner("Comparing..."):
                chat_prompt = f"You are analyzing these books: {[b['title'] for b in books]}. The parent asks: {user_question}. Compare them briefly for Samaira."
                chat_response = model.generate_content([chat_prompt, image])
                st.write(f"**Answer:** {chat_response.text}")
