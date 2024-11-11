from utils import MySQLBase
import time

#数据库连接
# if bLoadLocalDB:
ms = MySQLBase.MSSQL(2)

def updateProduct(data):

    try:
        for i in range(0,len(data)):
            symbol = data[i][0]
            sqlstr = "update product set contract_unit = %d, big_point_value = %d where product_code = '%s'" % (data[i][1], data[i][2],data[i][0])
            ms.ExecNonQuery(sqlstr)

    except Exception as e:
        print("数据库查找updateProduct表，出现错误,语句为：" + sqlstr + "异常代码：",e)
        #print(e)

def queryProduct():
    try:
        sqlstr = "select DISTINCT productCode from tbPriceData"
        data = ms.ExecQuery(sqlstr)
        ret = [x[0] for x in data]
        return ret
    except Exception as e:
        print("数据库查找queryProduct表，出现错误,语句为：" + sqlstr + "异常代码：",e)


def queryStratageProduct(stgID=1):
    result = []
    try:

        sqlstr = "select b.product_code,b.contract_unit,b.big_point_value from  stratage_product a, product b  where   a.product_id = b.product_id and  a.stratage_id = "+ str(stgID)
        data = ms.ExecQuery(sqlstr)

        result = [itor for itor in data]

    except Exception as e:
        print("数据库查找queryStratageProduct表，出现错误,语句为：" + sqlstr + "异常代码：",e)
        #print(e)


    return result

def insertPriceData30M(priceData):
    try:
        if len(priceData)==0:
            print("insertPriceData30M无数据...")
            return
        # 生成sql语句
        str1 = ""
        sqlstr = ""
        for itor in priceData:
            sqllist = []
            sqllist.append(itor[0])
            sqllist.append(itor[1])
            sqllist.append(itor[2])
            sqllist.append(itor[3])

            sqltuple = tuple(sqllist)
            str1 += ",(0,'%s',%f,0,0,0,'%s',%f)" % sqltuple

        sqlstr = "insert into tb_price_30m  VALUES " + str1[1:]
        ms.ExecNonQuery(sqlstr)

    except Exception as e:
        print("函数insertPriceData30M抛出异常",e,sqlstr)


def insertIndex30M(priceData):
    try:

        if len(priceData)==0:
            print("insertIndex30M无数据...")
            return

        # 生成sql语句
        str1 = ""
        sqlstr = ""
        for itor in priceData:
            sqllist = []
            sqllist.append(itor[0])
            sqllist.append(itor[1])
            sqllist.append(itor[2])


            sqltuple = tuple(sqllist)
            str1 += ",(0,'%s',%f,'%s')" % sqltuple

        sqlstr = "insert into tb_index_30m  VALUES " + str1[1:]
        ms.ExecNonQuery(sqlstr)

    except Exception as e:
        print("函数insertIndex30M抛出异常",e,sqlstr)

def clearStratageDetail():
    try:
        sqlstr = "delete  from stratage_detail"
        ms.ExecNonQuery(sqlstr)
        print("删除stratage_detail数据成功")
    except Exception as e:
        print("异常：clearStratageDetail函数抛出，原因：", e)


def clearPriceData30M():
    try:
        sqlstr = "delete  from tb_price_30m"
        ms.ExecNonQuery(sqlstr)
        print("删除okex_price_30m数据成功")
    except Exception as e:
        print("异常：clearPriceData30M函数抛出，原因：", e)

def clearIndex30M():
    try:
        sqlstr = "delete  from tb_index_30m"
        ms.ExecNonQuery(sqlstr)
        print("删除okex_index_30m数据成功")
    except Exception as e:
        print("异常：clearIndex30M函数抛出，原因：", e)

def queryPriceData(symbol):

    try:
        sqlstr = "select PriceTime, ClosePrice  from tbPriceData where ProductCode ='"+symbol+"' order by PriceTime asc"

        retData = ms.ExecQuery(sqlstr)
        return retData

    except Exception as e:
        print("执行queryPriceData抛出异常，原因是:",e,sqlstr)



