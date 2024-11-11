from utils import MySQLBase
import time
bLoadLocalDB = False #更新本地数据库True 否则远程

#数据库连接
# if bLoadLocalDB:
ms = MySQLBase.MSSQL()

#以下业务接口，为了让前端更简洁，把细节放在函数里，对一个表的“增、删、改、查”
#acct 表、stratage表、acct_money表
#函数名规范：动作+表名，去掉下划线直接连接

def insertAcctMoney(newData, delOld=False):
    try:
        if delOld:
            deleteAcctMoney(False)

        # 生成sql语句
        str1 = ""
        sqlstr = ""
        for itor in newData:
            sqllist = []
            sqllist.append(itor[0])
            sqllist.append(itor[1])
            sqllist.append(itor[2])
            sqllist.append(itor[3])

            sqltuple = tuple(sqllist)
            str1 += ",(0,%d,'%s',%f,%f)" % sqltuple

        sqlstr = "insert into acct_money  VALUES " + str1[1:]
        ms.ExecNonQuery(sqlstr)
    except Exception as e:
        print(sqlstr)
        print("执行insertAcctMoney抛出异常，原因是:", e)

def deleteAcctMoney(bDelAll=True,fieldname="",rawData=[]):

    try:
        if bDelAll:
            sqlstr = "delete  from acct_money"
            #print(sqlstr)
            ms.ExecNonQuery(sqlstr)
        else:
            #删除指定字段
            str1 = ""
            for itor in rawData:
                sqllist = []
                sqllist.append(itor[0])

                sqltuple = tuple(sqllist)
                str1 += ", '%s'" % sqltuple
            sqlstr = "delete from acct_money where " + fieldname + " in (" + str1[1:] + ")"
            #print(sqlstr)
            ms.ExecNonQuery(sqlstr)

        print("删除历史数据成功")
    except Exception as e:
        print("执行deleteAcctMoney抛出异常，原因是:", e)

def queryAcctMoneyMaxmin(days=7):
    result = [0,0]
    try:
        sqlstr = "SELECT max(sum_winner),min(sum_winner) FROM `stratage_sum` where datediff(now(),stratage_time) < "+str(days)+" order by stratage_time ASC;"
        retData = ms.ExecQuery(sqlstr)
        result = [retData[0][0],retData[0][1]]
    except Exception as e:
        print("执行queryAcctMoneyMaxmin抛出异常，原因是:",e)
        print(sqlstr)

    return result

#获得上一个
def queryAcctMoneyLast():
    result = 0
    try:
        sqlstr = "select sum_winner  from stratage_sum order by stratage_time DESC LIMIT  2"
        retData = ms.ExecQuery(sqlstr)
        result = retData[1][0]
    except Exception as e:
        print("执行queryAcctMoneyLatest抛出异常，原因是:",e)
        print(sqlstr)

    return result

def queryAcctMoneyLatest():
    result = 0
    try:
        sqlstr = "SELECT a.sum_winner FROM `stratage_sum` a, (select max(stratage_time) as max_time from stratage_sum ) b where a.stratage_time = b.max_time"
        retData = ms.ExecQuery(sqlstr)
        result = retData[0][0]
    except Exception as e:
        print("执行queryAcctMoneyLatest抛出异常，原因是:",e)
        print(sqlstr)

    return result

def queryAcctInfo(accName=""):

    result = []
    try:
        if accName == "":
            sqlstr = "select acct_id,memo,apikey,secretkey,apipass,status,email,sendflag from acct_info where state = 1"
            data = ms.ExecQuery(sqlstr)
            result = [itor for itor in data]
        else:
            sqlstr = "select acct_id,memo,apikey,secretkey,apipass,status,email,sendflag from acct_info where state = 1 and acct_name = '" + accName + "'"
            data = ms.ExecQuery(sqlstr)
            #print(data)
            result = data[0]

    except Exception as e:
        print("数据库查找账户acct_info表，"+accName+"出现错误,语句为："+sqlstr)
        print(e)

    return result

def queryAcctStratage(acctID,stgID=1):

    result = []
    try:

        sqlstr = "select init_money,level,up_money,up_level,down_money,down_level from acct_stratage where stratage_id = " + str(stgID) + " and acct_id = " + str(acctID)
        data = ms.ExecQuery(sqlstr)
        #print(data)
        result = data[0]


    except Exception as e:
        print("数据库查找账户queryAcctStratage表，stratage_id=",stgID,"出现错误,语句为："+sqlstr)
        print(e)

    return result

