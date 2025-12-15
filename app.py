import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests
import json

# --- SETUP ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Missing API Key in Secrets")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- HELPER FUNCTION: FETCH BOOK COVER ---
def get_book_cover(title, author):
    """Searches Google Books API for a cover image."""
    try:
        query = f"intitle:{title}+inauthor:{author}"
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1"
        response = requests.get(url).json()
        
        if "items" in response:
            book = response["items"][0]["volumeInfo"]
            # Try to get a thumbnail
            image_links = book.get("imageLinks", {})
            thumbnail = image_links.get("thumbnail")
            return thumbnail
    except:
        return None
    return None

# --- APP INTERFACE ---
st.set_page_config(page_title="Book Vet Pro", page_icon="📚")

st.title("📚 Parent Pal: Book Vet")

# Feature 2: Age Input (customizable)
target_age = st.number_input("Child's Age", min_value=5, max_value=18, value=12, step=1)

# Feature 1: Camera Input 
# (Note: Use the 'Rotate' icon on the screen to switch to back camera)
img_file = st.camera_input(f"Snap a photo for a {target_age}-year-old")

if img_file is not None:
    image = Image.open(img_file)
    
    with st.spinner("Identifying book and analyzing safety..."):
        try:
            # We ask Gemini for JSON so we can separate data (Title) from text (Analysis)
            prompt = f"""
            Analyze this book cover. The reader is a {target_age}-year-old child.
            
            Return a strictly valid JSON object with these 6 fields:
            {{
                "title": "Exact Book Title",
                "author": "Author Name",
                "series_info": "Book X of Y in [Series Name] (or 'Not a series')",
                "verdict": "APPROPRIATE, CAUTION, or NOT APPROPRIATE",
                "reasoning": "Explanation of maturity, themes, violence, or language.",
                "plot": "2 sentence summary."
            }}
            """
            
            response = model.generate_content([prompt, image])
            
            # Clean up the response to ensure it's pure JSON
            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw_text)
            
            # Feature 3: Fetch Verification Image
            official_cover_url = get_book_cover(data["title"], data["author"])
            
            # --- DISPLAY REPORT ---
            st.divider()
            
            # Header with Verdict
            icon = "✅"
            if "CAUTION" in data["verdict"]: icon = "⚠️"
            if "NOT" in data["verdict"]: icon = "❌"
            
            st.header(f"{icon} Verdict: {data['verdict']}")
            
            # Verification Section
            col1, col2 = st.columns([1, 2])
            with col1:
                if official_cover_url:
                    st.image(official_cover_url, caption="Found Online", width=100)
                else:
                    st.image(image, caption="Your Photo", width=100)
            with col2:
                st.subheader(f"{data['title']}")
                st.write(f"**By:** {data['author']}")
                st.info(f"**Series Check:** {data['series_info']}")
            
            # Detailed Analysis
            st.markdown(f"### 🧐 Why?")
            st.write(data["reasoning"])
            
            st.markdown(f"### 📖 Storyline")
            st.write(data["plot"])
            
        except Exception as e:
            st.error(f"Could not analyze image. Try a clearer photo. Error: {e}")
