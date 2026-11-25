import os
import time
import streamlit as st
from api_client import APIClient

# Page configuration
st.set_page_config(
    page_title="Deepfake Forensics — Agentic AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #9CA3AF;
        margin-bottom: 1.5rem;
    }
    .verdict-box {
        padding: 1.5rem;
        border-radius: 0.75rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .verdict-real {
        background-color: rgba(16, 185, 129, 0.12);
        border: 2px solid #10B981;
    }
    .verdict-deepfake {
        background-color: rgba(239, 68, 68, 0.12);
        border: 2px solid #EF4444;
    }
    .verdict-suspicious {
        background-color: rgba(245, 158, 11, 0.12);
        border: 2px solid #F59E0B;
    }
    .metric-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar configuration
default_api_url = os.getenv("API_URL", "http://localhost:8000")
st.sidebar.title("🛡️ System Control")
api_base_url = st.sidebar.text_input("Backend API URL", value=default_api_url)

client = APIClient(base_url=api_base_url)

# Health Status in Sidebar
st.sidebar.markdown("### 🔌 Service Status")
is_healthy, health_data = client.check_health()
if is_healthy:
    st.sidebar.success(f"API: Connected\nDB: {health_data.get('database', 'unknown')}")
else:
    st.sidebar.error(f"API Disconnected: {health_data.get('error', health_data.get('reason', 'unreachable'))}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔗 Quick Links")
st.sidebar.markdown(
    f"""
    - [Interactive Swagger API Docs]({api_base_url}/docs)
    - [MinIO Storage Console](http://localhost:9001)
    - [Dozzle Log Streamer](http://localhost:8080)
    - [Beszel Resource Monitor](http://localhost:8090)
    """
)

st.sidebar.markdown("---")
st.sidebar.caption("Deepfake Agentic AI — Forensic Multi-Signal Mesh")

# Main Header
st.markdown('<div class="main-header">🛡️ Deepfake Agentic AI Forensics</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Multi-signal forensic analysis leveraging Computer Vision (RetinaFace + SigLIP) & Agentic Reasoning.</div>',
    unsafe_allow_html=True,
)

tab_upload, tab_lookup, tab_arch = st.tabs(["📤 Media Upload & Analysis", "🔍 Result Lookup", "🏗️ Architecture"])

# -------------------------------------------------------------
# Helper function: Render Verdict
# -------------------------------------------------------------
def render_verdict_card(result: dict):
    verdict = (result.get("verdict") or "UNKNOWN").upper()
    score = result.get("verdict_score")
    score_pct = f"{score * 100:.1f}%" if score is not None else "N/A"

    if verdict == "REAL":
        box_class = "verdict-real"
        badge_color = "#10B981"
        headline = "✅ AUTHENTIC MEDIA (REAL)"
        description = "Signals indicate high forensic integrity. No significant spatial or facial anomalies detected."
    elif verdict == "DEEPFAKE":
        box_class = "verdict-deepfake"
        badge_color = "#EF4444"
        headline = "🚨 SYNTHETIC / DEEPFAKE DETECTED"
        description = "High probability of manipulation detected by model inference and agentic analysis."
    else:
        box_class = "verdict-suspicious"
        badge_color = "#F59E0B"
        headline = f"⚠️ {verdict} / INCONCLUSIVE"
        description = "Confidence threshold in middle zone or pipeline triggered reanalysis."

    st.markdown(
        f"""
        <div class="verdict-box {box_class}">
            <h2 style="margin: 0; color: {badge_color};">{headline}</h2>
            <p style="margin-top: 0.5rem; font-size: 1.05rem;">{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Verdict Score", score_pct if score is not None else "N/A")
    with c2:
        st.metric("Status", result.get("status", "unknown").upper())
    with c3:
        st.metric("File Size", f"{result.get('size_mb', 0):.3f} MB")
    with c4:
        st.metric("Record ID", f"#{result.get('id')}")

    with st.expander("📋 Detailed Technical Metadata"):
        st.json(result)


# -------------------------------------------------------------
# TAB 1: Upload & Analyze
# -------------------------------------------------------------
with tab_upload:
    uploaded_file = st.file_uploader(
        "Select an image or video to analyze",
        type=["jpg", "jpeg", "png", "mp4"],
        help="Allowed formats: JPEG, PNG, MP4. Maximum temp files concurrent: 2.",
    )

    if uploaded_file is not None:
        col_preview, col_action = st.columns([1, 1])

        with col_preview:
            st.markdown("#### 👁️ Media Preview")
            if uploaded_file.name.lower().endswith((".jpg", ".jpeg", ".png")):
                st.image(uploaded_file, use_container_width=True, caption=uploaded_file.name)
            else:
                st.video(uploaded_file)

        with col_action:
            st.markdown("#### ⚡ Pipeline Execution")
            st.info(f"**Filename:** `{uploaded_file.name}`\n\n**Size:** `{round(uploaded_file.size / (1024 * 1024), 3)} MB`")

            if st.button("🚀 Run Forensic Detection", type="primary", use_container_width=True):
                if not is_healthy:
                    st.error("Cannot proceed: Backend API or Database is not reachable. Check configuration.")
                else:
                    file_bytes = uploaded_file.getvalue()

                    with st.status("Analyzing media through Agentic Pipeline...", expanded=True) as status_box:
                        st.write("📤 Uploading media & registering record with API...")
                        upload_success, upload_res = client.upload_media(uploaded_file.name, file_bytes)

                        if not upload_success:
                            status_box.update(label="❌ Upload failed", state="error", expanded=True)
                            st.error(f"Upload rejected: {upload_res.get('reason', 'Unknown error')}")
                        else:
                            record_id = upload_res.get("id")
                            st.write(f"✅ Record registered (ID: `#{record_id}`). Uploaded to MinIO (`{upload_res.get('minio_object')}`).")
                            st.write("🧠 Dispatched to ML Service (RetinaFace + SigLIP) & Agents mesh...")

                            status_placeholder = st.empty()

                            def poll_callback(current_status, data):
                                status_placeholder.write(f"🔄 Current Pipeline State: **{current_status.upper()}**...")

                            poll_success, poll_data = client.poll_result(
                                record_id=record_id,
                                timeout_sec=90,
                                interval_sec=1.5,
                                status_callback=poll_callback,
                            )

                            if poll_success:
                                status_box.update(label="✅ Analysis complete!", state="complete", expanded=False)
                                st.success("Pipeline executed successfully!")
                                render_verdict_card(poll_data)
                            else:
                                if poll_data.get("status") == "timeout":
                                    status_box.update(label="⏱️ Analysis in progress (Timeout)", state="running", expanded=True)
                                    st.warning(
                                        f"Analysis is taking longer than expected for Record #{record_id}. "
                                        "You can check back anytime using the 'Result Lookup' tab."
                                    )
                                else:
                                    status_box.update(label="❌ Processing error", state="error", expanded=True)
                                    st.error(f"Error processing record: {poll_data.get('reason', 'Processing failed')}")


# -------------------------------------------------------------
# TAB 2: Lookup by Record ID
# -------------------------------------------------------------
with tab_lookup:
    st.markdown("#### 🔍 Query Existing Analysis Record")
    query_id = st.number_input("Enter Record ID", min_value=1, step=1, value=1)

    if st.button("Fetch Result", use_container_width=False):
        with st.spinner(f"Querying result for Record #{query_id}..."):
            fetch_success, fetch_data = client.get_result(record_id=int(query_id))
            if fetch_success:
                st.success(f"Found record #{query_id}")
                render_verdict_card(fetch_data)
            else:
                st.warning(f"Could not retrieve Record #{query_id}: {fetch_data.get('reason', 'Not found')}")


# -------------------------------------------------------------
# TAB 3: System Architecture
# -------------------------------------------------------------
with tab_arch:
    st.markdown("### 🏗️ Agentic Microservices Architecture")
    st.markdown(
        """
        ```mermaid
        flowchart LR
            Client[Streamlit UI :8501] -->|POST /upload| API[FastAPI :8000]
            API --> DB[(PostgreSQL :5432)]
            API --> MinIO[(MinIO S3 :9000)]
            API -->|HTTP async| Agents[Agent Service :8123]
            Agents -->|Inference request| ML[ML Service :8001]
            ML -->|RetinaFace + SigLIP| Agents
            Agents -->|Source Verifier & Log Analyser| Agents
            Agents -->|Weighted Aggregator & Decider| Agents
            Agents -->|POST /verdict| API
            Client -->|Poll GET /result/:id| API
        ```
        """
    )
    st.markdown(
        """
        * **API Service:** Validates file magic headers, enforces temp locks, and persists records.
        * **ML Service:** Runs deep visual feature extraction using RetinaFace face cropping and SigLIP ViT scoring.
        * **Agents Service:** Adaptive weighting aggregator with Path 3a middle-zone reanalysis and decision routing.
        """
    )