def queryAllAcctStratage(stgID = 1):

    result = []
    try:

        sqlstr = "SELECT b.acct_id, b.acct_name, b.memo, a.init_money, a.`level`, a.up_money, a.up_level, a.down_money, a.down_level FROM acct_stratage a,acct_info b where a.acct_id = b.acct_id and b.state = 1 and a.stratage_id = " + str(stgID)
        data = ms.ExecQuery(sqlstr)
        #print(data)
        result = [itor for itor in data]


    except Exception as e:
        print("数据库查找账户queryAcctStratage表，stratage_id="+stgID+"出现错误,语句为："+sqlstr)
        print(e)

    return result



#查询策略数据
def queryStratage(stgID = 1):
    result = ""
    try:

        sqlstr = "select stratage_id,stratage_name,frame, days,freq,money,product_num from stratage where stratage_id = " + str(stgID)
        data = ms.ExecQuery(sqlstr)
        result = data[0]

    except Exception as e:
        print("数据库查找stratage表，出现错误,语句为：" + sqlstr)
        print("异常：queryStratage函数抛出，原因：", e)

    return result

def queryStratageProduct(stgID=1):
    result = []
    try:

        sqlstr = "select b.product_id,b.product_code from stratage a , product b, stratage_product c where a.stratage_id = c.stratage_id and c.product_id = b.product_id and a.stratage_id = "+ str(stgID)
        data = ms.ExecQuery(sqlstr)

        result = [itor for itor in data]

    except Exception as e:
        print("数据库查找stratage表，出现错误,语句为：" + sqlstr + "异常代码：",e)
        #print(e)


    return result

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
        print("执行insertStratageDetail报异常：",e)


def insertStratageSum(newData):
    try:
        # 生成sql语句
        str1 = ""
        sqlstr = ""
        #print(newData)
        for itor in newData:
            sqllist = []
            sqllist.append(itor[0])
            sqllist.append(itor[1])
            sqllist.append(itor[2])
            sqllist.append(itor[3])
            sqllist.append(itor[4])
            sqllist.append(itor[5])
            sqllist.append(itor[6])



            sqltuple = tuple(sqllist)
            str1 += ",(0,%d,%f,%f,%f,'%s',%d,%d)" % sqltuple

        sqlstr = "insert into stratage_sum (id, stratage_id,total_winner,sum_winner,index_data,stratage_time,longnum,shortnum) VALUES " + str1[1:]
        ms.ExecNonQuery(sqlstr)
    except Exception as e:
        print("异常：insertStratageSum函数抛出，原因：", e)
        print(sqlstr)

def deleteStratageDetail():
    try:
        sqlstr = "delete  from stratage_detail"
        ms.ExecNonQuery(sqlstr)
        print("删除stratage_detail数据成功")
    except Exception as e:
        print("异常：deleteStratageDetail函数抛出，原因：", e)

def deleteStratageSum():
    try:
        sqlstr = "delete  from stratage_sum"
        ms.ExecNonQuery(sqlstr)
        print("删除stratage_sum数据成功")
    except Exception as e:
        print("异常：deleteStratageSum函数抛出，原因：", e)

def queryStratageDetail(stgID = 1, maxTry=20):
    #选出策略信息最新的数据

    result = []
    waitTime = 0
    try:
        while(True):
            sql = "select count(*) from stratage_product where stratage_id = " + str(stgID)
            result = ms.ExecQuery(sql)
            count = result[0][0]
            sql = "select a.product_code,a.close,a.num,a.stg,a.rate,a.winner,a.stratage_time,b.ctVal from stratage_detail a, product b where a.stratage_id = " + str(stgID) + " and a.stratage_time = (select max(stratage_time) from stratage_detail ) and a.product_code = b.product_code "

            result = ms.ExecQuery(sql)

            if len(result)!=count:
                print("策略数据",len(result),"与品种数",count,"不匹配，还在更新数据，等待5秒重试，累计等待："+str(waitTime*5))

                time.sleep(5)
            else:
                #print(result)
                result = [itor for itor in result]
                break

            waitTime += 1

            if waitTime > maxTry:
                break
    except Exception as e:
        print("异常：queryStratageDetail函数抛出，原因：",e)

    return result

def queryStratageSum(stgID=1):

    result = []
    waitTime = 0
    try:

        sql = "select index_data, sum_winner,stratage_time ,longnum,shortnum from stratage_sum where stratage_id = " + str(stgID) + " order by stratage_time ASC "
        result = ms.ExecQuery(sql)


    except Exception as e:
        print("异常：queryStratageSum函数抛出，原因：", e)

    return result

