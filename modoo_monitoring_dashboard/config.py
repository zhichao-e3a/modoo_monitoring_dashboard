"""MongoDB configuration module"""
import streamlit as st

# Default MongoDB Configuration
DEFAULT_MONGO_CONFIG = {
    "uri": "mongodb://root:E3Aroot888@dds-n9e25b39e6dfb0941313-pub.mongodb.rds.aliyuncs.com:3717/admin?replicaSet=mgset-90721735",
    "db_name": "Modoo_data",
    "collection_raw": "recruited_patients_raw_data",
    "collection_features": "recruited_patients_data"
}

def load_mongo_config():
    """加载MongoDB配置，优先使用用户自定义配置"""
    if 'mongo_config' not in st.session_state:
        st.session_state.mongo_config = DEFAULT_MONGO_CONFIG.copy()
    return st.session_state.mongo_config

def save_mongo_config(config):
    """保存MongoDB配置到session state"""
    st.session_state.mongo_config = config
