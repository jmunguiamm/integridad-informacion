"""
Streamlit App - Information Integrity Workshop (full version)
Includes full Workshop pages and navigation via sidebar.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime

from components.sidebar import render_sidebar


st.set_page_config(
    page_title="Information Integrity Workshop",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Basic styles used by the app
st.markdown(
    """
    <style>
      .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def main():
    """Main application function"""

    # Header
    st.markdown('<h1 class="main-header">🧭 Information Integrity Workshop</h1>', unsafe_allow_html=True)

    # Sidebar
    page = render_sidebar()

    # Routing
    if page == "Introduction":
        render_introduction_page()
    elif page == "Form #1":
        render_form1_page()
    elif page == "Encuadres narrativos":
        render_narrative_frames_page()
    elif page == "Form #2":
        render_form2_page()
    elif page == "Data Analysis":
        render_data_analysis_page()
    elif page == "Ask AI":
        render_ask_ai_page()
    else:
        st.info("Select a page from the sidebar.")


def render_introduction_page():
    """Render the introduction page"""

    st.header("🏠 Welcome to the Information Integrity Workshop")

    st.markdown(
        """
    This workshop is designed to help you understand and work with information integrity concepts.

    ### What you'll learn:
    - How to identify narrative frames
    - Data analysis techniques
    - Form handling and validation
    - AI-powered insights
    
    ### Getting Started:
    1. Complete Form #1 to begin your journey
    2. Explore narrative frames
    3. Fill out Form #2 with your insights
    4. Analyze your data
    5. Ask AI for additional insights
    """
    )

    st.info("👆 Use the navigation menu on the left to explore different sections of the workshop.")

    # Centered CTA button (1/5 width, not full width)
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Start now"):
            st.session_state.selected_page = "Form #1"
            st.rerun()


def render_form1_page():
    """Render Form #1 page"""

    st.header("📊 Form #1")

    with st.form("form1"):
        st.subheader("Initial Assessment")

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name *", placeholder="Enter your name")
            email = st.text_input("Email *", placeholder="Enter your email")
            organization = st.text_input("Organization", placeholder="Your organization")

        with col2:
            role = st.selectbox("Role", ["Researcher", "Analyst", "Manager", "Other"])
            experience = st.slider("Years of experience", 0, 50, 2)
            focus_area = st.selectbox("Focus Area", ["Data Analysis", "Research", "Policy", "Other"])

        # Assessment questions
        st.subheader("Assessment Questions")

        q1 = st.radio(
            "How familiar are you with information integrity concepts?",
            ["Not familiar", "Somewhat familiar", "Very familiar", "Expert"],
        )

        q2 = st.multiselect(
            "What are your main interests? (Select all that apply)",
            [
                "Data Analysis",
                "Narrative Analysis",
                "AI Tools",
                "Research Methods",
                "Policy Development",
            ],
        )

        q3 = st.text_area(
            "What specific challenges do you face in your work?",
            placeholder="Describe your main challenges...",
            height=100,
        )

        submitted = st.form_submit_button("Submit Form #1", use_container_width=True)

        if submitted:
            if name and email:
                form_data = {
                    "name": name,
                    "email": email,
                    "organization": organization,
                    "role": role,
                    "experience": experience,
                    "focus_area": focus_area,
                    "familiarity": q1,
                    "interests": q2,
                    "challenges": q3,
                    "timestamp": datetime.now().isoformat(),
                }

                st.success("✅ Form #1 submitted successfully!")

                if "form1_submissions" not in st.session_state:
                    st.session_state.form1_submissions = []
                st.session_state.form1_submissions.append(form_data)

                st.json(form_data)
            else:
                st.error("❌ Please fill in all required fields (*)")