def queryStratageSumLatestValue():

    result = 0
    try:

        sql = "select sum_winner from stratage_sum a, (select max(stratage_time) as max_time from stratage_sum ) b where stratage_time = b.max_time "
        ret = ms.ExecQuery(sql)
        result = ret[0][0]

    except Exception as e:
        print("异常：queryStratageSumLatestValue函数抛出，原因：", e)

    return result

def queryStratageSumMaxMin():

    result = [0,0]
    try:

        sql = "select max(sum_winner),min(sum_winner) from stratage_sum where DATE_SUB(CURDATE(), INTERVAL 6 DAY) <= stratage_time "
        ret = ms.ExecQuery(sql)
        result = [ret[0][0],ret[0][1]]

    except Exception as e:
        print("异常：queryStratageSumMaxMin函数抛出，原因：", e)

    return result

def queryStratageSumLongShortNum():

    result = [0,0]
    try:

        sql = "select longnum, shortnum from stratage_sum a, (select max(stratage_time) as max_time from stratage_sum ) b where stratage_time = b.max_time  "
        ret = ms.ExecQuery(sql)
        result = [ret[0][0],ret[0][1]]

    except Exception as e:
        print("异常：queryStratageSumLongShortNum函数抛出，原因：", e)

    return result

def deletePrice():

    try:
        sqlstr = "delete  from price_data"
        ms.ExecNonQuery(sqlstr)
        print("删除price_data数据成功")
    except Exception as e:
        print("异常：deletePrice函数抛出，原因：", e)


def queryPriceMaxDate():


    try:
        sqlstr = "select max(price_time) from price_data"
        retData = ms.ExecQuery(sqlstr)


    except Exception as e:
        print("异常：queryPriceMaxDate函数抛出，原因：", e)

    return retData

def deleteStratageMaDetail(productID):

    try:
        sqlstr = "delete  from stratage_ma_detail where product_id = " + str(productID)
        ms.ExecNonQuery(sqlstr)
        print("删除stratage_ma_detail数据成功")
    except Exception as e:
        print("异常：stratage_ma_detail函数抛出，原因：", e)


def queryPriceData(productID):
    result =""
    try:
        msLocal = MySQLBase.MSSQL(host, user, pwd, db)
        sqlstr = "select close,price_time from price_data where product_id =" + str(productID) + " order by price_time DESC  limit 200 "

        retData = msLocal.ExecQuery(sqlstr)

        result = [x for x in retData]
        ret = result[::-1]

        return ret
    except Exception as e:
        print(sqlstr)
        print("异常：queryPriceData函数抛出，原因：", e)

    return  result

def insertPrice(priceData):
    try:

        # 生成sql语句
        str1 = ""
        sqlstr = ""
        for itor in priceData:
            sqllist = []
            sqllist.append(itor[0])
            sqllist.append(itor[1])
            sqllist.append(itor[2])
            sqllist.append(itor[3])
            sqllist.append(itor[4])
            sqllist.append(itor[5])
            sqllist.append(itor[6])

            sqltuple = tuple(sqllist)
            str1 += ",(0,'%d',%f,%f,%f,%f,'%s','%s')" % sqltuple

        sqlstr = "insert into price_data  VALUES " + str1[1:]
        ms.ExecNonQuery(sqlstr)
    except Exception as e:
        print(sqlstr)
        print("执行insertPrice抛出异常，原因是:", e)

def queryProductCVal(symbol):
    try:
        sqlstr = "select ctVal from product where product_code = ''"+symbol+"'"
        retData = ms.ExecQuery(sqlstr)
        result = retData[0][0]
        return result
    except Exception as e:
        print("异常：queryProductCVal 函数抛出，原因：", e)



def queryStratageMADetailMaxDate():

    try:
        sqlstr = "select max(stratage_time) from stratage_ma_detail"
        retData = ms.ExecQuery(sqlstr)


    except Exception as e:
        print("异常：queryStratageMADetailMaxDate 函数抛出，原因：", e)

    return retData

