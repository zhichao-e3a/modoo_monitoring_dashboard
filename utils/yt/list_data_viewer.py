from utils.yt.plot_utils import *

import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

import streamlit as st

def is_list_string(s):
    """Check if a string or object represents a list"""
    if isinstance(s, list):
        return True
    if isinstance(s, str):
        try:
            # First try json.loads for safer parsing
            value = json.loads(s)
            return isinstance(value, list)
        except:
            try:
                # Fallback to eval for legacy format
                value = eval(s)
                return isinstance(value, list)
            except:
                # Try comma-separated format
                if ',' in s:
                    try:
                        values = [float(x.strip()) for x in s.split(',')]
                        return True
                    except:
                        pass
                return False
    return False

def parse_list_string(s):
    """Parse a string or object into a list"""
    if isinstance(s, list):
        return s
    if isinstance(s, str):
        try:
            # First try json.loads for safer parsing
            value = json.loads(s)
            if isinstance(value, list):
                return value
        except:
            try:
                # Fallback to eval for legacy format
                value = eval(s)
                if isinstance(value, list):
                    return value
            except:
                # Try comma-separated format
                if ',' in s:
                    try:
                        return [float(x.strip()) for x in s.split(',')]
                    except:
                        pass
    return None

def display_list_data(df):
    """Display visualization for columns containing list data"""
    st.subheader("Signal Data Visualization")
    
    # Check if dataframe is empty
    if df.empty:
        st.warning("No data available")
        return
    
    # Find columns containing list data
    list_columns = []
    for col in df.columns:
        # Sample a few non-null values to check format
        sample_values = df[col].dropna().head(5)
        for val in sample_values:
            if is_list_string(str(val)):
                list_columns.append(col)
                break
    
    if not list_columns:
        st.info("No signal data found in the dataset")
        # Show column information to help debug
        with st.expander("Column Information"):
            for col in df.columns:
                st.write(f"Column Name: {col}")
                st.write(f"Data Type: {df[col].dtype}")
                st.write(f"Sample Value: {df[col].head(1).values[0]}")
                st.write("---")
        return
    
    # Create control container with tabs
    control_tabs = st.tabs([
        "Signal Selection",
        "Signal Processing",
        "Additional Info"
    ])
    
    # First tab: Signal selection
    with control_tabs[0]:
        fhr_col = next((col for col in list_columns if 'fhr' in col.lower()), None)
        uc_col = next((col for col in list_columns if 'uc' in col.lower()), None)
        
        if fhr_col and uc_col:
            signal_view = st.radio(
                "Signal View",
                ["FHR", "UC", "Both"],
                key="signal_view",
                help="Select which signals to display"
            )
            
            # Set selected signals based on view choice
            if signal_view == "FHR":
                selected_signals = [fhr_col]
            elif signal_view == "UC":
                selected_signals = [uc_col]
            else:  # Both
                selected_signals = [fhr_col, uc_col]
        else:
            # Fallback to single signal selection if FHR/UC not found
            selected_signal = st.selectbox(
                "Select Signal",
                list_columns,
                index=0 if list_columns else None,
                key="signal_column"
            )
            selected_signals = [selected_signal] if selected_signal else []
    
    # Second tab: Signal processing
    processing_params = {}
    with control_tabs[1]:
        if selected_signals:
            # Signal processing toggle
            enable_processing = st.checkbox("Enable Signal Processing", key="enable_processing")
            
            if enable_processing:
                from signal_smoother import show_smoother_ui, process_signal
                # Create processing options for each selected signal
                if len(selected_signals) > 1:
                    processing_cols = st.columns(2)
                else:
                    processing_cols = [st.container()]
                
                for idx, signal in enumerate(selected_signals):
                    signal_type = "FHR" if "fhr" in signal.lower() else "UC"
                    with processing_cols[min(idx, len(processing_cols)-1)]:
                        st.markdown(f"### {signal_type} Signal Processing")
                        # Use signal name as unique key prefix
                        method, params = show_smoother_ui(key_prefix=f"signal_{idx}_{signal}")
                        processing_params[signal] = (method, params)
    
    # Third tab: Additional information
    with control_tabs[2]:
        # Info display column selection
        info_columns = [col for col in df.columns if col not in list_columns]
        display_names = {col: col[:30] + '...' if len(col) > 30 else col for col in info_columns}
        
        default_columns = []
        for col in ["composite_key", "gestational_age_days"]:
            if col in info_columns:
                default_columns.append(col)
        
        selected_info_columns = st.multiselect(
            "Select Additional Information",
            options=info_columns,
            default=default_columns if default_columns else None,
            format_func=lambda x: display_names[x],
            help="Choose additional columns to display alongside the signal data"
        )
    
    # Row selection container
    row_selection_container = st.container()
    with row_selection_container:
        if selected_signals:
            # Initialize selected_row
            selected_row = 0
            
            if len(df) == 0:
                st.warning("No data points available")
                selected_row = None
            elif len(df) == 1:
                st.info("Only one data point available")
                selected_row = 0
            else:
                row_indices = list(range(len(df)))
                # Create columns for point selection
                point_col1, point_col2 = st.columns([1, 1])
                
                with point_col1:
                    # Dropdown for precise selection
                    selected_row = st.selectbox(
                        "Select Data Point",
                        row_indices,
                        format_func=lambda x: f"Point {x}",
                        key="signal_row"
                    )
                
                with point_col2:
                    # Slider for continuous browsing
                    selected_row = st.slider(
                        "Browse Data Points",
                        min_value=0,
                        max_value=len(df) - 1,
                        value=selected_row,
                        key="signal_row_slider"
                    )
    
    if selected_signals and selected_row is not None:
        # Signal configuration
        signal_config = create_signal_config()
        processing_colors = create_processing_colors()
        
        # Create info box text
        info_text = "<br>".join([
            f"<b>{col}:</b> {df.iloc[selected_row][col]}"
            for col in selected_info_columns
            if col in df.columns
        ])
        
        # Process signal data
        signal_data = {}
        for signal_col in selected_signals:
            # Get selected row's signal data
            raw_data = df.iloc[selected_row][signal_col]
            
            # Debug information
            st.write(f"🔍 Processing signal: {signal_col}")
            
            try:
                # Try to parse signal data
                values = parse_list_string(raw_data)
                if values is None:
                    st.error(f"Unable to parse column '{signal_col}' data")
                    continue
                
                st.write(f"✅ Loaded {len(values)} data points")
                
                # Determine signal type
                is_fhr = 'fhr' in signal_col.lower()
                signal_type = 'fhr' if is_fhr else 'uc'
                
                # Add to signal data dictionary
                signal_data[signal_col] = {
                    'values': values,
                    'type': signal_type,
                    'config': signal_config[signal_type],
                    'name': 'FHR Signal' if is_fhr else 'UC Signal'
                }
                
                # If signal processing is enabled
                if enable_processing and signal_col in processing_params:
                    st.write(f"🔧 Applying signal processing...")
                    try:
                        method, params = processing_params[signal_col]
                        
                        # Import process_signal here to make sure it's available
                        from signal_smoother import process_signal
                        processed_values = process_signal(values, method, params)
                        
                        if processed_values is not None and hasattr(processed_values, '__len__') and len(processed_values) > 0:
                            processed_key = f"{signal_col}_processed"
                            signal_data[processed_key] = {
                                'values': processed_values,
                                'type': signal_type,
                                'config': signal_config[signal_type],
                                'name': f'Processed {signal_data[signal_col]["name"]} ({method})'
                            }
                            st.write(f"✅ Processing complete: {method}")
                        else:
                            st.error("❌ Processing failed")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            except Exception as e:
                st.error(f"Error processing signal '{signal_col}': {str(e)}")
                continue
        
        # Process and display signals
        if not signal_data:
            st.error("No valid signal data available for display")
            return
        
        # Debug: Show signal_data keys and structure
        st.write(f"📋 Available signals: {list(signal_data.keys())}")
        total_signals = len(signal_data)
        original_signals = len([k for k in signal_data.keys() if 'processed' not in k])
        processed_signals = total_signals - original_signals
        st.write(f"📊 Original: {original_signals}, Processed: {processed_signals}, Total: {total_signals}")
        
        # Decide plot layout
        show_both = len(selected_signals) == 2
        if enable_processing:
            # For signal processing, arrange original and processed signals vertically
            # Count original and processed signals separately for each signal type
            signal_types = {}
            for key, data in signal_data.items():
                signal_type = data['type']
                if signal_type not in signal_types:
                    signal_types[signal_type] = {'original': [], 'processed': []}
                
                if 'processed' in key:
                    signal_types[signal_type]['processed'].append((key, data))
                else:
                    signal_types[signal_type]['original'].append((key, data))
            
            # Calculate layout: vertical arrangement for original vs processed
            total_plots = 0
            for signal_type in signal_types:
                original_count = len(signal_types[signal_type]['original'])
                processed_count = len(signal_types[signal_type]['processed'])
                total_plots += max(original_count, processed_count) * 2  # original + processed
            
            # Use 2 rows per signal (original + processed), 1 column per signal type
            n_cols = len(signal_types) if len(signal_types) > 1 else 1
            n_rows = 2  # Original signal on top, processed on bottom
            
            subplot_titles = []
            for signal_type in signal_types:
                if signal_types[signal_type]['original']:
                    original_name = signal_types[signal_type]['original'][0][1]['name']
                    subplot_titles.append(f"Original {original_name}")
                if signal_types[signal_type]['processed']:
                    processed_name = signal_types[signal_type]['processed'][0][1]['name']
                    subplot_titles.append(processed_name)
            
            fig = make_subplots(
                rows=n_rows,
                cols=n_cols,
                subplot_titles=subplot_titles,
                vertical_spacing=0.2,  # More space between rows
                horizontal_spacing=0.1
            )
            
            # Update subplot title font colors
            for annotation in fig['layout']['annotations']:
                annotation['font'] = dict(color='black', size=12)
            
            # Add signals to subplots with vertical arrangement
            col_idx = 1
            for signal_type in signal_types:
                # Add original signal (top row)
                if signal_types[signal_type]['original']:
                    key, data = signal_types[signal_type]['original'][0]
                    x = list(range(len(data['values'])))
                    
                    fig.add_trace(
                        go.Scatter(
                            x=x,
                            y=data['values'],
                            name=data['name'],
                            line=dict(color=data['config']['color'])
                        ),
                        row=1,  # Top row for original
                        col=col_idx
                    )
                    
                    # Update axes for original signal
                    fig.update_xaxes(
                        title_text="Sample Points" if col_idx == 1 else "",
                        title_font=dict(color='black'),
                        tickfont=dict(color='black'),
                        showgrid=True,
                        gridwidth=1,
                        gridcolor='LightGray',
                        row=1,
                        col=col_idx
                    )
                    fig.update_yaxes(
                        title_text=data['config']['title'],
                        title_font=dict(color='black'),
                        tickfont=dict(color='black'),
                        showgrid=True,
                        gridwidth=1,
                        gridcolor='LightGray',
                        range=data['config']['range'],
                        row=1,
                        col=col_idx
                    )
                
                # Add processed signal (bottom row)
                if signal_types[signal_type]['processed']:
                    key, data = signal_types[signal_type]['processed'][0]
                    x = list(range(len(data['values'])))
                    
                    fig.add_trace(
                        go.Scatter(
                            x=x,
                            y=data['values'],
                            name=data['name'],
                            line=dict(color=data['config']['color'], dash='dash')  # Dashed line for processed
                        ),
                        row=2,  # Bottom row for processed
                        col=col_idx
                    )
                    
                    # Update axes for processed signal
                    fig.update_xaxes(
                        title_text="Sample Points",
                        title_font=dict(color='black'),
                        tickfont=dict(color='black'),
                        showgrid=True,
                        gridwidth=1,
                        gridcolor='LightGray',
                        row=2,
                        col=col_idx
                    )
                    fig.update_yaxes(
                        title_text=data['config']['title'],
                        title_font=dict(color='black'),
                        tickfont=dict(color='black'),
                        showgrid=True,
                        gridwidth=1,
                        gridcolor='LightGray',
                        range=data['config']['range'],
                        row=2,
                        col=col_idx
                    )
                
                col_idx += 1
        else:
            # Only show original signals
            n_rows = 2 if show_both else 1
            n_cols = 1
            
            fig = make_subplots(
                rows=n_rows,
                cols=n_cols,
                subplot_titles=[data['name'] for data in signal_data.values() if 'processed' not in data['name'].lower()],
                vertical_spacing=0.15
            )
            
            # Update subplot title font colors
            for annotation in fig['layout']['annotations']:
                annotation['font'] = dict(color='black', size=12)
            
            # Add signals to subplots
            for idx, (_, data) in enumerate(signal_data.items()):
                if 'processed' in data['name'].lower():
                    continue
                
                row = idx + 1 if show_both else 1
                
                # Create x-axis data
                x = list(range(len(data['values'])))
                
                # Add signal curve
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=data['values'],
                        name=data['name'],
                        line=dict(color=data['config']['color'])
                    ),
                    row=row,
                    col=1
                )
                
                # Update axes
                fig.update_xaxes(
                    title_text="Sample Points",
                    title_font=dict(color='black'),
                    tickfont=dict(color='black'),
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='LightGray',
                    row=row
                )
                fig.update_yaxes(
                    title_text=data['config']['title'],
                    title_font=dict(color='black'),
                    tickfont=dict(color='black'),
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='LightGray',
                    range=data['config']['range'],
                    row=row
                )
        
        # Update layout for all plot types and apply black text styling
        fig.update_layout(
            title=dict(
                text="Signal Data Visualization - Original vs Processed Comparison",
                font=dict(color='black', size=16)
            ),
            height=800,  # Increased height for vertical layout
            showlegend=True,
            legend=dict(
                font=dict(color='black')
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=50, r=50, t=80, b=50),  # More top margin for title
            font=dict(color='black')
        )
        
        # Apply consistent black text styling directly
        # fig = apply_black_text_style(fig)  # Temporarily disabled
        
        # Display the plot
        st.plotly_chart(fig, use_container_width=True)
        
        # Define available statistics
        statistic_options = {
            "Basic Statistics": {
                "Total Count": lambda values: len(values),
                "Non-zero Count": lambda values: len([x for x in values if x != 0]),
                "Zero Count": lambda values: len([x for x in values if x == 0])
            },
            "Central Tendency": {
                "Mean": lambda values: np.mean(values),
                "Median": lambda values: np.median(values),
                "Mode": lambda values: float(stats.mode(values, keepdims=True)[0][0])
            },
            "Dispersion": {
                "Standard Deviation": lambda values: np.std(values),
                "Variance": lambda values: np.var(values),
                "Range": lambda values: max(values) - min(values),
                "IQR": lambda values: np.percentile(values, 75) - np.percentile(values, 25)
            },
            "Extremes": {
                "Maximum": lambda values: max(values),
                "Minimum": lambda values: min(values),
                "Non-zero Minimum": lambda values: min([x for x in values if x != 0]) if any(x != 0 for x in values) else 0
            }
        }
        
        # Display statistics section
        with st.expander("Signal Statistics"):
            for signal_name, signal_data in signal_data.items():
                if isinstance(signal_data, dict) and 'values' in signal_data:
                    signal_values = np.array(signal_data['values'])
                    if len(signal_values) > 0:
                        st.subheader(f"{signal_data['name']} Statistics")
                        
                        # Create columns for different statistic categories
                        cols = st.columns(len(statistic_options))
                        
                        # Display statistics in columns
                        for col, (category, stats_dict) in zip(cols, statistic_options.items()):
                            with col:
                                st.markdown(f"**{category}**")
                                for stat_name, stat_func in stats_dict.items():
                                    try:
                                        value = stat_func(signal_values)
                                        st.write(f"{stat_name}: {value:.2f}")
                                    except Exception as e:
                                        st.write(f"{stat_name}: N/A")
                        
                        # Calculate non-zero values statistics
                        non_zero_values = signal_values[signal_values != 0]
                        
                        # Show distribution plots
                        if st.checkbox("Show Distribution Plots", key=f"dist_{signal_name}"):
                            dist_cols = st.columns(2)
                            
                            with dist_cols[0]:
                                # Show distribution of all values
                                fig1 = go.Figure(go.Histogram(
                                    x=signal_values,
                                    name="All Values",
                                    opacity=0.75
                                ))
                                fig1.update_layout(
                                    title="Distribution of All Values",
                                    xaxis_title="Value",
                                    yaxis_title="Count",
                                    height=300,
                                    showlegend=True
                                )
                                st.plotly_chart(fig1, use_container_width=True)
                            
                            with dist_cols[1]:
                                # Show distribution of non-zero values
                                if len(non_zero_values) > 0:
                                    fig2 = go.Figure(go.Histogram(
                                        x=non_zero_values,
                                        name="Non-zero Values",
                                        opacity=0.75
                                    ))
                                    fig2.update_layout(
                                        title="Distribution of Non-zero Values",
                                        xaxis_title="Value",
                                        yaxis_title="Count",
                                        height=300,
                                        showlegend=True
                                    )
                                    st.plotly_chart(fig2, use_container_width=True)
                                else:
                                    st.write("No non-zero values found")
                        
                        # Show raw data table
                        if st.checkbox("Show Raw Data", key=f"raw_{signal_name}"):
                            st.write("Raw Signal Data")
                            st.dataframe(pd.DataFrame({
                                "Index": range(len(signal_values)),
                                "Value": signal_values
                            }))
