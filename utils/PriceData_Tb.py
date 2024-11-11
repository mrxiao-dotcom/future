#主要用于下午收盘后更新行情信息，主要需要修改日期，将会删除日期开始的行情，然后从后台获取指定区间的最新行情，一定注意最后日期要多一天，不然夜盘漏掉
import tbpy
import datetime
import MySQLBase
import logging
import time
from comm import dbConnecterTB

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logging.info('Admin logged in')

bLoadLocalDB = True #更新本地数据库True 否则远程
bUpdateFutureInfo = False #更新期货信息表，可以不用再改
bUpdateFutureData = True #更新行情
bUpdateSingleData = False #补充单个品种行情



#数据库连接
if bLoadLocalDB:
    ms = MySQLBase.MSSQL(host="10.17.31.47", user="root", pwd="fsR6Hf$", db="xiaoDB")
else:
    ms = MySQLBase.MSSQL(host="203.195.135.65", user="chinastock", pwd="Chinaxdq^123", db="stock")

ret = tbpy.init()
if not ret:
    print("初始化错误，可能没有打开tbquant客户端")
    tbpy.exit()

#account_id = "tbsim_2017_001218"
account_id = "xuanniuassert"
account = tbpy.get_account(account_id)

symList = ['sc888.INE','ag888.SHFE','rb888.SHFE','i9888.DCE','jm888.DCE','hc888.SHFE','SM888.CZCE','ZC888.CZCE','fu888.SHFE','MA888.CZCE','pp888.DCE','bu888.SHFE','TA888.CZCE','l9888.DCE','pg888.DCE','eg888.DCE','eb888.DCE','v9888.DCE','UR888.CZCE','SA888.CZCE','p9888.DCE','m9888.DCE','RM888.CZCE','c9888.DCE','y9888.DCE','a9888.DCE','AP888.CZCE','OI888.CZCE','cs888.DCE','b9888.DCE','CJ888.CZCE','CF888.CZCE','SR888.CZCE','ru888.SHFE','jd888.DCE','FG888.CZCE','sp888.SHFE','ni888.SHFE','zn888.SHFE','al888.SHFE','cu888.SHFE','sn888.SHFE','pb888.SHFE']

#symList = ['sc888.INE','IF888.CFFEX','IC888.CFFEX','IH888.CFFEX','ag888.SHFE','rb888.SHFE','i9888.DCE','jm888.DCE','hc888.SHFE','SM888.CZCE','ZC888.CZCE','fu888.SHFE','MA888.CZCE','pp888.DCE','bu888.SHFE','TA888.CZCE','l9888.DCE','pg888.DCE','eg888.DCE','eb888.DCE','v9888.DCE','UR888.CZCE','SA888.CZCE','p9888.DCE','m9888.DCE','RM888.CZCE','c9888.DCE','y9888.DCE','a9888.DCE','AP888.CZCE','OI888.CZCE','cs888.DCE','b9888.DCE','CJ888.CZCE','CF888.CZCE','SR888.CZCE','ru888.SHFE','jd888.DCE','FG888.CZCE','sp888.SHFE','ni888.SHFE','zn888.SHFE','al888.SHFE','cu888.SHFE','sn888.SHFE','pb888.SHFE']
#symList = ['IF888.CFFEX','IC888.CFFEX','ag888.SHFE','i9888.DCE','hc888.SHFE','ZC888.CZCE','MA888.CZCE','bu888.SHFE','l9888.DCE','eg888.DCE','v9888.DCE','UR888.CZCE','p9888.DCE','RM888.CZCE','y9888.DEC','AP888.CZCE','cs888.DCE','CJ888.CZCE','SR888.CZCE','jd888.DCE','sp888.SHFE','zn888.SHFE','al888.SHFE','cu888.SHFE','pb888.SHFE']


freq = '30m'
beginstr = "2022-04-01"
endstr = "2022-04-10"
begintime = datetime.datetime.strptime(beginstr, '%Y-%m-%d')
endtime = datetime.datetime.strptime(endstr, '%Y-%m-%d')
#endtime = datetime.datetime.now()
#begintime = datetime.datetime.now().strftime('%Y%m%d')
#endtime = begintime

def UpdateFutureData():

    symList = dbConnecterTB.queryStratageProduct(2)

    for n in range(0, len(symList)):
        symbols = symList[n]

        ifBars = tbpy.get_history(symbols, freq, begintime, endtime, flag=tbpy.QuoteFlag.RolloverBackWard , fields=None, timeout='30s')
        lenClose = len(ifBars)
        data = ["","",0,0]
        index = ["",0,""]
        dataList = [data for x in range(lenClose)]
        indexList = [index for x in range(lenClose)]
        print("查询行情：" + symbols + "还有" + str(len(symList)-n) + "个品种，每个品种预计时间一分钟，请耐心等待...")

        for i in range(0,lenClose):
            data = [symbols,float(ifBars['close'][i]),ifBars['time'][i],float(ifBars['rollover'][i])]
            dataList[n] = data

            index = [symbols, float(ifBars['close'][i])*1000/float(ifBars['close'][0]),ifBars['time'][i]]
            indexList[n] = index

        print(dataList)
        print(indexList)
        dbConnecterTB.insertPriceData30M(dataList)
        dbConnecterTB.insertIndex30M(indexList)
        time.sleep(60)


    tbpy.exit()

UpdateFutureData()