def insertStatageMADetail(emaData):
    try:
        msLocal = MySQLBase.MSSQL(host, user, pwd, db)
        # 生成sql语句
        str1 = ""
        sqlstr = ""
        for itor in emaData:
            sqllist = []
            sqllist.append(itor[0])
            sqllist.append(itor[1])
            sqllist.append(itor[2])
            sqllist.append(itor[3])
            sqllist.append(itor[4])
            sqllist.append(itor[5])
            sqllist.append(itor[6])


            sqltuple = tuple(sqllist)
            str1 += ",(%d,%d,'%s',%f,%f,%f,'%s')" % sqltuple

        sqlstr = "insert into stratage_ma_detail (stratage_id, product_id,time_frame,MA1,MA2,MA3,stratage_time) VALUES " + str1[1:]
        print(sqlstr)
        msLocal.ExecNonQuery(sqlstr)
    except Exception as e:
        print(sqlstr)
        print("执行insertStatageMADetail抛出异常，原因是:", e)

def queryStratageStatus():

    latestSum = queryStratageSumLatestValue()
    ret = queryStratageSumMaxMin()
    maxSum = ret[0]
    minSum = ret[1]

    level1 = 10 - math.floor((latestSum - minSum)/((maxSum-minSum)/10))

    ret = queryStratageSumLongShortNum()
    longNum = ret[0]
    shortNum = ret[1]
    diff = abs(longNum-shortNum)
    level2 = 0
    if diff >=0 and diff<=4:
        level2 = 5
    elif diff>4 and diff<=8:
        level2 = 4
    elif diff > 8 and diff<=12:
        level2 = 3
    elif diff > 12 and diff<=16:
        level2 = 2
    else:
        level2 = 1

    num = (level1-1)*5+level2
    return num

def updateAcctStratageLevel(acctID, acctData):

    try:
        #调节账户的杠杆设置
        level = acctData[0]
        upMoney = acctData[1]
        uplevel = acctData[2]
        downMoney = acctData[3]
        downlevel = acctData[4]
        initMoney = acctData[5]

        sqlstr = "update acct_stratage set level = %f, up_money = %f, up_level = %f, down_money = %f, down_level = %f, init_money = %f where acct_id = %d " % (level,upMoney,uplevel,downMoney,downlevel,initMoney,acctID)
        print(sqlstr)
        ms.ExecNonQuery(sqlstr)

    except Exception as e:
        print("函数updateAcctStratageLevel抛出异常",e)


def insertPriceData30M(priceData):
    try:

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
            str1 += ",(0,'%s',%f,0,0,0,'%s','%s')" % sqltuple

        sqlstr = "insert into okex_price_30m  VALUES " + str1[1:]
        ms.ExecNonQuery(sqlstr)

    except Exception as e:
        print("函数insertPriceData30M抛出异常",e,sqlstr)


def insertIndex30M(priceData):
    try:

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
            str1 += ",(0,'%s',%f,'%s','%s')" % sqltuple

        sqlstr = "insert into okex_index_30m  VALUES " + str1[1:]
        ms.ExecNonQuery(sqlstr)

    except Exception as e:
        print("函数insertIndex30M抛出异常",e,sqlstr)

def clearPriceData30M():
    try:
        sqlstr = "delete  from okex_price_30m"
        ms.ExecNonQuery(sqlstr)
        print("删除okex_price_30m数据成功")
    except Exception as e:
        print("异常：clearPriceData30M函数抛出，原因：", e)

def clearIndex30M():
    try:
        sqlstr = "delete  from okex_index_30m"
        ms.ExecNonQuery(sqlstr)
        print("删除okex_index_30m数据成功")
    except Exception as e:
        print("异常：clearIndex30M函数抛出，原因：", e)

def queryPriceData30M(beginDate=""):
    result = 0
    try:
        if beginDate == "":
            sqlstr = "select close,price_time  from okex_price_30m order by price_time DESC"

        else:
            sqlstr = "select close,price_time  from okex_price_30m where price_time > " + beginDate + "order by price_time DESC "

        retData = ms.ExecQuery(sqlstr)
        result = retData
    except Exception as e:
        print("执行queryPriceData30M抛出异常，原因是:",e)
        print(sqlstr)

    return result


def queryIndex30M(symbols, beginDate=""):
    result = 0
    try:
        if beginDate == "":
            sqlstr = "select index_data,index_time  from okex_index_30m where product_code = '" + symbols + "' order by index_time ASC"

        else:
            sqlstr = "select index_data,index_time  from okex_index_30m where product_code = '" + symbols + "' and index_time > " + beginDate + "order by index_time ASC "

        retData = ms.ExecQuery(sqlstr)
        result = retData
    except Exception as e:
        print("执行queryIndex30M抛出异常，原因是:",e)
        print(sqlstr)

    return result