def queryPriceData30M(symbol,beginDate=""):
    result = 0
    try:
        if beginDate == "":
            sqlstr = "select close,price_time,rollover  from tb_price_30m where product_code ='"+symbol+"' order by price_time DESC"

        else:
            sqlstr = "select close,price_time,rollover  from tb_price_30m where product_code ='"+symbol+"' and price_time > " + beginDate + "order by price_time DESC "

        retData = ms.ExecQuery(sqlstr)
        result = retData
        result = result[::-1]
    except Exception as e:
        print("执行queryPriceData30M抛出异常，原因是:",e)
        print(sqlstr)

    return result


def queryIndex30M(symbols, beginDate=""):
    result = 0
    try:
        if beginDate == "":
            sqlstr = "select index_data,index_time  from tb_index_30m where product_code = '" + symbols + "' order by index_time ASC"

        else:
            sqlstr = "select index_data,index_time  from tb_index_30m where product_code = '" + symbols + "' and index_time > " + beginDate + "order by index_time ASC "

        retData = ms.ExecQuery(sqlstr)
        result = retData
    except Exception as e:
        print("执行queryIndex30M抛出异常，原因是:",e)
        print(sqlstr)

    return result

def queryMaxTime30M(symbol):

    result = 0
    try:
        sqlstr = "select count(price_time)  from tb_price_30m where product_code = '" + symbol + "'"
        retData = ms.ExecQuery(sqlstr)

        if retData[0][0]==0:
            result = ""
        else:
            sqlstr = "select max(price_time)  from tb_price_30m where product_code = '" + symbol + "'"
            retData = ms.ExecQuery(sqlstr)
            result = retData[0][0]
    except Exception as e:
        print("执行queryMaxTime30M抛出异常，原因是:",e)
        print(sqlstr)

    return result

def queryIndexFirst30M(symbol):

    result = 0
    try:
        #没有记录
        sqlstr = "select count(price_time)  from tb_price_30m where product_code = '" + symbol + "'"
        retData = ms.ExecQuery(sqlstr)

        if retData[0][0]==0:
            result = 0
        else:
            sqlstr = "select a.close from tb_price_30m a, (select min(price_time) as min_time from tb_price_30m ) b where a.product_code = '" + symbol + "' and a.price_time = b.min_time"
            retData = ms.ExecQuery(sqlstr)
            result = retData[0][0]
    except Exception as e:
        print("执行queryMaxTime30M抛出异常，原因是:",e)
        print(sqlstr)

    return result

def queryTime(symbol='ag'):
    try:
        sqlstr = "select PriceTime from tbPriceData  where ProductCode = '" + symbol + "' order by PriceTime ASC "
        retData = ms.ExecQuery(sqlstr)
        ret = [x[0] for x in retData]
        return ret
    except Exception as e:
        print("执行queryTime抛出异常，原因是:",e,sqlstr)


def queryTimeAg(symbol='ag888.SHFE'):

    result = 0
    try:
        #没有记录

        sqlstr = "select count(price_time)  from tb_price_30m where product_code = '" + symbol + "'"
        retData = ms.ExecQuery(sqlstr)

        if retData[0][0]==0:
            result = []
        else:
            sqlstr = "select index_time from tb_index_30m  where product_code = '" + symbol + "' order by index_time DESC limit 2925 "
            retData = ms.ExecQuery(sqlstr)
            result = [x[0] for x in retData]
            result = result[::-1]
    except Exception as e:
        print("执行queryMaxTime30M抛出异常，原因是:",e)
        print(sqlstr)

    return result

def querySyslog():
    try:
        sqlstr = "select create_time,log_string from sys_log order by create_time DESC limit 10"
        ret = ms.ExecQuery(sqlstr)
        return ret
    except Exception as e:
        print("异常：insertSyslog函数抛出，原因：", e,sqlstr)

