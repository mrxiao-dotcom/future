from utils import trade_common


class TableAction:
    table_name = ''
    key_name = ''

    # 定义构造方法
    def __init__(self, table_name, key_name):
        self.table_name = table_name
        self.key_name = key_name

    # 加载所有数据
    def load(self):
        sql = "select * from %s limit 2000 " % (self.table_name,)
        acct_info_list = trade_common.execute_query(sql)
        return acct_info_list

    # 获取详细数据
    def info(self, value):
        sql = ("select * from %s where %s=%s" % (self.table_name, self.key_name, value))
        acct_info_list = trade_common.execute_query(sql)
        if len(acct_info_list) > 0:
            return acct_info_list[0]
        return {}

    # 更新数据库数据
    def update(self, value_dict):
        key_value = value_dict[self.key_name]
        if key_value is None:
            return 0
        sql = "update %s set " % (self.table_name,)
        params = ()
        first = True
        for key, value in value_dict.items():
            if key == self.key_name:
                continue
            if value is None:
                continue
            if first:
                first = False
            else:
                sql = sql + ","
            sql = "%s %s = " % (sql, key)
            sql = sql + "%s"
            params = params + (value,)
        sql = "%s where %s = " % (sql, self.key_name)
        sql = sql + "%s"
        params = params + (key_value,)
        return trade_common.prepare_update(sql, params)

    # 新增数据库数据
    def insert(self, value_params):
        sql = "insert into %s ( " % (self.table_name,)
        values = "values("
        params = ()
        # 列表参数，批量新增
        if isinstance(value_params, list):
            params = []
            first = True
            item = value_params[0]
            param_item = ()
            for key, value in item.items():
                if value is None:
                    continue
                if first:
                    first = False
                else:
                    sql = sql + ","
                    values = values + ","
                sql = "%s %s " % (sql, key)
                values = values + "%s"
                param_item = param_item + (value,)
            sql = "%s) %s)" % (sql, values)
            params.append(param_item)
            for index in range(len(value_params)):
                if index == 0:
                    continue
                item = value_params[index]
                param_item = ()
                for key, value in item.items():
                    if value is None:
                        continue
                    param_item = param_item + (value,)
                params.append(param_item)
        else:
            first = True
            for key, value in value_params.items():
                if value is None:
                    continue
                if first:
                    first = False
                else:
                    sql = sql + ","
                    values = values + ","
                sql = "%s %s " % (sql, key)
                values = values + "%s"
                params = params + (value,)
            sql = "%s) %s)" % (sql, values)
        print(sql)
        print(trade_common.dumps(params))
        return trade_common.prepare_update(sql, params)


class AcctInfo(TableAction):
    # 定义构造方法
    def __init__(self):
        super(AcctInfo, self).__init__("acct_info", "acct_id")


class AcctMoney(TableAction):
    # 定义构造方法
    def __init__(self):
        super(AcctMoney, self).__init__("acct_money", "id")


class AcctStratage(TableAction):
    # 定义构造方法
    def __init__(self):
        super(AcctStratage, self).__init__("acct_stratage", "acct_id")


class AdminAcct(TableAction):
    # 定义构造方法
    def __init__(self):
        super(AdminAcct, self).__init__("admin_acct", "id")


class AdminInfo(TableAction):
    # 定义构造方法
    def __init__(self):
        super(AdminInfo, self).__init__("admin_info", "admin_id")


class IndexData(TableAction):
    # 定义构造方法
    def __init__(self):
        super(IndexData, self).__init__("index_data", "ID")


class PriceData(TableAction):
    # 定义构造方法
    def __init__(self):
        super(PriceData, self).__init__("price_data", "price_id")


class Product(TableAction):
    # 定义构造方法
    def __init__(self):
        super(Product, self).__init__("product", "product_id")


class Stratage(TableAction):
    # 定义构造方法
    def __init__(self):
        super(Stratage, self).__init__("stratage", "id")


class StratageDetail(TableAction):
    # 定义构造方法
    def __init__(self):
        super(StratageDetail, self).__init__("stratage_detail", "stratage_id")


class StratageMaDetail(TableAction):
    # 定义构造方法
    def __init__(self):
        super(StratageMaDetail, self).__init__("stratage_ma_detail", "stratage_id")


class StratageProduct(TableAction):
    # 定义构造方法
    def __init__(self):
        super(StratageProduct, self).__init__("stratage_product", "stratage_id")


class AcctTest(TableAction):
    # 定义构造方法
    def __init__(self):
        super(AcctTest, self).__init__("acct_test", "test_id")


class StratageSum(TableAction):
    # 定义构造方法
    def __init__(self):
        super(StratageSum, self).__init__("stratage_sum", "id")


class SysLog(TableAction):
    # 定义构造方法
    def __init__(self):
        super(SysLog, self).__init__("sys_log", "log_id")


def sys_log(log_string):
    print(log_string)
    __log = SysLog()
    __log.insert({"log_string": log_string})

