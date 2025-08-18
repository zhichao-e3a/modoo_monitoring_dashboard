#!/usr/bin/env python3
"""
Test script for signal processing functionality
This script demonstrates the improved signal smoothing features.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from signal_smoother import (
    SignalSmoother, 
    process_signal, 
    create_processed_dataframe,
    plot_comparison,
    calculate_metrics
)

def create_test_signal(length=1000, noise_level=0.1):
    """Create a test signal with noise for demonstration"""
    # Create time array
    t = np.linspace(0, 10, length)
    
    # Create a signal with multiple frequency components
    signal = (np.sin(2 * np.pi * 0.5 * t) +  # Low frequency component
              0.5 * np.sin(2 * np.pi * 2 * t) +  # Medium frequency component
              0.3 * np.sin(2 * np.pi * 5 * t))   # Higher frequency component
    
    # Add noise
    noise = noise_level * np.random.randn(length)
    noisy_signal = signal + noise
    
    return t, signal, noisy_signal

def test_all_methods():
    """Test all signal processing methods"""
    print("🔧 Testing Signal Processing Methods")
    print("=" * 50)
    
    # Create test data
    t, clean_signal, noisy_signal = create_test_signal()
    
    # Test parameters for each method
    test_methods = {
        "Moving Average": {"window_size": 15},
        "Savitzky-Golay Filter": {"window_size": 15, "poly_order": 3},
        "Median Filter": {"kernel_size": 11},
        "Bandpass Filter": {"lowcut": 0.1, "highcut": 3.0, "fs": 10.0, "order": 5},
        "Wavelet Denoising": {"wavelet": "db4", "level": 3}
    }
    
    results = {}
    
    for method_name, params in test_methods.items():
        print(f"\n🚀 Testing {method_name}...")
        
        try:
            # Process the signal
            processed = process_signal(noisy_signal, method_name, params)
            
            # Calculate metrics
            metrics = calculate_metrics(clean_signal, processed)
            
            results[method_name] = {
                'processed': processed,
                'metrics': metrics,
                'params': params
            }
            
            print(f"✅ {method_name} completed successfully")
            for key, value in metrics.items():
                print(f"   - {key}: {value}")
                
        except Exception as e:
            print(f"❌ {method_name} failed: {str(e)}")
            results[method_name] = None
    
    return t, clean_signal, noisy_signal, results

def test_dataframe_processing():
    """Test signal processing with DataFrame"""
    print("\n📊 Testing DataFrame Signal Processing")
    print("=" * 50)
    
    # Create test DataFrame
    t, clean_signal, noisy_signal = create_test_signal()
    
    df = pd.DataFrame({
        'time': t,
        'fhr_signal': noisy_signal,
        'uc_signal': noisy_signal * 0.8 + np.random.randn(len(noisy_signal)) * 0.05,
        'other_data': np.random.randn(len(noisy_signal))
    })
    
    print(f"📋 Created DataFrame with shape: {df.shape}")
    print(f"📋 Columns: {list(df.columns)}")
    
    # Test processing with the new function
    try:
        processed_df = create_processed_dataframe(
            df, 
            'fhr_signal', 
            'Savitzky-Golay Filter',
            {'window_size': 15, 'poly_order': 3}
        )
        
        print(f"✅ Processed DataFrame shape: {processed_df.shape}")
        print(f"✅ New columns: {list(processed_df.columns)}")
        
        # Show some statistics
        original_std = df['fhr_signal'].std()
        processed_col = [col for col in processed_df.columns if 'processed' in col][0]
        processed_std = processed_df[processed_col].std()
        
        print(f"📈 Original signal std: {original_std:.4f}")
        print(f"📈 Processed signal std: {processed_std:.4f}")
        print(f"📈 Noise reduction: {((original_std - processed_std) / original_std * 100):.1f}%")
        
        return processed_df
        
    except Exception as e:
        print(f"❌ DataFrame processing failed: {str(e)}")
        return None

def main():
    """Main test function"""
    print("🎯 Signal Processing Test Suite")
    print("=" * 70)
    
    # Test individual methods
    t, clean, noisy, results = test_all_methods()
    
    # Test DataFrame processing
    processed_df = test_dataframe_processing()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    
    successful_methods = [name for name, result in results.items() if result is not None]
    failed_methods = [name for name, result in results.items() if result is None]
    
    print(f"✅ Successful methods: {len(successful_methods)}")
    for method in successful_methods:
        print(f"   - {method}")
    
    if failed_methods:
        print(f"❌ Failed methods: {len(failed_methods)}")
        for method in failed_methods:
            print(f"   - {method}")
    
    if processed_df is not None:
        print("✅ DataFrame processing: Success")
    else:
        print("❌ DataFrame processing: Failed")
    
    print(f"\n🎉 Testing completed! Check the results above.")

if __name__ == "__main__":
    main()
