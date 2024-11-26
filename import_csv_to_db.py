import pandas as pd
import mysql.connector
from mysql.connector import Error
import time
import sys

class CSVImporter:
    def __init__(self):
        self.host = "10.17.31.104"
        self.user = "root"
        self.password = "Xj774913@"
        self.port = 3306
        self.database = "tbauto"
        self.table = "tbpricedata"
        self.max_retries = 3
        self.retry_delay = 2  # 秒

    def get_connection(self):
        """创建数据库连接，带重试机制"""
        for attempt in range(self.max_retries):
            try:
                print(f"尝试连接数据库 (尝试 {attempt + 1}/{self.max_retries})...")
                connection = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    port=self.port,
                    connect_timeout=10,  # 添加连接超时
                    charset='utf8mb4',
                    use_pure=True  # 使用纯Python实现
                )
                
                if connection.is_connected():
                    db_info = connection.get_server_info()
                    print(f"成功连接到MySQL数据库，版本: {db_info}")
                    return connection
                    
            except Error as e:
                print(f"数据库连接错误 (尝试 {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    print(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    print("达到最大重试次数，退出程序")
                    sys.exit(1)
            except Exception as e:
                print(f"发生未预期的错误: {e}")
                sys.exit(1)
        
        return None

    def test_connection(self):
        """测试数据库连接"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                print(f"数据库版本: {version[0]}")
                cursor.close()
                connection.close()
                return True
        except Error as e:
            print(f"测试连接失败: {e}")
            return False

    def check_duplicates(self, df):
        """检查重复记录"""
        try:
            # 使用第一列和第二列作为日期时间和品种
            duplicates = df[df.duplicated(subset=[df.columns[0], df.columns[1]], keep=False)]
            if not duplicates.empty:
                print("发现重复记录：")
                print(duplicates)
            else:
                print("没有发现重复记录。")
        except Exception as e:
            print(f"检查重复记录时出错: {e}")

    def import_to_db(self, df):
        """导入数据到数据库"""
        connection = self.get_connection()
        if connection is None:
            return

        cursor = None
        try:
            cursor = connection.cursor()
            
            # 打印数据框的列名和前几行数据
            print("数据框列名:", df.columns.tolist())
            print("前几行数据:")
            print(df.head())

            # 插入数据
            for index, row in df.iterrows():
                try:
                    sql = f"""
                    INSERT INTO {self.table} (PriceTime, ProductCode, ClosePrice, Position, StopPrice, Nums, Equity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    ClosePrice = VALUES(ClosePrice),
                    Position = VALUES(Position),
                    StopPrice = VALUES(StopPrice),
                    Nums = VALUES(Nums),
                    Equity = VALUES(Equity)
                    """
                    
                    values = (
                        row[df.columns[0]],  # PriceTime
                        row[df.columns[1]],  # ProductCode
                        float(row[df.columns[2]]) if pd.notna(row[df.columns[2]]) else None,  # ClosePrice
                        int(row[df.columns[3]]) if pd.notna(row[df.columns[3]]) else None,  # Position
                        float(row[df.columns[4]]) if pd.notna(row[df.columns[4]]) else None,  # StopPrice
                        int(row[df.columns[5]]) if pd.notna(row[df.columns[5]]) else None,  # Nums
                        float(row[df.columns[6]]) if pd.notna(row[df.columns[6]]) else None  # Equity
                    )
                    
                    cursor.execute(sql, values)
                    
                    if index % 100 == 0:  # 每100条记录提交一次
                        connection.commit()
                        print(f"已处理 {index + 1} 条记录")
                        
                except Exception as e:
                    print(f"插入记录 {index + 1} 时出错: {e}")
                    print("数据:", values)
                    continue

            connection.commit()
            print("数据导入完成。")
            
        except Error as e:
            print(f"数据库错误: {e}")
            
        finally:
            if cursor:
                cursor.close()
            if connection.is_connected():
                connection.close()
                print("数据库连接已关闭")

    def run(self, file_path):
        """运行导入过程"""
        try:
            # 首先测试数据库连接
            if not self.test_connection():
                print("数据库连接测试失败，程序退出")
                sys.exit(1)

            print(f"开始读取文件: {file_path}")
            # 读取 CSV 文件
            df = pd.read_csv(file_path)
            print(f"成功读取文件，共 {len(df)} 行数据")

            # 检查重复记录
            self.check_duplicates(df)

            # 导入数据到数据库
            self.import_to_db(df)
            
        except Exception as e:
            print(f"处理文件时出错: {e}")
            sys.exit(1)

if __name__ == "__main__":
    try:
        importer = CSVImporter()
        importer.run("tmpnew.csv")
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"程序执行出错: {e}")
        sys.exit(1)