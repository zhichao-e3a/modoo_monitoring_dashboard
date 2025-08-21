"""
Common plotting utilities and styles for the monitoring dashboard
"""


def apply_black_text_style(fig):
    """Apply black text styling to a Plotly figure

    Args:
        fig: Plotly figure object

    Returns:
        Updated figure with black text styling
    """
    # Update layout for black text
    fig.update_layout(
        font=dict(color='black'),
        title=dict(font=dict(color='black')) if fig.layout.title.text else {},
        legend=dict(font=dict(color='black')),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )

    # Update x-axis styling
    fig.update_xaxes(
        title_font=dict(color='black'),
        tickfont=dict(color='black')
    )

    # Update y-axis styling
    fig.update_yaxes(
        title_font=dict(color='black'),
        tickfont=dict(color='black')
    )

    # Update annotations (subplot titles) to black
    if hasattr(fig, 'layout') and hasattr(fig.layout, 'annotations'):
        for annotation in fig.layout.annotations:
            if hasattr(annotation, 'font'):
                annotation.font.color = 'black'
            else:
                annotation.font = dict(color='black', size=12)

    return fig


def create_signal_config():
    """Create standard signal configuration for FHR and UC signals

    Returns:
        Dictionary with signal configurations
    """
    return {
        'fhr': {
            'color': 'rgb(255,127,14)',  # Orange for FHR
            'range': [50, 210],  # Typical range for FHR
            'title': 'Fetal Heart Rate (FHR)',
            'unit': 'bpm'
        },
        'uc': {
            'color': 'rgb(31,119,180)',  # Blue for UC
            'range': [0, 100],  # Typical range for UC
            'title': 'Uterine Contractions (UC)',
            'unit': 'mmHg'
        }
    }


def create_processing_colors():
    """Create color scheme for processed signals

    Returns:
        Dictionary with color mappings for different processing methods
    """
    return {
        'moving_average': 'rgb(44,160,44)',  # Green
        'savitzky_golay_filter': 'rgb(214,39,40)',  # Red
        'median_filter': 'rgb(148,103,189)',  # Purple
        'bandpass_filter': 'rgb(140,86,75)',  # Brown
        'wavelet_denoising': 'rgb(227,119,194)'  # Pink
    }
