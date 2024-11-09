import time
import schedule
import datetime
import xlwings as xw
from comm import mult_conn_index as mci
from comm import commFunctions as cf

def show():
    ret = mci.queryInxlatest()
    lastDate = str(ret[0])
    print(lastDate)

    ret = mci.querySrcData(lastDate)
    if len(ret) == 0:
        print("没有最新数据")
    else:

        mci.insertIdxData(ret)

    print("this is show")

show()
schedule.every().day.at('15:31').do(show)  #

while True:
    schedule.run_pending()

