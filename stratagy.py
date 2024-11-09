import datetime
import MySQLBase
import logging
import time
from comm import dbConnecterTB1
from comm import commFunctions
import xlwings as xw

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logging.info('Admin logged in')

def calcStratagy():

    #逐个遍历品种：装载数据，计算三线，计算策略运行过程，存入数据库，四个步骤

    dbConnecterTB.clearStratageDetail()

    symList = dbConnecterTB.queryStratageProduct(2)
    days = 20 #策略窗口

    for n in range(0, len(symList)):
        symbols = symList[n][0]
        contract_unit = symList[n][1]
        big_point_value = symList[n][2]

        #资金
        money = 1000000


        rawData = dbConnecterTB.queryPriceData30M(symbols)
        rawDataLen = len(rawData)

        dbData = [0,"",0,"",0,0,0,0,0,0,0]
        dbDataList = [dbData for x in range(rawDataLen)]

        dayCount = 0 #用来计数的变量，超过指定的日期，就开始计算
        ArrNum = 0 #用来计数
        maxClose = 0
        minClose = 0
        arr_high = [0 for x in range(20)]
        arr_low = [0 for x in range(20)]
        top = [0 for x in range(rawDataLen)]
        buttom = [0 for x in range(rawDataLen)]
        mid = [0 for x in range(rawDataLen)]
        num = [0 for x in range(rawDataLen)] #手数
        rate = [0 for x in range(rawDataLen)]
        stg = [0 for x in range(rawDataLen)]
        winner = [0 for x in range(rawDataLen)]

        nCount = 0



        for i in range(0,rawDataLen):
            priceTime = rawData[i][1]
            close = rawData[i][0]



            rollover = rawData[i][2]

            if i == 0:
                #today = priceTime.day
                #beginTime = (today+priOffset).strftime('%Y-%m-%d 16:00:00')
                endTime = datetime.datetime(priceTime.year,priceTime.month,priceTime.day,16,00,00)
                maxClose = close #用来计算当天的最高收盘
                minClose = close #用来计算当天的最低收盘
                arr_high = [close for x in range(20)]
                arr_low = [close for x in range(20)]
            else:
                prePriceTime = rawData[i-1][1]
                preRollOver = rawData[i-1][2]
                if prePriceTime.hour == 14 and prePriceTime.minute ==30:

                    arr_high[ArrNum] = maxClose
                    arr_low[ArrNum] = minClose

                    dayCount = dayCount + 1
                    ArrNum = ArrNum + 1

                    maxClose = close #用来计算当天的最高收盘
                    minClose = close #用来计算当天的最低收盘
                else:
                    if close> maxClose:
                        maxClose = close

                    if close < minClose:
                        minClose = close

            if dayCount == 19:
                print("")

            top[i] = max(arr_high)
            buttom[i] = min(arr_low)
            mid[i] = (top[i]+buttom[i])/2



            #如果超过天数，即开始启动交易流程
            if dayCount > days-2:
                if nCount == 0:
                    if close > top[i]:
                        nCount = 1
                        stg[i] = 1
                        lots = money * rollover / (close*big_point_value*contract_unit)
                        num[i] = max(1,round(lots,0))
                    elif close < buttom[i]:
                        nCount = -1
                        stg[i] = -1
                        lots = money * rollover / (close*big_point_value*contract_unit)
                        num[i] = max(1,round(lots,0))

                elif nCount < 0:
                    if close <= mid[i]:
                        stg[i] = -2
                        rate[i] = (rawData[i-1][0] - close)/rawData[i-1][0]
                        num[i] = num[i-1]
                        winner[i] = rate[i]*num[i]*rawData[i-1][0]
                    elif close > mid[i]:
                        stg[i] = -3
                        rate[i] = (rawData[i-1][0] - close) / rawData[i-1][0]
                        winner[i] = rate[i] * num[i - 1] * rawData[i-1][0]
                        num[i] = 0
                        nCount = 0

                else:
                    if close >= mid[i]:
                        stg[i] = 2
                        rate[i] = (close - rawData[i - 1][0]) / rawData[i - 1][0]
                        num[i] = num[i - 1]
                        winner[i] = rate[i] * num[i] * rawData[i - 1][0]
                    elif close < mid[i]:
                        stg[i] = 3
                        rate[i] = (close - rawData[i - 1][0]) / rawData[i - 1][0]
                        winner[i] = rate[i] * num[i - 1] * rawData[i - 1][0]
                        num[i] = 0
                        nCount = 0


            #判断完了，更新最新的数据
            if ArrNum == days:
                ArrNum = 0



            dbData = [2,symbols,close,rawData[i][1],num[i],stg[i],rate[i],winner[i],top[i],mid[i],buttom[i]]
            dbDataList[i] = dbData



        dbConnecterTB.insertStratageDetail(dbDataList)
        print(symbols,"更新策略表成功...")

