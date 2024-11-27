# 期货品种代码与中文名称的映射
PRODUCT_NAMES = {
    # 上期所
    'CU': '沪铜',
    'AL': '沪铝',
    'ZN': '沪锌',
    'PB': '沪铅',
    'NI': '沪镍',
    'SN': '沪锡',
    'AU': '沪金',
    'AG': '沪银',
    'RB': '螺纹钢',
    'WR': '线材',
    'HC': '热轧卷板',
    'SS': '不锈钢',
    'BU': '沥青',
    'RU': '橡胶',
    'FU': '燃料油',
    'SP': '纸浆',

    # 大商所
    'C': '玉米',
    'CS': '玉米淀粉',
    'A': '豆一',
    'B': '豆二',
    'M': '豆粕',
    'Y': '豆油',
    'P': '棕榈油',
    'FB': '纤维板',
    'BB': '胶合板',
    'JD': '鸡蛋',
    'L': '塑料',
    'V': 'PVC',
    'PP': '聚丙烯',
    'J': '焦炭',
    'JM': '焦煤',
    'I': '铁矿石',
    'EG': '乙二醇',
    'EB': '苯乙烯',
    'PG': '液化石油气',

    # 郑商所
    'SR': '白糖',
    'CF': '棉花',
    'CY': '棉纱',
    'PM': '普麦',
    'WH': '强麦',
    'RI': '早籼稻',
    'LR': '晚籼稻',
    'JR': '粳稻',
    'RS': '菜籽',
    'OI': '菜油',
    'RM': '菜粕',
    'TA': 'PTA',
    'MA': '甲醇',
    'FG': '玻璃',
    'SF': '硅铁',
    'SM': '锰硅',
    'ZC': '动力煤',
    'AP': '苹果',
    'CJ': '红枣',
    'UR': '尿素',
    'SA': '纯碱',

    # 中金所
    'IF': '沪深300',
    'IC': '中证500',
    'IH': '上证50',
    'IM': '中证1000',
    'T': '10年期国债',
    'TF': '5年期国债',
    'TS': '2年期国债',

    # 能源所
    'SC': '原油',
    'LU': '低硫燃料油',
    'BC': '国际铜',

    # 广期所
    'SI': '工业硅',
    'LC': '碳排放',
}

def get_product_name(code):
    """获取品种的中文名称"""
    # 提取品种代码（去掉合约月份等）
    base_code = code.split('.')[0] if '.' in code else code
    while base_code and not base_code[-1].isalpha():
        base_code = base_code[:-1]
    
    return PRODUCT_NAMES.get(base_code.upper(), code)

def get_full_name(code):
    """获取完整名称（品种中文名 + 代码）"""
    return f"{get_product_name(code)} ({code})" 