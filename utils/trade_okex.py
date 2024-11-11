import ccxt
from ccxt.base.exchange import Exchange
import datetime
import time
import json


# 账户跟随操作
def trade_follow(leader_info, follower_info_list):
    leader_okex = build_trade_okex(leader_info)
    # 获取领导者持仓信息
    leader_balances = execute(leader_okex, "fetch_positions", ())
    leader_balances_dict = dict()
    # 领导者仓位转换为字典数据
    for item in leader_balances:
        symbol = item["symbol"]
        leader_balances_dict[symbol] = item

    # 产品面值字典
    ct_val_dict = dict()
    # 更新对应合约面值信息
    init_ct_val(leader_balances, ct_val_dict)
    for follower_info in follower_info_list:
        trade_syn(leader_balances, leader_balances_dict, ct_val_dict, follower_info)


# 同步持仓
def trade_syn(leader_balances, leader_balances_dict, ct_val_dict, follower_info):
    follower_okex = build_trade_okex(follower_info)
    # 获取跟随者持仓信息
    follower_balances = execute(follower_okex, "fetch_positions", ())
    # 更新对应合约面值信息
    init_ct_val(follower_balances, ct_val_dict)
    follower_balances_dict = dict()
    # 单品种购买金额
    std_money = follower_info["money"]

    # 跟随者仓位转换为字典数据
    for item in follower_balances:
        symbol = item["symbol"]
        follower_balances_dict[symbol] = item

    # 最后跟随者下单列表
    order_balances = []
    # 遍历所有领导者持仓信息
    for item in leader_balances:
        symbol = item["symbol"]
        # if item["marginType"] != "cross":
        #     # 只处理全仓的
        #     continue
        if follower_balances_dict.get(symbol, None) is None:
            # 领导者有的仓位，但是跟随着还没有对应的仓位，需要增加仓位
            order_balances.append({
                "symbol": symbol,
                "ordType": "market",
                "side": "buy",
                "amount": std_money / ct_val_dict[symbol],
                "params": {
                    "tdMode": item["marginType"],  # cross  全仓 isolated 逐仓
                    "leverage": "10"
                }
            })

    # 遍历所有跟随者持仓信息
    for item in follower_balances:
        symbol = item["symbol"]
        # if item["marginType"] != "cross":
        #     # 只处理全仓的
        #     continue
        if leader_balances_dict.get(symbol, None) is None:
            # 跟随者有的仓位，但是领导者已没有对应的仓位，需要全部卖出
            order_balances.append({
                "symbol": symbol,
                "ordType": "market",
                "side": "sell",
                "amount": item["contracts"],
                "params": {
                    "tdMode": "cross",  # cross  全仓 isolated 逐仓
                    "leverage": "10"
                }
            })
        else:
            if item["marginType"] == "cross":
                # 杠杆变化，对已有仓位进行处理
                # 数量发生变化
                diff = int(std_money / ct_val_dict[symbol]) - abs(item["contracts"])
                side = "buy"
                if diff > 0:
                    side = "sell"
                if abs(diff) > 0:
                    # 跟随者有的仓位，但是领导者已没有对应的仓位，需要全部卖出
                    order_balances.append({
                        "symbol": symbol,
                        "ordType": "market",
                        "side": side,
                        "amount": diff,
                        "params": {
                            "tdMode": "cross",  # cross  全仓 isolated 逐仓
                            "leverage": "10"
                        }
                    })

    print(dumps(leader_balances))
    print(dumps(follower_balances))
    print(dumps(order_balances))
    for order in order_balances:
        # 执行下单
        pass


# 获取合约面值信息
def init_ct_val(balances, ct_val_dict):
    public_okex = build_trade_okex()
    for item in balances:
        symbol = item["symbol"]
        # 取名称
        symbol_name = symbol[0:symbol.rfind('/', 1)]
        if ct_val_dict.get(symbol, None) is None:
            # 获得合约面值
            data = public_okex.public_get_public_instruments(params={
                "instType": "SWAP",
                "uly": symbol_name + "-USDT",
                "instId": symbol_name + "-USDT-SWAP"
            })
            ct_val_dict[symbol] = float(data['data'][0]['ctVal'])
        item["ctVal"] = ct_val_dict[symbol]


class __MyOkex(Exchange):
    pass


class MyOkex(__MyOkex, ccxt.okex):
    pass


# 构建okex执行对象所需要的参数
def build_okex_param(params):
    temp_params = {
        'hostname': 'okx.4008090.cn',
        'asyncio_loop': 'loop',
        'enableRateLimit': True,
        'options': {
            'defaultType': 'futures',
        }
    }
    return dict(temp_params, **params)


# 根据用户信息，构建okex执行对象
def build_trade_okex(acct_info_value=None):
    params = dict()
    if acct_info_value is not None:
        params = {
            'apiKey': acct_info_value['apikey'],
            'secret': acct_info_value['secretkey'],
            'password': acct_info_value['apipass']
        }
    trade_okex = MyOkex(build_okex_param(params))
    return trade_okex


# 执行okex方法，尝试3次执行
def execute(okex, function_name, args, max_retries=3):
    fun = getattr(okex, function_name)
    for i in range(0, max_retries):
        try:
            return fun(*args)
        except Exception:
            time.sleep(1)
    raise


# json序列化 时间处理
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return json.JSONEncoder.default(self, obj)


# json序列化
def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, cls=DateEncoder)
