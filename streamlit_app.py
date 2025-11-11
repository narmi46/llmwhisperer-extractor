import streamlit as st
import os
from unstract.llmwhisperer import LLMWhispererClientV2

st.set_page_config(page_title="LLM Whisperer Extractor", layout="centered")

st.title("📄 LLM Whisperer Extractor")
st.caption("Upload a document and extract text using Unstract LLM Whisperer API")

api_key = st.text_input("🔑 Enter your LLMWhisperer API Key", type="password")
mode = st.selectbox("Extraction Mode", ["high_quality", "low_cost", "table", "form", "native_text"])
uploaded = st.file_uploader("Upload your file", type=["pdf", "docx", "png", "jpg"])

if uploaded and api_key:
    st.info("Processing file... please wait ⏳")
    with open("temp_file", "wb") as f:
        f.write(uploaded.read())

    client = LLMWhispererClientV2(api_key=api_key)
    try:
        result = client.whisper(file_path="temp_file", wait_for_completion=True, mode=mode)
        text = result.get("extraction", {}).get("result_text", "")
        st.success("✅ Extraction complete!")
        st.text_area("Extracted Text", text, height=400)
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.warning("Please upload a file and enter your API key to start.")
