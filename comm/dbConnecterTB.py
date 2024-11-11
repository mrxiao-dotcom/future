from utils.MySQLBase import MSSQL
import time


class MyDBConn:
    def __init__(self, data_source): #local 1
        self.data_source = data_source
        self.ms = MSSQL(data_source)

    def ExceptionThrow(self,e):
        print(e.__traceback__.tb_frame.f_globals["__file__"])  # 发生异常所在的文件
        print("异常发生在(行):",e.__traceback__.tb_lineno)  # 发生异常所在的行数

    # 留
    def QueryProduct(self):
        try:
            sqlstr = "select DISTINCT productCode from tbPriceData"
            data = self.ms.ExecQuery(sqlstr)
            ret = [x[0] for x in data]
            return ret
        except Exception as e:
            print("数据库查找queryProduct表，出现错误,语句为：" + sqlstr + "异常代码：", e)
            self.ExceptionThrow(e)


    def QueryPriceData(self,symbol):

        try:
            sqlstr = "select PriceTime, ClosePrice  from tbPriceData where ProductCode ='" + symbol + "' order by PriceTime asc"

            retData = self.ms.ExecQuery(sqlstr)
            return retData

        except Exception as e:
            print("执行queryPriceData抛出异常，原因是:", e, sqlstr)
            self.ExceptionThrow(e)


    def QueryTime(self,symbol='ag'):
        try:
            sqlstr = "select PriceTime from tbPriceData  where ProductCode = '" + symbol + "' order by PriceTime ASC "
            retData = self.ms.ExecQuery(sqlstr)
            ret = [x[0] for x in retData]
            return ret
        except Exception as e:
            print("执行queryTime抛出异常，原因是:", e, sqlstr)
            self.ExceptionThrow(e)


    def QuerySyslog(self,):
        try:
            sqlstr = "select create_time,log_string from sys_log order by create_time DESC limit 10"
            ret = self.ms.ExecQuery(sqlstr)
            return ret
        except Exception as e:
            print("异常：insertSyslog函数抛出，原因：", e,sqlstr)
            self.ExceptionThrow(e)


    def InsertSyslog(self,log):

        try:
            sqlstr = "insert into sys_log value (0,'%s',now())" % log
            self.ms.ExecNonQuery(sqlstr)
        except Exception as e:
            print("异常：insertSyslog函数抛出，原因：", e,sqlstr)
            self.ExceptionThrow(e)


    def QueryAcctInfo(self):
        try:
            sqlstr = "select AcctName, InitMoney, Profit, Holding, Risk from tbAcctInfo "

            data = self.ms.ExecQuery(sqlstr)
            ret = [x for x in data]
            return ret
        except Exception as e:
            print("执行queryAcctInfo报异常：",e,sqlstr)
            self.ExceptionThrow(e)


    def QueryStratageHolding(self):
        try:
            sqlstr = "SELECT * FROM ( SELECT a.ProductCode AS ProductCode, a.PriceTime AS PriceTime, a.Position, b.FutureName, b.Class, b.Market, a.ClosePrice, a.StopPrice, a.nums,b.BigPointValue,b.ContractUnit FROM tbPriceData a, tb_FutureInfo b,		tbCombs c WHERE a.Position <> 0 AND a.ProductCode = b.MiniCode AND datediff(NOW(), a.PriceTime) <= 10 and b.MiniCode = c.ProductCode and c.CombName = 'A25' ) AS l JOIN (	SELECT max(PriceTime) AS PriceTime,ProductCode FROM tbPriceData	GROUP BY ProductCode) AS ls ON l.PriceTime = ls.PriceTime AND l.ProductCode = ls.ProductCode order by l.Class"
            data = self.ms.ExecQuery(sqlstr)
            ret = [x for x in data]
            return ret
        except Exception as e:
            print("执行queryStratageHolding报异常：",e,sqlstr)
            self.ExceptionThrow(e)


    def QueryProfit(self):
        result = 0
        try:
            # 没有记录
            sqlstr = "select count(Profit)  from tbProfit"
            retData = self.ms.ExecQuery(sqlstr)

            if retData[0][0] == 0:
                result = []
            else:
                sqlstr = "select Profit, LongNum, ShortNum, TotalNum, ProfitTime from tbProfit order by ProfitTime ASC"
                retData = self.ms.ExecQuery(sqlstr)
                result = retData
        except Exception as e:
            print("执行queryStratageDetail抛出异常，原因是:", e)
            self.ExceptionThrow(e)

        return result

    def QueryPartProfit(self):
        result = 0
        try:
            # 没有记录
            sqlstr = "select count(Profit)  from tbProfit"
            retData = self.ms.ExecQuery(sqlstr)

            if retData[0][0] == 0:
                result = []
            else:
                sqlstr = "select Profit, ProfitTime from tbProfit where ProfitTime>'2022-01-01 00:00:00' order by ProfitTime ASC"
                retData = self.ms.ExecQuery(sqlstr)
                result = retData
        except Exception as e:
            print("执行queryStratageDetail抛出异常，原因是:", e)
            self.ExceptionThrow(e)

        return result



    def QueryLatestProfit(self):
        result = 0
        try:
            # 没有记录
            sqlstr = "select count(Profit)  from tbProfit"
            retData = self.ms.ExecQuery(sqlstr)

            if retData[0][0] == 0:
                result = []
            else:
                sqlstr = "select Profit, ProfitTime from tbProfit  order by ProfitTime DESC limit 1"
                retData = self.ms.ExecQuery(sqlstr)
                result = retData[0]
        except Exception as e:
            print("执行queryStratageDetail抛出异常，原因是:", e)
            self.ExceptionThrow(e)

        return result

