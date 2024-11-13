from .dbConnectorTB import db_connector

class DBOperator:
    @staticmethod
    def execute_query(sql, params=None):
        """执行查询SQL语句"""
        conn = db_connector.get_connection()
        try:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(sql, params or ())
                    result = cursor.fetchall()
                    return result
                except Exception as e:
                    print(f"SQL execution error: {str(e)}")
                    raise
        except Exception as e:
            print(f"Database error: {str(e)}")
            raise
        finally:
            conn.close()
    
    @staticmethod
    def execute_update(sql, params=None):
        """执行更新SQL语句"""
        conn = db_connector.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                conn.commit()
                return cursor.rowcount
        finally:
            conn.close()
    
    @staticmethod
    def execute_many(sql, params_list):
        """批量执行SQL语句"""
        conn = db_connector.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.executemany(sql, params_list)
                conn.commit()
                return cursor.rowcount
        finally:
            conn.close()
            
    @staticmethod
    def get_connection():
        """获取数据库连接"""
        return db_connector.get_connection() 