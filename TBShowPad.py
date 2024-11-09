import datetime
import time
import xlwings as xw
from comm import dbConnecterTB1
from comm import commFunctions as cf
import schedule
#from comm import screencopy


days = 180

def readProfitFromDB():

    try:
        wb = xw.Book('TraderPadTB.xlsx')

        show = wb.sheets("净值")
        #show.range("A2:I9999").value = ""
        logOut("开始更新行情与策略数据...")
        retData = dbConnecterTB.queryProfit()
        lenList = len(retData)


        N = days*19 #60天数据

        rawData = retData[-(N+1):] #获得N+1个数据


        profit = [x[0]-rawData[0][0]+25000000 for x in rawData[1:]]
        timelist = [x[4] for x in rawData[1:]]
        longnum = [x[1] for x in rawData[1:]]
        shortnum = [x[2] for x in rawData[1:]]
        totalnum = [x[3] for x in rawData[1:]]

        maxdrawdown = [0 for x in profit]
        currentdrawdown = [0 for x in profit]
        drawdowntime = [0 for x in profit]
        risk = [0 for x in profit]



        for n in range(0,len(profit)):

            newData = [x+100000.0*20 for x in profit[0:n+1]]
            drawdown = cf.MaxDrawdown(newData)

            if drawdown != 0:
                maxdrawdown[n] = drawdown[0]
                currentdrawdown[n] = drawdown[3]
                drawdowntime[n] = drawdown[2]

        maxDraw = max(maxdrawdown)



        for n in range(0,len(profit)):
            current = currentdrawdown[n]
            risk[n] = (maxDraw*100 - current*100)/(100-current*100)*(totalnum[n]/max(totalnum))

        show.range(1,1).value = "时间"
        show.range(2,1).options(transpose=True).value = timelist
        show.range(1,2).value = "收益"
        show.range(2,2).options(transpose=True).value = profit
        show.range(1,3).value = "多头"
        show.range(2,3).options(transpose=True).value = longnum
        show.range(1,4).value = "空头"
        show.range(2,4).options(transpose=True).value = shortnum
        show.range(1,5).value = "多空总数"
        show.range(2,5).options(transpose=True).value = totalnum

        show.range(1,6).value = "最大回撤"
        show.range(2,6).options(transpose=True).value = maxdrawdown
        show.range(1,7).value = "当前回撤"
        show.range(2,7).options(transpose=True).value = currentdrawdown
        show.range(1,8).value = "回撤K线数"
        show.range(2,8).options(transpose=True).value = drawdowntime
        show.range(1,9).value = "回撤风险"
        show.range(2,9).options(transpose=True).value = risk

        show.range("A"+str(len(profit)+2)+":J9999").value = ""  #清理多余数据

        # 生成图片
        #outfile = screencopy.excel_catch_screen()

        # 获得邮件列表，发送邮件
        #receivers = ["1497436688@qq.com"]
        #screencopy.sent_mail_pic(outfile, receivers, "tb")


    except Exception as e:
        print("执行readProfitFromDB异常，错误代码：", e)

def createIndex():
    try:
        logOut("开始更新指数数据...")
        wb = xw.Book('TraderPadTB.xlsx')
        show = wb.sheets("净值")
        N = days * 19  # 60天数据
        symbolList = dbConnecterTB.queryProduct()
        lenSymb = len(symbolList)

        #找出白银商品的时间表，其他商品对齐时间，如果没有的，自动补齐上一个记录，保持时间一致
        agTime = dbConnecterTB.queryTime('ag')
        agTimeList = agTime[-N:]
        allList = len(agTimeList)

        initIndex = 0

        for i in range(0, lenSymb):
            symbol = symbolList[i]
            priceList = dbConnecterTB.queryPriceData(symbol)
            priceList = priceList[-N:]
            lenList = len(priceList)

            if initIndex == 0:
                indexAllList = [0 for x in range(allList)]
                initIndex = 1

            indexList = [0 for x in range(allList)]

            first = 0
            for n in range(0, allList):
                k = 0

                for x in range(0,lenList):

                    if agTimeList[n] == priceList[x][0]:
                        if first == 0:
                            first = priceList[x][1]

                        indexList[n] = priceList[x][1] * 1000 / first
                        break
                    k = k+1
                if k == lenList:
                    if n == 0:
                        indexList[n] = 1000
                    else:
                        indexList[n] = indexList[n - 1]

                indexAllList[n] = indexAllList[n] + indexList[n]

            #show.range(1,26+i).value = symbol
            #show.range(2, 26+i).options(transpose=True).value = indexList




        indexOut = [itor/25 for itor in indexAllList] #计算指数平均值


        show.range(1,10).value = "指数"
        show.range(2,10).options(transpose=True).value = indexOut

        show.range("J"+str(N+2)+":J9999").value = ""  #清理多余数据
    except Exception as e:
        print("执行createIndex异常，错误代码：", e)


