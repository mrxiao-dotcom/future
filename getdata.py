#主要用于下午收盘后更新行情信息，主要需要修改日期，将会删除日期开始的行情，然后从后台获取指定区间的最新行情，一定注意最后日期要多一天，不然夜盘漏掉
import tbpy
import datetime
import MySQLBase
import logging
import time
from comm import dbConnecterTB1
from comm import commFunctions
import xlwings as xw

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logging.info('Admin logged in')


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




def UpdateFutureData():

    symList = dbConnecterTB.queryStratageProduct(2)
    freq = '30m'

    for n in range(0, len(symList)):
        symbols = symList[n][0]
        maxTime = dbConnecterTB.queryMaxTime30M(symbols)
        if maxTime == "":
            beginstr = "2021-01-01"
            begintime = datetime.datetime.strptime(beginstr, '%Y-%m-%d')

        else:
            #beginstr = maxTime
            #begintime = datetime.datetime.strptime(beginstr, '%Y-%m-%d')
            begintime = maxTime

        currentTime = datetime.datetime.now().strftime('%Y-%m-%d')
        endtime = datetime.datetime.strptime(currentTime, '%Y-%m-%d')

        begintime = '2021-11-01'
        endtime = '2021-12-31'

        ifBars = tbpy.get_history(symbols, freq, begintime, endtime, flag=tbpy.QuoteFlag.RolloverBackWard , fields=None, timeout='30s')

        lenClose = len(ifBars['close'])
        print(lenClose,"本次获得k线数量",begintime,endtime)

        data = ["","",0,0]
        index = ["",0,""]
        dataList = [data for x in range(lenClose)]
        indexList = [index for x in range(lenClose)]
        print("查询行情：" + symbols + "还有" + str(len(symList)-n) + "个品种，每个品种预计时间一分钟，请耐心等待...")

        for i in range(0,lenClose):
            data = [symbols,float(ifBars['close'][i]),ifBars['time'][i],float(ifBars['rollover'][i])]
            dataList[i] = data


            indexFirst = dbConnecterTB.queryIndexFirst30M(symbols)
            if indexFirst ==0:
                First = ifBars['close'][0]
            else:
                First = indexFirst
            index = [symbols, float(ifBars['close'][i])*1000/First,ifBars['time'][i]]
            indexList[i] = index

        dbConnecterTB.insertPriceData30M(dataList)
        dbConnecterTB.insertIndex30M(indexList)
        time.sleep(60)


    tbpy.exit()


def loadTableData():

    wb = xw.Book('index.xlsx')

    show = wb.sheets("data")
    show.range("B2:U2999").value = ""
    timewrite = False

    symbols = dbConnecterTB.queryStratageProduct(2)
    lenSymb = len(symbols)
    symbollist = ["" for x in range(lenSymb)]

    #找出白银商品的时间表，其他商品对齐时间，如果没有的，自动补齐上一个记录，保持时间一致
    agTimeList = dbConnecterTB.queryTimeAg('ag888.SHFE')
    allList = len(agTimeList)

    # 获取原始数据到字典
    for i in range(0, 20):
        # 获取20天的行情数据

        symbolCode = symbols[i][0]
        symbollist[i] = symbolCode

        print("获取品种", symbolCode, "行情信息，计算指数，当前为：20-", i + 1)

        if symbolCode != '':
            closeList = dbConnecterTB.queryIndex30M(symbolCode)
            #print(closeList)

            lenList = len(closeList)

            indexList = [0 for x in range(allList)]

            for n in range(0, allList):
                k = 0
                for x in range(0,lenList):

                    if agTimeList[n] == closeList[x][1]:
                        indexList[n] = closeList[x][0] * 1000 / closeList[0][0]
                        break
                    k = k+1
                if k == lenList:
                    if n == 0:
                        indexList[n] = closeList[0][0]
                    else:
                        indexList[n] = indexList[n - 1]


            if timewrite == False:

                show.range(2, 1).options(transpose=True).value = agTimeList
                timewrite = True

            #print(indexList)
            show.range(2, 2 + i).options(transpose=True).value = indexList

    show.range(1, 2).options(transpose=False).value = symbollist

def getInstrument():

    symbols = dbConnecterTB.queryStratageProduct(2)
    lenSymb = len(symbols)
    data = ["",0,0]
    symbollist = [data for x in range(lenSymb)]

    for i in range(0, lenSymb):
        symbol = symbols[i][0]
        ret =tbpy.get_instrument(symbol)
        data = [symbol,ret.contract_unit,ret.big_point_value]
        symbollist[i] = data

    dbConnecterTB.updateProduct(symbollist)
    print("更新商品信息成功")

UpdateFutureData()
#loadTableData()
#getInstrument()