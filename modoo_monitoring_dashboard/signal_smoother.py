import numpy as np
import pandas as pd
from scipy.signal import savgol_filter, medfilt, butter, filtfilt
import streamlit as st

try:
    import pywt
    WAVELET_AVAILABLE = True
except ImportError:
    WAVELET_AVAILABLE = False

class SignalSmoother:
    """Signal smoothing and denoising class"""
    
    @staticmethod
    def moving_average(signal, window_size=5):
        """Moving average filter
        Args:
            signal: Input signal
            window_size: Window size
        """
        return pd.Series(signal).rolling(window=window_size, center=True).mean().fillna(method='bfill').fillna(method='ffill').values
    
    @staticmethod
    def savitzky_golay(signal, window_size=11, poly_order=3):
        """Savitzky-Golay filter
        Args:
            signal: Input signal
            window_size: Window size (odd number)
            poly_order: Polynomial order
        """
        if window_size % 2 == 0:
            window_size += 1
        return savgol_filter(signal, window_size, poly_order)
    
    @staticmethod
    def median_filter(signal, kernel_size=5):
        """Median filter
        Args:
            signal: Input signal
            kernel_size: Kernel size
        """
        return medfilt(signal, kernel_size)
    
    @staticmethod
    def bandpass_filter(signal, lowcut=0.03, highcut=3.0, fs=4.0, order=5):
        """Bandpass filter
        Args:
            signal: Input signal
            lowcut: Low frequency cutoff
            highcut: High frequency cutoff
            fs: Sampling rate
            order: Filter order
        """
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(order, [low, high], btype='band')
        return filtfilt(b, a, signal)
    
    @staticmethod
    def wavelet_denoise(signal, wavelet='db4', level=3):
        """Wavelet denoising
        If PyWavelets is not available, Savitzky-Golay filter is used as a fallback.
        
        Args:
            signal: Input signal
            wavelet: Wavelet basis function
            level: Decomposition level
        """
        if WAVELET_AVAILABLE:
            # Wavelet decomposition
            coeffs = pywt.wavedec(signal, wavelet, level=level)
            
            # Thresholding
            threshold = np.std(coeffs[-1]) * np.sqrt(2 * np.log(len(signal)))
            for i in range(1, len(coeffs)):
                coeffs[i] = pywt.threshold(coeffs[i], threshold, mode='soft')
            
            # Wavelet reconstruction
            return pywt.waverec(coeffs, wavelet)
        else:
            # Fallback to Savitzky-Golay if PyWavelets is not available
            st.warning("PyWavelets is not available, using Savitzky-Golay filter as a fallback.")
            window_size = 15  # Must be odd
            poly_order = 3
            return savgol_filter(signal, window_size, poly_order)

def show_smoother_ui(key_prefix=""):
    """Display user interface for signal processing
    Args:
        key_prefix: Unique prefix for widget keys to avoid duplicates
    """
    # Select processing method
    method = st.selectbox(
        "Select Processing Method",
        ["Moving Average", "Savitzky-Golay Filter", "Median Filter", "Bandpass Filter", "Wavelet Denoising"],
        help="Choose a method for signal smoothing or denoising",
        key=f"{key_prefix}_method_selector"
    )
    
    # Display parameters based on the selected method
    params = {}
    param_container = st.container()
    
    with param_container:
        if method == "Moving Average":
            params['window_size'] = st.slider(
                "Window Size", 
                3, 21, 5, 2,
                help="A larger window makes the signal smoother but may lose details",
                key=f"{key_prefix}_moving_avg_window"
            )
            
        elif method == "Savitzky-Golay Filter":
            params['window_size'] = st.slider(
                "Window Size", 
                5, 21, 11, 2,
                help="Window size must be an odd number",
                key=f"{key_prefix}_sg_window"
            )
            params['poly_order'] = st.slider(
                "Polynomial Order",
                2, 5, 3, 1,
                help="A higher order can preserve more details",
                key=f"{key_prefix}_sg_poly_order"
            )
            
        elif method == "Median Filter":
            params['kernel_size'] = st.slider(
                "Kernel Size",
                3, 15, 5, 2,
                help="A larger kernel removes noise more effectively but may blur signal details",
                key=f"{key_prefix}_median_kernel"
            )
            
        elif method == "Bandpass Filter":
            params['lowcut'] = st.number_input(
                "Low Cutoff (Hz)",
                0.01, 1.0, 0.03, 0.01,
                help="Signals below this frequency will be filtered out",
                key=f"{key_prefix}_bp_lowcut"
            )
            params['highcut'] = st.number_input(
                "High Cutoff (Hz)",
                1.0, 10.0, 3.0, 0.5,
                help="Signals above this frequency will be filtered out",
                key=f"{key_prefix}_bp_highcut"
            )
            params['fs'] = st.number_input(
                "Sampling Rate (Hz)",
                1.0, 100.0, 4.0, 1.0,
                help="The sampling frequency of the signal",
                key=f"{key_prefix}_bp_fs"
            )
            params['order'] = st.slider(
                "Filter Order",
                2, 8, 5, 1,
                help="A higher order provides a steeper frequency response",
                key=f"{key_prefix}_bp_order"
            )
            
        elif method == "Wavelet Denoising":
            if WAVELET_AVAILABLE:
                params['wavelet'] = st.selectbox(
                    "Wavelet Basis Function",
                    ['db4', 'sym5', 'coif3', 'haar'],
                    help="Different wavelet functions are suitable for different types of signals",
                    key=f"{key_prefix}_wavelet_basis"
                )
                params['level'] = st.slider(
                    "Decomposition Level",
                    1, 5, 3, 1,
                    help="A higher decomposition level can handle lower frequency noise",
                    key=f"{key_prefix}_wavelet_level"
                )
            else:
                st.warning("PyWavelets is not installed, using Savitzky-Golay filter as a fallback.")
                params = {'window_size': 15, 'poly_order': 3}
    # This layout configuration is handled above, no need to duplicate
    
    return method, params

