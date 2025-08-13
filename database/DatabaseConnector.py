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


