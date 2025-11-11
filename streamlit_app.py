import os
import tempfile
import requests
import streamlit as st
from dotenv import load_dotenv


def whisper_extract(file_path, api_key, mode="high_quality", pages="", vert=False, horiz=False):
    """
    Direct REST call to LLMWhisperer API.
    """
    url = "https://llmwhisperer-api.us-central.unstract.com/api/v2/whisper"
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "mode": mode,
        "pages_to_extract": pages,
        "mark_vertical_lines": str(vert).lower(),
        "mark_horizontal_lines": str(horiz).lower(),
        "wait_for_completion": "true",
        "wait_timeout": 200
    }

    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
        response = requests.post(url, headers=headers, files=files, data=data)

    if response.status_code != 200:
        raise RuntimeError(f"API error {response.status_code}: {response.text}")

    return response.json()


def main():
    st.set_page_config(page_title="LLMWhisperer Extractor", page_icon="🗂️", layout="centered")
    st.title("🗂️ LLMWhisperer Extractor (No SDK version)")
    st.write("Upload a document and extract text via LLMWhisperer’s REST API.")

    # Load environment variables (.env for local dev)
    load_dotenv(override=False)

    api_key = st.secrets.get("LLMWHISPERER_API_KEY", os.getenv("LLMWHISPERER_API_KEY"))
    if not api_key:
        st.error("❌ Missing `LLMWHISPERER_API_KEY`. Add it to .env or Streamlit Secrets.")
        st.stop()

    uploaded = st.file_uploader("Choose a file", type=None)
    mode = st.selectbox(
        "Extraction mode",
        ["native_text", "low_cost", "high_quality", "form", "table"],
        index=2,
        help="Extraction mode for LLMWhisperer",
    )
    pages = st.text_input(
        "Pages to extract (optional)",
        placeholder='e.g. "1-5", "7", "1-5,7,21-"',
    )
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

        st.info(f"Processing **{uploaded.name}** with mode **{mode}** ...")

        try:
            result = whisper_extract(tmp_path, api_key, mode, pages, vert, horiz)
            status = result.get("status")
            if status != "processed":
                st.error(f"Processing status: {status}\n\nMessage: {result.get('message')}")
                return

            extraction = result.get("extraction", {}) or {}
            text = extraction.get("result_text", "")
            metadata = extraction.get("metadata", {})

            st.success("✅ Extraction complete.")
            st.text_area("Extracted Text", text, height=350)
            st.download_button(
                "Download as .txt",
                data=text.encode("utf-8"),
                file_name=f"{os.path.splitext(uploaded.name)[0]}_extracted.txt",
                mime="text/plain",
            )
            if metadata:
                st.caption(f"Total pages processed: {len(metadata)}")

        except Exception as e:
            st.error(f"❌ Error: {e}")
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass


if __name__ == "__main__":
    main()