def process_signal(signal, method, params):
    """Process signal
    Args:
        signal: Input signal
        method: Processing method
        params: Parameter dictionary
    """
    smoother = SignalSmoother()
    
    # Convert input to numpy array if it isn't already
    import numpy as np
    signal = np.array(signal)
    
    result = None
    
    if method == "Moving Average":
        result = smoother.moving_average(signal, params['window_size'])
    
    elif method == "Savitzky-Golay Filter":
        result = smoother.savitzky_golay(signal, params['window_size'], params['poly_order'])
    
    elif method == "Median Filter":
        result = smoother.median_filter(signal, params['kernel_size'])
    
    elif method == "Bandpass Filter":
        result = smoother.bandpass_filter(
            signal, 
            params['lowcut'],
            params['highcut'],
            params['fs'],
            params['order']
        )
    
    elif method == "Wavelet Denoising":
        result = smoother.wavelet_denoise(signal, params['wavelet'], params['level'])
    
    else:
        result = signal
    
    # Ensure result is a list for consistency
    if result is not None:
        if hasattr(result, 'tolist'):
            return result.tolist()
        elif isinstance(result, (list, tuple)):
            return list(result)
        else:
            return [float(result)]  # Single value case
    
    return signal.tolist() if hasattr(signal, 'tolist') else list(signal)

def calculate_metrics(original_signal, processed_signal):
    """Calculate signal processing performance metrics"""
    # Calculate signal-to-noise ratio
    signal_power = np.mean(np.square(original_signal))
    noise_power = np.mean(np.square(original_signal - processed_signal))
    snr = 10 * np.log10(signal_power / noise_power) if noise_power > 0 else float('inf')
    
    # Calculate root mean square error
    rmse = np.sqrt(np.mean(np.square(original_signal - processed_signal)))
    
    # Calculate correlation coefficient
    correlation = np.corrcoef(original_signal, processed_signal)[0, 1]
    
    return {
        "Signal-to-Noise Ratio (SNR)": f"{snr:.2f} dB",
        "Root Mean Square Error (RMSE)": f"{rmse:.4f}",
        "Correlation Coefficient": f"{correlation:.4f}"
    }

def create_processed_dataframe(df, column_name, method, params):
    """Create a dataframe with both original and processed signal data
    
    Args:
        df: Original dataframe
        column_name: Name of the signal column to process
        method: Processing method
        params: Processing parameters
        
    Returns:
        DataFrame with additional processed column
    """
    if column_name not in df.columns:
        st.error(f"Column '{column_name}' not found in data")
        return df
    
    # Create a copy to avoid modifying original data
    result_df = df.copy()
    
    # Get the signal data
    signal_data = df[column_name].values
    
    # Process the signal
    processed_data = process_signal(signal_data, method, params)
    
    # Add processed column with clear naming
    processed_column_name = f"{column_name}_processed_{method.lower().replace(' ', '_')}"
    result_df[processed_column_name] = processed_data
    
    # Calculate and display metrics
    if len(signal_data) > 0 and len(processed_data) > 0:
        metrics = calculate_metrics(signal_data, processed_data)
        
        st.subheader(f"Processing Metrics for {column_name}")
        col1, col2, col3 = st.columns(3)
        
        metric_items = list(metrics.items())
        with col1:
            st.metric("SNR", metric_items[0][1])
        with col2:
            st.metric("RMSE", metric_items[1][1])
        with col3:
            st.metric("Correlation", metric_items[2][1])
    
    return result_df

