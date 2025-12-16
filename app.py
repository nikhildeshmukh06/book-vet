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

# --- FAIL-SAFE MODEL LOADER ---
# Cycles through verified model names to find one that works
def get_working_model():
    possible_models = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-flash-latest",
        "gemini-1.5-pro",
        "gemini-pro"
    ]
    for model_name in possible_models:
        try:
            test_model = genai.GenerativeModel(model_name)
            test_model.generate_content("test")
            return test_model
        except:
            continue
    return None

# Load model once and save to session state
if "active_model" not in st.session_state:
    with st.spinner("Connecting to AI..."):
        st.session_state.active_model = get_working_model()

if st.session_state.active_model is None:
    st.error("Could not connect to Google AI. Please check your API Key.")
    st.stop()

model = st.session_state.active_model

# SAFETY SETTINGS (Prevent AI from blocking "scary" book covers)
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# --- SESSION STATE ---
if 'history' not in st.session_state:
    st.session_state.history = []
if 'current_results' not in st.session_state:
    st.session_state.current_results = None
if 'current_img_id' not in st.session_state:
    st.session_state.current_img_id = ""

# --- APP UI ---
st.set_page_config(page_title="Samaira's Library", page_icon="📚")

# SIDEBAR: BOOKSHELF
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
    
    # 1. ANALYZE (Run only if it's a new photo)
    if st.session_state.current_img_id != img_file.file_id:
        with st.spinner("Analyzing books..."):
            try:
                prompt = f"""
                Look at this image. It may contain one book or MULTIPLE books.
                The reader is a {target_age}-year-old girl named Samaira.
                
                Identify EVERY book visible.
                
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
                            "details": "Detailed parents guide."
                        }}
                    ],
                    "best_pick": {{
                        "title": "Title of the most appropriate book",
                        "reason": "Why this is the winner."
                    }}
                }}
                """
                
                response = model.generate_content([prompt, image], safety_settings=safety_settings)
                
                if not response.text:
                    st.error("Error: The AI returned an empty response.")
                    st.stop()

                # FIX 1: Clean strings properly (Removed the stray dot)
                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_text)

                st.session_state.current_results = data
                st.session_state.current_img_id = img_file.file_id
                
                # Add to history
                for book in data.get('books', []):
                    if not any(b['title'] == book['title'] for b in st.session_state.history):
                        st.session_state.history.append(book)
                    
            except Exception as e:
                st.error(f"Technical Error: {e}")
                st.stop()

    # 2. DISPLAY RESULTS
    if st.session_state.current_results:
        data = st.session_state.current_results
        books = data.get("books", [])
        best = data.get("best_pick", {})

        with results_container:
            st.divider()
            
            # Show "Top Pick" only if multiple books found
            if len(books) > 1 and best:
                st.markdown("### 🏆 The Top Pick")
                st.success(f"**{best.get('title', 'Unknown')}** is the best choice because: {best.get('reason', 'N/A')}")
                st.divider()

            st.subheader(f"Found {len(books)} Books:")
            
            for i, book in enumerate(books):
                color = "green" if "Green" in book["verdict"] else "orange"
                if "Red" in book["verdict"]: color = "red"
                
                with st.expander(f"{i+1}. {book['title']} ({book['verdict']})", expanded=True):
                    st.markdown(f":{color}[**VERDICT: {book['verdict']}**]")
                    st.caption(f"By {book['author']}")
                    
                    if book.get("negative_highlights"):
                        st.error(f"⚠️ {book['negative_highlights']}")
                    st.success(f"🌟 {book['positive_highlights']}")
                    
                    # FIX 2: Safe Ratings (Defaults to 0 if AI forgets a key)
                    r = book.get("ratings", {})
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Pos", f"{r.get('positive_content', 0)}/5")
                    c2.metric("Viol", f"{r.get('violence', 0)}/5")
                    c3.metric("Lang", f"{r.get('language', 0)}/5")
                    c4.metric("Rom", f"{r.get('sex', 0)}/5")
                    
                    st.write(f"**Details:** {book.get('details', 'No details provided.')}")

        # 3. CHAT
        st.divider()
        st.subheader("💬 Ask about these books")
        user_question = st.text_input("Example: 'Which one is funniest?'")
        
        if user_question:
            with st.spinner("Comparing..."):
                titles = [b['title'] for b in books]
                chat_prompt = f"You are analyzing these books: {titles}. The parent asks: {user_question}. Compare them briefly for Samaira ({target_age})."
                chat_response = model.generate_content([chat_prompt, image])
                st.write(f"**Answer:** {chat_response.text}")
