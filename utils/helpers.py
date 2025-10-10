"""
Helper functions for the Streamlit app.
"""

import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import streamlit as st

def load_data(file_path: str) -> Optional[pd.DataFrame]:
    """
    Load data from various file formats.
    
    Args:
        file_path (str): Path to the data file
        
    Returns:
        Optional[pd.DataFrame]: Loaded dataframe or None if error
    """
    try:
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            return pd.read_excel(file_path)
        elif file_path.endswith('.json'):
            return pd.read_json(file_path)
        else:
            st.error(f"Unsupported file format: {file_path}")
            return None
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def save_data(data: pd.DataFrame, file_path: str, format: str = 'csv') -> bool:
    """
    Save data to various file formats.
    
    Args:
        data (pd.DataFrame): Data to save
        file_path (str): Output file path
        format (str): File format ('csv', 'xlsx', 'json')
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if format.lower() == 'csv':
            data.to_csv(file_path, index=False)
        elif format.lower() == 'xlsx':
            data.to_excel(file_path, index=False)
        elif format.lower() == 'json':
            data.to_json(file_path, orient='records', indent=2)
        else:
            st.error(f"Unsupported format: {format}")
            return False
        return True
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
        return False

def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email (str): Email to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_sample_data(n_rows: int = 100) -> pd.DataFrame:
    """
    Generate sample data for testing and demos.
    
    Args:
        n_rows (int): Number of rows to generate
        
    Returns:
        pd.DataFrame: Generated sample data
    """
    np.random.seed(42)
    
    data = {
        'id': range(1, n_rows + 1),
        'name': [f'User {i}' for i in range(1, n_rows + 1)],
        'email': [f'user{i}@example.com' for i in range(1, n_rows + 1)],
        'age': np.random.randint(18, 65, n_rows),
        'salary': np.random.normal(50000, 15000, n_rows).round(2),
        'department': np.random.choice(['Sales', 'Marketing', 'Engineering', 'HR', 'Finance'], n_rows),
        'join_date': pd.date_range('2020-01-01', periods=n_rows, freq='D'),
        'is_active': np.random.choice([True, False], n_rows, p=[0.8, 0.2])
    }
    
    return pd.DataFrame(data)

def format_currency(amount: float, currency: str = 'USD') -> str:
    """
    Format number as currency.
    
    Args:
        amount (float): Amount to format
        currency (str): Currency code
        
    Returns:
        str: Formatted currency string
    """
    if currency == 'USD':
        return f"${amount:,.2f}"
    elif currency == 'EUR':
        return f"€{amount:,.2f}"
    else:
        return f"{currency} {amount:,.2f}"

def get_file_size(file_path: str) -> str:
    """
    Get human-readable file size.
    
    Args:
        file_path (str): Path to file
        
    Returns:
        str: Human-readable file size
    """
    try:
        size = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except OSError:
        return "Unknown"

def log_activity(activity: str, details: Dict[str, Any] = None):
    """
    Log user activity (in a real app, you'd save to database).
    
    Args:
        activity (str): Activity description
        details (Dict[str, Any]): Additional details
    """
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "activity": activity,
        "details": details or {}
    }
    
    # In a real app, you'd save this to a database or log file
    if 'activity_log' not in st.session_state:
        st.session_state.activity_log = []
    
    st.session_state.activity_log.append(log_entry)

def clear_session_state():
    """
    Clear all session state data.
    """
    for key in list(st.session_state.keys()):
        del st.session_state[key]

def export_data_as_csv(data: pd.DataFrame, filename: str = None) -> str:
    """
    Convert DataFrame to CSV string for download.
    
    Args:
        data (pd.DataFrame): Data to export
        filename (str): Optional filename
        
    Returns:
        str: CSV string
    """
    return data.to_csv(index=False)

def import_data_from_string(data_string: str, format: str = 'csv') -> Optional[pd.DataFrame]:
    """
    Import data from string (e.g., from uploaded file).
    
    Args:
        data_string (str): Data as string
        format (str): Data format
        
    Returns:
        Optional[pd.DataFrame]: Imported dataframe or None if error
    """
    try:
        if format.lower() == 'csv':
            from io import StringIO
            return pd.read_csv(StringIO(data_string))
        elif format.lower() == 'json':
            from io import StringIO
            return pd.read_json(StringIO(data_string))
        else:
            st.error(f"Unsupported format: {format}")
            return None
    except Exception as e:
        st.error(f"Error importing data: {str(e)}")
        return None

def calculate_metrics(data: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate basic metrics for a dataframe.
    
    Args:
        data (pd.DataFrame): Data to analyze
        
    Returns:
        Dict[str, Any]: Calculated metrics
    """
    metrics = {
        'total_rows': len(data),
        'total_columns': len(data.columns),
        'missing_values': data.isnull().sum().sum(),
        'duplicate_rows': data.duplicated().sum(),
        'numeric_columns': len(data.select_dtypes(include=[np.number]).columns),
        'text_columns': len(data.select_dtypes(include=['object']).columns),
        'date_columns': len(data.select_dtypes(include=['datetime64']).columns)
    }
    
    return metrics
