import os
import time
import tempfile
import requests
import streamlit as st
from dotenv import load_dotenv

BASE_URL = "https://llmwhisperer-api.us-central.unstract.com/api/v2"

def whisper_start(file_path, api_key, mode="high_quality", pages="", vert=False, horiz=False, output_mode="layout_preserving"):
    # params go in the query string per docs
    params = {
        "mode": mode,
        "output_mode": output_mode,
    }
    if pages:
        params["pages_to_extract"] = pages
    if vert:
        params["mark_vertical_lines"] = "true"
    if horiz:
        params["mark_horizontal_lines"] = "true"

    headers = {"unstract-key": api_key}
    with open(file_path, "rb") as f:
        # API expects raw body; multipart generally works, but send raw bytes to match docs
        resp = requests.post(f"{BASE_URL}/whisper", headers=headers, params=params, data=f)
    if resp.status_code == 401:
        raise RuntimeError(f"Auth failed (401). Check key and header. Body: {resp.text}")
    if resp.status_code not in (202, 200):
        raise RuntimeError(f"Whisper start failed {resp.status_code}: {resp.text}")
    return resp.json().get("whisper_hash")

def whisper_status(whisper_hash, api_key):
    headers = {"unstract-key": api_key}
    r = requests.get(f"{BASE_URL}/whisper-status", headers=headers, params={"whisper_hash": whisper_hash})
    r.raise_for_status()
    return r.json()

def whisper_retrieve(whisper_hash, api_key):
    headers = {"unstract-key": api_key}
    r = requests.get(f"{BASE_URL}/whisper-retrieve", headers=headers, params={"whisper_hash": whisper_hash})
    r.raise_for_status()
    return r.json()

def main():
    st.set_page_config(page_title="LLMWhisperer Extractor", page_icon="🗂️", layout="centered")
    st.title("🗂️ LLMWhisperer Extractor (REST)")

    load_dotenv(override=False)
    api_key = st.secrets.get("LLMWHISPERER_API_KEY", os.getenv("LLMWHISPERER_API_KEY"))
    if not api_key:
        st.error("❌ Missing `LLMWHISPERER_API_KEY`. Add it to .env or Streamlit Secrets.")
        st.stop()

    uploaded = st.file_uploader("Choose a file", type=None)
    mode = st.selectbox("Extraction mode", ["native_text", "low_cost", "high_quality", "form", "table"], index=2)
    pages = st.text_input("Pages to extract (optional)", placeholder='e.g. "1-5", "7", "1-5,7,21-"')
    vert = st.checkbox("Recreate vertical table borders (--vert)", value=False)
    horiz = st.checkbox("Recreate horizontal table borders (--horiz)", value=False)
    if horiz and not vert:
        st.warning("⚠️ `--horiz` requires `--vert`.")

    if st.button("Extract"):
        if not uploaded:
            st.warning("Please upload a file.")
            st.stop()
        if horiz and not vert:
            st.error("`--horiz` requires `--vert`. Please enable vertical borders.")
            st.stop()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name

        st.info(f"Uploading **{uploaded.name}** (mode **{mode}**) ...")

        try:
            whisper_hash = whisper_start(tmp_path, api_key, mode, pages, vert, horiz)
            if not whisper_hash:
                st.error("No whisper_hash received; cannot continue.")
                return

            with st.spinner("Processing..."):
                # simple poll loop (max ~200s per docs)
                t0 = time.time()
                while True:
                    status = whisper_status(whisper_hash, api_key)
                    if status.get("status") == "processed":
                        break
                    if status.get("status") == "failed":
                        st.error(f"Processing failed: {status}")
                        return
                    if time.time() - t0 > 200:
                        st.error("Timed out waiting for completion (200s). Try again or retrieve later.")
                        return
                    time.sleep(3)

            data = whisper_retrieve(whisper_hash, api_key)
            text = (data or {}).get("result_text", "") or data.get("extracted_text", "")
            st.success("✅ Extraction complete.")
            st.text_area("Extracted Text", text, height=350)
            st.download_button(
                "Download as .txt",
                data=text.encode("utf-8"),
                file_name=f"{os.path.splitext(uploaded.name)[0]}_extracted.txt",
                mime="text/plain",
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

if __name__ == "__main__":
    main()