def insertSyslog(log):

    try:
        sqlstr = "insert into sys_log value (0,'%s',now())" % log
        ms.ExecNonQuery(sqlstr)
    except Exception as e:
        print("异常：insertSyslog函数抛出，原因：", e,sqlstr)

def queryAcctInfo():
    try:
        sqlstr = "select AcctName, InitMoney, Profit, Holding, Risk from tbAcctInfo "

        data = ms.ExecQuery(sqlstr)
        ret = [x for x in data]
        return ret
    except Exception as e:
        print("执行queryAcctInfo报异常：",e,sqlstr)

def queryStratageHolding():
    try:
        sqlstr = "SELECT * FROM ( SELECT a.ProductCode AS ProductCode, a.PriceTime AS PriceTime, a.Position, b.FutureName, b.Class, b.Market, a.ClosePrice, a.StopPrice, a.nums,b.BigPointValue,b.ContractUnit FROM tbPriceData a, tb_FutureInfo b,		tbCombs c WHERE a.Position <> 0 AND a.ProductCode = b.MiniCode AND datediff(NOW(), a.PriceTime) <= 10 and b.MiniCode = c.ProductCode and c.CombName = 'A25' ) AS l JOIN (	SELECT max(PriceTime) AS PriceTime,ProductCode FROM tbPriceData	GROUP BY ProductCode) AS ls ON l.PriceTime = ls.PriceTime AND l.ProductCode = ls.ProductCode order by l.Class"
        data = ms.ExecQuery(sqlstr)
        ret = [x for x in data]
        return ret
    except Exception as e:
        print("执行queryStratageHolding报异常：",e,sqlstr)

def insertStratageDetail(newData):
    try:
        # 生成sql语句
        str1 = ""
        sqlstr = ""
        for itor in newData:
            sqllist = []
            sqllist.append(itor[0])
            sqllist.append(itor[1])
            sqllist.append(itor[2])
            sqllist.append(itor[3])
            sqllist.append(itor[4])
            sqllist.append(itor[5])
            sqllist.append(itor[6])
            sqllist.append(itor[7])
            sqllist.append(itor[8])
            sqllist.append(itor[9])
            sqllist.append(itor[10])


            sqltuple = tuple(sqllist)
            str1 += ",(%d,'%s',%f,'%s',%d,%d,%f,%f,%f,%f,%f)" % sqltuple

        sqlstr = "insert into stratage_detail  VALUES " + str1[1:]
        ms.ExecNonQuery(sqlstr)
    except Exception as e:
        #print(sqlstr)
        print("执行insertStratageDetail报异常：",e,sqlstr)

def queryStratageDetail(symbol):
    result = 0
    try:
        #没有记录
        sqlstr = "select count(product_code)  from stratage_detail where product_code = '" + symbol + "'"
        retData = ms.ExecQuery(sqlstr)

        if retData[0][0]==0:
            result = []
        else:
            sqlstr = "select close,stratage_time,num,stg,rate,winner,top,mid,but from stratage_detail  where product_code = '" + symbol + "' order by stratage_time DESC limit 2925 "
            retData = ms.ExecQuery(sqlstr)
            result = retData[::-1]
    except Exception as e:
        print("执行queryStratageDetail抛出异常，原因是:",e)
        print(sqlstr)

    return result

def queryProfit():
    result = 0
    try:
        #没有记录
        sqlstr = "select count(Profit)  from tbProfit1"
        retData = ms.ExecQuery(sqlstr)

        if retData[0][0]==0:
            result = []
        else:
            sqlstr = "select Profit, LongNum, ShortNum, TotalNum, ProfitTime from tbProfit1 order by ProfitTime ASC"
            retData = ms.ExecQuery(sqlstr)
            result = retData
    except Exception as e:
        print("执行queryStratageDetail抛出异常，原因是:",e)
        print(sqlstr)

    return result