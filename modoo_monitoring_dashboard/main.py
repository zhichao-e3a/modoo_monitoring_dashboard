"""
==================================================
Modoo监控仪表板 - 主程序入口
==================================================

功能描述：
- 多数据源监控仪表板的主入口程序
- 提供简洁的侧边栏导航界面
- 支持CSV文件数据分析和MongoDB数据查看
- 集成信号处理、EDA分析和数据可视化功能

主要功能模块：
1. CSV数据分析页面 - 自定义数据上传和可视化
2. MongoDB数据页面 - 数据库连接和高级分析
 
最后更新: 2025-08-18
==================================================
"""

import streamlit as st
import pandas as pd
from custom_data_page import show_custom_data_page
from Mongo_Reader import show_mongodb_data_page
import os

# Configure Streamlit to handle large files - this must be the first st command
st.set_page_config(
    page_title="Data Analysis Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Display logos in sidebar
logo_path = os.path.join(os.path.dirname(__file__), "peter.png")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, width=260)

# Increase the upload limit (set to 1GB)
st.cache_data.clear()
st._config.set_option('server.maxUploadSize', 1024)

# Create page selector
page = st.sidebar.selectbox(
    "Data Source",
    ["CSV", "MongoDB"],
    format_func=lambda x: f"Load from {x}"
)

# Reset settings button
if st.sidebar.button("Reset All Settings"):
    # Create a copy of keys since we'll be modifying the dict during iteration
    keys = list(st.session_state.keys())
    for key in keys:
        del st.session_state[key]
    st.rerun()

st.sidebar.markdown("---")

# Display selected page
if page == "CSV":
    show_custom_data_page()
else:
    show_mongodb_data_page()