def render_narrative_frames_page():
    """Render narrative frames page"""

    st.header("📈 Encuadres Narrativos")

    st.markdown(
        """
    ## Understanding Narrative Frames

    Narrative frames are the underlying structures that shape how information is presented and understood.
    They influence how we interpret data and make decisions.
    """
    )

    frames_data = pd.DataFrame(
        {
            "Frame": [
                "Economic",
                "Social",
                "Political",
                "Environmental",
                "Technological",
            ],
            "Description": [
                "Focus on financial impacts and market dynamics",
                "Emphasis on community and social relationships",
                "Political implications and policy considerations",
                "Environmental consequences and sustainability",
                "Technology adoption and digital transformation",
            ],
            "Example": [
                "Cost-benefit analysis of new policies",
                "Community impact assessments",
                "Policy effectiveness studies",
                "Carbon footprint calculations",
                "Digital literacy programs",
            ],
        }
    )

    st.dataframe(frames_data, use_container_width=True)

    st.subheader("Select a Frame to Explore")
    selected_frame = st.selectbox(
        "Choose a narrative frame:", frames_data["Frame"].tolist()
    )

    if selected_frame:
        frame_info = frames_data[frames_data["Frame"] == selected_frame].iloc[0]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Description:** {frame_info['Description']}")
        with col2:
            st.markdown(f"**Example:** {frame_info['Example']}")

    st.subheader("Frame Analysis Tool")
    with st.form("frame_analysis"):
        text_input = st.text_area(
            "Enter text to analyze for narrative frames:",
            placeholder="Paste your text here for frame analysis...",
            height=150,
        )
        analyze_btn = st.form_submit_button("Analyze Frames", use_container_width=True)

        if analyze_btn and text_input:
            detected_frames = []
            for frame in frames_data["Frame"]:
                if frame.lower() in text_input.lower():
                    detected_frames.append(frame)
            if detected_frames:
                st.success(f"Detected frames: {', '.join(detected_frames)}")
            else:
                st.info(
                    "No specific narrative frames detected. Try using more specific terminology."
                )


def render_form2_page():
    """Render Form #2 page"""

    st.header("📝 Form #2")

    with st.form("form2"):
        st.subheader("Follow-up Assessment")

        if "form1_submissions" not in st.session_state or not st.session_state.form1_submissions:
            st.warning("⚠️ Please complete Form #1 first before filling out Form #2.")
            st.stop()

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name *", placeholder="Enter your name")
            email = st.text_input("Email *", placeholder="Enter your email")
        with col2:
            workshop_date = st.date_input("Workshop Date", value=date.today())
            session_id = st.text_input("Session ID", placeholder="Optional session identifier")

        st.subheader("Learning Assessment")
        learning_goals = st.multiselect(
            "What did you hope to learn? (Select all that apply)",
            [
                "Data Analysis",
                "Narrative Frames",
                "AI Tools",
                "Research Methods",
                "Policy Development",
            ],
        )
        knowledge_gained = st.slider(
            "How much new knowledge did you gain? (1-10)", min_value=1, max_value=10, value=5
        )
        practical_applications = st.text_area(
            "How do you plan to apply what you learned?",
            placeholder="Describe your planned applications...",
            height=100,
        )

        st.subheader("Feedback")
        overall_rating = st.slider(
            "Overall workshop rating (1-10)", min_value=1, max_value=10, value=5
        )
        improvements = st.text_area(
            "Suggestions for improvement", placeholder="What could be improved?", height=80
        )

        submitted = st.form_submit_button("Submit Form #2", use_container_width=True)
        if submitted:
            if name and email:
                form_data = {
                    "name": name,
                    "email": email,
                    "workshop_date": workshop_date.isoformat(),
                    "session_id": session_id,
                    "learning_goals": learning_goals,
                    "knowledge_gained": knowledge_gained,
                    "practical_applications": practical_applications,
                    "overall_rating": overall_rating,
                    "improvements": improvements,
                    "timestamp": datetime.now().isoformat(),
                }

                st.success("✅ Form #2 submitted successfully!")
                if "form2_submissions" not in st.session_state:
                    st.session_state.form2_submissions = []
                st.session_state.form2_submissions.append(form_data)
                st.json(form_data)
            else:
                st.error("❌ Please fill in all required fields (*)")


def render_data_analysis_page():
    """Simple data analysis page (placeholder)"""
    st.header("📊 Data Analysis")
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"]) 
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ File uploaded successfully! Shape: {df.shape}")
            st.subheader("📋 Data Preview")
            st.dataframe(df.head(), use_container_width=True)
            st.subheader("📊 Basic Statistics")
            st.dataframe(df.describe(), use_container_width=True)
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")
    else:
        st.info("👆 Please upload a CSV file to start analysis")


def render_ask_ai_page():
    """Render Ask AI page"""
    st.header("🤖 Ask AI")
    st.markdown(
        """
    ## AI-Powered Insights
    
    Use this section to get AI-powered insights about your data and workshop experience.
    """
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask AI about your data or workshop experience..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            response = (
                f"I understand you're asking about: '{prompt}'. This is a simulated AI response. "
                "In a real implementation, this would connect to an AI service."
            )
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    st.subheader("Your Data Summary")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Form #1 Submissions", len(st.session_state.get("form1_submissions", [])))
    with col2:
        st.metric("Form #2 Submissions", len(st.session_state.get("form2_submissions", [])))


if __name__ == "__main__":
    main()