def loadStratagy(index=1):
    wb = xw.Book('index.xlsx')

    show = wb.sheets("stratagy")
    show.range("A3:CY2999").value = ""
    symList = dbConnecterTB.queryStratageProduct(2)
    symbol = symList[index][0]
    ret = dbConnecterTB.queryStratageDetail(symbol)
    rawDataLen = len(ret)
    timeList = ["" for x in range(rawDataLen)]
    closeList = [0 for x in range(rawDataLen)]
    top = [0 for x in range(rawDataLen)]
    buttom = [0 for x in range(rawDataLen)]
    mid = [0 for x in range(rawDataLen)]

    for i in range(0,rawDataLen):
        closeList[i]= ret[i][0]
        timeList[i] = ret[i][1]
        top[i] = ret[i][6]
        buttom[i] = ret[i][7]
        mid[i] = ret[i][8]

    # 对excel 写时间序列
    show.cells(1,  1).value = symbol
    slicing = 500
    show.range(3, 1).options(transpose=True).value = timeList[-slicing:]
    show.range(3, 2).options(transpose=True).value = closeList[-slicing:]
    show.range(3, 3).options(transpose=True).value = top[-slicing:]
    show.range(3, 4).options(transpose=True).value = mid[-slicing:]
    show.range(3, 5).options(transpose=True).value = buttom[-slicing:]


def loadStratagyInfo():
    wb = xw.Book('index.xlsx')

    show = wb.sheets("info")
    show.range("A2:D2999").value = ""
    symList = dbConnecterTB.queryStratageProduct(2)
    agTime = dbConnecterTB.queryTimeAg()
    agLen= len(agTime)

    total = [0 for x in range(agLen)]
    sumList = [0 for x in range(agLen)]
    longList = [0 for x in range(agLen)]
    shortList = [0 for x in range(agLen)]

    for i in range(0,len(symList)):

        symbol = symList[i][0]
        ret = dbConnecterTB.queryStratageDetail(symbol)
        lenList = len(ret)

        for j in range(0,agLen):
            k = 0
            for x in range(0, lenList):

                if agTime[j] == ret[x][1]:
                    total[j] = ret[x][5]
                    if j==0 :
                        sumList[j] = 0
                    else:
                        sumList[j] = sumList[j-1] + total[j]
                    longList[j] = longList[j] + (1 if ret[x][3] > 0 else 0)
                    shortList[j] = shortList[j] + (1 if ret[x][3] < 0 else 0)
                    break
                k = k + 1
            if k == lenList:
                if j == 0:
                    total[j] = 0
                else:
                    total[j] = total[j-1]
                    longList[j] = longList[j-1]
                    shortList[j] = shortList[j-1]



    # 对excel 写时间序列
    show.range(2, 1).options(transpose=True).value = agTime
    show.range(2, 2).options(transpose=True).value = sumList
    show.range(2, 3).options(transpose=True).value = longList
    show.range(2, 4).options(transpose=True).value = shortList



calcStratagy()
loadStratagyInfo()
#loadStratagy(1)