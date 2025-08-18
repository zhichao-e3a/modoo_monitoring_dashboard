"""
==================================================
MongoDB数据阅读器和EDA分析模块
==================================================

功能描述：
- MongoDB数据库连接和数据提取
- 综合性EDA（探索性数据分析）功能
- 信号数据可视化和特征分析
- 支持多种统计分析和数据质量评估

核心功能：
1. MongoDB连接管理和查询执行
2. 缺失值分析和数据质量检查
3. 特征相关性分析（热力图和散点图矩阵）
4. 基础统计分析和分布可视化
5. 妊娠周期分析和异常值检测
6. 信号数据处理和可视化

支持的分析类型：
- Basic Statistics: 基础统计和分布分析
- Correlation Analysis: 特征相关性热力图分析
- Gestational Week Analysis: 妊娠周期相关分析
- Outlier Detection: 异常值检测和可视化

作者: Modoo团队
最后更新: 2025-08-18
==================================================
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
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
                ["Basic Statistics", "Correlation Analysis", "PCA Analysis", "t-SNE Analysis", "Gestational Week Analysis", "Outlier Detection"]
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
            
            elif analysis_type == "Correlation Analysis":
                st.write("### Feature Correlation Analysis")
                
                if len(selected_features) >= 2:
                    # 调用热力图函数
                    plot_feature_correlation(df, selected_features)
                    
                    # 额外显示相关性统计表
                    st.write("### Correlation Matrix Table")
                    corr_matrix = df[selected_features].corr()
                    st.dataframe(corr_matrix.style.background_gradient(cmap='RdBu'))
                    
                else:
                    st.warning("Please select at least 2 features for correlation analysis.")
            
            elif analysis_type == "PCA Analysis":
                st.write("### Principal Component Analysis (PCA)")
                
                # 检查是否有days_to_labor_ADD目标变量
                target_var = "days_to_labor_ADD"
                has_target = target_var in df.columns
                
                if not has_target:
                    st.warning(f"Target variable '{target_var}' not found in the dataset.")
                    st.info("PCA analysis can still be performed without the target variable.")
                
                if len(selected_features) >= 2:
                    # PCA参数设置
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        n_components = st.slider(
                            "Number of Principal Components",
                            min_value=2,
                            max_value=min(len(selected_features), 10),
                            value=min(3, len(selected_features)),
                            help="Choose the number of principal components to compute"
                        )
                    
                    with col2:
                        standardize = st.checkbox(
                            "Standardize Features",
                            value=True,
                            help="Standardize features before PCA (recommended)"
                        )
                    
                    try:
                        from sklearn.decomposition import PCA
                        from sklearn.preprocessing import StandardScaler
                        import matplotlib.pyplot as plt
                        
                        # 准备数据
                        feature_data = df[selected_features].dropna()
                        
                        if feature_data.empty:
                            st.error("No valid data available for PCA analysis.")
                        else:
                            st.write(f"**Data Shape:** {feature_data.shape[0]} samples, {feature_data.shape[1]} features")
                            
                            # 标准化数据（如果选择）
                            if standardize:
                                scaler = StandardScaler()
                                feature_data_scaled = scaler.fit_transform(feature_data)
                                feature_data_scaled = pd.DataFrame(
                                    feature_data_scaled, 
                                    columns=feature_data.columns,
                                    index=feature_data.index
                                )
                            else:
                                feature_data_scaled = feature_data
                            
                            # 执行PCA
                            pca = PCA(n_components=n_components)
                            pca_result = pca.fit_transform(feature_data_scaled)
                            
                            # 创建PCA结果DataFrame
                            pca_columns = [f'PC{i+1}' for i in range(n_components)]
                            pca_df = pd.DataFrame(pca_result, columns=pca_columns, index=feature_data.index)
                            
                            # 如果有目标变量，添加到PCA结果中
                            if has_target:
                                target_data = df.loc[feature_data.index, target_var].dropna()
                                common_idx = pca_df.index.intersection(target_data.index)
                                pca_df_with_target = pca_df.loc[common_idx]
                                target_aligned = target_data.loc[common_idx]
                            
                            # 显示解释方差
                            st.write("### Explained Variance Analysis")
                            
                            # 解释方差比例
                            explained_var_ratio = pca.explained_variance_ratio_
                            cumulative_var_ratio = np.cumsum(explained_var_ratio)
                            
                            # 创建解释方差图
                            fig_var = go.Figure()
                            
                            # 添加个别解释方差
                            fig_var.add_trace(go.Bar(
                                x=pca_columns,
                                y=explained_var_ratio * 100,
                                name='Individual',
                                marker_color='lightcoral'
                            ))
                            
                            # 添加累积解释方差
                            fig_var.add_trace(go.Scatter(
                                x=pca_columns,
                                y=cumulative_var_ratio * 100,
                                mode='lines+markers',
                                name='Cumulative',
                                line=dict(color='red', width=3),
                                marker=dict(size=8)
                            ))
                            
                            fig_var.update_layout(
                                title='Explained Variance by Principal Components',
                                xaxis_title='Principal Components',
                                yaxis_title='Explained Variance (%)',
                                font=dict(color='black'),
                                plot_bgcolor='white',
                                showlegend=True
                            )
                            
                            st.plotly_chart(fig_var, use_container_width=True)
                            
                            # 显示数值表格
                            variance_df = pd.DataFrame({
                                'Component': pca_columns,
                                'Individual Variance (%)': (explained_var_ratio * 100).round(2),
                                'Cumulative Variance (%)': (cumulative_var_ratio * 100).round(2)
                            })
                            st.dataframe(variance_df, use_container_width=True)
                            
                            # PCA散点图
                            st.write("### PCA Scatter Plots")
                            
                            if n_components >= 2:
                                # 2D散点图
                                if has_target and len(common_idx) > 0:
                                    fig_2d = px.scatter(
                                        x=pca_df_with_target['PC1'],
                                        y=pca_df_with_target['PC2'],
                                        color=target_aligned,
                                        title='PCA: First Two Components (Colored by Days to Labor)',
                                        labels={'x': f'PC1 ({explained_var_ratio[0]:.1%})', 
                                               'y': f'PC2 ({explained_var_ratio[1]:.1%})',
                                               'color': 'Days to Labor'},
                                        color_continuous_scale='Reds'
                                    )
                                else:
                                    fig_2d = px.scatter(
                                        x=pca_df['PC1'],
                                        y=pca_df['PC2'],
                                        title='PCA: First Two Components',
                                        labels={'x': f'PC1 ({explained_var_ratio[0]:.1%})', 
                                               'y': f'PC2 ({explained_var_ratio[1]:.1%})'},
                                        color_discrete_sequence=['crimson']
                                    )
                                
                                fig_2d.update_layout(font=dict(color='black'))
                                st.plotly_chart(fig_2d, use_container_width=True)
                            
                            # 3D散点图（如果有3个或更多组件）
                            if n_components >= 3:
                                if has_target and len(common_idx) > 0:
                                    fig_3d = px.scatter_3d(
                                        x=pca_df_with_target['PC1'],
                                        y=pca_df_with_target['PC2'],
                                        z=pca_df_with_target['PC3'],
                                        color=target_aligned,
                                        title='PCA: First Three Components (Colored by Days to Labor)',
                                        labels={'x': f'PC1 ({explained_var_ratio[0]:.1%})',
                                               'y': f'PC2 ({explained_var_ratio[1]:.1%})',
                                               'z': f'PC3 ({explained_var_ratio[2]:.1%})',
                                               'color': 'Days to Labor'},
                                        color_continuous_scale='Reds'
                                    )
                                else:
                                    fig_3d = px.scatter_3d(
                                        x=pca_df['PC1'],
                                        y=pca_df['PC2'],
                                        z=pca_df['PC3'],
                                        title='PCA: First Three Components',
                                        labels={'x': f'PC1 ({explained_var_ratio[0]:.1%})',
                                               'y': f'PC2 ({explained_var_ratio[1]:.1%})',
                                               'z': f'PC3 ({explained_var_ratio[2]:.1%})'},
                                        color_discrete_sequence=['crimson']
                                    )
                                
                                fig_3d.update_layout(font=dict(color='black'))
                                st.plotly_chart(fig_3d, use_container_width=True)
                            
                            # 特征载荷分析
                            st.write("### Feature Loadings Analysis")
                            
                            # 计算特征载荷
                            loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
                            loadings_df = pd.DataFrame(
                                loadings,
                                columns=pca_columns,
                                index=selected_features
                            )
                            
                            # 显示载荷热力图
                            fig_loadings = go.Figure(data=go.Heatmap(
                                z=loadings_df.values,
                                x=loadings_df.columns,
                                y=loadings_df.index,
                                colorscale='RdBu',
                                zmid=0,
                                text=np.round(loadings_df.values, 3),
                                texttemplate='%{text}',
                                textfont={'size': 10}
                            ))
                            
                            fig_loadings.update_layout(
                                title='Feature Loadings Heatmap',
                                font=dict(color='black'),
                                xaxis_title='Principal Components',
                                yaxis_title='Original Features'
                            )
                            
                            st.plotly_chart(fig_loadings, use_container_width=True)
                            
                            # 显示载荷数值表格
                            st.write("### Feature Loadings Table")
                            st.dataframe(loadings_df.style.background_gradient(cmap='RdBu'))
                            
                            # 如果有目标变量，计算相关性
                            if has_target and len(common_idx) > 0:
                                st.write("### PCA Components vs Target Variable")
                                
                                correlations = []
                                for i, pc in enumerate(pca_columns):
                                    corr = np.corrcoef(pca_df_with_target[pc], target_aligned)[0, 1]
                                    correlations.append(corr)
                                
                                corr_df = pd.DataFrame({
                                    'Component': pca_columns,
                                    'Correlation with Days_to_Labor': correlations
                                })
                                
                                # 相关性条形图
                                fig_corr = go.Figure(go.Bar(
                                    x=corr_df['Component'],
                                    y=corr_df['Correlation with Days_to_Labor'],
                                    marker_color=['darkred' if abs(x) > 0.3 else 'lightcoral' for x in correlations]
                                ))
                                
                                fig_corr.update_layout(
                                    title='PCA Components Correlation with Days to Labor',
                                    xaxis_title='Principal Components',
                                    yaxis_title='Correlation Coefficient',
                                    font=dict(color='black')
                                )
                                
                                st.plotly_chart(fig_corr, use_container_width=True)
                                st.dataframe(corr_df.round(3), use_container_width=True)
                            
                            # 聚类分析部分
                            st.write("### Clustering Analysis on PCA Components")
                            
                            st.info(
                                "💡 **Enhanced Clustering Features:** "
                                "• Support up to 15 clusters (auto-limited by sample size) "
                                "• Dynamic red-scale color generation "
                                "• Automatic statistical validation"
                            )
                            
                            perform_clustering = st.checkbox(
                                "Perform Clustering on PCA Results",
                                help="Apply clustering algorithms to the PCA-transformed data"
                            )
                            
                            if perform_clustering:
                                try:
                                    from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
                                    from sklearn.metrics import silhouette_score, calinski_harabasz_score
                                    
                                    # 聚类参数设置
                                    cluster_cols = st.columns(3)
                                    
                                    with cluster_cols[0]:
                                        clustering_method = st.selectbox(
                                            "Clustering Method",
                                            ["K-Means", "Hierarchical", "DBSCAN"],
                                            help="Choose clustering algorithm"
                                        )
                                    
                                    # Elbow Method 分析 (仅针对K-Means)
                                    if clustering_method == "K-Means":
                                        st.write("#### 📈 Elbow Method for Optimal Number of Clusters")
                                        
                                        # 为Elbow分析准备数据
                                        elbow_data_option = st.selectbox(
                                            "Data for Elbow Analysis",
                                            ["All PCA Components", "First 2 Components", "First 3 Components"],
                                            help="Choose which PCA components to use for Elbow analysis"
                                        )
                                        
                                        if st.button("🔍 Run Elbow Analysis", help="Calculate optimal number of clusters"):
                                            with st.spinner("Running Elbow Method analysis..."):
                                                try:
                                                    # 准备Elbow分析的数据
                                                    if elbow_data_option == "First 2 Components":
                                                        elbow_data = pca_df.iloc[:, :2]
                                                    elif elbow_data_option == "First 3 Components" and n_components >= 3:
                                                        elbow_data = pca_df.iloc[:, :3]
                                                    else:
                                                        elbow_data = pca_df
                                                    
                                                    max_k = min(10, len(elbow_data) // 3)  # 最多测试10个聚类
                                                    k_range = range(1, max_k + 1)
                                                    
                                                    # 计算不同K值的WCSS (Within-Cluster Sum of Squares)
                                                    wcss = []
                                                    silhouette_scores = []
                                                    
                                                    for k in k_range:
                                                        if k == 1:
                                                            # K=1时没有聚类，WCSS为所有点到中心的距离平方和
                                                            center = elbow_data.mean()
                                                            wcss_k = ((elbow_data - center) ** 2).sum().sum()
                                                            wcss.append(wcss_k)
                                                            silhouette_scores.append(0)  # K=1时轮廓系数为0
                                                        else:
                                                            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                                                            kmeans.fit(elbow_data)
                                                            wcss.append(kmeans.inertia_)
                                                            
                                                            # 计算轮廓系数
                                                            if k > 1:
                                                                sil_score = silhouette_score(elbow_data, kmeans.labels_)
                                                                silhouette_scores.append(sil_score)
                                                    
                                                    # 创建Elbow图
                                                    fig_elbow = go.Figure()
                                                    
                                                    # WCSS曲线
                                                    fig_elbow.add_trace(go.Scatter(
                                                        x=list(k_range),
                                                        y=wcss,
                                                        mode='lines+markers',
                                                        name='WCSS (Within-Cluster Sum of Squares)',
                                                        line=dict(color='darkred', width=3),
                                                        marker=dict(size=8, color='red')
                                                    ))
                                                    
                                                    fig_elbow.update_layout(
                                                        title='Elbow Method for Optimal Number of Clusters',
                                                        xaxis_title='Number of Clusters (K)',
                                                        yaxis_title='WCSS',
                                                        font=dict(color='black'),
                                                        plot_bgcolor='white',
                                                        showlegend=True
                                                    )
                                                    
                                                    # 添加注释
                                                    fig_elbow.add_annotation(
                                                        x=max_k//2,
                                                        y=max(wcss)*0.8,
                                                        text="Look for the 'elbow' point<br>where the curve bends sharply",
                                                        showarrow=True,
                                                        arrowhead=2,
                                                        arrowcolor='black',
                                                        font=dict(color='black')
                                                    )
                                                    
                                                    st.plotly_chart(fig_elbow, use_container_width=True)
                                                    
                                                    # 轮廓系数图
                                                    if len(silhouette_scores) > 1:
                                                        fig_sil = go.Figure()
                                                        
                                                        fig_sil.add_trace(go.Scatter(
                                                            x=list(range(2, len(silhouette_scores) + 2)),
                                                            y=silhouette_scores[1:],  # 跳过K=1的情况
                                                            mode='lines+markers',
                                                            name='Silhouette Score',
                                                            line=dict(color='crimson', width=3),
                                                            marker=dict(size=8, color='lightcoral')
                                                        ))
                                                        
                                                        fig_sil.update_layout(
                                                            title='Silhouette Score vs Number of Clusters',
                                                            xaxis_title='Number of Clusters (K)',
                                                            yaxis_title='Silhouette Score',
                                                            font=dict(color='black'),
                                                            plot_bgcolor='white'
                                                        )
                                                        
                                                        # 添加最佳K值标记
                                                        best_k_sil = silhouette_scores[1:].index(max(silhouette_scores[1:])) + 2
                                                        fig_sil.add_annotation(
                                                            x=best_k_sil,
                                                            y=max(silhouette_scores[1:]),
                                                            text=f"Best K={best_k_sil}<br>(Highest Silhouette)",
                                                            showarrow=True,
                                                            arrowhead=2,
                                                            arrowcolor='darkred',
                                                            font=dict(color='black')
                                                        )
                                                        
                                                        st.plotly_chart(fig_sil, use_container_width=True)
                                                    
                                                    # 显示数值表格
                                                    elbow_df = pd.DataFrame({
                                                        'K': list(k_range),
                                                        'WCSS': wcss,
                                                        'Silhouette Score': silhouette_scores
                                                    })
                                                    
                                                    st.write("#### Elbow Analysis Results")
                                                    st.dataframe(elbow_df.round(3), use_container_width=True)
                                                    
                                                    # 建议最佳K值
                                                    # 使用肘部法则：寻找WCSS下降率最大的点
                                                    wcss_diff = np.diff(wcss)
                                                    wcss_diff2 = np.diff(wcss_diff)  # 二阶导数
                                                    
                                                    if len(wcss_diff2) > 0:
                                                        suggested_k = np.argmax(wcss_diff2) + 2  # +2因为索引从0开始，且我们计算的是二阶导数
                                                        suggested_k = min(suggested_k, max_k)  # 确保不超过最大值
                                                    else:
                                                        suggested_k = 3
                                                    
                                                    best_sil_k = silhouette_scores[1:].index(max(silhouette_scores[1:])) + 2 if len(silhouette_scores) > 1 else 3
                                                    
                                                    st.write("#### 🎯 Recommendations")
                                                    rec_cols = st.columns(2)
                                                    
                                                    with rec_cols[0]:
                                                        st.info(f"**Elbow Method Suggests:** K = {suggested_k}")
                                                        st.write("Based on the point where WCSS reduction slows down")
                                                    
                                                    with rec_cols[1]:
                                                        st.info(f"**Silhouette Score Suggests:** K = {best_sil_k}")
                                                        st.write("Based on the highest average silhouette score")
                                                    
                                                    # 综合建议
                                                    if suggested_k == best_sil_k:
                                                        st.success(f"🎉 **Both methods agree:** K = {suggested_k} is recommended!")
                                                    else:
                                                        st.warning(f"📊 **Methods differ:** Consider K = {min(suggested_k, best_sil_k)} to {max(suggested_k, best_sil_k)}")
                                                
                                                except Exception as e:
                                                    st.error(f"Error in Elbow analysis: {str(e)}")
                                        
                                        st.divider()
                                    
                                    with cluster_cols[1]:
                                        if clustering_method in ["K-Means", "Hierarchical"]:
                                            max_clusters = min(15, len(pca_df) // 3)  # 放宽到15个，最少3个样本per cluster
                                            n_clusters = st.slider(
                                                "Number of Clusters",
                                                min_value=2,
                                                max_value=max_clusters,
                                                value=min(3, max_clusters),
                                                help=f"Number of clusters to form (max: {max_clusters} based on sample size)"
                                            )
                                        else:  # DBSCAN
                                            eps = st.slider(
                                                "Epsilon (DBSCAN)",
                                                min_value=0.1,
                                                max_value=2.0,
                                                value=0.5,
                                                step=0.1,
                                                help="Maximum distance between samples"
                                            )
                                    
                                    with cluster_cols[2]:
                                        if clustering_method == "DBSCAN":
                                            min_samples = st.slider(
                                                "Min Samples (DBSCAN)",
                                                min_value=2,
                                                max_value=10,
                                                value=3,
                                                help="Minimum samples in a cluster"
                                            )
                                        else:
                                            use_pca_subset = st.selectbox(
                                                "PCA Components to Use",
                                                ["All Components", "First 2", "First 3"],
                                                help="Select which PCA components to use for clustering"
                                            )
                                    
                                    # 准备聚类数据
                                    if clustering_method != "DBSCAN":
                                        if use_pca_subset == "First 2":
                                            cluster_data = pca_df.iloc[:, :2]
                                        elif use_pca_subset == "First 3" and n_components >= 3:
                                            cluster_data = pca_df.iloc[:, :3]
                                        else:
                                            cluster_data = pca_df
                                    else:
                                        cluster_data = pca_df
                                    
                                    # 执行聚类
                                    if clustering_method == "K-Means":
                                        clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                                        cluster_labels = clusterer.fit_predict(cluster_data)
                                        cluster_centers = clusterer.cluster_centers_
                                    elif clustering_method == "Hierarchical":
                                        clusterer = AgglomerativeClustering(n_clusters=n_clusters)
                                        cluster_labels = clusterer.fit_predict(cluster_data)
                                        cluster_centers = None
                                    else:  # DBSCAN
                                        clusterer = DBSCAN(eps=eps, min_samples=min_samples)
                                        cluster_labels = clusterer.fit_predict(cluster_data)
                                        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
                                        cluster_centers = None
                                    
                                    # 计算聚类评估指标
                                    if len(set(cluster_labels)) > 1:
                                        try:
                                            silhouette_avg = silhouette_score(cluster_data, cluster_labels)
                                            calinski_harabasz = calinski_harabasz_score(cluster_data, cluster_labels)
                                        except:
                                            silhouette_avg = None
                                            calinski_harabasz = None
                                    else:
                                        silhouette_avg = None
                                        calinski_harabasz = None
                                    
                                    # 显示聚类结果
                                    st.write(f"#### Clustering Results ({clustering_method})")
                                    
                                    # 聚类统计
                                    result_cols = st.columns(4)
                                    with result_cols[0]:
                                        st.metric("Number of Clusters", len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0))
                                    with result_cols[1]:
                                        if silhouette_avg is not None:
                                            st.metric("Silhouette Score", f"{silhouette_avg:.3f}")
                                        else:
                                            st.metric("Silhouette Score", "N/A")
                                    with result_cols[2]:
                                        if calinski_harabasz is not None:
                                            st.metric("Calinski-Harabasz Index", f"{calinski_harabasz:.0f}")
                                        else:
                                            st.metric("Calinski-Harabasz Index", "N/A")
                                    with result_cols[3]:
                                        noise_points = sum(cluster_labels == -1) if clustering_method == "DBSCAN" else 0
                                        st.metric("Noise Points", noise_points)
                                    
                                    # 聚类可视化
                                    if n_components >= 2:
                                        st.write("#### Cluster Visualization")
                                        
                                        # 创建聚类数据框
                                        cluster_df = pca_df.copy()
                                        cluster_df['Cluster'] = cluster_labels
                                        cluster_df['Cluster'] = cluster_df['Cluster'].astype(str)
                                        
                                        # 如果有目标变量，添加到聚类结果中
                                        if has_target and len(common_idx) > 0:
                                            cluster_df_with_target = cluster_df.loc[common_idx]
                                            cluster_df_with_target['days_to_labor_ADD'] = target_aligned
                                        
                                        # 动态生成聚类颜色
                                        def generate_red_colors(n_colors):
                                            """生成指定数量的红色系颜色"""
                                            base_colors = ['red', 'darkred', 'lightcoral', 'crimson', 'firebrick', 
                                                         'indianred', 'maroon', 'salmon', 'tomato', 'orangered',
                                                         'rosybrown', 'lightpink', 'hotpink', 'deeppink', 'palevioletred']
                                            
                                            if n_colors <= len(base_colors):
                                                return base_colors[:n_colors]
                                            else:
                                                # 如果需要更多颜色，生成红色渐变
                                                import matplotlib.cm as cm
                                                import matplotlib.colors as mcolors
                                                
                                                # 使用matplotlib的Reds色系生成渐变颜色
                                                reds_cmap = cm.get_cmap('Reds')
                                                colors = []
                                                for i in range(n_colors):
                                                    # 从0.3到1.0生成渐变（避免太浅的颜色）
                                                    intensity = 0.3 + (0.7 * i / max(1, n_colors - 1))
                                                    rgb = reds_cmap(intensity)[:3]  # 获取RGB，忽略alpha
                                                    hex_color = mcolors.rgb2hex(rgb)
                                                    colors.append(hex_color)
                                                return colors
                                        
                                        try:
                                            n_unique_clusters = len(set(cluster_labels))
                                            cluster_colors = generate_red_colors(n_unique_clusters)
                                        except ImportError:
                                            # 如果matplotlib不可用，回退到基础颜色并循环使用
                                            base_colors = ['red', 'darkred', 'lightcoral', 'crimson', 'firebrick', 
                                                         'indianred', 'maroon', 'salmon', 'tomato', 'orangered',
                                                         'rosybrown', 'lightpink', 'hotpink', 'deeppink', 'palevioletred']
                                            n_unique_clusters = len(set(cluster_labels))
                                            cluster_colors = [base_colors[i % len(base_colors)] for i in range(n_unique_clusters)]
                                        
                                        fig_cluster_2d = px.scatter(
                                            cluster_df,
                                            x='PC1',
                                            y='PC2',
                                            color='Cluster',
                                            title=f'{clustering_method} Clustering Results (2D)',
                                            labels={'PC1': f'PC1 ({explained_var_ratio[0]:.1%})',
                                                   'PC2': f'PC2 ({explained_var_ratio[1]:.1%})'},
                                            color_discrete_sequence=cluster_colors
                                        )
                                        
                                        # 添加聚类中心（如果有）
                                        if cluster_centers is not None and cluster_centers.shape[1] >= 2:
                                            fig_cluster_2d.add_trace(go.Scatter(
                                                x=cluster_centers[:, 0],
                                                y=cluster_centers[:, 1],
                                                mode='markers',
                                                marker=dict(
                                                    symbol='x',
                                                    size=15,
                                                    color='black',
                                                    line=dict(width=2)
                                                ),
                                                name='Cluster Centers'
                                            ))
                                        
                                        fig_cluster_2d.update_layout(font=dict(color='black'))
                                        st.plotly_chart(fig_cluster_2d, use_container_width=True)
                                        
                                        # 3D聚类散点图（如果有3个或更多组件）
                                        if n_components >= 3:
                                            fig_cluster_3d = px.scatter_3d(
                                                cluster_df,
                                                x='PC1',
                                                y='PC2',
                                                z='PC3',
                                                color='Cluster',
                                                title=f'{clustering_method} Clustering Results (3D)',
                                                labels={'PC1': f'PC1 ({explained_var_ratio[0]:.1%})',
                                                       'PC2': f'PC2 ({explained_var_ratio[1]:.1%})',
                                                       'PC3': f'PC3 ({explained_var_ratio[2]:.1%})'},
                                                color_discrete_sequence=cluster_colors
                                            )
                                            
                                            fig_cluster_3d.update_layout(font=dict(color='black'))
                                            st.plotly_chart(fig_cluster_3d, use_container_width=True)
                                    
                                    # 聚类特征分析
                                    if has_target and len(common_idx) > 0:
                                        st.write("#### Cluster Analysis vs Target Variable")
                                        
                                        # 每个聚类的目标变量统计
                                        cluster_target_stats = []
                                        for cluster_id in sorted(set(cluster_labels)):
                                            if cluster_id == -1:  # 噪声点
                                                cluster_name = "Noise"
                                            else:
                                                cluster_name = f"Cluster {cluster_id}"
                                            
                                            mask = cluster_labels == cluster_id
                                            cluster_indices = cluster_df.index[mask]
                                            common_cluster_indices = [idx for idx in cluster_indices if idx in common_idx]
                                            
                                            if common_cluster_indices:
                                                cluster_target_values = target_aligned.loc[common_cluster_indices]
                                                
                                                cluster_target_stats.append({
                                                    'Cluster': cluster_name,
                                                    'Count': len(common_cluster_indices),
                                                    'Mean Days to Labor': cluster_target_values.mean(),
                                                    'Std Days to Labor': cluster_target_values.std(),
                                                    'Min Days to Labor': cluster_target_values.min(),
                                                    'Max Days to Labor': cluster_target_values.max(),
                                                    'Median Days to Labor': cluster_target_values.median()
                                                })
                                        
                                        cluster_stats_df = pd.DataFrame(cluster_target_stats)
                                        st.dataframe(cluster_stats_df.round(2), use_container_width=True)
                                        
                                        # 聚类目标变量分布箱线图
                                        if len(cluster_target_stats) > 1:
                                            cluster_target_data = []
                                            for cluster_id in sorted(set(cluster_labels)):
                                                if cluster_id == -1:
                                                    cluster_name = "Noise"
                                                else:
                                                    cluster_name = f"Cluster {cluster_id}"
                                                
                                                mask = cluster_labels == cluster_id
                                                cluster_indices = cluster_df.index[mask]
                                                common_cluster_indices = [idx for idx in cluster_indices if idx in common_idx]
                                                
                                                if common_cluster_indices:
                                                    cluster_target_values = target_aligned.loc[common_cluster_indices]
                                                    for value in cluster_target_values:
                                                        cluster_target_data.append({
                                                            'Cluster': cluster_name,
                                                            'Days to Labor': value
                                                        })
                                            
                                            cluster_target_df = pd.DataFrame(cluster_target_data)
                                            
                                            fig_box = px.box(
                                                cluster_target_df,
                                                x='Cluster',
                                                y='Days to Labor',
                                                title='Days to Labor Distribution by Cluster',
                                                color='Cluster',
                                                color_discrete_sequence=cluster_colors
                                            )
                                            fig_box.update_layout(font=dict(color='black'))
                                            st.plotly_chart(fig_box, use_container_width=True)
                                    
                                    # 原始特征分析
                                    st.write("#### Original Features by Cluster")
                                    
                                    # 创建包含聚类标签的完整数据框
                                    full_cluster_df = feature_data.copy()
                                    full_cluster_df['Cluster'] = cluster_labels
                                    
                                    # 显示每个聚类的原始特征统计
                                    for cluster_id in sorted(set(cluster_labels)):
                                        if cluster_id == -1:
                                            cluster_name = "Noise Points"
                                        else:
                                            cluster_name = f"Cluster {cluster_id}"
                                        
                                        cluster_mask = full_cluster_df['Cluster'] == cluster_id
                                        cluster_features = full_cluster_df[cluster_mask][selected_features]
                                        
                                        if len(cluster_features) > 0:
                                            with st.expander(f"{cluster_name} (n={len(cluster_features)})"):
                                                st.write("**Feature Statistics:**")
                                                st.dataframe(cluster_features.describe().round(3))
                                
                                except ImportError:
                                    st.error("Additional clustering libraries may be required. All clustering functions are included in scikit-learn.")
                                except Exception as e:
                                    st.error(f"Error performing clustering analysis: {str(e)}")
                            
                            # 导出PCA结果选项
                            if st.checkbox("Export PCA Results"):
                                st.write("### Export Options")
                                
                                # 创建完整的PCA结果数据
                                export_df = pca_df.copy()
                                if has_target and len(common_idx) > 0:
                                    export_df['days_to_labor_ADD'] = target_aligned
                                
                                # 添加原始特征
                                for feature in selected_features:
                                    export_df[f'original_{feature}'] = feature_data.loc[export_df.index, feature]
                                
                                st.write("**PCA Results Preview:**")
                                st.dataframe(export_df.head(10))
                                
                                # 下载按钮
                                csv_data = export_df.to_csv(index=True)
                                st.download_button(
                                    label="📥 Download PCA Results as CSV",
                                    data=csv_data,
                                    file_name=f"pca_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                                    mime="text/csv"
                                )
                    
                    except ImportError:
                        st.error("scikit-learn is required for PCA analysis. Please install it using: pip install scikit-learn")
                    except Exception as e:
                        st.error(f"Error performing PCA analysis: {str(e)}")
                
                else:
                    st.warning("Please select at least 2 features for PCA analysis.")
            
            elif analysis_type == "t-SNE Analysis":
                # =============================
                # t-SNE Analysis Section
                # =============================
                if len(selected_features) >= 2:
                    try:
                        from sklearn.manifold import TSNE
                        from sklearn.preprocessing import StandardScaler
                        from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
                        from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score

                        st.write("### t-SNE Dimensionality Reduction & Visualization")

                        # Prepare feature data (raw, with possible NaNs) and target variable
                        feature_data = df[selected_features].copy()
                        target_var_name = "days_to_labor_ADD"
                        has_target = target_var_name in df.columns
                        target_series = df[target_var_name] if has_target else None
                        if not has_target:
                            st.info(f"Target variable '{target_var_name}' not found. Proceeding without coloring by target.")

                        tsne_col_params = st.columns(3)
                        with tsne_col_params[0]:
                            perplexity = st.slider(
                                "Perplexity",
                                min_value=5,
                                max_value=min(50, max(5, len(df)//3)),
                                value=30,
                                step=1,
                                help="Balance between local and global aspects (should be < number of samples/3)"
                            )
                        with tsne_col_params[1]:
                            learning_rate = st.slider(
                                "Learning Rate",
                                min_value=10,
                                max_value=1000,
                                value=200,
                                step=10,
                                help="Too small may get stuck, too large may have poor embedding"
                            )
                        with tsne_col_params[2]:
                            n_iter = st.slider(
                                "Iterations (n_iter)",
                                min_value=250,
                                max_value=2000,
                                value=1000,
                                step=50,
                                help="Number of optimization iterations"
                            )

                        metric = st.selectbox(
                            "Distance Metric",
                            ["euclidean", "cosine", "manhattan"],
                            index=0,
                            help="Metric used to compute pairwise distances"
                        )

                        st.markdown("---")
                        st.write("### Run t-SNE")
                        run_tsne = st.button("🚀 Run t-SNE", key="run_tsne_button")

                        if run_tsne:
                            with st.spinner("Running t-SNE (this may take some time)..."):
                                try:
                                    tsne_features = feature_data[selected_features].copy()
                                    tsne_features = tsne_features.dropna()
                                    if tsne_features.empty:
                                        st.error("Selected features contain only missing values after dropping NA.")
                                    else:
                                        scaler = StandardScaler()
                                        scaled_data = scaler.fit_transform(tsne_features)

                                        tsne = TSNE(
                                            n_components=2,
                                            perplexity=perplexity,
                                            learning_rate=learning_rate,
                                            n_iter=n_iter,
                                            metric=metric,
                                            init="pca",
                                            random_state=42,
                                            verbose=0
                                        )
                                        embedding = tsne.fit_transform(scaled_data)

                                        tsne_df = pd.DataFrame(embedding, columns=["TSNE1", "TSNE2"], index=tsne_features.index)

                                        if has_target and target_series is not None and not target_series.isna().all():
                                            target_aligned = target_series.reindex(tsne_df.index)
                                            valid_target_mask = ~target_aligned.isna()
                                        else:
                                            target_aligned = None
                                            valid_target_mask = pd.Series([False]*len(tsne_df), index=tsne_df.index)

                                        st.success("t-SNE completed successfully.")

                                        # 2D Scatter
                                        st.write("### t-SNE 2D Scatter Plot")
                                        if has_target and valid_target_mask.any():
                                            fig_tsne = px.scatter(
                                                tsne_df[valid_target_mask],
                                                x="TSNE1",
                                                y="TSNE2",
                                                color=target_aligned[valid_target_mask],
                                                title="t-SNE Embedding (Colored by Days to Labor)",
                                                color_continuous_scale="Reds",
                                                labels={"color": "Days to Labor"}
                                            )
                                        else:
                                            fig_tsne = px.scatter(
                                                tsne_df,
                                                x="TSNE1",
                                                y="TSNE2",
                                                title="t-SNE Embedding",
                                                color_discrete_sequence=["crimson"]
                                            )
                                        fig_tsne.update_layout(font=dict(color='black'))
                                        st.plotly_chart(fig_tsne, use_container_width=True)

                                        # Clustering on t-SNE embedding
                                        st.write("### Clustering on t-SNE Embedding")
                                        perform_tsne_clustering = st.checkbox(
                                            "Perform Clustering on t-SNE Results",
                                            key="perform_tsne_clustering",
                                            help="Apply clustering algorithms to the t-SNE embedding"
                                        )
                                        if perform_tsne_clustering:
                                            cluster_cols = st.columns(3)
                                            with cluster_cols[0]:
                                                tsne_clustering_method = st.selectbox(
                                                    "Clustering Method (t-SNE)",
                                                    ["K-Means", "Hierarchical", "DBSCAN"],
                                                    key="tsne_cluster_method",
                                                    help="Choose clustering algorithm"
                                                )
                                            with cluster_cols[1]:
                                                if tsne_clustering_method in ["K-Means", "Hierarchical"]:
                                                    max_clusters_tsne = min(15, len(tsne_df)//3 if len(tsne_df) > 3 else 3)
                                                    tsne_n_clusters = st.slider(
                                                        "Number of Clusters",
                                                        min_value=2,
                                                        max_value=max_clusters_tsne if max_clusters_tsne >= 2 else 2,
                                                        value=min(3, max_clusters_tsne) if max_clusters_tsne >= 3 else 2,
                                                        key="tsne_n_clusters",
                                                        help="Number of clusters to form"
                                                    )
                                                else:
                                                    tsne_eps = st.slider(
                                                        "Epsilon (DBSCAN)",
                                                        min_value=0.1,
                                                        max_value=5.0,
                                                        value=1.5,
                                                        step=0.1,
                                                        key="tsne_eps",
                                                        help="Maximum distance between samples"
                                                    )
                                            with cluster_cols[2]:
                                                if tsne_clustering_method == "DBSCAN":
                                                    tsne_min_samples = st.slider(
                                                        "Min Samples (DBSCAN)",
                                                        min_value=2,
                                                        max_value=20,
                                                        value=5,
                                                        key="tsne_min_samples",
                                                        help="Minimum samples in a cluster"
                                                    )
                                                else:
                                                    tsne_dummy = st.empty()

                                            # Execute clustering
                                            if tsne_clustering_method == "K-Means":
                                                tsne_clusterer = KMeans(n_clusters=tsne_n_clusters, random_state=42, n_init=10)
                                                tsne_labels = tsne_clusterer.fit_predict(tsne_df)
                                                tsne_centers = tsne_clusterer.cluster_centers_
                                            elif tsne_clustering_method == "Hierarchical":
                                                tsne_clusterer = AgglomerativeClustering(n_clusters=tsne_n_clusters)
                                                tsne_labels = tsne_clusterer.fit_predict(tsne_df)
                                                tsne_centers = None
                                            else:
                                                tsne_clusterer = DBSCAN(eps=tsne_eps, min_samples=tsne_min_samples)
                                                tsne_labels = tsne_clusterer.fit_predict(tsne_df)
                                                tsne_centers = None

                                            # Metrics
                                            if len(set(tsne_labels)) > 1:
                                                try:
                                                    tsne_silhouette = silhouette_score(tsne_df, tsne_labels)
                                                    tsne_calinski = calinski_harabasz_score(tsne_df, tsne_labels)
                                                    tsne_davies = davies_bouldin_score(tsne_df, tsne_labels)
                                                except Exception:
                                                    tsne_silhouette = tsne_calinski = tsne_davies = None
                                            else:
                                                tsne_silhouette = tsne_calinski = tsne_davies = None

                                            st.write(f"#### Clustering Results ({tsne_clustering_method})")
                                            metric_cols = st.columns(4)
                                            with metric_cols[0]:
                                                st.metric("Clusters", len(set(tsne_labels)) - (1 if -1 in tsne_labels else 0))
                                            with metric_cols[1]:
                                                st.metric("Silhouette", f"{tsne_silhouette:.3f}" if tsne_silhouette is not None else "N/A")
                                            with metric_cols[2]:
                                                st.metric("Calinski-Harabasz", f"{tsne_calinski:.0f}" if tsne_calinski is not None else "N/A")
                                            with metric_cols[3]:
                                                st.metric("Davies-Bouldin", f"{tsne_davies:.3f}" if tsne_davies is not None else "N/A")

                                            # Color palette for clusters
                                            def generate_red_colors(n_colors):
                                                base_colors = ['red', 'darkred', 'lightcoral', 'crimson', 'firebrick',
                                                               'indianred', 'maroon', 'salmon', 'tomato', 'orangered',
                                                               'rosybrown', 'lightpink', 'hotpink', 'deeppink', 'palevioletred']
                                                if n_colors <= len(base_colors):
                                                    return base_colors[:n_colors]
                                                else:
                                                    import matplotlib.cm as cm
                                                    import matplotlib.colors as mcolors
                                                    reds_cmap = cm.get_cmap('Reds')
                                                    colors = []
                                                    for i in range(n_colors):
                                                        intensity = 0.3 + (0.7 * i / max(1, n_colors - 1))
                                                        rgb = reds_cmap(intensity)[:3]
                                                        colors.append(mcolors.rgb2hex(rgb))
                                                    return colors
                                            try:
                                                cluster_colors_tsne = generate_red_colors(len(set(tsne_labels)))
                                            except Exception:
                                                base_colors_fallback = ['red', 'darkred', 'lightcoral', 'crimson', 'firebrick']
                                                cluster_colors_tsne = [base_colors_fallback[i % len(base_colors_fallback)] for i in range(len(set(tsne_labels)))]

                                            tsne_cluster_df = tsne_df.copy()
                                            tsne_cluster_df['Cluster'] = tsne_labels.astype(str)
                                            if has_target and target_aligned is not None and valid_target_mask.any():
                                                tsne_cluster_df['days_to_labor_ADD'] = target_aligned

                                            fig_tsne_cluster = px.scatter(
                                                tsne_cluster_df,
                                                x='TSNE1',
                                                y='TSNE2',
                                                color='Cluster',
                                                title=f't-SNE Clustering Results ({tsne_clustering_method})',
                                                color_discrete_sequence=cluster_colors_tsne
                                            )
                                            if tsne_centers is not None:
                                                fig_tsne_cluster.add_trace(go.Scatter(
                                                    x=tsne_centers[:, 0],
                                                    y=tsne_centers[:, 1],
                                                    mode='markers',
                                                    marker=dict(symbol='x', size=15, color='black', line=dict(width=2)),
                                                    name='Cluster Centers'
                                                ))
                                            fig_tsne_cluster.update_layout(font=dict(color='black'))
                                            st.plotly_chart(fig_tsne_cluster, use_container_width=True)

                                            # Relationship with target
                                            if has_target and target_aligned is not None and valid_target_mask.any():
                                                st.write("#### Cluster vs Target Variable")
                                                cluster_target_stats = []
                                                for cluster_id in sorted(set(tsne_labels)):
                                                    cluster_name = "Noise" if cluster_id == -1 else f"Cluster {cluster_id}"
                                                    mask_cluster = tsne_labels == cluster_id
                                                    indices_cluster = tsne_df.index[mask_cluster]
                                                    aligned_values = target_aligned.loc[indices_cluster].dropna()
                                                    if not aligned_values.empty:
                                                        cluster_target_stats.append({
                                                            'Cluster': cluster_name,
                                                            'Count': len(aligned_values),
                                                            'Mean Days': aligned_values.mean(),
                                                            'Std Days': aligned_values.std(),
                                                            'Min Days': aligned_values.min(),
                                                            'Max Days': aligned_values.max(),
                                                            'Median Days': aligned_values.median()
                                                        })
                                                if cluster_target_stats:
                                                    st.dataframe(pd.DataFrame(cluster_target_stats).round(2), use_container_width=True)

                                        # Export t-SNE results
                                        if st.checkbox("Export t-SNE Results"):
                                            export_tsne_df = tsne_df.copy()
                                            if has_target and target_aligned is not None and valid_target_mask.any():
                                                export_tsne_df['days_to_labor_ADD'] = target_aligned
                                            for feature in selected_features:
                                                export_tsne_df[f'original_{feature}'] = feature_data.loc[export_tsne_df.index, feature]
                                            st.write("**t-SNE Results Preview:**")
                                            st.dataframe(export_tsne_df.head(10))
                                            csv_tsne = export_tsne_df.to_csv(index=True)
                                            st.download_button(
                                                label="📥 Download t-SNE Results as CSV",
                                                data=csv_tsne,
                                                file_name=f"tsne_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                                                mime="text/csv",
                                                key="download_tsne_csv"
                                            )

                                except Exception as e:
                                    st.error(f"Error running t-SNE: {str(e)}")
                    except ImportError:
                        st.error("scikit-learn is required for t-SNE. Please install it using: pip install scikit-learn")
                    except Exception as e:
                        st.error(f"Unexpected error in t-SNE section: {str(e)}")
                else:
                    st.warning("Please select at least 2 features for t-SNE analysis.")

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
                            