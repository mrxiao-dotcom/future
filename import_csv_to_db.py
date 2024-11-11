import pandas as pd
import mysql.connector
from mysql.connector import Error

class CSVImporter:
    def __init__(self):
        self.host = "10.17.31.47"
        self.user = "root"
        self.password = "fsR6Hf$"
        self.port = 3306
        self.database = "tbauto"
        self.table = "tbPriceData"

    def get_connection(self):
        """创建数据库连接"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port
            )
            if connection.is_connected():
                print("成功连接到数据库")
            return connection
        except Error as e:
            print(f"数据库连接错误: {e}")
            return None

    def check_duplicates(self, df):
        """检查重复记录"""
        # 使用第一列和第二列作为日期时间和品种
        duplicates = df[df.duplicated(subset=[df.columns[0], df.columns[1]], keep=False)]
        if not duplicates.empty:
            print("发现重复记录：")
            for index, row in duplicates.iterrows():
                print(f"行 {index + 1}: 日期时间={row[df.columns[0]]}, 品种={row[df.columns[1]]}")
        else:
            print("没有发现重复记录。")

    def import_to_db(self, df):
        """导入数据到数据库"""
        connection = self.get_connection()
        if connection is None:
            return

        try:
            cursor = connection.cursor()

            # 插入数据
            for index, row in df.iterrows():
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
                cursor.execute(sql, (
                    row[df.columns[0]],  # PriceTime
                    row[df.columns[1]],  # ProductCode
                    row[df.columns[2]],  # ClosePrice
                    row[df.columns[3]],  # Position
                    row[df.columns[4]],  # StopPrice
                    row[df.columns[5]],  # Nums
                    row[df.columns[6]]   # Equity
                ))

            connection.commit()
            print("数据导入成功。")
        except Error as e:
            print(f"数据库错误: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def run(self, file_path):
        """运行导入过程"""
        # 读取 CSV 文件
        df = pd.read_csv(file_path)

        # 检查重复记录
        self.check_duplicates(df)

        # 导入数据到数据库
        self.import_to_db(df)

if __name__ == "__main__":
    importer = CSVImporter()
    importer.run("tmpnew.csv")