def plot_comparison(original_signal, processed_signal, title="Signal Comparison", 
                   original_label="Original", processed_label="Processed"):
    """Plot comparison between original and processed signals
    
    Args:
        original_signal: Original signal data
        processed_signal: Processed signal data
        title: Plot title
        original_label: Label for original signal
        processed_label: Label for processed signal
    """
    import matplotlib.pyplot as plt
    
    # Set matplotlib to use black text
    plt.rcParams['text.color'] = 'black'
    plt.rcParams['axes.labelcolor'] = 'black'
    plt.rcParams['xtick.color'] = 'black'
    plt.rcParams['ytick.color'] = 'black'
    plt.rcParams['axes.titlecolor'] = 'black'
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
    
    # Plot original signal
    ax1.plot(original_signal, 'b-', alpha=0.7, linewidth=1)
    ax1.set_title(f"{original_label} Signal", color='black')
    ax1.set_ylabel("Amplitude", color='black')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(colors='black')
    
    # Plot processed signal
    ax2.plot(processed_signal, 'r-', alpha=0.7, linewidth=1)
    ax2.set_title(f"{processed_label} Signal", color='black')
    ax2.set_ylabel("Amplitude", color='black')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(colors='black')
    
    # Plot overlay comparison
    ax3.plot(original_signal, 'b-', alpha=0.5, linewidth=1, label=original_label)
    ax3.plot(processed_signal, 'r-', alpha=0.7, linewidth=1.5, label=processed_label)
    ax3.set_title("Comparison Overlay", color='black')
    ax3.set_xlabel("Sample Index", color='black')
    ax3.set_ylabel("Amplitude", color='black')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.tick_params(colors='black')
    
    # Ensure legend text is also black
    legend = ax3.get_legend()
    for text in legend.get_texts():
        text.set_color('black')
    
    plt.tight_layout()
    st.pyplot(fig)
    
    return fig

def complete_signal_processing_interface(df, signal_columns):
    """Complete interface for signal processing with data saving and visualization
    
    Args:
        df: Input dataframe
        signal_columns: List of column names containing signal data
        
    Returns:
        Processed dataframe with additional columns
    """
    st.subheader("🔧 Signal Processing Interface")
    
    if not signal_columns:
        st.warning("No signal columns available for processing")
        return df
    
    # Column selection
    selected_column = st.selectbox(
        "Select Signal Column to Process",
        signal_columns,
        help="Choose which signal column you want to process"
    )
    
    if selected_column not in df.columns:
        st.error(f"Selected column '{selected_column}' not found in data")
        return df
    
    # Processing method and parameters
    method, params = show_smoother_ui(key_prefix="complete_interface")
    
    # Processing controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        process_button = st.button("🚀 Process Signal", type="primary")
    
    with col2:
        save_processed = st.checkbox("💾 Save Processed Data", value=True)
    
    with col3:
        show_comparison = st.checkbox("📊 Show Comparison Plot", value=True)
    
    if process_button:
        with st.spinner("Processing signal..."):
            try:
                # Get original signal
                original_signal = df[selected_column].values
                
                if len(original_signal) == 0:
                    st.error("No data available in selected column")
                    return df
                
                # Process signal
                processed_signal = process_signal(original_signal, method, params)
                
                # Create processed dataframe
                result_df = df.copy()
                
                if save_processed:
                    # Create descriptive column name
                    processed_col_name = f"{selected_column}_processed_{method.lower().replace(' ', '_').replace('-', '_')}"
                    result_df[processed_col_name] = processed_signal
                    
                    st.success(f"✅ Processed data saved as column: `{processed_col_name}`")
                
                # Show metrics
                if len(original_signal) > 1 and len(processed_signal) > 1:
                    metrics = calculate_metrics(original_signal, processed_signal)
                    
                    st.subheader("📈 Processing Performance Metrics")
                    metric_cols = st.columns(3)
                    
                    metric_items = list(metrics.items())
                    for i, (key, value) in enumerate(metric_items):
                        with metric_cols[i]:
                            st.metric(key.split('(')[0].strip(), value)
                
                # Show comparison plot
                if show_comparison:
                    st.subheader("📊 Signal Comparison")
                    plot_comparison(
                        original_signal, 
                        processed_signal,
                        title=f"Signal Processing: {method}",
                        original_label=f"Original {selected_column}",
                        processed_label=f"Processed ({method})"
                    )
                
                # Show data preview
                if save_processed:
                    st.subheader("🔍 Data Preview")
                    
                    preview_cols = [selected_column]
                    if f"{selected_column}_processed_{method.lower().replace(' ', '_').replace('-', '_')}" in result_df.columns:
                        preview_cols.append(f"{selected_column}_processed_{method.lower().replace(' ', '_').replace('-', '_')}")
                    
                    st.dataframe(
                        result_df[preview_cols].head(20),
                        use_container_width=True
                    )
                
                return result_df
                
            except Exception as e:
                st.error(f"❌ Error processing signal: {str(e)}")
                return df
    
    return df
