import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pymongo import MongoClient
import numpy as np
from datetime import datetime
import json
from list_data_viewer import display_list_data
from mongodb_helper import fetch_features
from sklearn.ensemble import IsolationForest
import warnings
warnings.filterwarnings('ignore')

from signal_smoother import show_smoother_ui, process_signal

def safe_float(value, default=0.0):
    """Safely convert a value to float"""
    if isinstance(value, dict):
        if "$numberDouble" in value:
            return float(value["$numberDouble"])
        elif "$numberInt" in value:
            return float(value["$numberInt"])
        elif "$numberLong" in value:
            return float(value["$numberLong"])
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Safely convert a value to integer"""
    try:
        return int(safe_float(value)) if value is not None else default
    except (ValueError, TypeError):
        return default

def extract_feature_dict(measurement, composite_key, date_str, time_str):
    """Extract features from measurement data"""
    feature_dict = {
        "composite_key": composite_key,
        "date": date_str,
        "timestamp": time_str,
        "gestational_age_days": safe_float(measurement.get("gestational_age_days")),
        "hours_sin": safe_float(measurement.get("hours_sin")),
        "hours_cos": safe_float(measurement.get("hours_cos")),
        "test_duration_seconds": safe_float(measurement.get("test_duration_seconds")),
        "total_auc": safe_float(measurement.get("total_auc")),
        "baseline_tone": safe_float(measurement.get("baseline_tone")),
        "sample_entropy": safe_float(measurement.get("sample_entropy")),
        "total_contraction_count": safe_int(measurement.get("total_contraction_count"))
    }

    # Process windows array
    windows = measurement.get("windows", [])
    if windows and len(windows) > 0:
        window = windows[0]  # Get first window
        feature_dict.update({
            "window_mask": safe_int(window.get("window_mask")),
            "window_auc": safe_float(window.get("window_auc")),
            "contraction_rate": safe_float(window.get("contraction_rate"))
        })

    # 处理数组计数
    feature_dict.update({
        "contraction_zones_count": len(measurement.get("contraction_zones", [])),
        "accelerations_count": len(measurement.get("accelerations", [])),
        "decelerations_count": len(measurement.get("decelerations", []))
    })

    # 处理分娩相关天数
    feature_dict.update({
        "days_to_labor_EDD": safe_int(measurement.get("days_to_labor_EDD"), None),
        "days_to_labor_ADD": safe_int(measurement.get("days_to_labor_ADD"), None)
    })
    
    return feature_dict

def plot_feature_correlation(df, features):
    """Plot feature correlation heatmap"""
    if len(features) > 1:
        corr_matrix = df[features].corr()
        
        # 使用plotly创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmin=-1,
            zmax=1,
            text=np.round(corr_matrix.values, 2),
            texttemplate='%{text}',
            textfont={'size': 10},
            hoverongaps=False
        ))
        
        fig.update_layout(
            title=dict(
                text='Feature Correlation Heatmap',
                font=dict(color='black')
            ),
            width=700,
            height=700,
            xaxis={
                'side': 'bottom',
                'tickfont': dict(color='black'),
                'title_font': dict(color='black')
            },
            yaxis={
                'tickfont': dict(color='black'),
                'title_font': dict(color='black')
            },
            xaxis_tickangle=-45,
            font=dict(color='black')
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 显示高相关性特征对
        st.write("### High Correlation Pairs (|correlation| > 0.7):")
        high_corr = []
        for i in range(len(features)):
            for j in range(i + 1, len(features)):
                corr = abs(corr_matrix.iloc[i, j])
                if corr > 0.7:
                    high_corr.append(f"{features[i]} - {features[j]}: {corr:.2f}")
        
        if high_corr:
            for pair in high_corr:
                st.write(pair)
        else:
            st.write("No high correlation pairs found.")

from mongo_config import load_mongo_config, save_mongo_config, DEFAULT_MONGO_CONFIG

def show_mongo_config():
    """显示MongoDB配置界面"""
    with st.expander("MongoDB Configuration", expanded=False):
        config = load_mongo_config()
        
        col1, col2 = st.columns([3, 1])
        with col1:
            # 使用当前配置作为默认值
            uri = st.text_input("MongoDB URI", value=config["uri"])
            db_name = st.text_input("Database Name", value=config["db_name"])
            collection_raw = st.text_input("Raw Data Collection", value=config["collection_raw"])
            collection_features = st.text_input("Features Collection", value=config["collection_features"])
        
        with col2:
            st.write("Actions")
            if st.button("Save Configuration"):
                new_config = {
                    "uri": uri,
                    "db_name": db_name,
                    "collection_raw": collection_raw,
                    "collection_features": collection_features
                }
                save_mongo_config(new_config)
                st.success("Configuration saved!")
            
            if st.button("Reset to Default"):
                save_mongo_config(DEFAULT_MONGO_CONFIG)
                st.success("Configuration reset to default!")
                st.rerun()

def fetch_raw_data(contact_numbers=None):
    """Fetch raw signal data from MongoDB"""
    config = load_mongo_config()
    try:
        # Connect to database
        client = MongoClient(config["uri"])
        db = client[config["db_name"]]
        collection = db[config["collection_raw"]]
        
        # Build query conditions
        query = {}
        if contact_numbers:
            query["contact_number"] = {"$in": contact_numbers}
        
        # Get total document count and show progress
        total_docs = collection.count_documents(query)
        st.write(f"Found {total_docs} documents in raw data collection")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 在数据处理前添加信号处理选项
        enable_signal_processing = False
        fhr_method = None
        fhr_params = None
        uc_method = None
        uc_params = None
        
        with st.sidebar:
            enable_signal_processing = st.checkbox("Enable Signal Processing", key="enable_signal_processing")
            if enable_signal_processing:
                st.write("### FHR Signal Processing")
                fhr_method, fhr_params = show_smoother_ui(key_prefix="fhr")
                st.write("### UC Signal Processing")
                uc_method, uc_params = show_smoother_ui(key_prefix="uc")
        
        # 准备记录列表
        records = []
        
        # 获取并处理每个文档
        for i, doc in enumerate(collection.find(query, {"contact_number": 1, "measurement_date": 1, "data": 1})):
            # 更新进度
            progress = (i + 1) / total_docs
            progress_bar.progress(progress)
            status_text.write(f"Processing document {i + 1} of {total_docs}")
            
            # 获取基本数据
            contact_number = doc.get("contact_number", "")
            measurement_date = doc.get("measurement_date", "")
            
            # 处理信号数据
            data = doc.get('data', [])
            fhr_list = []
            uc_list = []
            
            try:
                # 如果数据是字符串格式，尝试解析
                if isinstance(data, str):
                    data = eval(data)
                
                # 确保数据是列表格式
                if isinstance(data, list):
                    for point in data:
                        try:
                            # 处理嵌套列表情况
                            if isinstance(point, list) and len(point) >= 2:
                                try:
                                    fhr = float(point[0]) if point[0] is not None else 0.0
                                    uc = float(point[1]) if point[1] is not None else 0.0
                                except (ValueError, TypeError):
                                    fhr = 0.0
                                    uc = 0.0
                            else:
                                fhr = 0.0
                                uc = 0.0
                                
                            # 处理 NaN 和无效值
                            if np.isnan(fhr) or fhr < 0:
                                fhr = 0.0
                            if np.isnan(uc) or uc < 0:
                                uc = 0.0
                                
                            fhr_list.append(fhr)
                            uc_list.append(uc)
                            
                        except (ValueError, TypeError, IndexError) as e:
                            if len(records) == 0:  # 调试信息
                                st.write(f"Debug: Error parsing point at index {i}: {str(e)}")
                                st.write(f"Debug: Point value: {point}")
                            fhr_list.append(0.0)
                            uc_list.append(0.0)
                
                # 显示调试信息
                if len(records) == 0:
                    st.write("Debug: Processing first record")
                    st.write(f"- Raw data sample: {str(data[:20])}")
                    st.write(f"- Processed FHR values: {fhr_list[:20]}")
                    st.write(f"- Processed UC values: {uc_list[:20]}")
                    
            except Exception as e:
                if len(records) == 0:
                    st.write(f"Debug: Error processing data: {str(e)}")
                fhr_list = []
                uc_list = []
            
            # Filter invalid values and store as JSON strings
            fhr_list = [x for x in fhr_list if isinstance(x, (int, float))]
            uc_list = [x for x in uc_list if isinstance(x, (int, float))]
            
            # Save original signal data
            original_fhr_list = fhr_list.copy()
            original_uc_list = uc_list.copy()
            
            # Process signals
            if enable_signal_processing:
                if len(fhr_list) > 0:
                    # Save original data before processing
                    fhr_list = process_signal(np.array(fhr_list), fhr_method, fhr_params).tolist()
                if len(uc_list) > 0:
                    uc_list = process_signal(np.array(uc_list), uc_method, uc_params).tolist()
                
                # Store original and processed signals
                processed_signals = {
                    "fhr_original": json.dumps(original_fhr_list),
                    "uc_original": json.dumps(original_uc_list),
                    "fhr_processed": json.dumps(fhr_list),
                    "uc_processed": json.dumps(uc_list)
                }
            
            # Only add records when signal data is valid
            if len(fhr_list) > 0 and len(uc_list) > 0:
                # Ensure signal data is completely valid
                if any(np.isnan(fhr_list)) or any(np.isnan(uc_list)):
                    if len(records) == 0:
                        st.write("Debug: Skipping record with NaN values")
                    continue
                
                record_data = {
                    "contact_number": contact_number,
                    "measurement_date": measurement_date,
                    "composite_key": f"{contact_number}_{measurement_date}",
                    "signal_points": len(fhr_list)
                }
                
                if enable_signal_processing:
                    # 如果启用了信号处理，存储原始和处理后的信号
                    record_data.update(processed_signals)
                else:
                    # If signal processing is not enabled, store raw signals only
                    record_data.update({
                        "fhr_signals": json.dumps(fhr_list),
                        "uc_signals": json.dumps(uc_list)
                    })
                
                records.append(record_data)
            elif len(records) == 0:
                st.write("Debug: Skipping empty signal record")
            
            # Print debug information
            if len(records) == 0:
                st.write("Debug: First record signal lengths:")
                st.write(f"- FHR signal points: {len(fhr_list)}")
                st.write(f"- UC signal points: {len(uc_list)}")
                if fhr_list:
                    st.write(f"- FHR sample values: {fhr_list[:20]}")
                if uc_list:
                    st.write(f"- UC sample values: {uc_list[:20]}")
        
        client.close()
        
        # 创建DataFrame并显示统计信息
        df = pd.DataFrame(records)
        if not df.empty:
            # 创建详细的数据分析报告
            total_records = len(df)
            valid_signals = 0
            invalid_signals = {"nan": 0, "empty": 0, "error": 0}
            signal_lengths = []
            
            for idx, row in df.iterrows():
                try:
                    fhr_signals = json.loads(row['fhr_signals'])
                    uc_signals = json.loads(row['uc_signals'])
                    
                    if len(fhr_signals) == 0 or len(uc_signals) == 0:
                        invalid_signals["empty"] += 1
                        continue
                        
                    if (any(not isinstance(x, (int, float)) or np.isnan(x) for x in fhr_signals) or
                        any(not isinstance(x, (int, float)) or np.isnan(x) for x in uc_signals)):
                        invalid_signals["nan"] += 1
                        continue
                        
                    valid_signals += 1
                    signal_lengths.append(len(fhr_signals))
                    
                except (json.JSONDecodeError, TypeError):
                    invalid_signals["error"] += 1
                    continue
            
            # 显示统计信息
            st.success(f"Data Analysis Summary")
            
            # 基本统计信息
            st.write("Basic Statistics:")
            st.write(f"- Total records: {total_records}")
            st.write(f"- Valid records: {valid_signals}")
            st.write(f"- Number of unique contact numbers: {df['contact_number'].nunique()}")
            
            # 信号质量统计
            st.write("\nSignal Quality Analysis:")
            st.write(f"- Records with NaN values: {invalid_signals['nan']}")
            st.write(f"- Records with empty signals: {invalid_signals['empty']}")
            st.write(f"- Records with decode errors: {invalid_signals['error']}")
            
            if signal_lengths:
                st.write("\nSignal Length Analysis:")
                st.write(f"- Minimum signal length: {min(signal_lengths)}")
                st.write(f"- Maximum signal length: {max(signal_lengths)}")
                st.write(f"- Average signal length: {sum(signal_lengths)/len(signal_lengths):.1f}")
            
            # 时间范围信息
            st.write("\nDate Range:")
            st.write(f"- From: {df['measurement_date'].min()}")
            st.write(f"- To: {df['measurement_date'].max()}")
            
            # 如果发现问题，显示警告
            if invalid_signals["nan"] > 0 or invalid_signals["empty"] > 0 or invalid_signals["error"] > 0:
                st.warning("Some records have quality issues. Consider filtering or cleaning the data.")
        
        return df
    
    except Exception as e:
        st.error(f"Error fetching raw data: {str(e)}")
        return pd.DataFrame()
    finally:
        progress_bar.empty()
        status_text.empty()

def fetch_features(contact_numbers=None):
    """Fetch feature data from MongoDB"""
    config = load_mongo_config()
    try:
        # Connect to MongoDB
        st.write("Connecting to MongoDB...")
        client = MongoClient(config["uri"])
        db = client[config["db_name"]]
        collection = db[config["collection_features"]]
        
        # 构建查询条件
        query = {}
        if contact_numbers:
            query["contact_number"] = {"$in": contact_numbers}
        
        # 显示查询信息
        total_docs = collection.count_documents(query)
        st.write(f"Found {total_docs} documents in the database")
        
        if total_docs == 0:
            st.warning("No documents found matching the criteria")
            return pd.DataFrame()
            
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 用于收集所有特征
        all_features = []
        processed_docs = 0
        
        # 遍历所有文档
        for doc in collection.find(query):
            processed_docs += 1
            progress = processed_docs / total_docs
            progress_bar.progress(progress)
            status_text.write(f"Processing document {processed_docs} of {total_docs}")
            
            # 提取基本信息
            contact_number = doc.get("contact_number")
            measurements = doc.get("measurements", [])
            
            if not measurements:
                st.warning(f"No measurements found for contact number: {contact_number}")
                continue
            
            # 遍历每个测量记录
            for measurement in measurements:
                if not isinstance(measurement, dict):
                    continue
                    
                # 记录时间信息
                date_str = measurement.get("date", "")
                time_str = measurement.get("timestamp", "")
                dt_str = f"{date_str} {time_str}"
                
                # 创建特征字典
                feature_dict = {
                    "composite_key": f"{contact_number}_{dt_str}",
                    "contact_number": contact_number,
                    "measurement_time": dt_str,
                    "gestational_age_days": safe_float(measurement.get("gestational_age_days")),
                    "test_duration_seconds": safe_float(measurement.get("test_duration_seconds")),
                    "total_auc": safe_float(measurement.get("total_auc")),
                    "baseline_tone": safe_float(measurement.get("baseline_tone")),
                    "sample_entropy": safe_float(measurement.get("sample_entropy")),
                    "has_contraction": bool(measurement.get("has_contraction", False))
                }
                
                # 处理数组计数
                feature_dict.update({
                    "contraction_zones_count": len(measurement.get("contraction_zones", [])),
                    "accelerations_count": len(measurement.get("accelerations", [])),
                    "decelerations_count": len(measurement.get("decelerations", []))
                })
                
                # 处理windows数据
                windows = measurement.get("windows", [])
                if windows and len(windows) > 0:
                    window = windows[0]
                    feature_dict.update({
                        "window_mask": safe_int(window.get("window_mask")),
                        "window_auc": safe_float(window.get("window_auc")),
                        "contraction_rate": safe_float(window.get("contraction_rate"))
                    })
                
                # 处理信号数据
                signal_data = measurement.get("signal_data", {})
                if isinstance(signal_data, dict):
                    feature_dict.update({
                        "signal_points": len(signal_data.get("points", [])),
                        "fhr_baseline": safe_float(signal_data.get("fhr_baseline")),
                        "fhr_baseline_std": safe_float(signal_data.get("fhr_baseline_std"))
                    })
                
                # 处理分娩相关数据
                feature_dict.update({
                    "days_to_labor_EDD": safe_int(measurement.get("days_to_labor_EDD")),
                    "days_to_labor_ADD": safe_int(measurement.get("days_to_labor_ADD"))
                })
                
                # 添加统计特征
                feature_dict.update({
                    "min_contraction": safe_float(measurement.get("min_contraction")),
                    "max_contraction": safe_float(measurement.get("max_contraction")),
                    "mean_contraction": safe_float(measurement.get("mean_contraction")),
                    "std_contraction": safe_float(measurement.get("std_contraction")),
                    "median_duration": safe_float(measurement.get("median_duration")),
                    "median_peak_intensity": safe_float(measurement.get("median_peak_intensity"))
                })
                
                all_features.append(feature_dict)
                
        # 清理进度显示
        progress_bar.empty()
        status_text.empty()
        
        # 创建DataFrame
        df = pd.DataFrame(all_features)
        
        if df.empty:
            st.warning("No feature data was extracted")
            return df
            
        # 显示数据统计
        st.write("\nFeature Extraction Summary:")
        st.write(f"Total measurements processed: {len(df)}")
        st.write(f"Number of unique patients: {df['contact_number'].nunique()}")
        
        # 显示数据可用性统计
        missing_stats = df.isnull().sum()
        st.write("\nMissing Value Statistics:")
        for col in missing_stats.index:
            missing_pct = (missing_stats[col] / len(df)) * 100
            if missing_pct > 0:
                st.write(f"- {col}: {missing_pct:.1f}% missing")
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching features: {str(e)}")
        return pd.DataFrame()
    finally:
        if 'client' in locals() and client:
            client.close()
        if 'progress_bar' in locals() and 'progress_bar' in globals() and progress_bar:
            progress_bar.empty()
        if 'status_text' in locals() and 'status_text' in globals() and status_text:
            status_text.empty()

def plot_feature_correlation(df, selected_features):
    """绘制特征相关性图"""
    if len(selected_features) < 2:
        st.warning("Please select at least 2 features to plot correlation")
        return
        
    feature_data = df[selected_features].dropna()
    
    if feature_data.empty:
        st.warning("No valid data for selected features")
        return
        
    fig = px.scatter_matrix(
        feature_data,
        dimensions=selected_features,
        title="Feature Correlations"
    )
    
    fig.update_layout(
        height=800,
        width=800,
        showlegend=False,
        title=dict(
            text="Feature Correlations",
            font=dict(color='black')
        ),
        font=dict(color='black')
    )
    
    st.plotly_chart(fig)

def show_mongodb_data_page():
    # 创建一个主要布局
    main_container = st.container()
    
    with main_container:
        # 创建标题行的两列布局
        title_col, peter_col = st.columns([4, 1])
        
        with title_col:
            st.title("MongoDB Data Viewer")
        
        with peter_col:
            pass

    
    # 添加侧边栏用于数据过滤
    with st.sidebar:
        st.header("Data Filters")
        
        # 从MongoDB获取所有可用的联系人号码
        try:
            config = load_mongo_config()
            client = MongoClient(config["uri"])
            db = client[config["db_name"]]
            collection = db[config["collection_features"]]
            
            # 获取唯一的联系人号码列表
            all_contact_numbers = sorted(collection.distinct("contact_number"))
            client.close()
            
            # 创建多选框
            selected_contacts = st.multiselect(
                "选择联系人号码",
                options=all_contact_numbers,
                default=None,
                help="可以选择多个联系人号码进行过滤，不选择则显示所有数据"
            )
            
            # 如果有选择，则使用选择的联系人号码；否则使用None表示显示所有数据
            contact_numbers = selected_contacts if selected_contacts else None
            
        except Exception as e:
            st.error(f"获取联系人列表失败: {str(e)}")
            contact_numbers = None
        
        # 添加数据加载按钮
        if st.button("Load Data from MongoDB"):
            with st.spinner("Fetching data from MongoDB..."):
                try:
                    # 获取原始信号数据
                    raw_df = fetch_raw_data(contact_numbers)
                    if not raw_df.empty:
                        st.session_state['raw_df'] = raw_df
                        st.success(f"Loaded {len(raw_df)} raw signal records")
                    
                    # 获取特征数据
                    features_df = fetch_features(contact_numbers)
                    if not features_df.empty:
                        st.session_state['features_df'] = features_df
                        st.success(f"Loaded {len(features_df)} feature records")
                    else:
                        st.warning("No feature data was loaded. Please check the MongoDB connection and data availability.")
                except Exception as e:
                    st.error(f"Error during data loading: {str(e)}")
                    st.info("Please check your MongoDB connection settings and try again.")
                
                # 合并数据
                if 'raw_df' in st.session_state and 'features_df' in st.session_state:
                    raw_df = st.session_state['raw_df']
                    features_df = st.session_state['features_df']
                    
                    # 显示数据集信息
                    st.write("Raw data columns:", raw_df.columns.tolist())
                    st.write("Features data columns:", features_df.columns.tolist())
                    
                    # 确保两个数据集都有 composite_key
                    if 'composite_key' not in raw_df.columns:
                        st.error("Raw data missing composite_key!")
                        return
                    if 'composite_key' not in features_df.columns:
                        st.error("Features data missing composite_key!")
                        return
                    
                    # 显示数据校验信息
                    st.write("Data validation:")
                    st.write(f"Raw data records: {len(raw_df)}")
                    st.write(f"Feature records: {len(features_df)}")
                    
                    # 合并数据
                    try:
                        merged_df = pd.merge(
                            raw_df,
                            features_df,
                            on='composite_key',
                            how='left'
                        )
                        st.session_state['merged_df'] = merged_df
                        st.success(f"Created merged dataset with {len(merged_df)} records")
                        
                        # 显示合并后的数据统计
                        st.write("Merged data info:")
                        st.write(f"Total rows: {len(merged_df)}")
                        st.write(f"Number of matched records: {merged_df['gestational_age_days'].notna().sum()}")
                        
                    except Exception as e:
                        st.error(f"Error merging datasets: {str(e)}")
                        st.write("Please check the data structure and try again")
    
    # 主界面
    if 'merged_df' in st.session_state:
        df = st.session_state['merged_df'].copy() # Use a copy to avoid modifying the original
        
        if df.empty:
            st.warning("No data available. Please try different filter settings or check your MongoDB connection.")
            return
        
        # 在侧边栏添加移除高缺失值行的选项
        with st.sidebar:
            st.header("Data Cleaning")
            if st.checkbox("Remove rows with NaN values", key="remove_nan_rows"):
                # 移除所有包含NaN值的行
                original_rows = len(df)
                df = df.dropna()
                removed_rows = original_rows - len(df)
                if removed_rows > 0:
                    st.success(f"Removed {removed_rows} rows containing NaN values.")
                else:
                    st.info("No rows needed to be removed.")
        
        if df.empty:
            st.warning("No data available after cleaning. Please adjust your filtering options.")
            return
        
        # 创建选项卡
        tab1, tab2 = st.tabs(["Signal Visualization", "Feature Analysis"])
        
        with tab1:
            st.subheader("Signal Data Visualization")
            display_list_data(df)
        
        with tab2:
            st.subheader("Feature Analysis")
            
            # 获取数值型特征列表
            numeric_features = df.select_dtypes(include=[np.number]).columns.tolist()
            numeric_features = [col for col in numeric_features if col not in ['fhr_signals', 'uc_signals']]
            
            # 显示所有特征的缺失值情况
            st.write("### Missing Values Analysis")
            
            # 计算每个特征的缺失值比例
            missing_data = pd.DataFrame({
                'Feature': numeric_features,
                'Missing Count': [df[col].isna().sum() for col in numeric_features],
                'Total Count': len(df)
            })
            missing_data['Missing Percentage'] = (missing_data['Missing Count'] / missing_data['Total Count'] * 100).round(2)
            missing_data = missing_data.sort_values('Missing Percentage', ascending=False)

            # 创建缺失值比例的条形图
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=missing_data['Feature'],
                y=missing_data['Missing Percentage'],
                marker_color='red',
                name='Missing Data'
            ))
            fig.add_trace(go.Bar(
                x=missing_data['Feature'],
                y=100 - missing_data['Missing Percentage'],
                marker_color='blue',
                name='Available Data'
            ))
            
            fig.update_layout(
                title=dict(
                    text='Data Availability by Feature',
                    font=dict(color='black')
                ),
                barmode='stack',
                yaxis_title='Percentage (%)',
                xaxis_title='Feature',
                xaxis_tickangle=-45,
                height=400,
                font=dict(color='black'),
                xaxis=dict(
                    tickfont=dict(color='black'),
                    title_font=dict(color='black')
                ),
                yaxis=dict(
                    tickfont=dict(color='black'),
                    title_font=dict(color='black')
                ),
                legend=dict(font=dict(color='black'))
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 显示具体的缺失值统计
            st.write("#### Detailed Missing Values Statistics")
            missing_stats = pd.DataFrame({
                'Missing Count': missing_data['Missing Count'],
                'Missing Percentage (%)': missing_data['Missing Percentage'],
                'Available Count': missing_data['Total Count'] - missing_data['Missing Count']
            }).round(2)
            st.dataframe(missing_stats)

            # 使用之前定义的numeric_features列表
            
            selected_features = st.multiselect(
                "Select Features to Analyze",
                options=numeric_features,
                default=numeric_features[:4] if len(numeric_features) >= 4 else numeric_features
            )
            
            # 分析类型选择
            analysis_type = st.radio(
                "Select Analysis Type",
                ["Basic Statistics", "Gestational Week Analysis", "Outlier Detection"]
            )

            # 创建妊娠周特征
            create_gest_week = False
            if analysis_type == "Gestational Week Analysis":
                if "gestational_age_days" in df.columns:
                    # 检查是否有有效的孕周数据
                    valid_ga = df['gestational_age_days'].dropna()
                    
                    if not valid_ga.empty:
                        # 转换为周数并创建孕周特征
                        df['gest_week'] = df['gestational_age_days'].astype(float) / 7.0
                        create_gest_week = True
                        
                        # 创建周数区间（考虑实际数据范围）
                        min_week = max(20, int(df['gest_week'].min()))
                        max_week = min(45, int(df['gest_week'].max()) + 1)
                        bins = list(range(min_week, max_week + 1, 2))  # 每2周一个区间
                        labels = [f'{bins[i]}-{bins[i+1]}' for i in range(len(bins)-1)]
                        
                        df['gest_week_bin'] = pd.cut(df['gest_week'], bins=bins, labels=labels)
                        
                        # 根据分析类型显示不同的可视化
            # 根据分析类型执行相应的分析
            if analysis_type == "Basic Statistics":
                st.write("### Basic Statistics Analysis")
                # 对每个选定的特征进行分析
                for feature in selected_features:
                    if feature != 'gestational_age_days':
                        st.write(f"#### {feature}")
                        # 创建直方图
                        fig = px.histogram(
                            df,
                            x=feature,
                            title=f"Distribution of {feature}",
                            labels={feature: feature}
                        )
                        fig.update_layout(bargap=0.1)
                        st.plotly_chart(fig)
                        
                        # 显示基本统计信息
                        desc = df[feature].describe()
                        st.write("Summary Statistics:")
                        st.write(f"- Mean: {desc['mean']:.2f}")
                        st.write(f"- Std Dev: {desc['std']:.2f}")
                        st.write(f"- Min: {desc['min']:.2f}")
                        st.write(f"- Max: {desc['max']:.2f}")
                        st.write(f"- Median: {desc['50%']:.2f}")
            
            elif analysis_type == "Gestational Week Analysis":
                if not create_gest_week:
                    st.error("No valid gestational week data available for analysis.")
                    return
                
                st.write("### Gestational Week Analysis")
                
                # 显示基本统计信息
                st.write("#### Basic Information")
                st.write(f"- Total samples: {len(valid_ga)}")
                st.write(f"- Gestational age range: {int(df['gest_week'].min()):.0f} to {int(df['gest_week'].max()):.0f} weeks")
                
                # 创建孕周分布图
                fig = px.histogram(
                    df,
                    x='gest_week',
                    title="Distribution of Gestational Age",
                    labels={'gest_week': 'Gestational Age (weeks)'}
                )
                fig.update_layout(bargap=0.1)
                st.plotly_chart(fig)
                
                # 如果选择了特征，分析各孕周段的特征分布
                if selected_features:
                    st.write("#### Feature Analysis by Gestational Week")
                    for feature in selected_features:
                        if feature != 'gestational_age_days' and feature != 'gest_week':
                            fig = px.box(
                                df,
                                x='gest_week_bin',
                                y=feature,
                                title=f"{feature} by Gestational Week",
                                labels={'gest_week_bin': 'Gestational Week', feature: feature}
                            )
                            st.plotly_chart(fig)
            
            elif analysis_type == "Outlier Detection":
                st.write("### Outlier Detection")
                # 对每个选定的特征检测异常值
                for feature in selected_features:
                    if feature != 'gestational_age_days':
                        st.write(f"#### {feature}")
                        # 计算四分位数
                        Q1 = df[feature].quantile(0.25)
                        Q3 = df[feature].quantile(0.75)
                        IQR = Q3 - Q1
                        outlier_range = (Q1 - 1.5 * IQR, Q3 + 1.5 * IQR)
                        
                        # 创建直方图，标记异常值
                        fig = go.Figure()
                        fig.add_trace(go.Histogram(
                            x=df[df[feature].between(*outlier_range)][feature],
                            name="Normal",
                            marker_color='blue',
                            opacity=0.7
                        ))
                        fig.add_trace(go.Histogram(
                            x=df[~df[feature].between(*outlier_range)][feature],
                            name="Outliers",
                            marker_color='red',
                            opacity=0.7
                        ))
                        fig.update_layout(
                            title=f"Distribution of {feature} with Outliers Highlighted",
                            barmode='overlay'
                        )
                        st.plotly_chart(fig)
                        
                        # 显示异常值统计
                        outliers = df[~df[feature].between(*outlier_range)][feature]
                        st.write(f"Found {len(outliers)} outliers ({len(outliers)/len(df[feature])*100:.1f}% of data)")
                        if not outliers.empty:
                            st.write("Outlier Statistics:")
                            st.write(f"- Min outlier: {outliers.min():.2f}")
                            st.write(f"- Max outlier: {outliers.max():.2f}")
                            st.write(f"- Normal range: [{outlier_range[0]:.2f}, {outlier_range[1]:.2f}]")
                    # 显示基本统计信息
                    st.write("Basic Statistics:")
                    st.write(df[selected_features].describe())
                    
                    # 继续其他分析
                    for feature in selected_features:
                        if feature != 'gestational_age_days':
                            st.write(f"#### {feature}")
                            