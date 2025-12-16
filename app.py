import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests
import json

# --- SETUP ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Missing API Key")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- SESSION STATE (The Memory) ---
# This keeps data alive even when you click buttons
if 'history' not in st.session_state:
    st.session_state.history = []

# --- HELPER: BOOK SEARCH ---
def get_book_cover(title, author):
    try:
        clean_query = f"{title} {author}"
        url = f"https://www.googleapis.com/books/v1/volumes?q={clean_query}&maxResults=1"
        response = requests.get(url).json()
        if "items" in response:
            return response["items"][0]["volumeInfo"].get("imageLinks", {}).get("thumbnail")
    except:
        return None
    return None

# --- APP UI ---
st.set_page_config(page_title="Book Vet Pro", page_icon="🛡️")

# SIDEBAR: THE BOOKSHELF
with st.sidebar:
    st.header(f"📚 My Stack ({len(st.session_state.history)})")
    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()
    
    for book in st.session_state.history:
        # Color code the history items
        emoji = "✅" if "Green" in book['verdict'] else "⚠️"
        if "Red" in book['verdict']: emoji = "❌"
        
        with st.expander(f"{emoji} {book['title']}"):
            st.caption(book['author'])
            st.write(book['one_line_verdict'])

# MAIN PAGE
st.title("🛡️ Parent Pal: Scanner")

# Custom Filters (Feature #2 Idea)
filters = st.multiselect(
    "Flag these specific topics if found:",
    ["Bullying", "Death of a Pet", "Romance", "Ghost/Horror", "Swearing"],
    default=[]
)

col1, col2 = st.columns([2,1])
with col2:
    target_age = st.number_input("Age", 5, 18, 12)

img_file = st.camera_input(f"Scan book for {target_age}-year-old")

if img_file:
    image = Image.open(img_file)
    
    with st.spinner("Reading & Reviewing..."):
        try:
            # Add user filters to prompt
            filter_text = ""
            if filters:
                filter_text = f"CRITICAL: The parent specifically wants to know if the book contains: {', '.join(filters)}. If found, mention it prominently."

            prompt = f"""
            Analyze this book cover. Reader: {target_age}-year-old.
            {filter_text}
            
            Return valid JSON:
            {{
                "title": "Title",
                "author": "Author",
                "series": "Series Info",
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
            
            # SAVE TO HISTORY (Avoid duplicates)
            if not any(b['title'] == data['title'] for b in st.session_state.history):
                st.session_state.history.append(data)
            
            official_cover = get_book_cover(data["title"], data["author"])
            
            # --- REPORT DISPLAY ---
            st.divider()
            c1, c2 = st.columns([1, 2])
            with c1:
                st.image(official_cover if official_cover else image, width=100)
            with c2:
                color = "green" if "Green" in data["verdict"] else "orange"
                if "Red" in data["verdict"]: color = "red"
                st.markdown(f":{color}[**VERDICT: {data['verdict']}**]")
                st.subheader(data["title"])
                st.caption(f"Series: {data['series']}")

            # Special Flag Warning
            if filters:
                st.markdown("### 🚩 Filter Check")
                st.info("Checked for: " + ", ".join(filters))

            st.markdown("### 📊 Ratings")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Violence:** {data['ratings']['violence']}/5")
                st.progress(int(data['ratings']['violence'])/5)
            with col_b:
                st.write(f"**Role Models:** {data['ratings']['role_models']}/5")
                st.progress(int(data['ratings']['role_models'])/5)
                
            st.markdown("### 📝 Details")
            st.write(data["details"])

        except Exception as e:
            st.error(f"Error: {e}")
