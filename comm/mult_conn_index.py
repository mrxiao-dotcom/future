from utils import MySQLConn
import time

#数据库连接
# if bLoadLocalDB:
ms_idx = MySQLConn.MSSQL_IDX()
ms_src = MySQLConn.MSSQL_SRC()

def queryInxlatest():
    try:
        sqlstr = "select max(xni_date) from t_xuan_niu_index "
        ret = ms_idx.ExecQuery(sqlstr)
        return ret[0]
    except Exception as e:
        print("数据库查找queryIDXlatest表，出现错误,语句为：" + sqlstr + "异常代码：",e)
        #print(e)

def deleteInxData():
    try:
        sqlstr = "delete from t_xuan_niu_index "
        ms_idx.ExecNonQuery(sqlstr)

    except Exception as e:
        print("deleteInxData，出现错误,语句为：" + sqlstr + "异常代码：", e)
        # print(e)

def querySrcData(lastDate):
    try:
        sqlstr = " select 0,'GD宣牛指数','money=1000000|day=20|productCount=20|offset=1|lastSecond=15',Profit,Profit/25000000,DATE_FORMAT(ProfitTime,'20%y%m%d'), 180000, 1590484795,1590490959 from tbProfit where time(ProfitTime)='14:30:00' and DATE_FORMAT(ProfitTime,'20%y%m%d') > " + str(lastDate)
        ret = ms_src.ExecQuery(sqlstr)
        return ret
    except Exception as e:
        print("数据库查找queryIDXlatest表，出现错误,语句为：" + sqlstr + "异常代码：",e)
        #print(e)

def insertIdxData(dataSet):

    try:
        # 生成sql语句
        str1 = ""
        sqlstr = ""
        for itor in dataSet:
            sqllist = []
            sqllist.append(itor[0])
            sqllist.append(itor[1])
            sqllist.append(itor[2])
            sqllist.append(itor[3])
            sqllist.append(itor[4])
            sqllist.append(int(itor[5]))
            sqllist.append(itor[6])
            sqllist.append(itor[7])
            sqllist.append(itor[8])

            sqltuple = tuple(sqllist)
            str1 += ",(%d,'%s','%s',%.6f,%.6f,%d,%d,%d,%d)" % sqltuple

        sqlstr = "insert into t_xuan_niu_index  VALUES " + str1[1:]
        ms_idx.ExecNonQuery(sqlstr)
    except Exception as e:
        # print(sqlstr)
        print("执行insertIdxData报异常：", e, sqlstr)
