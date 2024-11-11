import pandas as pd
import datetime
from .dboper import DBOperator  # 使用相对导入
import sys
sys.path.append('..')  # 添加父目录到路径
from utils.trade_common_src import *  # 导入现有的交易相关函数
import tushare as ts
import os
import time
from utils.rate_limiter import RateLimiter
import json

class FuturesDataHandler:
    def __init__(self):
        self.db = DBOperator()
        self.progress = 0
        self.ts_token = os.getenv('TUSHARE_TOKEN')
        self.pro = ts.pro_api(self.ts_token)
        # 创建限流器：每分钟最多180次请求（留20次余量）
        self.rate_limiter = RateLimiter(max_requests=180, time_window=60)
        self.is_updating = False
        self.cancel_update = False
    
    def _call_tushare_api(self, func, **kwargs):
        """
        调用Tushare API的包装方法
        """
        try:
            # 获取令牌，如果需要会自动等待
            current_requests = self.rate_limiter.acquire()
            
            # 如果接近限制，增加额外等待时间
            if current_requests > 150:  # 请求数接近限制时
                time.sleep(0.5)  # 增加额外延迟
            
            # 添加调试日志
            print(f"Calling Tushare API with params: {kwargs}")
            result = func(**kwargs)
            print(f"API response shape: {result.shape if result is not None else 'None'}")
            if result is not None and not result.empty:
                print(f"API response columns: {result.columns.tolist()}")
            return result
        except Exception as e:
            print(f"Tushare API call failed: {str(e)}")
            raise
    
    def get_futures_quotes(self, date):
        """获取期货行情数据"""
        sql = """
        SELECT 
            trade_date,
            code,
            name,
            close_price,
            change_rate,
            volume,
            amount,
            open_interest
        FROM futures_quotes 
        WHERE trade_date = %s
        """
        return self.db.execute_query(sql, (date,))
    
    def get_futures_positions(self, date):
        """获取期货持仓数据"""
        sql = """
        SELECT 
            trade_date,
            code,
            long_position,
            short_position,
            net_position
        FROM futures_positions 
        WHERE trade_date = %s
        """
        return self.db.execute_query(sql, (date,))
    
    def get_filtered_futures(self, filters):
        """根据条件筛选期货"""
        conditions = []
        params = []
        
        if filters.get('change_min') is not None:
            conditions.append("change_rate >= %s")
            params.append(filters['change_min'])
        
        if filters.get('change_max') is not None:
            conditions.append("change_rate <= %s")
            params.append(filters['change_max'])
            
        if filters.get('volume_min') is not None:
            conditions.append("volume >= %s")
            params.append(filters['volume_min'])
            
        if filters.get('volume_max') is not None:
            conditions.append("volume <= %s")
            params.append(filters['volume_max'])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
        SELECT 
            f.trade_date,
            f.code,
            f.name,
            f.close_price,
            f.change_rate,
            f.volume,
            f.amount,
            f.open_interest,
            p.net_position
        FROM futures_quotes f
        LEFT JOIN futures_positions p 
            ON f.code = p.code 
            AND f.trade_date = p.trade_date
        WHERE {where_clause}
        """
        
        return self.db.execute_query(sql, tuple(params))
    
    def get_futures_history(self, code, days=7):
        """获取期货历史数据"""
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        
        sql = """
        SELECT 
            f.trade_date,
            f.close_price,
            f.change_rate,
            f.volume,
            f.amount,
            f.open_interest,
            p.net_position
        FROM futures_quotes f
        LEFT JOIN futures_positions p 
            ON f.code = p.code 
            AND f.trade_date = p.trade_date
        WHERE f.code = %s
            AND f.trade_date BETWEEN %s AND %s
        ORDER BY f.trade_date
        """
        
        return self.db.execute_query(sql, (code, start_date, end_date))
    
    def update_futures_basic(self):
        """更新期货品种基础信息"""
        if self.is_updating:
            return False
            
        self.is_updating = True
        self.cancel_update = False
        self.progress = 0
        self.update_status = {
            'current_exchange': '',
            'updated_count': 0,
            'remaining_exchanges': [],
            'logs': [],
            'status': 'running'
        }
        
        # 交易所列表
        exchanges = {
            'CFFEX': '中金所',
            'DCE': '大商所',
            'CZCE': '郑商所',
            'SHFE': '上期所',
            'INE': '上海国际能源交易中心',
            'GFEX': '广州期货交易所'
        }
        total_exchanges = len(exchanges)
        self.update_status['remaining_exchanges'] = list(exchanges.keys())
        
        try:
            # 获取数据库中现有的期货品种
            self.update_status['logs'].append("获取数据库中现有期货品种...")
            existing_sql = "SELECT ts_code FROM futures_basic"
            existing_codes = {row[0] for row in self.db.execute_query(existing_sql)}
            self.update_status['logs'].append(f"数据库中现有{len(existing_codes)}个品种")
            
            # 记录所有获取到的品种代码
            all_codes = set()
            
            for i, (exchange_code, exchange_name) in enumerate(exchanges.items()):
                if self.cancel_update:
                    break
                    
                try:
                    self.update_status['current_exchange'] = f"{exchange_code}({exchange_name})"
                    self.update_status['remaining_exchanges'].remove(exchange_code)
                    self.update_status['logs'].append(f"开始获取{exchange_name}数据...")
                    
                    # 获取期货品种数据
                    df = self._call_tushare_api(
                        self.pro.fut_basic,
                        exchange=exchange_code,
                        fields='ts_code,symbol,exchange,name,fut_code,multiplier,trade_unit,'
                               'per_unit,quote_unit,quote_unit_desc,d_mode_desc,list_date,'
                               'delist_date,d_month,last_ddate,trade_time_desc'
                    )
                    
                    if df is None or df.empty:
                        self.update_status['logs'].append(f"{exchange_name}没有获取到数据")
                        continue
                    
                    # 处理 NaN 值
                    df = df.fillna({
                        'multiplier': 0,
                        'per_unit': 0,
                        'trade_unit': '',
                        'quote_unit': '',
                        'quote_unit_desc': '',
                        'd_mode_desc': '',
                        'list_date': '',
                        'delist_date': '',
                        'd_month': '',
                        'last_ddate': '',
                        'trade_time_desc': ''
                    })
                    
                    # 记录本次获取的代码
                    current_codes = set(df['ts_code'].tolist())
                    all_codes.update(current_codes)
                    
                    # 需要新约
                    new_contracts = df[~df['ts_code'].isin(existing_codes)]
                    
                    if not new_contracts.empty:
                        # 插入新的合约
                        insert_sql = """
                        INSERT INTO futures_basic (
                            ts_code, symbol, exchange, name, fut_code, multiplier,
                            trade_unit, per_unit, quote_unit, quote_unit_desc,
                            d_mode_desc, list_date, delist_date, d_month,
                            last_ddate, trade_time_desc
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s
                        )
                        """
                        
                        params = [(
                            row['ts_code'],
                            row['symbol'],
                            row['exchange'],
                            row.get('name', ''),
                            row.get('fut_code', ''),
                            float(row.get('multiplier', 0) or 0),  # 处理可能的 NaN
                            str(row.get('trade_unit', '') or ''),  # 处理可能的 NaN
                            float(row.get('per_unit', 0) or 0),    # 处理可能的 NaN
                            str(row.get('quote_unit', '') or ''),
                            str(row.get('quote_unit_desc', '') or ''),
                            str(row.get('d_mode_desc', '') or ''),
                            str(row.get('list_date', '') or ''),
                            str(row.get('delist_date', '') or ''),
                            str(row.get('d_month', '') or ''),
                            str(row.get('last_ddate', '') or ''),
                            str(row.get('trade_time_desc', '') or '')
                        ) for _, row in new_contracts.iterrows()]
                        
                        affected_rows = self.db.execute_many(insert_sql, params)
                        self.update_status['logs'].append(
                            f"{exchange_name}新增{len(params)}个合约"
                        )
                    else:
                        self.update_status['logs'].append(f"{exchange_name}没有需要新增的合约")
                    
                    self.progress = int((i + 1) / total_exchanges * 100)
                    
                except Exception as e:
                    error_msg = f"处理{exchange_name}数据时出错: {str(e)}"
                    self.update_status['logs'].append(error_msg)
                    print(error_msg)
                    continue
            
            if not self.cancel_update:
                self.update_status['status'] = 'completed'
                self.update_status['logs'].append("所有交易所数据更新完成")
            
            return True
            
        except Exception as e:
            error_msg = f"更新过程发生错误: {str(e)}"
            self.update_status['logs'].append(error_msg)
            self.update_status['status'] = 'error'
            print(error_msg)
            return False
            
        finally:
            self.is_updating = False
            self.cancel_update = False
    
    def cancel_update_process(self):
        """取消更进程"""
        if self.is_updating:
            self.cancel_update = True
            return True
        return False
    
    def get_update_progress(self):
        """获取更新进度"""
        return self.progress
    
    def get_update_status(self):
        """获取更新状态"""
        return {
            'progress': self.progress,
            'status': getattr(self, 'update_status', {})
        }

    def _check_table_structure(self):
        """检查数据库表结构"""
        try:
            # 获取表结构
            describe_sql = "DESCRIBE futures_basic"
            columns = self.db.execute_query(describe_sql)
            print("Table structure:")
            for col in columns:
                print(col)
            return True
        except Exception as e:
            print(f"Error checking table structure: {str(e)}")
            return False

    def get_futures_by_exchange(self):
        """获取按交易所分组的期货品种"""
        try:
            # 获取当前月份第一天
            today = datetime.datetime.now()
            current_month_start = today.replace(day=1).strftime('%Y%m%d')
            
            # 获取每个交易所的期货品种
            sql = """
            SELECT DISTINCT
                exchange,
                name
            FROM futures_basic
            WHERE delist_date >= %s
            AND name IS NOT NULL
            AND name != ''
            ORDER BY exchange, name
            """
            
            results = self.db.execute_query(sql, (current_month_start,))
            print(f"Query returned {len(results)} rows")
            
            # 交易所名称映射
            exchange_names = {
                'CFFEX': '中金所',
                'DCE': '大商所',
                'CZCE': '郑商所',
                'SHFE': '上期所',
                'INE': '上海国际能源交易中心',
                'GFEX': '广州期货交易所'
            }
            
            # 手动分理
            futures_by_exchange = {}
            for row in results:
                exchange = row[0]
                full_name = row[1]
                
                # 手动处理名称，去掉数字
                base_name = ''.join([c for c in full_name if not c.isdigit()])
                base_name = base_name.strip()
                
                if not exchange or not base_name:
                    continue
                    
                if exchange not in futures_by_exchange:
                    futures_by_exchange[exchange] = {
                        'name': exchange_names.get(exchange, exchange),
                        'products': []
                    }
                
                # 检查是否已经存在该品种
                if not any(p['name'] == base_name for p in futures_by_exchange[exchange]['products']):
                    futures_by_exchange[exchange]['products'].append({
                        'name': base_name,
                        'display_name': base_name
                    })
            
            # 打印调试信息
            for exchange, data in futures_by_exchange.items():
                print(f"{exchange}: {len(data['products'])} products")
                print(f"First few products: {data['products'][:3]}")
            
            return futures_by_exchange
            
        except Exception as e:
            print(f"Error in get_futures_by_exchange: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}

    def get_contracts_by_product(self, product_code):
        """获取期货品种的所有合约"""
        # 从 Tushare 获取合约信息
        try:
            df = self._call_tushare_api(
                self.pro.fut_basic,
                fut_code=product_code
            )
            
            if df is None or df.empty:
                return []
            
            # 处理约类型标记
            contracts = []
            for _, row in df.iterrows():
                contract_type = 'normal'
                name_suffix = ''
                
                if row.get('is_main') == 1:
                    contract_type = 'main'
                    name_suffix = '(M)'
                elif row.get('is_continuous') == 1:
                    contract_type = 'continuous'
                    name_suffix = '(C)'
                
                contracts.append({
                    'ts_code': row['ts_code'],
                    'symbol': row['symbol'],
                    'name': f"{row.get('name', '')}{name_suffix}",
                    'contract_type': contract_type,
                    'list_date': row.get('list_date'),
                    'delist_date': row.get('delist_date'),
                    'status': '交易中' if pd.Timestamp.now().strftime('%Y%m%d') <= row.get('delist_date', '99991231') else '已到期'
                })
            
            return contracts
        except Exception as e:
            print(f"获取合约信息失败: {str(e)}")
            return []

    def fetch_main_contract_data(self):
        """获取主力合约最近30个交易日的数据"""
        if self.is_updating:
            return False
            
        self.is_updating = True
        self.progress = 0
        self.update_status = {
            'current_process': '',
            'updated_count': 0,
            'logs': [],
            'status': 'running'
        }
        
        try:
            # 1. 获所有主力合约
            self.update_status['logs'].append("正在获取主力约列表...")
            main_contracts = self._get_main_contracts()
            total_contracts = len(main_contracts)
            
            if not main_contracts:
                self.update_status['logs'].append("未找到主力合约")
                return False
                
            self.update_status['logs'].append(f"找到{total_contracts}个主力合约")
            
            # 2. 获取交易日历
            self.update_status['logs'].append("获交易日历...")
            trade_dates = self._get_trade_calendar(30)
            
            # 3. 清理旧数据
            self._clean_old_data(trade_dates[0])
            
            # 4. 获取各类数据
            for i, contract in enumerate(main_contracts):
                if self.cancel_update:
                    break
                    
                ts_code = contract['ts_code']
                self.update_status['current_process'] = f"处理合约 {ts_code}"
                
                # 4.1 获取日线数据
                self.update_status['logs'].append(f"获取{ts_code}日线数据...")
                self._fetch_daily_data(ts_code, trade_dates)
                
                # 4.2 获取仓单数据
                self.update_status['logs'].append(f"获取{ts_code}仓单数...")
                self._fetch_warehouse_data(ts_code, trade_dates)
                
                # 4.3 获取构持仓数据
                self.update_status['logs'].append(f"获取{ts_code}机构持仓数据...")
                self._fetch_institution_data(ts_code, trade_dates)
                
                self.progress = int((i + 1) / total_contracts * 100)
                self.update_status['updated_count'] = i + 1
                
            if not self.cancel_update:
                self.update_status['status'] = 'completed'
                self.update_status['logs'].append("所有数据更新完成")
            
            return True
            
        except Exception as e:
            error_msg = f"更新过程发生错误: {str(e)}"
            self.update_status['logs'].append(error_msg)
            self.update_status['status'] = 'error'
            print(error_msg)
            return False
            
        finally:
            self.is_updating = False
            self.cancel_update = False

    def _get_main_contracts(self):
        """获取所有主力合约"""
        sql = """
        SELECT ts_code, symbol, name 
        FROM futures_basic 
        WHERE delist_date >= CURDATE()
        """
        results = self.db.execute_query(sql)
        return [{'ts_code': row[0], 'symbol': row[1], 'name': row[2]} for row in results]

    def _get_trade_calendar(self, days):
        """获取最近N个交易日"""
        cal_df = self._call_tushare_api(
            self.pro.trade_cal,
            exchange='DCE',
            start_date=(datetime.datetime.now() - datetime.timedelta(days=60)).strftime('%Y%m%d'),
            end_date=datetime.datetime.now().strftime('%Y%m%d'),
            is_open=1
        )
        return sorted(cal_df['cal_date'].tolist())[-days:]

    def _clean_old_data(self, start_date):
        """清理旧数据"""
        tables = [
            'futures_daily_quotes',
            'futures_warehouse_stocks',
            'futures_institution_positions'
        ]
        
        for table in tables:
            sql = f"DELETE FROM {table} WHERE trade_date < %s"
            self.db.execute_update(sql, (start_date,))
            self.update_status['logs'].append(f"清理{table}旧数据完成")

    def _fetch_daily_data(self, ts_code, trade_dates):
        """获取日线数据"""
        try:
            df = self._call_tushare_api(
                self.pro.fut_daily,
                ts_code=ts_code,
                start_date=trade_dates[0],
                end_date=trade_dates[-1]
            )
            
            if not df.empty:
                # 记录数据获取情况
                self.update_status['logs'].append(f"获取到{ts_code}日线数据{len(df)}条")
                
                # 据预处理：处理字段名变化
                df = df.rename(columns={
                    'change1': 'change_rate',  # 涨跌幅
                    'change2': 'price_change'  # 涨跌额
                })
                
                insert_sql = """
                INSERT INTO futures_daily_quotes 
                    (trade_date, ts_code, open, high, low, close, 
                     pre_close, change_rate, vol, amount, oi, oi_chg)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    open = VALUES(open),
                    high = VALUES(high),
                    low = VALUES(low),
                    close = VALUES(close),
                    pre_close = VALUES(pre_close),
                    change_rate = VALUES(change_rate),
                    vol = VALUES(vol),
                    amount = VALUES(amount),
                    oi = VALUES(oi),
                    oi_chg = VALUES(oi_chg)
                """
                
                params = [(
                    row['trade_date'],
                    ts_code,
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    float(row['pre_close']),
                    float(row['change_rate']),  # 使用重命名后的字段
                    float(row['vol']),
                    float(row['amount']),
                    float(row['oi']),
                    float(row['oi_chg'])
                ) for _, row in df.iterrows()]
                
                affected_rows = self.db.execute_many(insert_sql, params)
                self.update_status['logs'].append(f"保存{ts_code}日线数据{affected_rows}条")
                
            else:
                self.update_status['logs'].append(f"未获取到{ts_code}的日线数据")
                
        except Exception as e:
            error_msg = f"处理{ts_code}时出错: {str(e)}"
            self.update_status['logs'].append(error_msg)
            print(error_msg)
            # 打印更详细的错误信息
            import traceback
            traceback.print_exc()

    def _fetch_warehouse_data(self, ts_code, trade_dates):
        """获取仓单数据"""
        try:
            df = self._call_tushare_api(
                self.pro.fut_wsr,
                trade_date=trade_dates[-1]  # 获取最新日期的仓单数据
            )
            
            if not df.empty:
                insert_sql = """
                INSERT INTO futures_warehouse_stocks 
                    (trade_date, ts_code, warehouse, area, stock, unit)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    stock = VALUES(stock),
                    unit = VALUES(unit)
                """
                
                params = [(
                    row['trade_date'],
                    ts_code,
                    row['warehouse'],
                    row.get('area', ''),
                    row['vol'],
                    row.get('unit', '')
                ) for _, row in df.iterrows()]
                
                self.db.execute_many(insert_sql, params)
                
        except Exception as e:
            print(f"Error fetching warehouse data: {str(e)}")

    def _fetch_institution_data(self, ts_code, trade_dates):
        """获取机构持仓数据"""
        try:
            # 获取期货品种代码（去掉月份）
            symbol = ts_code.split('.')[0][:-4]  # 例如从 'C2401.DCE' 提取 'C'
            exchange = ts_code.split('.')[1]     # 获取交易所代码
            
            self.update_status['logs'].append(f"获取{ts_code}机构持仓数据，品种代码：{symbol}")
            
            df = self._call_tushare_api(
                self.pro.fut_holding,
                symbol=symbol,
                start_date=trade_dates[0],
                end_date=trade_dates[-1],
                exchange=exchange
            )
            
            if not df.empty:
                # 记录数据获取情况
                self.update_status['logs'].append(f"获取到{len(df)}条机构持仓记录")
                
                # 数据预处理：处理NaN值
                df = df.fillna(0)
                
                insert_sql = """
                INSERT INTO futures_holding_rank 
                    (trade_date, ts_code, broker, vol, vol_chg, 
                     long_hld, long_chg, short_hld, short_chg)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    vol = VALUES(vol),
                    vol_chg = VALUES(vol_chg),
                    long_hld = VALUES(long_hld),
                    long_chg = VALUES(long_chg),
                    short_hld = VALUES(short_hld),
                    short_chg = VALUES(short_chg)
                """
                
                params = [(
                    row['trade_date'],
                    ts_code,  # 使用完整的合约代码
                    str(row['broker']),  # 确保 broker 是字符串
                    float(row['vol'] or 0),
                    float(row['vol_chg'] or 0),
                    float(row['long_hld'] or 0),
                    float(row['long_chg'] or 0),
                    float(row['short_hld'] or 0),
                    float(row['short_chg'] or 0)
                ) for _, row in df.iterrows()]
                
                affected_rows = self.db.execute_many(insert_sql, params)
                self.update_status['logs'].append(f"更新{affected_rows}条机构持仓记录")
                
            else:
                self.update_status['logs'].append(f"未获取到{ts_code}的机构持仓数据")
                
        except Exception as e:
            error_msg = f"获取机构持仓数据失败: {str(e)}"
            self.update_status['logs'].append(error_msg)
            print(error_msg)

    def _recreate_futures_basic_table(self):
        """重新创建期货基础信息表"""
        try:
            # 先删除旧表
            drop_table_sql = "DROP TABLE IF EXISTS futures_basic"
            self.db.execute_update(drop_table_sql)
            
            # 创建新表
            create_table_sql = """
            CREATE TABLE futures_basic (
                ts_code VARCHAR(20) PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                name VARCHAR(50),
                exchange VARCHAR(10) NOT NULL,
                exchange_name VARCHAR(50),
                fut_code VARCHAR(20),
                trade_type VARCHAR(10),
                list_date VARCHAR(8),
                delist_date VARCHAR(8),
                last_trade_date VARCHAR(8),
                delivery_month VARCHAR(8),
                update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
            self.db.execute_update(create_table_sql)
            return True
        except Exception as e:
            print(f"Error recreating table: {str(e)}")
            return False

    def get_contracts_by_base_name(self, base_name, exchange):
        """根据品种名称取合约"""
        try:
            # 获取当前日期
            today = datetime.datetime.now()
            today_str = today.strftime('%Y%m%d')
            
            # 修改SQL查询，只获取最后交易日大于今天的合约
            sql = """
            SELECT 
                ts_code,
                name,
                list_date,
                delist_date,
                CASE 
                    WHEN ts_code = (
                        SELECT ts_code 
                        FROM futures_basic 
                        WHERE name LIKE %s
                        AND exchange = %s 
                        AND delist_date >= %s
                        ORDER BY ts_code DESC 
                        LIMIT 1
                    ) THEN 'main'
                    WHEN ts_code LIKE '%%L.%%' THEN 'continuous'
                    WHEN ts_code LIKE '%%I.%%' THEN 'index'
                    ELSE 'normal'
                END as contract_type,
                multiplier,
                trade_unit,
                per_unit,
                quote_unit,
                quote_unit_desc
            FROM futures_basic
            WHERE name LIKE %s
            AND exchange = %s
            AND delist_date >= %s
            ORDER BY 
                CASE 
                    WHEN ts_code LIKE '%%I.%%' THEN 1
                    WHEN ts_code LIKE '%%L.%%' THEN 2
                    WHEN ts_code = (
                        SELECT ts_code 
                        FROM futures_basic 
                        WHERE name LIKE %s
                        AND exchange = %s 
                        AND delist_date >= %s
                        ORDER BY ts_code DESC 
                        LIMIT 1
                    ) THEN 3
                    ELSE 4
                END,
                ts_code ASC
            """
            
            name_pattern = f"%{base_name}%"
            params = (
                name_pattern, exchange, today_str,  # 用于主力合约判断
                name_pattern, exchange, today_str,  # 用于WHERE条件
                name_pattern, exchange, today_str   # 用于ORDER BY件
            )
            
            results = self.db.execute_query(sql, params)
            print(f"Found {len(results)} contracts for {base_name}")
            
            contracts = []
            for row in results:
                contract_type = row[4]
                name_suffix = {
                    'main': '(M)',
                    'continuous': '(C)',
                    'index': '(I)'
                }.get(contract_type, '')
                
                # 格式化日期为中文格式
                list_date = datetime.datetime.strptime(row[2], '%Y%m%d').strftime('%Y年%m月%d日') if row[2] else '-'
                delist_date = datetime.datetime.strptime(row[3], '%Y%m%d').strftime('%Y年%m月%d日') if row[3] else '-'
                
                contract_info = {
                    'ts_code': row[0],
                    'name': f"{row[1]}{name_suffix}",
                    'contract_type': contract_type,
                    'list_date': list_date,
                    'delist_date': delist_date,
                    'multiplier': row[5],
                    'trade_unit': row[6],
                    'per_unit': row[7],
                    'quote_unit': row[8],
                    'quote_unit_desc': row[9],
                    'status': '交易中' if row[3] >= today_str else '已到期'
                }
                
                # 添加交易单位说明
                if contract_info['per_unit'] and contract_info['trade_unit']:
                    contract_info['unit_desc'] = f"{contract_info['per_unit']}{contract_info['trade_unit']}/手"
                else:
                    contract_info['unit_desc'] = '-'
                
                contracts.append(contract_info)
            
            return contracts
            
        except Exception as e:
            print(f"获取合约信息失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def fetch_futures_data(self):
        """获取期货数据"""
        if self.is_updating:
            return False
            
        self.is_updating = True
        self.progress = 0
        self.update_status = {
            'current_process': '',
            'updated_count': 0,
            'logs': [],
            'status': 'running'
        }
        
        try:
            # 1. 获取今天的日期
            today = datetime.datetime.now().strftime('%Y%m%d')
            self.update_status['logs'].append(f"开始获取{today}的期货数据...")
            
            # 2. 获取所有未到期的合约
            sql = """
            SELECT ts_code 
            FROM futures_basic 
            WHERE delist_date >= %s
            """
            contracts = self.db.execute_query(sql, (today,))
            total_contracts = len(contracts)
            self.update_status['logs'].append(f"找到{total_contracts}个未到期合约")
            
            # 3. 获取主力合约列表
            sql_main = """
            SELECT DISTINCT ts_code 
            FROM futures_basic 
            WHERE delist_date >= %s 
            AND ts_code IN (
                SELECT ts_code 
                FROM futures_basic 
                WHERE ts_code = (
                    SELECT ts_code 
                    FROM futures_basic 
                    WHERE LEFT(ts_code, LENGTH(ts_code) - 5) = LEFT(ts_code, LENGTH(ts_code) - 5)
                    AND delist_date >= %s
                    ORDER BY ts_code DESC 
                    LIMIT 1
                )
            )
            """
            main_contracts = self.db.execute_query(sql_main, (today, today))
            main_contract_codes = {row[0] for row in main_contracts}
            self.update_status['logs'].append(f"找到{len(main_contract_codes)}个主力合约")
            
            # 4. 获取最近30个交易日历
            trade_dates = self._get_trade_calendar(30)
            self.update_status['logs'].append(f"获取到最近30个交易日")
            
            processed_count = 0
            total_count = len(contracts)
            
            # 5. 处理每个合约
            for ts_code, in contracts:
                if self.cancel_update:
                    break
                
                try:
                    is_main = ts_code in main_contract_codes
                    self.update_status['current_process'] = f"处理{ts_code}{'(主力)' if is_main else ''}"
                    
                    # 5.1 检查日线数据是否存在
                    daily_exists = self._check_daily_data_exists(ts_code, today if not is_main else trade_dates[0])
                    
                    if not daily_exists:
                        # 获取日线数据
                        if is_main:
                            df_daily = self._call_tushare_api(
                                self.pro.fut_daily,
                                ts_code=ts_code,
                                start_date=trade_dates[0],
                                end_date=trade_dates[-1]
                            )
                        else:
                            df_daily = self._call_tushare_api(
                                self.pro.fut_daily,
                                ts_code=ts_code,
                                trade_date=today
                            )
                        
                        if not df_daily.empty:
                            # 处理 None 值和 NaN 值
                            df_daily = df_daily.fillna(0)
                            
                            # 处理涨跌幅字段
                            if 'change1' in df_daily.columns:
                                df_daily['change'] = df_daily['change1'].fillna(0)
                            else:
                                df_daily['change'] = df_daily.apply(
                                    lambda row: ((float(row['close'] or 0) - float(row['pre_close'] or 0)) 
                                               / float(row['pre_close'] or 1) * 100 
                                               if row['pre_close'] else 0),
                                    axis=1
                                ).round(2)
                            
                            # 保存日线数据
                            self._save_daily_data(df_daily, ts_code)
                            self.update_status['logs'].append(f"保存{ts_code}日线数据成功")
                    else:
                        self.update_status['logs'].append(f"{ts_code}日线数据已存在，跳过")
                    
                    # 5.2 如果是主力合约，检查并获取成交持仓数据
                    if is_main:
                        holding_exists = self._check_holding_data_exists(ts_code, today)
                        
                        if not holding_exists:
                            df_holding = self._call_tushare_api(
                                self.pro.fut_holding,
                                ts_code=ts_code,
                                trade_date=today
                            )
                            
                            if not df_holding.empty:
                                # 保存成交持仓数据
                                self._save_holding_data(df_holding, ts_code, today)
                                self.update_status['logs'].append(f"保存{ts_code}成交持仓数据成功")
                        else:
                            self.update_status['logs'].append(f"{ts_code}成交持仓数据存在，跳过")
                    
                    processed_count += 1
                    self.progress = int(processed_count * 100 / total_count)
                    self.update_status['updated_count'] = processed_count
                
                except Exception as e:
                    error_msg = f"处理{ts_code}时出错: {str(e)}"
                    self.update_status['logs'].append(error_msg)
                    print(error_msg)
                    continue
            
            if not self.cancel_update:
                self.update_status['status'] = 'completed'
                self.update_status['logs'].append(f"数据获取完成，共处理{processed_count}个合约")
            
            return True
            
        except Exception as e:
            error_msg = f"数据获取过程发生错误: {str(e)}"
            self.update_status['logs'].append(error_msg)
            self.update_status['status'] = 'error'
            print(error_msg)
            return False
            
        finally:
            self.is_updating = False
            self.cancel_update = False

    def _check_daily_data_exists(self, ts_code, date):
        """检查日线数据是否存在"""
        sql = """
        SELECT COUNT(*) 
        FROM futures_daily_quotes 
        WHERE ts_code = %s AND trade_date = %s
        """
        result = self.db.execute_query(sql, (ts_code, date))
        return result[0][0] > 0 if result else False

    def _check_holding_data_exists(self, ts_code, date):
        """检查成交持仓数据是否存在"""
        sql = """
        SELECT COUNT(*) 
        FROM futures_holding_rank 
        WHERE ts_code = %s AND trade_date = %s
        """
        result = self.db.execute_query(sql, (ts_code, date))
        return result[0][0] > 0 if result else False

    def _save_daily_data(self, df, ts_code):
        """保存日线数据"""
        try:
            # 数据预处理：处理 NaN 值
            df = df.fillna(0)
            
            # 处理涨跌幅字段
            if 'change1' in df.columns:
                df['change'] = df['change1']
            else:
                df['change'] = df.apply(
                    lambda row: ((float(row['close'] or 0) - float(row['pre_close'] or 0)) 
                               / float(row['pre_close'] or 1) * 100 
                               if row['pre_close'] else 0),
                    axis=1
                ).round(2)
            
            insert_sql = """
            INSERT INTO futures_daily_quotes 
                (trade_date, ts_code, open, high, low, close, 
                 pre_close, change_rate, vol, amount, oi, oi_chg)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                open = VALUES(open),
                high = VALUES(high),
                low = VALUES(low),
                close = VALUES(close),
                pre_close = VALUES(pre_close),
                change_rate = VALUES(change_rate),
                vol = VALUES(vol),
                amount = VALUES(amount),
                oi = VALUES(oi),
                oi_chg = VALUES(oi_chg)
            """
            
            params = [(
                row['trade_date'],
                ts_code,
                float(row['open'] or 0),
                float(row['high'] or 0),
                float(row['low'] or 0),
                float(row['close'] or 0),
                float(row['pre_close'] or 0),
                float(row['change'] or 0),
                float(row['vol'] or 0),
                float(row['amount'] or 0),
                float(row['oi'] or 0),
                float(row['oi_chg'] or 0)
            ) for _, row in df.iterrows()]
            
            affected_rows = self.db.execute_many(insert_sql, params)
            self.update_status['logs'].append(f"保存{ts_code}日线数据{affected_rows}条")
            return affected_rows
            
        except Exception as e:
            error_msg = f"保存{ts_code}日线数据时出错: {str(e)}"
            self.update_status['logs'].append(error_msg)
            print(error_msg)
            raise

    def _save_holding_data(self, df, ts_code, trade_date):
        """保存持仓排名数据"""
        try:
            # 数据预处理：处理 NaN 值
            df = df.fillna(0)
            
            insert_sql = """
            INSERT INTO futures_holding_rank 
                (trade_date, ts_code, broker, vol, vol_chg,
                 long_hld, long_chg, short_hld, short_chg)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                vol = VALUES(vol),
                vol_chg = VALUES(vol_chg),
                long_hld = VALUES(long_hld),
                long_chg = VALUES(long_chg),
                short_hld = VALUES(short_hld),
                short_chg = VALUES(short_chg)
            """
            
            params = [(
                trade_date,
                ts_code,
                str(row['broker']),  # 确保 broker 是字符串
                float(row['vol'] or 0),
                float(row['vol_chg'] or 0),
                float(row['long_hld'] or 0),
                float(row['long_chg'] or 0),
                float(row['short_hld'] or 0),
                float(row['short_chg'] or 0)
            ) for _, row in df.iterrows()]
            
            affected_rows = self.db.execute_many(insert_sql, params)
            self.update_status['logs'].append(f"保存{ts_code}持仓排名数据{affected_rows}条")
            return affected_rows
            
        except Exception as e:
            error_msg = f"保存{ts_code}持仓排名数据时出错: {str(e)}"
            self.update_status['logs'].append(error_msg)
            print(error_msg)
            raise

    def fetch_quotes_data(self):
        """获取行情数据"""
        if self.is_updating:
            return False
            
        self.is_updating = True
        self.progress = 0
        self.update_status = {
            'current_process': '',
            'updated_count': 0,
            'logs': [],
            'status': 'running'
        }
        
        try:
            # 1. 获取今天的日期
            today = datetime.datetime.now().strftime('%Y%m%d')
            self.update_status['logs'].append(f"开始获取{today}的行情数据...")
            
            # 2. 获取所有未到期的合约
            sql = """
            SELECT ts_code 
            FROM futures_basic 
            WHERE delist_date >= %s
            """
            contracts = self.db.execute_query(sql, (today,))
            total_contracts = len(contracts)
            self.update_status['logs'].append(f"找到{total_contracts}个未到期合约")
            
            processed_count = 0
            
            # 3. 获取每个合约的行情数据
            for ts_code, in contracts:
                if self.cancel_update:
                    break
                
                try:
                    self.update_status['current_process'] = f"获取{ts_code}行情数据"
                    
                    # 检查数据是否已存在
                    if not self._check_daily_data_exists(ts_code, today):
                        df = self._call_tushare_api(
                            self.pro.fut_daily,
                            ts_code=ts_code,
                            trade_date=today
                        )
                        
                        if not df.empty:
                            self._save_daily_data(df, ts_code)
                            self.update_status['logs'].append(f"保存{ts_code}行情数据成功")
                    else:
                        self.update_status['logs'].append(f"{ts_code}行情数据已存在，跳过")
                    
                    processed_count += 1
                    self.progress = int(processed_count * 100 / total_contracts)
                    self.update_status['updated_count'] = processed_count
                    
                except Exception as e:
                    error_msg = f"处理{ts_code}时出错: {str(e)}"
                    self.update_status['logs'].append(error_msg)
                    print(error_msg)
                    continue
            
            if not self.cancel_update:
                self.update_status['status'] = 'completed'
                self.update_status['logs'].append(f"行情数据获取完成，共处理{processed_count}个合约")
            
            return True
            
        except Exception as e:
            error_msg = f"行情数据获取过程发生错误: {str(e)}"
            self.update_status['logs'].append(error_msg)
            self.update_status['status'] = 'error'
            print(error_msg)
            return False
            
        finally:
            self.is_updating = False
            self.cancel_update = False

    def _get_trading_date(self):
        """获取持仓数据的交易日期"""
        try:
            # 获取当前时间
            now = datetime.datetime.now()
            today = now.strftime('%Y%m%d')
            
            # 获取最近的交易日历
            cal_df = self._call_tushare_api(
                self.pro.trade_cal,
                exchange='DCE',
                end_date=today,
                is_open='1',
                limit=5  # 获取最近5个交易日
            )
            
            if not cal_df.empty:
                # 按日期降序排序
                cal_df = cal_df.sort_values('cal_date', ascending=False)
                
                # 如果今天是交易日且时间在15:30之后，使用今天的日期
                if today in cal_df['cal_date'].values:
                    if now.hour > 15 or (now.hour == 15 and now.minute >= 30):
                        print(f"当前时间满足条件，使用今天的日期：{today}")
                        return today
                    else:
                        print(f"当前时间不满足条件，使用上一个交易日：{cal_df.iloc[1]['cal_date']}")
                        return cal_df.iloc[1]['cal_date']  # 返回上一个交易日
                else:
                    print(f"今天不是交易日，使用最近的���易日：{cal_df.iloc[0]['cal_date']}")
                    return cal_df.iloc[0]['cal_date']  # 返回最近的交易日
                
            print("获取交易日历失败，返回上一个工作日")
            # 如果获取交易日历失败，返回上一个工作日
            yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y%m%d')
            return yesterday
            
        except Exception as e:
            print(f"Error getting trading date: {str(e)}")
            # 发生错误时返回上一个工作日
            yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y%m%d')
            return yesterday

    def fetch_holdings_data(self):
        """获取机构成交持仓数据"""
        if self.is_updating:
            return False
            
        self.is_updating = True
        self.progress = 0
        self.update_status = {
            'current_process': '',
            'updated_count': 0,
            'logs': [],
            'status': 'running'
        }
        
        try:
            # 1. 获取正确的交易日期
            trade_date = self._get_trading_date()
            self.update_status['logs'].append(f"开始获取{trade_date}的机构成交持仓数据...")
            
            # 2. 获取所有主力合约和品种代码
            df_main = self._call_tushare_api(
                self.pro.fut_mapping,
                trade_date=trade_date
            )
            
            if df_main.empty:
                self.update_status['logs'].append("未获取到主力合约数据")
                return False
                
            # 获取主力合约列表
            main_contracts = df_main['mapping_ts_code'].tolist()
            
            # 获取品种代码列表（从主力合约中提取）
            symbols = list(set([code.split('.')[0][:-4] for code in main_contracts]))
            
            # 合并处理列表
            process_list = [
                ('主力合约', main_contracts),
                ('品种', symbols)
            ]
            
            total_items = len(main_contracts) + len(symbols)
            self.update_status['logs'].append(f"找到{len(main_contracts)}个主力合约和{len(symbols)}个品种")
            
            # 打印处理列表
            print("\n=== 数据获取列表 ===")
            print("主力合约:")
            for i, ts_code in enumerate(main_contracts, 1):
                print(f"{i}. {ts_code}")
            print("\n品种代码:")
            for i, symbol in enumerate(symbols, 1):
                print(f"{i}. {symbol}")
            print(f"共计: {total_items}个")
            print("==================\n")
            
            # 3. 处理每个合约和品种
            processed_count = 0
            
            # 3.1 处理主力合约
            for ts_code in main_contracts:
                if self.cancel_update:
                    break
                    
                try:
                    self.update_status['current_process'] = f"处理主力合约: {ts_code}"
                    print(f"正在处理主力合约: {ts_code}")
                    
                    if not self._check_holding_data_exists(ts_code, trade_date):
                        df = self._call_tushare_api(
                            self.pro.fut_holding,
                            ts_code=ts_code,
                            trade_date=trade_date
                        )
                        
                        if not df.empty:
                            self._save_holding_records(df, ts_code, trade_date)
                            print(f"已保存主力合约数据")
                        else:
                            print(f"未获取到持仓数据")
                    else:
                        print(f"数据已存在，跳过")
                    
                    processed_count += 1
                    self.progress = int(processed_count * 100 / total_items)
                    self.update_status['updated_count'] = processed_count
                    print(f"进度: {self.progress}%\n")
                    
                except Exception as e:
                    error_msg = f"处理主力合约{ts_code}时出错: {str(e)}"
                    self.update_status['logs'].append(error_msg)
                    print(error_msg)
                    continue
            
            # 3.2 处理品种代码
            for symbol in symbols:
                if self.cancel_update:
                    break
                    
                try:
                    self.update_status['current_process'] = f"处理品种: {symbol}"
                    print(f"正在处理品种: {symbol}")
                    
                    df = self._call_tushare_api(
                        self.pro.fut_holding,
                        symbol=symbol,
                        trade_date=trade_date
                    )
                    
                    if not df.empty:
                        self._save_holding_records(df, symbol, trade_date)
                        print(f"已保存品种数据")
                    else:
                        print(f"未获取到持仓数据")
                    
                    processed_count += 1
                    self.progress = int(processed_count * 100 / total_items)
                    self.update_status['updated_count'] = processed_count
                    print(f"进度: {self.progress}%\n")
                    
                except Exception as e:
                    error_msg = f"处理品种{symbol}时出错: {str(e)}"
                    self.update_status['logs'].append(error_msg)
                    print(error_msg)
                    continue
            
            if not self.cancel_update:
                self.update_status['status'] = 'completed'
                self.update_status['logs'].append(f"机构成交持仓数据获取完成，共处理{processed_count}个项目")
                print("\n=== 数据获取完成 ===")
                print(f"共处理 {processed_count} 个项目")
                print("==================\n")
                
        except Exception as e:
            error_msg = f"获取机构成交持仓数据失败: {str(e)}"
            self.update_status['logs'].append(error_msg)
            self.update_status['status'] = 'error'
            print(error_msg)
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            self.is_updating = False
            self.cancel_update = False

    def _save_holding_records(self, df, code, trade_date):
        """保存持仓记录"""
        try:
            # 处理 NaN 值
            df = df.fillna(0)
            
            # 保存数据到数据库
            insert_sql = """
            INSERT INTO futures_holding_rank 
                (trade_date, ts_code, broker, vol, vol_chg,
                 long_hld, long_chg, short_hld, short_chg)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                vol = VALUES(vol),
                vol_chg = VALUES(vol_chg),
                long_hld = VALUES(long_hld),
                long_chg = VALUES(long_chg),
                short_hld = VALUES(short_hld),
                short_chg = VALUES(short_chg)
            """
            
            params = [(
                trade_date,
                code,  # 可能是主力合约代码或品种代码
                str(row['broker']),
                float(row['vol']),
                float(row['vol_chg']),
                float(row['long_hld']),
                float(row['long_chg']),
                float(row['short_hld']),
                float(row['short_chg'])
            ) for _, row in df.iterrows()]
            
            affected_rows = self.db.execute_many(insert_sql, params)
            self.update_status['logs'].append(f"保存{code}持仓数据{affected_rows}条")
            return affected_rows
            
        except Exception as e:
            error_msg = f"保存{code}持仓数据时出错: {str(e)}"
            self.update_status['logs'].append(error_msg)
            print(error_msg)
            raise

# 创建全局实例
futures_handler = FuturesDataHandler()
