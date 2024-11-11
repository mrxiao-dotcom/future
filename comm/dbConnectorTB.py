import pymysql
from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

class DBConnector:
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBConnector, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._pool is None:
            self._pool = PooledDB(
                creator=pymysql,
                maxconnections=int(os.getenv('DB_MAX_CONNECTIONS', 6)),
                mincached=int(os.getenv('DB_MIN_CACHED', 2)),
                maxcached=int(os.getenv('DB_MAX_CACHED', 5)),
                blocking=True,
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 3306)),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', ''),
                database=os.getenv('DB_NAME', 'futures_db'),
                charset='utf8mb4'
            )
    
    def get_connection(self):
        return self._pool.connection()

# 创建单例实例
db_connector = DBConnector()