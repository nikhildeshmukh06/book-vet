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
# This function tries multiple model names until one works
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
            # We test the model with a tiny "hello" to see if it responds
            test_model = genai.GenerativeModel(model_name)
            test_model.generate_content("test")
            return test_model # If we get here, it worked!
        except:
            continue # If it failed, try the next one
    return None # If all failed

# Load the working model once and save it
if "active_model" not in st.session_state:
    with st.spinner("Finding the best available AI server..."):
        st.session_state.active_model = get_working_model()

if st.session_state.active_model is None:
    st.error("Could not connect to ANY Google AI model. Check your API Key.")
    st.stop()

model = st.session_state.active_model

# SAFETY SETTINGS
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

st.title("📚 Can Samaira read these?")
st.caption("Tip: You can take a photo of multiple books at once!")

col1, col2 = st.columns([2,1])
with col2:
    target_age = st.number_input("Age", 5, 18, 12)

img_file = st.camera_input(f"Scan books")

if img_file:
    image = Image.open(img_file)
    results_container = st.container()
    
    if st.session_state.current_img_id != img_file.file_id:
        with st.spinner("Analyzing all books in the photo..."):
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
                            "details": "Details parents guide."
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

                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_text)

                st.session_state.current_results = data
                st.session_state.current_img_id = img_file.file_id
                
                for book in data['books']:
                    if not any(b['title'] == book['title'] for b in st.session_state.history):
                        st.session_state.history.append(book)
                    
            except Exception as e:
                st.error(f"Technical Error: {e}")
                if 'response' in locals() and hasattr(response, 'text'):
                    with st.expander("Debug Info"):
                        st.text(response.text)
                st.stop()

    if st.session_state.current_results:
        data = st.session_state.current_results
        books = data.get("books", [])
        best = data.get("best_pick", {})

        with results
