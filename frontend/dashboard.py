import streamlit as st
import requests
import json
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="AI ATS Dashboard", layout="wide")

st.title("🚀 AI Applicant Tracking System (ATS)")
st.markdown("---")

# Sidebar for Auth
with st.sidebar:
    st.header("Authentication")
    email = st.text_input("Email", "recruiter@example.com")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        # Placeholder for real login
        st.session_state["token"] = "dummy_token"
        st.success("Logged in!")

# Main Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Analytics", "📄 Upload & Match", "🕵️ Bias Report", "💬 Candidate Chat"])

with tab1:
    st.header("System Metrics")
    try:
        res = requests.get(f"{API_URL}/api/metrics")
        if res.status_code == 200:
            metrics = res.json()
            col1, col2 = st.columns(2)
            col1.metric("Total Candidates", metrics["count"])
            col2.metric("Average Score", f"{metrics['average_score']}%")
    except:
        st.warning("API not reachable. Ensure backend is running.")

with tab2:
    st.header("Resume Screening")
    
    # Job Postings
    st.subheader("1. Select Job Posting")
    # In a real app, we'd fetch jobs. Here's a placeholder select.
    job_id = st.number_input("Job ID", min_value=1, value=1)
    
    # Upload
    st.subheader("2. Upload Resume")
    uploaded_file = st.file_uploader("Choose a PDF or TXT file", type=["pdf", "txt"])
    
    if uploaded_file is not None and st.button("Process & Screen"):
        with st.spinner("AI Agents working..."):
            files = {"file": uploaded_file.getvalue()}
            data = {"job_id": job_id}
            # Note: This needs the token in headers in a real app
            res = requests.post(f"{API_URL}/api/resume/upload", files={"file": (uploaded_file.name, uploaded_file.getvalue())}, data=data)
            
            if res.status_code == 200:
                result = res.json()
                st.success("Analysis Complete!")
                st.write(result["analysis"]["final_result"]["explanation"])
                
                with st.expander("Detailed AI Evaluation"):
                    st.markdown(result["analysis"]["llm_evaluation"])
                
                with st.expander("Parsed Skills"):
                    st.write(result["analysis"]["candidate"]["skills"])
            else:
                st.error("Upload failed.")

with tab3:
    st.header("Bias Detection Report")
    bias_job_id = st.number_input("Job ID for Bias Check", min_value=1, value=1, key="bias_job")
    if st.button("Generate Report"):
        res = requests.get(f"{API_URL}/api/bias-report?job_id={bias_job_id}")
        if res.status_code == 200:
            report = res.json()
            st.json(report)
        else:
            st.error("Report generation failed.")

with tab4:
    st.header("Search Candidate Pool (RAG)")
    query = st.text_input("Ask about your candidates...", "Find Python developers with 5+ years experience")
    if st.button("Search"):
        res = requests.post(f"{API_URL}/api/chat?query={query}")
        if res.status_code == 200:
            results = res.json()["results"]
            for r in results:
                st.markdown(f"**Candidate {r['id']}** - Score: {round((1-r['distance'])*100, 2)}%")
                st.text_area("Snippet", r['document'], height=100)
                st.markdown("---")
