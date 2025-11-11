import os
import tempfile
import streamlit as st
from dotenv import load_dotenv

# Your client comes from this package
from llmwhisperer.client import LLMWhispererClientV2

DEFAULT_BASE_URL = "https://llmwhisperer-api.us-central.unstract.com/api/v2"

def get_secret(name: str, default: str | None = None) -> str | None:
    # Prefer Streamlit secrets in Cloud; fall back to env/.env locally
    v = st.secrets.get(name) if hasattr(st, "secrets") else None
    if v is not None:
        return v
    return os.getenv(name, default)

def main():
    st.set_page_config(page_title="LLMWhisperer Extractor", page_icon="🗂️", layout="centered")

    # Load .env for local dev; Streamlit Cloud uses st.secrets instead
    load_dotenv(override=False)

    st.title("🗂️ LLMWhisperer Extractor")
    st.write("Upload a document and extract text using LLMWhisperer modes.")

    # Secrets / config
    api_key = get_secret("LLMWHISPERER_API_KEY")
    base_url = get_secret("LLMWHISPERER_BASE_URL_V2", DEFAULT_BASE_URL)

    with st.expander("⚙️ Configuration", expanded=False):
        st.write("`LLMWHISPERER_BASE_URL_V2` (optional)")
        st.code(base_url)

    if not api_key:
        st.error("Missing `LLMWHISPERER_API_KEY`. Add it to **.streamlit/secrets.toml** (Cloud) or your environment/.env (local).")
        st.stop()

    # UI controls mirroring your CLI flags
    uploaded = st.file_uploader("Choose a file", type=None, accept_multiple_files=False)
    mode = st.selectbox(
        "Extraction mode",
        options=["native_text", "low_cost", "high_quality", "form", "table"],
        index=2,  # default: high_quality
        help="Matches CLI: -m/--mode"
    )
    pages = st.text_input(
        "Pages to extract (optional)",
        placeholder='e.g., "1-5", "7", "1-5,7,21-"',
        help='Matches CLI: -p/--pages; leave empty for all pages'
    )
    vert = st.checkbox("Recreate vertical table borders (--vert)", value=False)
    horiz = st.checkbox("Recreate horizontal table borders (--horiz, requires --vert)", value=False)

    if horiz and not vert:
        st.warning("`--horiz` requires `--vert`. Enable vertical borders or disable horizontal borders.")

    run = st.button("Extract")

    if run:
        if not uploaded:
            st.warning("Please upload a file.")
            st.stop()

        if horiz and not vert:
            st.error("`--horiz` requires `--vert`. Please enable vertical borders.")
            st.stop()

        try:
            # Persist upload to a temp file for the client
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name

            st.info(f"Processing **{uploaded.name}** with mode **{mode}**. This can take a moment…")

            client = LLMWhispererClientV2(base_url=base_url, api_key=api_key)

            result = client.whisper(
                file_path=tmp_path,
                wait_for_completion=True,
                mode=mode,
                pages_to_extract=pages or "",
                mark_vertical_lines=bool(vert),
                mark_horizontal_lines=bool(horiz),
                wait_timeout=200,
            )

            status = result.get("status")
            if status != "processed":
                st.error(f"Processing status: {status}\n\nMessage: {result.get('message')}")
                return

            extraction = result.get("extraction", {}) or {}
            extracted_text = extraction.get("result_text", "") or ""
            metadata = extraction.get("metadata", {}) or {}

            st.success("Extraction complete.")

            # Show summary + preview
            st.subheader("Extracted Text")
            if extracted_text.strip():
                st.text_area("Result", extracted_text, height=350)
                st.download_button(
                    label="Download as .txt",
                    data=extracted_text.encode("utf-8"),
                    file_name=f"{os.path.splitext(uploaded.name)[0]}_extracted.txt",
                    mime="text/plain",
                )
            else:
                st.warning("No text returned.")

            if metadata:
                st.caption(f"Total pages processed: {len(metadata)}")

        except Exception as e:
            # Try to surface useful fields, similar to your CLI
            msg = getattr(e, "message", str(e))
            code = getattr(e, "status_code", None)
            if code:
                st.error(f"Error ({code}): {msg}")
            else:
                st.error(f"Error: {msg}")
        finally:
            # Cleanup temp file
            try:
                os.remove(tmp_path)
            except Exception:
                pass

if __name__ == "__main__":
    main()
