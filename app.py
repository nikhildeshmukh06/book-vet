import streamlit as st
import google.generativeai as genai
from PIL import Image
import os

# --- SETUP ---
# This looks for the key in the cloud's secure vault
api_key = st.secrets["GOOGLE_API_KEY"] 

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- APP INTERFACE ---
st.set_page_config(page_title="Book Vet", page_icon="📚")
st.title("📚 Parent Pal: Book Vetting")

img_file = st.camera_input("Take a picture of the book")

if img_file is not None:
    image = Image.open(img_file)
    with st.spinner("Analyzing for a 12-year-old reader..."):
        try:
            prompt = """
            Look at this book cover. Identify title/author.
            Reader: 12-year-old girl (born 2013). 
            
            Report format:
            1. **Title/Author**
            2. **Verdict**: ✅ APPROPRIATE / ⚠️ CAUTION / ❌ NOT APPROPRIATE
            3. **The "Why"**: Specifics on maturity, language, themes.
            4. **Plot**: 2-sentence summary.
            5. **Series Check**: Is it part of a series? Which number?
            """
            response = model.generate_content([prompt, image])
            st.markdown("### 📋 Report")
            st.markdown(response.text)
        except Exception as e:
            st.error(f"Error: {e}")
