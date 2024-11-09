import schedule
import json
import time
import requests
import hmac
import hashlib
import base64
import urllib.parse
from comm import dbConnecter as dc

dingding_text = 'This is a new message from DingDing Robot'

webhook = 'https://oapi.dingtalk.com/robot/send?access_token=ddbb46940ed39ab07f073993bb09f0e36bd291df71db8fd38f045e4cc674dce6'
secret = 'SEC2e7c4934275518717c96c964babe32d42201227dee84e45de621f4740c0561b3'

timestamp = str(round(time.time() * 1000))
secret_enc = secret.encode('utf-8')
string_to_sign = '{}\n{}'.format(timestamp, secret)
string_to_sign_enc = string_to_sign.encode('utf-8')
hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
url = '%s&timestamp=%s&sign=%s' % (webhook, timestamp, sign)

headers = {'Content-Type': 'application/json'}


def queryAcctData():

    result = dc.queryAllAcctMoney()
    text = ""
    for itor in result:
        line = itor[0] + ",\t" + str(itor[1]) + ",\t" + str(itor[2]) + ",\t" + str(itor[4]) + "\n"
        text = text + line

    return text


def queryHoldingData():

    result = dc.queryStratageDetailProduct()
    text = ""
    longNum = 0
    shortNum = 0
    for itor in result:

        if itor[1] == 1:
            longNum += 1
            strout = "多开"
        if itor[1] == 2:
            longNum += 1
            strout = "多头持仓"
        if itor[1] == -1:
            shortNum += 1
            strout = "空开"
        if itor[1] == -2:
            shortNum += 1
            strout = "空头持仓"

        line = itor[0] + ",\t" + strout + "\n"
        text = text + line

    line = "当前多头："+str(longNum)+",当前空头："+str(shortNum)
    text = text + line

    return text

def job(type=1):
    dingding_text = "由Ding python 程序推送"
    if type == 1:
        dingding_text = queryAcctData()

    if type == 2:
        dingding_text = queryHoldingData()

    data = {
        "msgtype": "text",
        'text': {
            'content': f'{dingding_text}\n'
        }
    }

    res = requests.post(url, data=json.dumps(data), headers=headers)

    if res.json()['errmsg'] == 'ok':
        print(time.time(),"message send success")

def queryAcct():
    job(1)

def queryStratage():
    job(2)

job(1)
job(2)
schedule.every(60).seconds.do(queryAcct)
schedule.every(1800).seconds.do(queryStratage)
while True:
    schedule.run_pending()