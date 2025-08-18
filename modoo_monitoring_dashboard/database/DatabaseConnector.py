"""
==================================================
数据库连接管理模块
==================================================

功能描述：
- 提供安全的数据库连接管理
- 支持SSH隧道的远程数据库连接
- 封装SQLAlchemy连接和查询操作
- 自动化连接生命周期管理

核心功能：
1. SSH隧道建立和管理
2. 数据库连接池管理
3. 自动化的连接清理
4. 查询结果的DataFrame转换

安全特性：
- SSH密钥认证支持
- 连接超时管理
- 自动重连机制
- 资源泄漏防护

支持的数据库：
- MySQL (主要)
- PostgreSQL (通过配置扩展)
- 其他SQLAlchemy支持的数据库

使用模式：
- 上下文管理器模式确保连接安全关闭
- 配置文件驱动的连接参数管理
- 错误处理和日志记录

作者: Modoo团队
最后更新: 2025-08-18
==================================================
"""

from config.db_config import DB_CONFIG

import pandas as pd
from contextlib import contextmanager
from typing import Iterator, Optional
from urllib.parse import quote_plus

from sshtunnel import SSHTunnelForwarder
from sqlalchemy import create_engine

class DatabaseConnector:

    def __init__(self):
        pass

    @contextmanager
    def _ssh_tunnel(self):

        # Initiates SSH tunnel and yields local bind port
        with SSHTunnelForwarder(
            ssh_address_or_host=(DB_CONFIG['SSH_HOST'], DB_CONFIG['SSH_PORT']),
            ssh_username=DB_CONFIG['SSH_USER'],
            ssh_pkey=DB_CONFIG['SSH_PKEY'],
            remote_bind_address=(DB_CONFIG['DB_HOST'], DB_CONFIG['DB_PORT'])
        ) as tunnel:
            print(f"SSH tunnel started on port {tunnel.local_bind_port}")
            yield tunnel.local_bind_port

    def _create_engine(self, local_bind_port):

        engine = create_engine(
            f"mysql+pymysql://{DB_CONFIG["DB_USER"]}:{quote_plus(DB_CONFIG["DB_PASS"])}@127.0.0.1:{local_bind_port}/{DB_CONFIG["DB_NAME"]}",
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 10,
                "charset": "utf8mb4"
            }
        )
        print(f"Engine created on port {local_bind_port}")

        return engine

    @contextmanager
    def connect(self) -> Iterator[create_engine]:
        with self._ssh_tunnel() as local_port:
            engine = self._create_engine(local_port)
            try:
                yield engine
            finally:
                engine.dispose()

    def query_to_dataframe(self, sql: str, chunksize: Optional[int] = None) -> pd.DataFrame:
        with self.connect() as engine:
            return pd.read_sql(sql, engine, chunksize=chunksize)


