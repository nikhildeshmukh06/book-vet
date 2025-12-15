import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- SETUP ---
# This gets your secure key from Streamlit's settings
api_key = st.secrets["GOOGLE_API_KEY"]

genai.configure(api_key=api_key)

# UPDATED: Using the specific model we found in your scanner
model = genai.GenerativeModel('gemini-2.5-flash')

# --- APP INTERFACE ---
st.set_page_config(page_title="Book Vet", page_icon="📚")
st.title("📚 Parent Pal: Book Vetting")
st.write("Snap a photo to check if a book is good for a 12-year-old (born 2013).")

# Camera Input
img_file = st.camera_input("Take a picture of the book cover")

if img_file is not None:
    # Display the image briefly so you know it worked
    image = Image.open(img_file)
    
    with st.spinner("Analyzing story and series info..."):
        try:
            # The Instructions for the AI
            prompt = """
            Look at this book cover. Identify the title and author.
            The reader is a 12-year-old girl (born in 2013). 
            
            Please provide the following structured analysis:
            
            1. **Title & Author**: [Name] by [Author]
            2. **Verdict**: (Start with ✅ APPROPRIATE, ⚠️ CAUTION, or ❌ NOT APPROPRIATE)
            3. **The "Why"**: Explain specifically why it is or isn't appropriate for a 12-year-old. Mention maturity level, language, or themes (romance, violence, horror).
            4. **Plot Summary**: A brief 2-sentence summary of the storyline.
            5. **Series Check**: Is this part of a series? If yes, which number book is it? (e.g., "Book 2 of 5"). *Highlight if she needs to read previous books first.*
            """
            
            # Send to AI
            response = model.generate_content([prompt, image])
            
            # Display Results
            st.markdown("### 📋 Analysis Report")
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"An error occurred: {e}")

st.markdown("---")
st.caption("Always double-check. AI suggestions are based on general book data.")
