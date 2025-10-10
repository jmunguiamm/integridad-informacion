"""
Sidebar component for navigation.
"""

import streamlit as st
from typing import List, Dict

def render_sidebar() -> str:
    """
    Render the sidebar navigation.
    
    Returns:
        str: Selected page name
    """
    
    st.sidebar.title("🧭 Information Integrity Workshop")
    
    # Navigation menu
    pages = [
        {"name": "Introduction", "icon": "🏠"},
        {"name": "Form #1", "icon": "📊"},
        {"name": "Encuadres narrativos", "icon": "📈"},
        {"name": "Form #2", "icon": "📝"},
        {"name": "Data Analysis", "icon": "⚙️"},
        {"name": "Ask AI", "icon": "⚙️"}
    ]
    
    # Initialize session state for selected page
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = "Introduction"
    
    # Add custom CSS for navigation buttons and sidebar alignment
    st.sidebar.markdown("""
    <style>
    /* Align entire sidebar content to left */
    .css-1d391kg {
        text-align: left !important;
    }
    
    /* Navigation buttons styling */
    .nav-button {
        width: 100%;
        margin: 2px 0;
        padding: 8px 12px;
        border-radius: 6px;
        border: 1px solid #e0e0e0;
        background-color: #f8f9fa;
        color: #333;
        text-align: left;
        font-size: 14px;
        transition: all 0.3s ease;
        justify-content: flex-start;
        display: flex;
        align-items: center;
    }
    .nav-button:hover {
        background-color: #e9ecef;
        border-color: #1f77b4;
    }
    .nav-button.selected {
        background-color: #1f77b4;
        color: white;
        border-color: #1f77b4;
        font-weight: bold;
    }
    .nav-button.selected:hover {
        background-color: #1565c0;
    }
    
    /* Override Streamlit button alignment */
    .stButton > button {
        justify-content: flex-start !important;
        text-align: left !important;
    }
    
    /* Align all sidebar text to left */
    .sidebar .stMarkdown {
        text-align: left !important;
    }
    
    /* Align sidebar headers */
    .sidebar h1, .sidebar h2, .sidebar h3 {
        text-align: left !important;
    }
    
    /* Align sidebar content */
    .sidebar .element-container {
        text-align: left !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create navigation buttons
    st.sidebar.markdown("### 🧭 Navigation")
    
    for idx, page in enumerate(pages):
        # Determine if this page is selected
        is_selected = st.session_state.selected_page == page["name"]
        
        # Create button with custom styling
        if st.sidebar.button(
            f"{page['icon']} {page['name']}",
            key=f"nav_{idx}_{page['name']}",
            use_container_width=True,
            type="primary" if is_selected else "secondary"
        ):
            st.session_state.selected_page = page["name"]
            st.rerun()
    
    selected_page = st.session_state.selected_page
    
    # Add some spacing
    st.sidebar.markdown("---")
    
    # App info
    st.sidebar.subheader("ℹ️ App Info")
    st.sidebar.info(
        """
        **Accelerator Lab**
        
        Version: 0.0.1
        Last updated: 2025
        
        Built with ❤️ by AccLab and Mottum.
        """
    )
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 0.8rem;'>
            Made with Streamlit
        </div>
        """,
        unsafe_allow_html=True
    )
    
    return selected_page

def render_filters_sidebar() -> Dict:
    """
    Render filter options in sidebar.
    
    Returns:
        Dict: Selected filters
    """
    
    st.sidebar.subheader("🔍 Filters")
    
    filters = {}
    
    # Date range filter
    date_range = st.sidebar.date_input(
        "Date Range",
        value=[],
        help="Select date range for filtering"
    )
    filters['date_range'] = date_range
    
    # Category filter
    categories = ['All', 'Category A', 'Category B', 'Category C']
    selected_category = st.sidebar.selectbox(
        "Category",
        categories,
        index=0
    )
    filters['category'] = selected_category
    
    # Status filter
    status_options = ['All', 'Active', 'Inactive', 'Pending']
    selected_status = st.sidebar.multiselect(
        "Status",
        status_options[1:],  # Exclude 'All' from multiselect
        default=status_options[1:]
    )
    filters['status'] = selected_status
    
    # Numeric range filter
    numeric_range = st.sidebar.slider(
        "Numeric Range",
        min_value=0,
        max_value=100,
        value=(0, 100)
    )
    filters['numeric_range'] = numeric_range
    
    return filters

def render_user_info_sidebar():
    """
    Render user information in sidebar.
    """
    
    st.sidebar.subheader("👤 User Info")
    
    # Mock user data (in a real app, this would come from authentication)
    user_data = {
        'name': 'John Doe',
        'email': 'john.doe@example.com',
        'role': 'Admin',
        'last_login': '2024-01-15 10:30:00'
    }
    
    st.sidebar.write(f"**Name:** {user_data['name']}")
    st.sidebar.write(f"**Email:** {user_data['email']}")
    st.sidebar.write(f"**Role:** {user_data['role']}")
    st.sidebar.write(f"**Last Login:** {user_data['last_login']}")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
