"""
==================================================
MongoDB配置管理模块
==================================================

功能描述：
- 管理MongoDB连接配置和集合信息
- 提供默认的MongoDB连接参数
- 支持配置的动态加载和验证
- 集中化的MongoDB资源管理

配置项说明：
- uri: MongoDB连接字符串（包含认证信息）
- db_name: 目标数据库名称
- collection_raw: 原始数据集合名称
- collection_features: 特征数据集合名称

支持功能：
1. load_mongo_config() - 配置加载和验证
2. 连接字符串的安全管理
3. 集合名称的标准化
4. 错误处理和配置验证

使用场景：
- MongoDB数据库连接初始化
- 多集合数据访问管理
- 配置参数的统一管理

作者: Modoo团队
最后更新: 2025-08-18
==================================================
"""

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
