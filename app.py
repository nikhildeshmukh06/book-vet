import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests
import json

# --- SETUP ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Missing API Key. Please add it to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=api_key)
# Using the 2.5 Flash model you found (fastest & smartest)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- HELPER: ROBUST BOOK SEARCH ---
def get_book_cover(title, author):
    """
    Searches Google Books API.
    Uses a broad search 'q=Title Author' instead of strict 'intitle:'.
    """
    try:
        # "clean" the query to avoid errors
        clean_query = f"{title} {author}"
        url = f"https://www.googleapis.com/books/v1/volumes?q={clean_query}&maxResults=1"
        
        response = requests.get(url).json()
        
        if "items" in response:
            book = response["items"][0]["volumeInfo"]
            image_links = book.get("imageLinks", {})
            # Try getting the largest available image, fallback to thumbnail
            return image_links.get("thumbnail")
    except:
        return None
    return None

# --- APP UI ---
st.set_page_config(page_title="Book Vet Pro", page_icon="🛡️")

st.title("🛡️ Parent Pal: Reviewer")

# User Inputs
col1, col2 = st.columns([2,1])
with col1:
    st.write("Snap a photo to generate a detailed safety report.")
with col2:
    target_age = st.number_input("Age", 5, 18, 12)

# Camera
img_file = st.camera_input(f"Scan book for {target_age}-year-old")

if img_file:
    image = Image.open(img_file)
    
    with st.spinner("Analyzing content & searching library..."):
        try:
            # --- THE PROMPT ---
            # We ask for a strict JSON format with 0-5 ratings
            prompt = f"""
            Analyze this book cover. The reader is a {target_age}-year-old child.
            
            Return a valid JSON object with these exact keys:
            {{
                "title": "Book Title",
                "author": "Author Name",
                "series": "Book X of Y (or 'Standalone')",
                "age_rating": "Recommended Minimum Age (e.g. 10+)",
                "verdict": "Green (Go) / Yellow (Caution) / Red (Stop)",
                "one_line_verdict": "Short sentence explaining the verdict.",
                "ratings": {{
                    "educational": "0 to 5",
                    "positive_messages": "0 to 5",
                    "positive_role_models": "0 to 5",
                    "violence": "0 to 5",
                    "sex": "0 to 5",
                    "language": "0 to 5",
                    "drinking_drugs": "0 to 5"
                }},
                "parents_need_to_know": "A paragraph explaining the sensitive content in detail.",
                "story_summary": "Two sentence plot summary."
            }}
            """
            
            response = model.generate_content([prompt, image])
            
            # --- PARSE DATA ---
            # Clean text to ensure JSON is valid
            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw_text)
            
            # Fetch Cover
            official_cover = get_book_cover(data["title"], data["author"])
            
            # --- DISPLAY THE REPORT ---
            st.divider()

            # 1. TOP HEADER (Verdict & Cover)
            c1, c2 = st.columns([1, 2])
            with c1:
                if official_cover:
                    st.image(official_cover, caption="Library Match", width=110)
                else:
                    st.image(image, caption="Your Scan", width=110)
            
            with c2:
                # Color-coded Verdict
                color = "green"
                if "Yellow" in data["verdict"]: color = "orange"
                if "Red" in data["verdict"]: color = "red"
                
                st.markdown(f":{color}[**VERDICT: {data['verdict'].upper()}**]")
                st.subheader(data["title"])
                st.caption(f"By {data['author']} | {data['series']}")
                st.markdown(f"**Target Age:** {data['age_rating']}")

            st.info(f"**Bottom Line:** {data['one_line_verdict']}")

            # 2. THE "COMMON SENSE" GRID
            st.markdown("### 📊 Content Grid")
            st.caption("Scale: 0 (None) to 5 (Heavy)")
            
            # Helper to draw progress bars
            def draw_rating(label, score, is_bad_thing=True):
                # Calculate color: If it's a "bad" thing (Violence), high score is Red.
                # If it's a "good" thing (Role Models), high score is Green.
                score = int(score)
                bar_color = "red" if is_bad_thing else "green"
                st.write(f"**{label}** ({score}/5)")
                st.progress(score / 5)

            r = data["ratings"]
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### ⚠️ Sensitive")
                draw_rating("Violence & Scary", r["violence"], True)
                draw_rating("Sex & Romance", r["sex"], True)
                draw_rating("Language", r["language"], True)
                draw_rating("Drinking/Drugs", r["drinking_drugs"], True)
                
            with col_b:
                st.markdown("#### ✅ Positive")
                draw_rating("Role Models", r["positive_role_models"], False)
                draw_rating("Pos. Messages", r["positive_messages"], False)
                draw_rating("Educational", r["educational"], False)

            # 3. TEXT DETAILS
            st.markdown("### 📝 Parents Need to Know")
            st.write(data["parents_need_to_know"])
            
            st.markdown("### 📖 The Story")
            st.write(data["story_summary"])

        except Exception as e:
            st.error("Oops! Could not analyze. Please try a clearer photo.")
            with st.expander("See technical error"):
                st.write(e)
