"""
Chart components for data visualization.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, List, Any, Optional

def create_sample_chart(chart_type: str = "line", data: Optional[pd.DataFrame] = None) -> go.Figure:
    """
    Create a sample chart based on type.
    
    Args:
        chart_type (str): Type of chart to create
        data (Optional[pd.DataFrame]): Data to use, generates sample if None
        
    Returns:
        go.Figure: Plotly figure object
    """
    
    if data is None:
        # Generate sample data
        np.random.seed(42)
        n_points = 50
        
        sample_data = pd.DataFrame({
            'x': range(n_points),
            'y': np.cumsum(np.random.randn(n_points)),
            'category': np.random.choice(['A', 'B', 'C'], n_points),
            'value': np.random.randint(10, 100, n_points)
        })
        data = sample_data
    
    if chart_type == "line":
        fig = px.line(data, x='x', y='y', title='Line Chart')
        
    elif chart_type == "bar":
        fig = px.bar(data, x='category', y='value', title='Bar Chart')
        
    elif chart_type == "scatter":
        fig = px.scatter(data, x='x', y='y', color='category', title='Scatter Plot')
        
    elif chart_type == "histogram":
        fig = px.histogram(data, x='value', title='Histogram')
        
    elif chart_type == "pie":
        category_counts = data['category'].value_counts()
        fig = px.pie(values=category_counts.values, names=category_counts.index, title='Pie Chart')
        
    elif chart_type == "heatmap":
        # Create correlation matrix for heatmap
        numeric_data = data.select_dtypes(include=[np.number])
        corr_matrix = numeric_data.corr()
        fig = px.imshow(corr_matrix, title='Correlation Heatmap')
        
    else:
        # Default to line chart
        fig = px.line(data, x='x', y='y', title='Default Line Chart')
    
    return fig

def create_dashboard_charts(data: pd.DataFrame) -> Dict[str, go.Figure]:
    """
    Create a set of dashboard charts.
    
    Args:
        data (pd.DataFrame): Data for charts
        
    Returns:
        Dict[str, go.Figure]: Dictionary of chart figures
    """
    
    charts = {}
    
    # Line chart
    charts['line'] = create_sample_chart("line", data)
    
    # Bar chart
    charts['bar'] = create_sample_chart("bar", data)
    
    # Scatter plot
    charts['scatter'] = create_sample_chart("scatter", data)
    
    # Histogram
    charts['histogram'] = create_sample_chart("histogram", data)
    
    return charts

def render_chart_controls() -> Dict[str, Any]:
    """
    Render chart customization controls.
    
    Returns:
        Dict[str, Any]: Chart configuration
    """
    
    st.subheader("🎨 Chart Customization")
    
    config = {}
    
    col1, col2 = st.columns(2)
    
    with col1:
        config['show_grid'] = st.checkbox("Show Grid", value=True)
        config['show_legend'] = st.checkbox("Show Legend", value=True)
        config['show_labels'] = st.checkbox("Show Labels", value=False)
    
    with col2:
        config['color_scheme'] = st.selectbox(
            "Color Scheme",
            ["Default", "Viridis", "Plasma", "Inferno", "Magma", "Cividis"]
        )
        
        config['chart_height'] = st.slider(
            "Chart Height",
            min_value=300,
            max_value=800,
            value=500
        )
    
    # Advanced options
    with st.expander("Advanced Options"):
        config['opacity'] = st.slider(
            "Opacity",
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            step=0.1
        )
        
        config['line_width'] = st.slider(
            "Line Width",
            min_value=1,
            max_value=10,
            value=2
        )
        
        config['marker_size'] = st.slider(
            "Marker Size",
            min_value=1,
            max_value=20,
            value=6
        )
    
    return config

def apply_chart_config(fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
    """
    Apply configuration to a chart.
    
    Args:
        fig (go.Figure): Chart figure
        config (Dict[str, Any]): Configuration to apply
        
    Returns:
        go.Figure: Updated figure
    """
    
    # Update layout
    fig.update_layout(
        showlegend=config.get('show_legend', True),
        height=config.get('chart_height', 500),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    # Update axes
    if config.get('show_grid', True):
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    else:
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False)
    
    # Update traces
    for trace in fig.data:
        if hasattr(trace, 'opacity'):
            trace.opacity = config.get('opacity', 1.0)
        if hasattr(trace, 'line'):
            trace.line.width = config.get('line_width', 2)
        if hasattr(trace, 'marker'):
            trace.marker.size = config.get('marker_size', 6)
    
    return fig

def create_interactive_chart(data: pd.DataFrame) -> go.Figure:
    """
    Create an interactive chart with multiple views.
    
    Args:
        data (pd.DataFrame): Data for the chart
        
    Returns:
        go.Figure: Interactive figure
    """
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Line Chart', 'Bar Chart', 'Scatter Plot', 'Histogram'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Add line chart
    fig.add_trace(
        go.Scatter(x=data['x'], y=data['y'], mode='lines', name='Line'),
        row=1, col=1
    )
    
    # Add bar chart
    category_counts = data['category'].value_counts()
    fig.add_trace(
        go.Bar(x=category_counts.index, y=category_counts.values, name='Bar'),
        row=1, col=2
    )
    
    # Add scatter plot
    fig.add_trace(
        go.Scatter(x=data['x'], y=data['y'], mode='markers', name='Scatter'),
        row=2, col=1
    )
    
    # Add histogram
    fig.add_trace(
        go.Histogram(x=data['value'], name='Histogram'),
        row=2, col=2
    )
    
    fig.update_layout(height=600, showlegend=True, title_text="Interactive Dashboard")
    
    return fig

def export_chart(fig: go.Figure, format: str = "png") -> bytes:
    """
    Export chart to various formats.
    
    Args:
        fig (go.Figure): Chart figure
        format (str): Export format ('png', 'jpeg', 'pdf', 'svg')
        
    Returns:
        bytes: Chart data
    """
    
    return fig.to_image(format=format, width=800, height=600, scale=2)
