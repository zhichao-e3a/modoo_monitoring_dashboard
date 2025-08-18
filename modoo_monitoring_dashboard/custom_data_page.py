"""
==================================================
自定义数据分析页面模块
==================================================

功能描述：
- 提供CSV文件上传和自定义数据可视化功能
- 支持多Y轴数据的交互式图表创建
- 集成信号数据的专业可视化分析
- 用户友好的数据探索界面

主要功能：
1. CSV文件拖拽上传界面
2. 多变量条形图可视化
3. X轴和Y轴数据的灵活选择
4. 基础统计信息展示
5. 信号数据的详细分析（调用list_data_viewer）

图表特色：
- 支持最多3个Y轴变量同时显示
- 预定义的颜色方案
- 叠加显示模式
- 容器自适应宽度

使用场景：
- 快速数据探索和分析
- CSV数据的可视化验证
- 多变量关系分析
- 信号数据的初步查看

作者: Modoo团队
最后更新: 2025-08-18
==================================================
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from list_data_viewer import display_list_data

def show_custom_data_page():
    st.title("Signal Data Visualization")
    
    # File upload with info about large file support
    st.info("💡 This application supports large CSV files (up to 1GB)")
    uploaded_file = st.file_uploader(
        "Choose CSV File",
        type=['csv'],
        help="Upload your CSV file containing signal data"
    )
    
    if uploaded_file is not None:
        try:
            # 读取CSV文件
            df = pd.read_csv(uploaded_file)
            
            # Display data preview
            st.subheader("Data Preview")
            st.dataframe(df.head())
            
            # Select columns to display
            st.subheader("Select Data to Display")
            
            # Get numeric columns
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if not numeric_columns:
                st.error("No numeric columns found in the CSV file")
                return
                
            # Select X-axis data
            x_column = st.selectbox(
                "Select X-axis Data (Time)",
                numeric_columns,
                index=0 if numeric_columns else None
            )
            
            # Select multiple Y-axis data
            y_columns = st.multiselect(
                "Select Y-axis Data (Multiple)",
                [col for col in numeric_columns if col != x_column],
                max_selections=3  # Maximum 3 data series
            )
            
            if y_columns:
                # Create chart
                fig = go.Figure()
                
                # Add each selected data series
                colors = ['rgb(158,202,225)', 'rgb(255,127,14)', 'rgb(44,160,44)']  # predefined colors
                for i, y_column in enumerate(y_columns):
                    fig.add_trace(
                        go.Bar(
                            x=df[x_column],
                            y=df[y_column],
                            name=y_column,
                            marker_color=colors[i % len(colors)]
                        )
                    )
                
                # Update layout
                fig.update_layout(
                    title="Data Visualization",
                    xaxis_title=x_column,
                    yaxis_title="Value",
                    height=600,
                    showlegend=True,
                    bargap=0,  # Remove gap between bars
                    bargroupgap=0.1,  # Small gap between different data series
                    barmode='overlay'  # Overlay bars on top of each other
                )
                
                # 显示图表
                st.plotly_chart(fig, use_container_width=True)
                
                # Display basic statistics
                st.subheader("Data Statistics")
                for col in y_columns:
                    with st.expander(f"{col} Statistics"):
                        stats = df[col].describe()
                        st.write(stats)
                        
            # Add a separator
            st.divider()
            
            # Display list data visualization
            display_list_data(df)
                
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
            st.info("Please ensure the CSV file format is correct and contains numeric columns")
    
    # Add example file format description
    with st.expander("CSV File Format Guide"):
        st.markdown("""
        The CSV file should contain:
        - At least one numeric column for X-axis (time)
        - At least one numeric column for Y-axis (signal data)
        
        Example:
        ```
        time,value1,value2
        0,100,20
        1,102,22
        2,98,18
        ...
        ```
        """)
