from utils.MySQLBase import MSSQL
import time
from decimal import Decimal


class MyDBConn:
    def __init__(self, data_source): #local 1
        self.data_source = data_source
        self.ms = MSSQL(data_source)

    def ExceptionThrow(self,e):
        print(e.__traceback__.tb_frame.f_globals["__file__"])  # 发生异常所在的文件
        print("异常发生在(行):",e.__traceback__.tb_lineno)  # 发生异常所在的行数


    def QueryProfit(self):

        result = []
        try:

            sqlstr = "select Profit,ProfitTime from tbProfit order by id ASC "
            data = self.ms.ExecQuery(sqlstr)
            result = data

        except Exception as e:

            print(e)

        return result