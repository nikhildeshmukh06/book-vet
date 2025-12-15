import streamlit as st
import google.generativeai as genai

# --- SETUP ---
# On Streamlit Cloud, use this:
api_key = st.secrets["GOOGLE_API_KEY"]

# If using Pydroid on phone, comment out the line above and use this instead:
# api_key = "PASTE_YOUR_LONG_KEY_HERE"

genai.configure(api_key=api_key)

st.title("🛠 Model Scanner")

try:
    st.write("Asking Google for available models...")
    # This command asks Google: "What works?"
    available_models = genai.list_models()
    
    found_flash = False
    
    for m in available_models:
        # We only care about models that can 'generateContent'
        if 'generateContent' in m.supported_generation_methods:
            st.write(f"- `{m.name}`")
            if "flash" in m.name:
                found_flash = True
                st.success(f"✅ FOUND FLASH! Use this name: `{m.name}`")

    if not found_flash:
        st.error("❌ No Flash model found. Try using 'gemini-pro' instead.")

except Exception as e:
    st.error(f"Error: {e}")
