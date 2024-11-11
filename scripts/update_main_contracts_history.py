import sys
import os
sys.path.append('.')
from dotenv import load_dotenv
from comm.dboper import DBOperator
import datetime
import tushare as ts
from utils.rate_limiter import RateLimiter
import time

# 加载环境变量
load_dotenv()

class MainContractHistoryUpdater:
    def __init__(self):
        self.db = DBOperator()
        self.ts_token = os.getenv('TUSHARE_TOKEN')
        self.pro = ts.pro_api(self.ts_token)
        self.rate_limiter = RateLimiter(max_requests=180, time_window=60)
    
    def _call_tushare_api(self, func, **kwargs):
        """调用Tushare API的包装方法"""
        try:
            current_requests = self.rate_limiter.acquire()
            if current_requests > 150:
                time.sleep(0.5)
            return func(**kwargs)
        except Exception as e:
            print(f"Tushare API call failed: {str(e)}")
            raise
    
    def get_trading_dates(self, start_date, end_date):
        """获取交易日期列表"""
        sql = """
        SELECT DISTINCT trade_date
        FROM futures_daily_quotes
        WHERE trade_date BETWEEN %s AND %s
        ORDER BY trade_date DESC
        """
        dates = self.db.execute_query(sql, (start_date, end_date))
        return [date[0] for date in dates]
    
    def get_main_contracts_by_date(self, trade_date):
        """获取指定日期的所有主力合约"""
        try:
            # 1. 先获取当天有行情数据的合约
            quotes_sql = """
            SELECT ts_code, amount, oi
            FROM futures_daily_quotes
            WHERE trade_date = %s
            """
            
            print(f"Getting quotes data for {trade_date}")
            quotes_data = self.db.execute_query(quotes_sql, (trade_date,))
            print(f"Found {len(quotes_data)} contracts with quotes")
            
            # 2. 获取合约基本信息
            if not quotes_data:
                return []
                
            ts_codes = tuple(row[0] for row in quotes_data)
            basic_sql = """
            SELECT ts_code, exchange
            FROM futures_basic
            WHERE ts_code IN %s
            AND ts_code NOT LIKE '%%L.%%'
            AND ts_code NOT LIKE '%%99.%%'
            """
            
            basic_data = self.db.execute_query(basic_sql, (ts_codes,))
            print(f"Found {len(basic_data)} valid contracts")
            
            # 3. 合并数据
            contract_info = {}
            for row in basic_data:
                contract_info[row[0]] = row[1]  # ts_code -> exchange
            
            # 4. 按品种分组
            products = {}
            for row in quotes_data:
                ts_code, amount, oi = row
                if ts_code not in contract_info:
                    continue
                    
                product = ts_code.split('.')[0][:-4]  # 提取品种代码
                exchange = contract_info[ts_code]
                
                if product not in products:
                    products[product] = []
                products[product].append({
                    'ts_code': ts_code,
                    'amount': float(amount or 0),
                    'oi': float(oi or 0),
                    'exchange': exchange
                })
            
            # 5. 找出每个品种的主力合约
            main_contracts = []
            for product, contracts in products.items():
                if not contracts:
                    continue
                    
                # 计算每个合约的得分
                max_score = 0
                main_contract = None
                
                for contract in contracts:
                    score = contract['amount'] * 0.4 + contract['oi'] * 0.6
                    if score > max_score:
                        max_score = score
                        main_contract = contract
                
                if main_contract:
                    print(f"Found main contract for {product}: {main_contract['ts_code']}")
                    main_contracts.append((
                        main_contract['ts_code'],
                        main_contract['exchange'],
                        product
                    ))
            
            print(f"Total main contracts found: {len(main_contracts)}")
            return main_contracts
            
        except Exception as e:
            print(f"Error getting main contracts: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def check_missing_data(self, ts_codes, trade_dates):
        """检查哪些数据缺失"""
        missing_data = []
        
        # 构建查询条件
        conditions = []
        params = []
        for ts_code in ts_codes:
            for date in trade_dates:
                conditions.append("(ts_code = %s AND trade_date = %s)")
                params.extend([ts_code, date])
        
        if not conditions:
            return []
        
        # 查询已存在的数据
        sql = f"""
        SELECT ts_code, trade_date
        FROM futures_daily_quotes
        WHERE {' OR '.join(conditions)}
        """
        
        existing_data = self.db.execute_query(sql, tuple(params))
        existing_set = {(row[0], row[1]) for row in existing_data}
        
        # 找出缺失的数据
        for ts_code in ts_codes:
            for date in trade_dates:
                if (ts_code, date) not in existing_set:
                    missing_data.append((ts_code, date))
        
        return missing_data
    
    def update_history(self):
        """更新主力合约历史数据"""
        try:
            # 1. 获取日期范围
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=45)  # 取45天以确保覆盖30个交易日
            
            # 2. 获取交易日列表
            trading_dates = self.get_trading_dates(
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )
            print(f"Found {len(trading_dates)} trading dates")
            
            # 3. 获取最新交易日的主力合约列表
            latest_date = trading_dates[0]
            main_contracts = self.get_main_contracts_by_date(latest_date)
            main_contract_codes = [row[0] for row in main_contracts]
            print(f"Found {len(main_contract_codes)} main contracts")
            
            # 4. 检查缺失的数据
            missing_data = self.check_missing_data(main_contract_codes, trading_dates)
            print(f"Found {len(missing_data)} missing data points")
            
            # 5. 获取并保存缺失的数据
            for ts_code, trade_date in missing_data:
                try:
                    date_str = trade_date.strftime('%Y%m%d')
                    print(f"Fetching data for {ts_code} on {date_str}")
                    
                    df = self._call_tushare_api(
                        self.pro.fut_daily,
                        ts_code=ts_code,
                        start_date=date_str,
                        end_date=date_str
                    )
                    
                    if not df.empty:
                        # 保存数据
                        insert_sql = """
                        INSERT INTO futures_daily_quotes 
                            (ts_code, trade_date, open, high, low, close, 
                             pre_close, change_rate, vol, amount, oi)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        for _, row in df.iterrows():
                            # 处理可能的字段名差异
                            change_rate = row.get('change_rate', row.get('change', 0))
                            
                            params = (
                                row['ts_code'],
                                row['trade_date'],
                                row['open'],
                                row['high'],
                                row['low'],
                                row['close'],
                                row['pre_close'],
                                change_rate,  # 使用处理后的涨跌幅
                                row['vol'],
                                row['amount'],
                                row['oi']
                            )
                            self.db.execute_update(insert_sql, params)
                        print(f"Data saved for {ts_code} on {date_str}")
                    else:
                        print(f"No data available for {ts_code} on {date_str}")
                
                except Exception as e:
                    print(f"Error processing {ts_code} on {date_str}: {str(e)}")
                    print("Data fields available:", df.columns.tolist() if 'df' in locals() and not df.empty else "No data")
                    continue
            
            print("\nHistory update completed")
            
        except Exception as e:
            print(f"Error updating history: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    updater = MainContractHistoryUpdater()
    updater.update_history()