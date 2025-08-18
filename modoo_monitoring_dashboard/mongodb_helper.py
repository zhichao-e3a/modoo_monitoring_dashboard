import streamlit as st
from pymongo import MongoClient
import pandas as pd
from mongo_config import load_mongo_config

def extract_mongodb_value(value):
    """从MongoDB数据中提取数值"""
    if isinstance(value, dict):
        if "$numberDouble" in value:
            return float(value["$numberDouble"])
        elif "$numberInt" in value:
            return int(value["$numberInt"])
        elif "$numberLong" in value:
            return int(value["$numberLong"])
    return value

def fetch_features(contact_numbers=None):
    """从MongoDB获取特征数据"""
    try:
        config = load_mongo_config()  # 获取MongoDB配置
        st.write("Loading MongoDB configuration...")
        st.write(f"Database: {config['db_name']}")
        st.write(f"Collection: {config['collection_features']}")
        st.write("Connecting to MongoDB...")
        client = MongoClient(config["uri"])
        db = client[config["db_name"]]
        collection = db[config["collection_features"]]
        st.write("Successfully connected to MongoDB")
        
        all_features = []
        query = {}
        if contact_numbers:
            query["contact_number"] = {"$in": contact_numbers}
            
        # 获取总文档数
        total_docs = collection.count_documents(query)
        st.write(f"Found {total_docs} documents in features collection")
        
        # 调试：显示第一条文档的结构
        first_doc = collection.find_one(query)
        if first_doc:
            st.write("Debug: Document structure:")
            st.write(list(first_doc.keys()))
            if "measurements" in first_doc:
                st.write("Number of measurements:", len(first_doc.get("measurements", [])))
                if first_doc["measurements"]:
                    st.write("First measurement keys:", list(first_doc["measurements"][0].keys()))
        
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
            
        for i, doc in enumerate(collection.find(query)):
            # 更新进度
            progress = (i + 1) / total_docs
            progress_bar.progress(progress)
            status_text.write(f"Processing document {i + 1} of {total_docs}")
            
            contact_number = doc.get("contact_number")
            if not contact_number:
                continue

            measurements = doc.get("measurements", [])
            
            # 显示每个文档的测量数
            st.write(f"Document {i+1}: Found {len(measurements)} measurements for contact number {contact_number}")
                
            for idx, measurement in enumerate(measurements):
                if not isinstance(measurement, dict):
                    st.warning(f"Skipping invalid measurement {idx+1} for contact number {contact_number}")
                    continue
                
                # 调试第一条记录
                if len(all_features) == 0:
                    st.write("Debug: First measurement data:")
                    st.write({k: v for k, v in measurement.items() if k != 'data'})
                
                # 创建特征字典
                feature_dict = {
                    "composite_key": f"{contact_number}_{measurement.get('date', '')}_{measurement.get('timestamp', '')}",
                    "gestational_age_days": extract_mongodb_value(measurement.get("gestational_age_days")),
                    "contraction_rate": extract_mongodb_value(measurement.get("total_contraction_rate")),
                    "sample_entropy": extract_mongodb_value(measurement.get("sample_entropy")),
                    "acceleration_count": extract_mongodb_value(measurement.get("acceleration_count")),
                    "deceleration_count": extract_mongodb_value(measurement.get("deceleration_count")),
                    "days_to_labor_EDD": extract_mongodb_value(measurement.get("days_to_labor_EDD")),
                    "days_to_labor_ADD": extract_mongodb_value(measurement.get("days_to_labor_ADD")),
                    "mean_auc": extract_mongodb_value(measurement.get("mean_auc")),
                    "mean_rise_time": extract_mongodb_value(measurement.get("mean_rise_time")),
                    "mean_fall_time": extract_mongodb_value(measurement.get("mean_fall_time")),
                    "contraction_count": extract_mongodb_value(measurement.get("total_contraction_count")),
                    "median_duration": extract_mongodb_value(measurement.get("median_duration")),
                    "median_peak_intensity": extract_mongodb_value(measurement.get("median_peak_intensity")),
                    "baseline_tone": extract_mongodb_value(measurement.get("baseline_tone")),
                    "test_duration_seconds": extract_mongodb_value(measurement.get("test_duration_seconds")),
                    "range": extract_mongodb_value(measurement.get("range")),
                    "mean_intensity": extract_mongodb_value(measurement.get("mean_intensity")),
                    "min_contraction": extract_mongodb_value(measurement.get("min_contraction")),
                    "max_contraction": extract_mongodb_value(measurement.get("max_contraction")),
                    "mean_contraction": extract_mongodb_value(measurement.get("mean_contraction")),
                    "std_contraction": extract_mongodb_value(measurement.get("std_contraction"))
                }
                
                # 处理特殊字段
                if "total_auc" in measurement:
                    feature_dict["total_auc"] = extract_mongodb_value(measurement["total_auc"])
                if "mvu_array" in measurement:
                    feature_dict["mvu_value"] = extract_mongodb_value(measurement["mvu_array"])
                
                all_features.append(feature_dict)
                
                # 调试第一条记录的解析结果
                if len(all_features) == 1:
                    st.write("Debug: First processed feature record:")
                    st.write(feature_dict)
        
        # 创建DataFrame
        df = pd.DataFrame(all_features)
        
        # 调试信息
        if not df.empty:
            st.write("\nDebug: DataFrame info:")
            st.write("Shape:", df.shape)
            st.write("Columns:", list(df.columns))
            st.write("Non-null counts:")
            st.write(df.count())
        else:
            st.warning("No features data was extracted!")
            
        return df
        
    except Exception as e:
        st.error(f"Error fetching features: {str(e)}")
        return pd.DataFrame()
    finally:
        client.close()
        if 'progress_bar' in locals():
            progress_bar.empty()
        if 'status_text' in locals():
            status_text.empty()
