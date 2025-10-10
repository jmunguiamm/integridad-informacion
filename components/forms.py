"""
Form components for data input and user interaction.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import json

def render_data_form() -> Optional[Dict[str, Any]]:
    """
    Render a data input form.
    
    Returns:
        Optional[Dict[str, Any]]: Form data if submitted, None otherwise
    """
    
    with st.form("data_input_form"):
        st.subheader("📊 Data Input Form")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Name *", placeholder="Enter name")
            email = st.text_input("Email *", placeholder="Enter email")
            age = st.number_input("Age", min_value=0, max_value=120, value=25)
        
        with col2:
            department = st.selectbox(
                "Department",
                ["Sales", "Marketing", "Engineering", "HR", "Finance", "Operations"]
            )
            salary = st.number_input("Salary", min_value=0, value=50000)
            start_date = st.date_input("Start Date", value=date.today())
        
        # Additional fields
        skills = st.multiselect(
            "Skills",
            ["Python", "JavaScript", "SQL", "Excel", "PowerBI", "Tableau", "Machine Learning"]
        )
        
        experience_years = st.slider("Years of Experience", min_value=0, max_value=50, value=2)
        
        notes = st.text_area("Notes", placeholder="Additional notes...", height=100)
        
        # Form submission
        submitted = st.form_submit_button("💾 Save Data", use_container_width=True)
        
        if submitted:
            if name and email:
                form_data = {
                    "name": name,
                    "email": email,
                    "age": age,
                    "department": department,
                    "salary": salary,
                    "start_date": start_date.isoformat(),
                    "skills": skills,
                    "experience_years": experience_years,
                    "notes": notes,
                    "created_at": datetime.now().isoformat()
                }
                
                st.success("✅ Data saved successfully!")
                return form_data
            else:
                st.error("❌ Please fill in all required fields (*)")
                return None
    
    return None

def render_user_registration_form() -> Optional[Dict[str, Any]]:
    """
    Render a user registration form.
    
    Returns:
        Optional[Dict[str, Any]]: Registration data if submitted, None otherwise
    """
    
    with st.form("registration_form"):
        st.subheader("👤 User Registration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            first_name = st.text_input("First Name *", placeholder="Enter first name")
            last_name = st.text_input("Last Name *", placeholder="Enter last name")
            username = st.text_input("Username *", placeholder="Choose username")
        
        with col2:
            email = st.text_input("Email *", placeholder="Enter email address")
            phone = st.text_input("Phone", placeholder="Enter phone number")
            birth_date = st.date_input("Birth Date", value=None)
        
        # Password fields
        password = st.text_input("Password *", type="password", placeholder="Enter password")
        confirm_password = st.text_input("Confirm Password *", type="password", placeholder="Confirm password")
        
        # Preferences
        st.subheader("Preferences")
        col3, col4 = st.columns(2)
        
        with col3:
            newsletter = st.checkbox("Subscribe to newsletter")
            notifications = st.checkbox("Enable notifications")
        
        with col4:
            theme = st.selectbox("Preferred theme", ["Light", "Dark", "Auto"])
            language = st.selectbox("Language", ["English", "Spanish", "French", "German"])
        
        # Terms and conditions
        terms_accepted = st.checkbox("I agree to the Terms and Conditions *")
        
        # Submit button
        submitted = st.form_submit_button("🚀 Register", use_container_width=True)
        
        if submitted:
            if not all([first_name, last_name, username, email, password, confirm_password]):
                st.error("❌ Please fill in all required fields (*)")
                return None
            
            if password != confirm_password:
                st.error("❌ Passwords do not match")
                return None
            
            if not terms_accepted:
                st.error("❌ Please accept the Terms and Conditions")
                return None
            
            registration_data = {
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "email": email,
                "phone": phone,
                "birth_date": birth_date.isoformat() if birth_date else None,
                "newsletter": newsletter,
                "notifications": notifications,
                "theme": theme,
                "language": language,
                "terms_accepted": terms_accepted,
                "registered_at": datetime.now().isoformat()
            }
            
            st.success("✅ Registration successful!")
            return registration_data
    
    return None

def render_feedback_form() -> Optional[Dict[str, Any]]:
    """
    Render a feedback form.
    
    Returns:
        Optional[Dict[str, Any]]: Feedback data if submitted, None otherwise
    """
    
    with st.form("feedback_form"):
        st.subheader("💬 Feedback Form")
        
        # Rating
        rating = st.slider("Overall Rating", min_value=1, max_value=5, value=3)
        
        # Feedback categories
        categories = st.multiselect(
            "Categories",
            ["User Interface", "Performance", "Features", "Support", "Documentation", "Other"]
        )
        
        # Feedback text
        feedback_text = st.text_area(
            "Your Feedback",
            placeholder="Please share your thoughts, suggestions, or report any issues...",
            height=150
        )
        
        # Contact information (optional)
        st.subheader("Contact Information (Optional)")
        col1, col2 = st.columns(2)
        
        with col1:
            contact_name = st.text_input("Name", placeholder="Your name")
        
        with col2:
            contact_email = st.text_input("Email", placeholder="Your email")
        
        # Submit button
        submitted = st.form_submit_button("📤 Submit Feedback", use_container_width=True)
        
        if submitted:
            if not feedback_text.strip():
                st.error("❌ Please provide your feedback")
                return None
            
            feedback_data = {
                "rating": rating,
                "categories": categories,
                "feedback_text": feedback_text,
                "contact_name": contact_name,
                "contact_email": contact_email,
                "submitted_at": datetime.now().isoformat()
            }
            
            st.success("✅ Thank you for your feedback!")
            return feedback_data
    
    return None

def render_settings_form() -> Optional[Dict[str, Any]]:
    """
    Render a settings configuration form.
    
    Returns:
        Optional[Dict[str, Any]]: Settings data if submitted, None otherwise
    """
    
    with st.form("settings_form"):
        st.subheader("⚙️ Application Settings")
        
        # General settings
        st.subheader("General")
        col1, col2 = st.columns(2)
        
        with col1:
            app_name = st.text_input("App Name", value="Streamlit Template App")
            theme = st.selectbox("Theme", ["Light", "Dark", "Auto"])
            language = st.selectbox("Language", ["English", "Spanish", "French", "German"])
        
        with col2:
            timezone = st.selectbox(
                "Timezone",
                ["UTC", "EST", "PST", "CET", "JST", "AEST"]
            )
            date_format = st.selectbox(
                "Date Format",
                ["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY", "DD-MM-YYYY"]
            )
        
        # Data settings
        st.subheader("Data")
        col3, col4 = st.columns(2)
        
        with col3:
            auto_save = st.checkbox("Auto-save data", value=True)
            max_file_size = st.number_input("Max file size (MB)", min_value=1, max_value=100, value=10)
        
        with col4:
            data_retention = st.number_input("Data retention (days)", min_value=1, max_value=365, value=30)
            backup_frequency = st.selectbox(
                "Backup frequency",
                ["Daily", "Weekly", "Monthly", "Never"]
            )
        
        # Notification settings
        st.subheader("Notifications")
        col5, col6 = st.columns(2)
        
        with col5:
            email_notifications = st.checkbox("Email notifications", value=True)
            push_notifications = st.checkbox("Push notifications", value=False)
        
        with col6:
            notification_frequency = st.selectbox(
                "Notification frequency",
                ["Immediate", "Daily", "Weekly", "Never"]
            )
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Settings", use_container_width=True)
        
        if submitted:
            settings_data = {
                "app_name": app_name,
                "theme": theme,
                "language": language,
                "timezone": timezone,
                "date_format": date_format,
                "auto_save": auto_save,
                "max_file_size": max_file_size,
                "data_retention": data_retention,
                "backup_frequency": backup_frequency,
                "email_notifications": email_notifications,
                "push_notifications": push_notifications,
                "notification_frequency": notification_frequency,
                "updated_at": datetime.now().isoformat()
            }
            
            st.success("✅ Settings saved successfully!")
            return settings_data
    
    return None

def validate_form_data(form_data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """
    Validate form data.
    
    Args:
        form_data (Dict[str, Any]): Form data to validate
        required_fields (List[str]): List of required field names
        
    Returns:
        List[str]: List of validation errors
    """
    
    errors = []
    
    for field in required_fields:
        if field not in form_data or not form_data[field]:
            errors.append(f"{field} is required")
    
    return errors

def save_form_data_to_session(form_data: Dict[str, Any], key: str):
    """
    Save form data to session state.
    
    Args:
        form_data (Dict[str, Any]): Form data to save
        key (str): Session state key
    """
    
    if key not in st.session_state:
        st.session_state[key] = []
    
    st.session_state[key].append(form_data)