def getMarket(code):

    if code == "DCE":
        codeName = "大商所"
    elif code == "SHFE":
        codeName = "上期所"
    elif code == "CZCE":
        codeName = "郑商所"
    elif code == "CFFEX":
        codeName = "中金所"
    else:
        codeName = "未知"

    return codeName

def readHolding():
    try:
        logOut("开始更新持仓数据...")
        retData = dbConnecterTB.queryStratageHolding()
        wb = xw.Book('TraderPadTB.xlsx')
        show = wb.sheets("持仓")
        dataNum = len(retData)
        for i in range(0,dataNum):
            side = retData[i][2]

            show.range(3 + i, 1).value = retData[i][4]
            show.range(3+i,2).value = retData[i][0]
            show.range(3 + i, 3).value = retData[i][3]
            show.range(3 + i, 4).value = "多头" if side > 0 else "空头"
            show.range(3 + i, 5).value = getMarket(retData[i][5])
            show.range(3 + i, 6).value = retData[i][6]
            show.range(3 + i, 7).value = retData[i][7]
            show.range(3 + i, 8).value = retData[i][8]
            vvalue = retData[i][6]-retData[i][7] if side > 0 else retData[i][7]-retData[i][6]
            show.range(3 + i, 9).value = vvalue*retData[i][8]*retData[i][9]*retData[i][10]

        show.range("A"+str(3+dataNum)+":F99").value = ""
    except Exception as e:
        print("执行readHolding异常，错误代码：", e)


def logOut(logstr):
    print("日志",logstr)
    dbConnecterTB.insertSyslog(logstr)

def showSyslog():
    #定时读取日志表日志，更新到前台
    try:
        ret = dbConnecterTB.querySyslog()
        wb = xw.Book('TraderPadTB.xlsx')

        show = wb.sheets("日志")
        for n in range(0,len(ret)):
            show.range(n+3,1).value = ret[n][0]
            show.range(n + 3, 2).value = ret[n][1]
    except Exception as e:
        print("执行showSyslog异常，错误代码：", e)


def showAcctInfo():
    ret = dbConnecterTB.queryAcctInfo()
    wb = xw.Book('TraderPadTB.xlsx')
    show = wb.sheets("账号")

    for i in range(0, len(ret)):
        show.range(3+i, 1).value = ret[i][0]
        show.range(3 + i, 2).value = ret[i][1]
        show.range(3 + i, 3).value = ret[i][2]
        show.range(3 + i, 4).value = ret[i][3]
        show.range(3 + i, 5).value = ret[i][4]

    logOut("更新账户信息完成...")

def myjob():

    #收市后不跑
    hour = datetime.datetime.now().hour
    if hour > 16 and hour < 21:

        return

    if hour > 3 and hour < 9:
        return
    readProfitFromDB()
    createIndex()
    readHolding()



def showjob():

    #收市后不跑
    hour = datetime.datetime.now().hour
    if hour > 16 and hour < 21:

        return

    if hour > 3 and hour < 9:
        return

    #showSyslog()
    showAcctInfo()


myjob()
schedule.every().hour.at(':31').do(myjob)  #半小时
schedule.every().hour.at(':01').do(myjob)

schedule.every(10).minutes.do(showjob)

while True:
    schedule.run_pending()
    time.sleep(1)
