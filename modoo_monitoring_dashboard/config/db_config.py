"""
==================================================
数据库配置管理模块
==================================================

功能描述：
- 集中管理数据库连接配置参数
- 支持环境变量和.env文件配置
- 提供SSH隧道和数据库连接的完整配置
- 安全的敏感信息管理

配置项说明：
- DB_HOST: 数据库服务器地址
- DB_PORT: 数据库端口
- DB_USER/DB_PASS: 数据库认证信息
- DB_NAME: 目标数据库名称
- SSH_HOST/SSH_PORT: SSH隧道服务器配置
- SSH_USER/SSH_PASS: SSH认证信息

安全特性：
- 环境变量优先加载
- 敏感信息不硬编码
- 支持.env文件配置管理

使用方式：
- 通过DB_CONFIG字典访问所有配置
- 与DatabaseConnector模块配合使用

作者: Modoo团队
最后更新: 2025-08-18
==================================================
"""

import os
from dotenv import load_dotenv

load_dotenv("config/.env")

DB_CONFIG = {
    'DB_HOST'   : os.getenv("DB_HOST"),
    'DB_PORT'   : int(os.getenv("DB_PORT")),
    'DB_USER'   : os.getenv("DB_USER"),
    'DB_PASS'   : os.getenv("DB_PASS"),
    'DB_NAME'   : os.getenv("DB_NAME"),
    'SSH_HOST'  : os.getenv("SSH_HOST"),
    'SSH_PORT'  : int(os.getenv("SSH_PORT")),
    'SSH_USER'  : os.getenv("SSH_USER"),
    'SSH_PKEY'  : os.getenv("SSH_PKEY")
}
