from flask import Flask, render_template, jsonify, request, Response
import sys
import json
import time
import datetime
sys.path.append('.')  # 添加当前目录到路径
from comm.commFunctions import futures_handler
import pandas as pd

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/filter-contracts/<exchange>')
def get_filter_contracts(exchange):
    try:
        # 获取当前日期
        today = datetime.datetime.now().strftime('%Y%m%d')
        
        # 获取未到期合约的唯一品种代码
        sql = """
        SELECT DISTINCT fut_code
        FROM futures_basic
        WHERE exchange = %s
        AND delist_date >= %s
        AND fut_code IS NOT NULL
        AND fut_code != ''
        ORDER BY fut_code
        """
        
        results = futures_handler.db.execute_query(sql, (exchange, today))
        
        # 转数式
        contracts = [{
            'code': row[0],
            'name': row[0]  # 直接使用 fut_code 作为显示名称
        } for row in results if row[0]]  # 确保 fut_code 不为空
        
        return jsonify({
            'status': 'success',
            'data': contracts
        })
        
    except Exception as e:
        print(f"Error getting filter contracts: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/equity-data', methods=['POST'])
def get_equity_data():
    try:
        data = request.get_json()
        contracts = [contract.upper() for contract in data.get('contracts', [])]
        
        if not contracts:
            return jsonify({
                'status': 'error',
                'message': '未选择合约'
            })
        
        # 获取最新和上一个时间点的数据
        sql = """
        WITH latest_time AS (
            SELECT MAX(PriceTime) as max_time
            FROM tbpricedata
            WHERE TIME(PriceTime) = '14:30:00'
        ),
        previous_time AS (
            SELECT MAX(PriceTime) as prev_time
            FROM tbpricedata
            WHERE TIME(PriceTime) = '14:30:00'
            AND PriceTime < (SELECT max_time FROM latest_time)
        )
        SELECT 
            t.PriceTime,
            t.ProductCode,
            t.Equity
        FROM tbpricedata t
        WHERE t.ProductCode IN %s
        AND t.PriceTime IN (
            (SELECT max_time FROM latest_time),
            (SELECT prev_time FROM previous_time)
        )
        ORDER BY t.PriceTime DESC, t.ProductCode
        """
        
        results = futures_handler.db.execute_query(sql, (tuple(contracts),))
        
        # 处理数据
        latest_data = {'time': None, 'equities': {}}
        previous_data = {'time': None, 'equities': {}}
        
        for row in results:
            time_str = row[0].strftime('%Y-%m-%d %H:%M:%S')
            code = row[1]
            equity = float(row[2] or 0)
            
            if latest_data['time'] is None:
                latest_data['time'] = time_str
                latest_data['equities'][code] = equity
            elif time_str == latest_data['time']:
                latest_data['equities'][code] = equity
            else:
                if previous_data['time'] is None:
                    previous_data['time'] = time_str
                previous_data['equities'][code] = equity
        
        return jsonify({
            'status': 'success',
            'data': {
                'latest_equity': latest_data,
                'previous_equity': previous_data
            }
        })
        
    except Exception as e:
        print(f"Error getting equity data: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/portfolios', methods=['GET'])
def get_portfolios():
    try:
        sql = """
        SELECT id, portfolio_name
        FROM futures_portfolio
        ORDER BY create_time DESC
        """
        
        results = futures_handler.db.execute_query(sql)
        portfolios = [{
            'id': row[0],
            'name': row[1]
        } for row in results]
        
        return jsonify({
            'status': 'success',
            'data': portfolios
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/portfolios', methods=['POST'])
def create_portfolio():
    try:
        data = request.get_json()
        name = data.get('name')
        contracts = data.get('contracts', [])
        
        if not name or not contracts:
            return jsonify({
                'status': 'error',
                'message': '组合名称和合约列表不能为空'
            })
        
        # 始事务
        conn = futures_handler.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查组合是否已存在
            check_sql = "SELECT id FROM futures_portfolio WHERE portfolio_name = %s"
            cursor.execute(check_sql, (name,))
            existing = cursor.fetchone()
            
            if existing:
                portfolio_id = existing[0]
                # 删除旧的约
                delete_sql = "DELETE FROM futures_portfolio_contract WHERE portfolio_id = %s"
                cursor.execute(delete_sql, (portfolio_id,))
                print(f"Updated portfolio {name} (id: {portfolio_id})")
            else:
                # 插入新组合
                insert_portfolio = """
                INSERT INTO futures_portfolio (portfolio_name)
                VALUES (%s)
                """
                cursor.execute(insert_portfolio, (name,))
                portfolio_id = cursor.lastrowid
                print(f"Created new portfolio {name} (id: {portfolio_id})")
            
            # 插入新的合约关系
            insert_contracts = """
            INSERT INTO futures_portfolio_contract (portfolio_id, fut_code)
            VALUES (%s, %s)
            """
            contract_params = [(portfolio_id, code) for code in contracts]
            cursor.executemany(insert_contracts, contract_params)
            print(f"Added {len(contracts)} contracts to portfolio {name}")
            
            conn.commit()
            return jsonify({
                'status': 'success',
                'message': '组合更新成功' if existing else '组创建成功'
            })
            
        except Exception as e:
            conn.rollback()
            print(f"Error saving portfolio: {str(e)}")
            raise
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/portfolios/<int:portfolio_id>/contracts')
def get_portfolio_contracts(portfolio_id):
    try:
        sql = """
        SELECT pc.fut_code
        FROM futures_portfolio_contract pc
        WHERE pc.portfolio_id = %s
        """
        
        results = futures_handler.db.execute_query(sql, (portfolio_id,))
        contracts = [{'fut_code': row[0]} for row in results]
        
        return jsonify({
            'status': 'success',
            'data': contracts
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/portfolios/<int:portfolio_id>', methods=['DELETE'])
def delete_portfolio(portfolio_id):
    try:
        # 由于设置了外键级联删除，只需要删除组合即可
        sql = "DELETE FROM futures_portfolio WHERE id = %s"
        futures_handler.db.execute_update(sql, (portfolio_id,))
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/monitor/portfolio-details/<int:portfolio_id>')
def get_portfolio_details(portfolio_id):
    """获取组合详细信息，包括每个品种的多空方向和最新权益"""
    try:
        sql = """
        SELECT 
            pc.fut_code,
            t2.PriceTime as update_time,
            t2.Equity as current_equity,
            t2.ClosePrice as current_price,
            t2.StopPrice as stop_price
        FROM futures_portfolio_contract pc
        LEFT JOIN (
            SELECT 
                t1.ProductCode,
                t1.PriceTime,
                t1.Equity,
                t1.ClosePrice,
                t1.StopPrice
            FROM tbpricedata t1
            INNER JOIN (
                SELECT 
                    ProductCode,
                    MAX(PriceTime) as max_time
                FROM tbpricedata
                WHERE TIME(PriceTime) = '14:30:00'
                GROUP BY ProductCode
            ) latest ON t1.ProductCode = latest.ProductCode 
            AND t1.PriceTime = latest.max_time
        ) t2 ON t2.ProductCode = pc.fut_code
        WHERE pc.portfolio_id = %s
        """
        
        results = futures_handler.db.execute_query(sql, (portfolio_id,))
        
        details = [{
            'fut_code': row[0],
            'update_time': row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else '-',
            'current_equity': float(row[2]) if row[2] else 0,
            'current_price': float(row[3]) if row[3] else None,
            'stop_price': float(row[4]) if row[4] else None
        } for row in results]
        
        return jsonify({
            'status': 'success',
            'data': details
        })
        
    except Exception as e:
        print(f"Error getting portfolio details: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/monitor/portfolio-stats/<int:portfolio_id>')
def get_portfolio_stats(portfolio_id):
    try:
        # 获取组合包含的合约
        contracts_sql = """
        SELECT fut_code
        FROM futures_portfolio_contract
        WHERE portfolio_id = %s
        """
        contracts = futures_handler.db.execute_query(contracts_sql, (portfolio_id,))
        contract_codes = [code[0].upper() for code in contracts]
        
        # 获取最近20个时
        time_sql = """
        SELECT DISTINCT PriceTime
        FROM tbpricedata
        WHERE ProductCode = %s
        ORDER BY PriceTime DESC
        LIMIT 20
        """
        time_points = futures_handler.db.execute_query(time_sql, (contract_codes[0],))
        
        if not time_points:
            return jsonify({
                'status': 'success',
                'data': []
            })
        
        # 获取这些时间点的所有合约数据
        data_sql = """
        SELECT 
            t1.PriceTime,
            t1.ProductCode,
            COALESCE(
                t1.Equity,
                (
                    SELECT Equity
                    FROM tbpricedata t2
                    WHERE t2.ProductCode = t1.ProductCode
                    AND t2.PriceTime < t1.PriceTime
                    AND t2.Equity IS NOT NULL
                    ORDER BY t2.PriceTime DESC
                    LIMIT 1
                )
            ) as Equity
        FROM tbpricedata t1
        WHERE t1.ProductCode IN %s
        AND t1.PriceTime IN %s
        ORDER BY t1.PriceTime DESC, t1.ProductCode
        """
        
        time_values = tuple(t[0] for t in time_points)
        results = futures_handler.db.execute_query(
            data_sql, 
            (tuple(contract_codes), time_values)
        )
        
        # 处理数据
        stats_data = []
        time_data = {}
        
        # 按时间点组织据
        for row in results:
            time_str = row[0].strftime('%Y-%m-%d %H:%M:%S')
            code = row[1]
            equity = float(row[2] or 0)
            
            if time_str not in time_data:
                time_data[time_str] = {
                    'positions': {},
                    'total_equity': 0,
                    'contracts_count': len(contract_codes),
                    'long_count': 0,
                    'short_count': 0
                }
            
            time_data[time_str]['positions'][code] = equity
            time_data[time_str]['total_equity'] += equity
            
            if equity > 0:
                time_data[time_str]['long_count'] += 1
            elif equity < 0:
                time_data[time_str]['short_count'] += 1
        
        # 计算每个时间点的统计数据
        for time_str in sorted(time_data.keys(), reverse=True):
            point_data = time_data[time_str]
            
            # 计算最大权益和回撤
            max_equity = point_data['total_equity']
            max_equity_time = time_str
            min_equity = point_data['total_equity']
            
            # 遍历当前时间点之前的所有数据来计算最大权益和最小权益
            for t, d in time_data.items():
                if t <= time_str:  # 只考虑当前时间点及之前的数据
                    if d['total_equity'] > max_equity:
                        max_equity = d['total_equity']
                        max_equity_time = t
                    if d['total_equity'] < min_equity:
                        min_equity = d['total_equity']
            
            # 计算回天数
            from datetime import datetime
            current_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            max_time = datetime.strptime(max_equity_time, '%Y-%m-%d %H:%M:%S')
            drawdown_days = (current_time - max_time).days
            
            # 计算回撤百分比
            current_drawdown = 0
            max_drawdown = 0
            if max_equity > 0:
                current_drawdown = ((max_equity - point_data['total_equity']) / max_equity) * 100
                max_drawdown = ((max_equity - min_equity) / max_equity) * 100
            
            stats_data.append({
                'time': time_str,
                'current_equity': point_data['total_equity'],
                'max_equity': max_equity,
                'max_equity_time': max_equity_time,
                'drawdown_days': drawdown_days,
                'current_drawdown': current_drawdown,
                'max_drawdown': max_drawdown,
                'contracts_count': point_data['contracts_count'],
                'long_count': point_data['long_count'],
                'short_count': point_data['short_count']
            })
        
        return jsonify({
            'status': 'success',
            'data': stats_data
        })
        
    except Exception as e:
        print(f"Error getting portfolio stats: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/main-contracts')
def get_main_contracts():
    try:
        today = datetime.datetime.now().strftime('%Y%m%d')
        week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y%m%d')
        month_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')
        
        # 获取最新交易日期
        date_sql = "SELECT MAX(trade_date) FROM futures_daily_quotes"
        latest_date = futures_handler.db.execute_query(date_sql)[0][0]
        print(f"Latest trade date: {latest_date}")
        
        # 简化 SQL 查询，分两步取数据
        # 1. 先获取所有合约基本信息
        basic_sql = """
        SELECT ts_code, name, exchange, fut_code
        FROM futures_basic
        WHERE delist_date >= %s
        """
        
        basic_data = futures_handler.db.execute_query(basic_sql, (today,))
        print(f"Found {len(basic_data)} basic contracts")
        
        # 2. 获这些合约的情数据
        contracts_data = {}
        for row in basic_data:
            ts_code = row[0]
            # 掉连续合约和特殊合约
            if 'L.' in ts_code or '99.' in ts_code:
                continue
                
            quote_sql = """
            SELECT amount, oi
            FROM futures_daily_quotes
            WHERE ts_code = %s AND trade_date = %s
            """
            quote_data = futures_handler.db.execute_query(quote_sql, (ts_code, latest_date))
            
            if quote_data:
                amount = float(quote_data[0][0] or 0)
                oi = float(quote_data[0][1] or 0)
                score = amount * 0.4 + oi * 0.6
                
                base_code = ts_code.split('.')[0][:-4]
                contract_data = {
                    'ts_code': ts_code,
                    'name': row[1],
                    'exchange': row[2],
                    'fut_code': row[3],
                    'score': score
                }
                
                if base_code not in contracts_data or score > contracts_data[base_code]['score']:
                    contracts_data[base_code] = contract_data
        
        # 获取主力合约详细数据
        contracts = []
        for contract in contracts_data.values():
            ts_code = contract['ts_code']
            
            # 取新行情数据
            latest_sql = """
            SELECT amount, high, low, pre_close, close, vol, oi
            FROM futures_daily_quotes
            WHERE ts_code = %s AND trade_date = %s
            """
            
            # 获取周数据（5个交易日）
            week_sql = """
            SELECT 
                SUM(amount) as total_amount,
                MAX(high) as max_price,
                MIN(low) as min_price
            FROM (
                SELECT amount, high, low
                FROM futures_daily_quotes
                WHERE ts_code = %s
                AND trade_date <= %s
                ORDER BY trade_date DESC
                LIMIT 5
            ) t
            """
            
            # 获取月数据（22个交易日）
            month_sql = """
            SELECT 
                SUM(amount) as total_amount,
                MAX(high) as max_price,
                MIN(low) as min_price
            FROM (
                SELECT amount, high, low
                FROM futures_daily_quotes
                WHERE ts_code = %s
                AND trade_date <= %s
                ORDER BY trade_date DESC
                LIMIT 22
            ) t
            """
            
            latest_data = futures_handler.db.execute_query(latest_sql, (ts_code, latest_date))
            week_data = futures_handler.db.execute_query(week_sql, (ts_code, latest_date))
            month_data = futures_handler.db.execute_query(month_sql, (ts_code, latest_date))
            
            if latest_data and latest_data[0]:
                latest = latest_data[0]
                week = week_data[0] if week_data else (0, 0, 0)
                month = month_data[0] if month_data else (0, 0, 0)
                
                # 计算日振
                latest_amplitude = ((float(latest[1] or 0) - float(latest[2] or 0)) / float(latest[3] or 1)) * 100 if latest[3] else 0
                
                # 计算周振幅（5日最高最低价之差/最低价）
                week_min_price = float(week[2] or 0)
                week_max_price = float(week[1] or 0)
                week_amplitude = ((week_max_price - week_min_price) / week_min_price * 100) if week_min_price > 0 else 0
                
                # 计算月振幅（22日最高最低价之差/最低价）
                month_min_price = float(month[2] or 0)
                month_max_price = float(month[1] or 0)
                month_amplitude = ((month_max_price - month_min_price) / month_min_price * 100) if month_min_price > 0 else 0
                
                # 计算价格百分位
                price_position = 0
                if month_max_price > month_min_price:
                    current_price = float(latest[4] or 0)
                    price_position = ((current_price - month_min_price) / (month_max_price - month_min_price)) * 100
                
                contracts.append({
                    'ts_code': ts_code,
                    'name': contract['name'],
                    'exchange': contract['exchange'],
                    'fut_code': contract['fut_code'],
                    'latest_amount': float(latest[0] or 0) / 10000,  # 转换为亿
                    'latest_amplitude': latest_amplitude,
                    'close_price': float(latest[4] or 0),
                    'volume': float(latest[5] or 0),  # 成交量
                    'oi': float(latest[6] or 0),  # 持仓量
                    'week_amount': float(week[0] or 0) / 10000,  # 转换为亿
                    'week_amplitude': week_amplitude,  # 周振幅
                    'month_amount': float(month[0] or 0) / 10000,  # 转换为亿
                    'month_amplitude': month_amplitude,  # 月振幅
                    'month_low': month_min_price,
                    'month_high': month_max_price,
                    'price_position': price_position
                })
        
        return jsonify({
            'status': 'success',
            'data': contracts
        })
        
    except Exception as e:
        print(f"Error getting main contracts: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/contract-details/<ts_code>')
def get_contract_details(ts_code):
    try:
        # 获取最近10个交易日的数据
        history_sql = """
        SELECT 
            trade_date,
            close,
            pre_close,
            amount,
            oi
        FROM futures_daily_quotes
        WHERE ts_code = %s COLLATE utf8mb4_general_ci
        ORDER BY trade_date DESC
        LIMIT 10
        """
        
        history_data = futures_handler.db.execute_query(history_sql, (ts_code,))
        
        # 计算每日涨跌幅
        daily_data = []
        for row in reversed(history_data):  # 反转数据使其按时间正序
            change_rate = ((float(row[1] or 0) - float(row[2] or 0)) / float(row[2] or 1)) * 100 if row[2] else 0
            daily_data.append({
                'date': row[0].strftime('%m/%d'),
                'close': float(row[1] or 0),
                'change_rate': change_rate,
                'amount': float(row[3] or 0) / 10000,  # 转换为亿
                'oi': float(row[4] or 0)
            })
        
        # 获取相关合约
        base_code = ts_code.split('.')[0]
        product_code = ''
        for char in base_code:
            if not char.isdigit():
                product_code += char
            else:
                break
        
        exchange = ts_code.split('.')[1]
        today = datetime.datetime.now().strftime('%Y%m%d')
        
        # 简化的相关合约查询
        contracts_sql = """
        SELECT 
            b.ts_code,
            b.delist_date,
            q.close,
            q.amount,
            q.oi
        FROM futures_basic b
        LEFT JOIN futures_daily_quotes q ON b.ts_code COLLATE utf8mb4_general_ci = q.ts_code
        WHERE b.exchange COLLATE utf8mb4_general_ci = %s
        AND b.delist_date >= %s
        AND b.ts_code REGEXP %s
        AND b.ts_code NOT LIKE '%%L.%%'
        AND b.ts_code NOT LIKE '%%99.%%'
        ORDER BY b.ts_code
        """
        
        # 构建正则表达式，确保只匹配完全相同的品种代码
        regex_pattern = f"^{product_code}[0-9]"
        
        contracts = futures_handler.db.execute_query(
            contracts_sql, 
            (exchange, today, regex_pattern)
        )
        
        # 转换数据
        related_contracts = []
        for row in contracts:
            if row[0] != ts_code:  # 排除当前合约
                # 处理日期格式
                delist_date = row[1]
                if isinstance(delist_date, datetime.datetime):
                    delist_date = delist_date.strftime('%Y-%m-%d')
                elif isinstance(delist_date, str):
                    delist_date = f"{delist_date[:4]}-{delist_date[4:6]}-{delist_date[6:]}"
                
                related_contracts.append({
                    'ts_code': row[0],
                    'delist_date': delist_date,
                    'close': float(row[2] or 0),
                    'amount': float(row[3] or 0) / 10000,  # 转换为亿
                    'oi': float(row[4] or 0)
                })
        
        # 按合约代码排序
        related_contracts.sort(key=lambda x: x['ts_code'])
        
        return jsonify({
            'status': 'success',
            'data': {
                'daily_data': daily_data,
                'related_contracts': related_contracts
            }
        })
        
    except Exception as e:
        print(f"Error getting contract details: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

# 在 app.py 中添加一个函数来判断是否是主力合约
def is_main_contract(ts_code, latest_date):
    try:
        # 获取该品种所有合约的成交额持仓量
        base_code = ts_code.split('.')[0][:-4]  # 提取品种代码
        exchange = ts_code.split('.')[1]
        
        sql = """
        SELECT b.ts_code, q.amount, q.oi
        FROM futures_basic b
        JOIN futures_daily_quotes q ON b.ts_code = q.ts_code
        WHERE b.exchange = %s
        AND LEFT(b.ts_code, LENGTH(%s)) = %s
        AND q.trade_date = %s
        AND b.ts_code NOT LIKE '%%L.%%'
        AND b.ts_code NOT LIKE '%%99.%%'
        """
        
        results = futures_handler.db.execute_query(sql, (exchange, base_code, base_code, latest_date))
        
        # 计算每个合约的得分（成交40%，持仓量60%）
        max_score = 0
        main_ts_code = None
        
        for row in results:
            contract_ts_code = row[0]
            amount = float(row[1] or 0)
            oi = float(row[2] or 0)
            score = amount * 0.4 + oi * 0.6
            
            if score > max_score:
                max_score = score
                main_ts_code = contract_ts_code
        
        return ts_code == main_ts_code
        
    except Exception as e:
        print(f"Error checking main contract: {str(e)}")
        return False

# 添加交易日判断函数
def is_trading_day(date_str):
    # 转换为datetime对象
    date = datetime.datetime.strptime(date_str, '%Y%m%d')
    
    # 周末不是交易日
    if date.weekday() >= 5:  # 5是周六，6是周日
        return False
        
    # TODO: 后续可以添加节假日判断
    return True

def get_latest_trading_day():
    now = datetime.datetime.now()
    
    # 如果当前时间早于15:30，使用前一个交易日
    if now.hour < 15 or (now.hour == 15 and now.minute < 30):
        check_date = now - datetime.timedelta(days=1)
    else:
        check_date = now
    
    # 往前查找直到找到交易日
    while not is_trading_day(check_date.strftime('%Y%m%d')):
        check_date = check_date - datetime.timedelta(days=1)


    return check_date.strftime('%Y%m%d')

# 修改行情数据更新函数
@app.route('/api/update-quotes', methods=['GET', 'POST'])
def update_quotes():
    try:
        if futures_handler.is_updating:
            return jsonify({
                'status': 'error',
                'message': '另一个更新任务正在进行中'
            })
        
        futures_handler.is_updating = True
        futures_handler.cancel_update = False
        futures_handler.update_status = {
            'status': 'running',
            'progress': 0,
            'current_process': '',
            'logs': [],
            'updated_count': 0
        }
        
        # 获取当前时间
        now = datetime.datetime.now()
        
        # 使用 get_latest_trading_day 获取最新交易日
        latest_available_date = get_latest_trading_day()
        print(f"Latest trading day determined: {latest_available_date}")
        
        # 获取数据库中的最新交易日期
        latest_date_sql = "SELECT MAX(trade_date) FROM futures_daily_quotes"
        db_latest_date = futures_handler.db.execute_query(latest_date_sql)[0][0]
        db_latest_date_str = db_latest_date.strftime('%Y%m%d') if db_latest_date else None
        
        print(f"Database latest date: {db_latest_date_str}")
        print(f"Latest available date: {latest_available_date}")
        
        # 如果数据库已经是最新的，不需要更新
        if db_latest_date_str == latest_available_date:
            futures_handler.update_status['status'] = 'completed'
            futures_handler.update_status['logs'].append("数据库已经是最新的，需更新")
            return jsonify({'status': 'success', 'message': '数据已是最新'})
        
        # 获取所有未到的合约
        contracts_sql = """
        SELECT ts_code, 
               (SELECT MAX(trade_date) 
                FROM futures_daily_quotes 
                WHERE ts_code = b.ts_code) as last_update_date
        FROM futures_basic b
        WHERE delist_date >= CURDATE()
        """
        contracts = futures_handler.db.execute_query(contracts_sql)
        
        total_contracts = len(contracts)
        processed_count = 0
        updated_count = 0
        
        for row in contracts:
            if futures_handler.cancel_update:
                break
                
            ts_code = row[0]
            last_update = row[1]
            last_update_str = last_update.strftime('%Y%m%d') if last_update else None
            
            futures_handler.update_status['current_process'] = f"处理合约: {ts_code}"
            
            try:
                # 检查是否需要更新
                if last_update_str == latest_available_date:
                    print(f"{ts_code} 数据已是最新")
                    processed_count += 1
                    futures_handler.progress = int(processed_count * 100 / total_contracts)
                    continue
                
                # 检查是否是主力合约
                is_main = is_main_contract(ts_code, last_update)
                
                if is_main:
                    # 主力合约：检查最���30个交易日的数据是否完整
                    check_date = (now - datetime.timedelta(days=45)).strftime('%Y%m%d')
                    start_date = check_date
                else:
                    # 非主力合约：只获取缺失的最新数据
                    start_date = (last_update + datetime.timedelta(days=1)).strftime('%Y%m%d') if last_update else latest_available_date
                
                end_date = latest_available_date
                print(f"获取{ts_code}的数据: {start_date} 到 {end_date}" + ("（主力合约）" if is_main else ""))
                
                # 有在需要更新数据时才调用API
                if start_date <= end_date:
                    df = futures_handler._call_tushare_api(
                        futures_handler.pro.fut_daily,
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if not df.empty:
                        print(f"获取到{ts_code}的{len(df)}条据")
                        # 保存数据
                        insert_sql = """
                        INSERT INTO futures_daily_quotes 
                            (ts_code, trade_date, open, high, low, close, 
                             pre_close, change_rate, vol, amount, oi)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            open = VALUES(open),
                            high = VALUES(high),
                            low = VALUES(low),
                            close = VALUES(close),
                            pre_close = VALUES(pre_close),
                            change_rate = VALUES(change_rate),
                            vol = VALUES(vol),
                            amount = VALUES(amount),
                            oi = VALUES(oi)
                        """
                        
                        params = [(
                            row['ts_code'],
                            row['trade_date'],
                            row['open'],
                            row['high'],
                            row['low'],
                            row['close'],
                            row['pre_close'],
                            row['change'],
                            row['vol'],
                            row['amount'],
                            row['oi']
                        ) for _, row in df.iterrows()]
                        
                        futures_handler.db.execute_many(insert_sql, params)
                        futures_handler.update_status['logs'].append(
                            f"更新{ts_code}数据{len(params)}条" + 
                            ("（主力合约）" if is_main else "")
                        )
                        updated_count += 1
                    else:
                        print(f"未获取到{ts_code}的数据")
                else:
                    print(f"{ts_code}数据已是最新")
                
                processed_count += 1
                futures_handler.progress = int(processed_count * 100 / total_contracts)
                futures_handler.update_status['updated_count'] = updated_count
                
            except Exception as e:
                error_msg = f"处理合约{ts_code}时出错: {str(e)}"
                futures_handler.update_status['logs'].append(error_msg)
                print(error_msg)
                continue
        
        if not futures_handler.cancel_update:
            futures_handler.update_status['status'] = 'completed'
            futures_handler.update_status['logs'].append(
                f"行情数据更新完成，共处理{processed_count}个合约，更新{updated_count}个合约"
            )
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        futures_handler.update_status['status'] = 'error'
        futures_handler.update_status['logs'].append(f"更新失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})
        
    finally:
        futures_handler.is_updating = False
        futures_handler.cancel_update = False


# 修改行情数据更新函数
@app.route('/api/fetch-mainquotes', methods=['GET', 'POST'])
def fetch_main_quotes():
    print("btn clicked")
    pass

@app.route('/api/monitor/chart-data/<portfolio_id>')
def get_monitor_chart_data(portfolio_id):
    try:
        # 1. 获取组合包含的品种
        contracts_sql = """
        SELECT fut_code
        FROM futures_portfolio_contract
        WHERE portfolio_id = %s
        """
        contracts = futures_handler.db.execute_query(contracts_sql, (portfolio_id,))
        contract_codes = [code[0].upper() for code in contracts]
        
        print(f"Found contracts: {contract_codes}")  # 调��日志
        
        if not contract_codes:
            print("No contracts found")  # 调试日志
            return jsonify({
                'status': 'success',
                'data': {
                    'chart_data': [],
                    'statistics': None
                }
            })
            
        # 2. 获取最近90个交易日14:30的数据 - 修改表名为 tbpricedata
        data_sql = """
        WITH time_points AS (
            SELECT DISTINCT PriceTime
            FROM tbpricedata
            WHERE TIME(PriceTime) = '14:30:00'
            AND PriceTime >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            ORDER BY PriceTime
        )
        SELECT 
            t1.PriceTime,
            t1.ProductCode,
            COALESCE(t1.Equity, 1000000) as Equity
        FROM time_points tp
        CROSS JOIN (
            SELECT DISTINCT ProductCode
            FROM tbpricedata
            WHERE ProductCode IN %s
        ) products
        LEFT JOIN tbpricedata t1 
            ON t1.PriceTime = tp.PriceTime 
            AND t1.ProductCode = products.ProductCode
        ORDER BY t1.PriceTime, t1.ProductCode
        """
        
        print(f"Executing query for contracts: {contract_codes}")
        results = futures_handler.db.execute_query(data_sql, (tuple(contract_codes),))
        print(f"Query returned {len(results)} rows")
        
        # 3. 处理数据,按时间点汇总权益
        chart_data = {}
        base_equity = len(contract_codes) * 1000000  # 计算基准权益
        
        for row in results:
            if row[0] is None:  # 跳过无效数据
                continue
                
            time_str = row[0].strftime('%Y-%m-%d %H:%M:%S')
            equity = float(row[2] or 1000000)  # 如果没有数据使用初始资金
            
            if time_str not in chart_data:
                chart_data[time_str] = 0
            chart_data[time_str] += equity
        
        # 4. 计算统计指标
        sorted_data = sorted(chart_data.items())
        times = [item[0] for item in sorted_data]
        values = [item[1] for item in sorted_data]
        
        if not times:  # 如果没有数据，返回空结果
            return jsonify({
                'status': 'success',
                'data': {
                    'chart_data': [],
                    'statistics': None
                }
            })
        
        # 计算最大权益和时间
        max_equity = max(values)
        max_equity_index = values.index(max_equity)
        max_equity_time = times[max_equity_index]
        
        # 计算当前权益和回撤
        current_equity = values[-1] if values else 0
        current_drawdown = ((max_equity - current_equity) / base_equity) * 100 if max_equity > 0 else 0
        
        # 计算最大回撤
        max_drawdown = 0
        min_equity = min(values) if values else 0
        if max_equity > 0:
            max_drawdown = ((max_equity - min_equity) / base_equity) * 100
        
        # 计算回撤天数
        drawdown_days = 0
        if max_equity_index < len(times) - 1:
            max_time = datetime.datetime.strptime(max_equity_time, '%Y-%m-%d %H:%M:%S')
            current_time = datetime.datetime.strptime(times[-1], '%Y-%m-%d %H:%M:%S')
            drawdown_days = (current_time - max_time).days
        
        # 5. 转换为图表所需格式
        data = {
            'chart_data': [{
                'time': time_str,
                'equity': value
            } for time_str, value in sorted_data],
            'statistics': {
                'max_equity': max_equity,
                'max_equity_time': max_equity_time,
                'current_equity': current_equity,
                'min_equity': min_equity,
                'current_drawdown': current_drawdown,
                'max_drawdown': max_drawdown,
                'drawdown_days': drawdown_days,
                'base_equity': base_equity
            }
        }
        
        print(f"Processed {len(data['chart_data'])} data points")
        print(f"Statistics: {data['statistics']}")  # 调试信息
        
        return jsonify({
            'status': 'success',
            'data': data
        })
        
    except Exception as e:
        print(f"Error getting chart data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/track/component-curves', methods=['POST'])
def get_component_curves():
    try:
        data = request.get_json()
        components = [comp.lower() for comp in data.get('components', [])]  # 转换为小写
        
        if not components:
            return jsonify({
                'status': 'error',
                'message': '未选择品种'
            })
            
        # 修改查询范围为365天
        curves_sql = """
        SELECT 
            PriceTime,
            ProductCode,
            Equity
        FROM tbpricedata
        WHERE LOWER(ProductCode) IN %s
        AND TIME(PriceTime) = '14:30:00'
        AND PriceTime >= DATE_SUB(NOW(), INTERVAL 365 DAY)
        ORDER BY PriceTime, ProductCode
        """
        
        results = futures_handler.db.execute_query(curves_sql, (tuple(components),))
        
        # 处理数据
        times = []
        curves = {component.upper(): [] for component in components}  # 使用大写作为键
        statistics = {component.upper(): {  # 使用大写作为键
            'current_equity': 0,
            'max_equity': 0,
            'max_equity_time': None,
            'current_drawdown': 0,
            'max_drawdown': 0,
            'drawdown_days': 0
        } for component in components}
        
        for row in results:
            time_str = row[0].strftime('%Y-%m-%d %H:%M:%S')
            component = row[1].upper()  # 转换为大写
            equity = float(row[2] or 0)
            
            if time_str not in times:
                times.append(time_str)
            
            if component.lower() in components:  # 使用小写比较
                curves[component].append(equity)
                
                # 更新统计数据
                stats = statistics[component]
                if equity > stats['max_equity']:
                    stats['max_equity'] = equity
                    stats['max_equity_time'] = time_str
                
                stats['current_equity'] = equity
                if stats['max_equity'] > 0:
                    current_drawdown = ((stats['max_equity'] - equity) / stats['max_equity']) * 100
                    stats['current_drawdown'] = current_drawdown
                    stats['max_drawdown'] = max(stats['max_drawdown'], current_drawdown)
                
                if stats['max_equity_time']:
                    max_time = datetime.datetime.strptime(stats['max_equity_time'], '%Y-%m-%d %H:%M:%S')
                    current_time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                    stats['drawdown_days'] = (current_time - max_time).days
        
        return jsonify({
            'status': 'success',
            'data': {
                'times': times,
                'components': [comp.upper() for comp in components],  # 返回大写的品种代码
                'curves': curves,
                'statistics': statistics
            }
        })
        
    except Exception as e:
        print(f"Error getting component curves: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/track/portfolio-curves', methods=['POST'])
def get_portfolio_curves():
    try:
        data = request.get_json()
        portfolio_ids = data.get('portfolios', [])
        
        if not portfolio_ids:
            return jsonify({
                'status': 'error',
                'message': '未选择组合'
            })
        
        # 获取组合名称
        portfolios_sql = """
        SELECT id, portfolio_name
        FROM futures_portfolio
        WHERE id IN %s
        """
        
        portfolio_results = futures_handler.db.execute_query(
            portfolios_sql, 
            (tuple(portfolio_ids),)
        )
        
        portfolio_names = {str(row[0]): row[1] for row in portfolio_results}
        
        # 获取组合的资金曲线数据
        curves_data = {}
        statistics = {}
        all_times = set()
        
        for portfolio_id in portfolio_ids:
            # 获取组合包含的品种
            contracts_sql = """
            SELECT fut_code
            FROM futures_portfolio_contract
            WHERE portfolio_id = %s
            """
            
            contracts = futures_handler.db.execute_query(contracts_sql, (portfolio_id,))
            contract_codes = [code[0].upper() for code in contracts]
            
            if not contract_codes:
                continue
            
            # 修改查询范围为365天
            curves_sql = """
            SELECT 
                PriceTime,
                ProductCode,
                COALESCE(Equity, 1000000) as equity
            FROM tbpricedata
            WHERE ProductCode IN %s
            AND TIME(PriceTime) = '14:30:00'
            AND PriceTime >= DATE_SUB(NOW(), INTERVAL 365 DAY)
            ORDER BY PriceTime
            """
            
            results = futures_handler.db.execute_query(curves_sql, (tuple(contract_codes),))
            
            # 处理数据
            portfolio_curve = {}
            max_equity = 0  # 改为 0 而不是 -inf
            max_equity_time = None
            
            for row in results:
                time_str = row[0].strftime('%Y-%m-%d %H:%M:%S')
                equity = float(row[2] or 0)
                
                all_times.add(time_str)
                
                if time_str not in portfolio_curve:
                    portfolio_curve[time_str] = 0
                portfolio_curve[time_str] += equity
                
                if portfolio_curve[time_str] > max_equity:
                    max_equity = portfolio_curve[time_str]
                    max_equity_time = time_str
            
            # 计算统计数据
            portfolio_name = portfolio_names[str(portfolio_id)]
            current_equity = portfolio_curve[max(portfolio_curve.keys())] if portfolio_curve else 0
            
            current_drawdown = 0
            max_drawdown = 0
            drawdown_days = 0
            
            if max_equity > 0:
                current_drawdown = ((max_equity - current_equity) / max_equity) * 100
                max_drawdown = current_drawdown
                
                if max_equity_time:
                    max_time = datetime.datetime.strptime(max_equity_time, '%Y-%m-%d %H:%M:%S')
                    current_time = datetime.datetime.strptime(max(portfolio_curve.keys()), '%Y-%m-%d %H:%M:%S')
                    drawdown_days = (current_time - max_time).days
            
            curves_data[portfolio_name] = portfolio_curve
            statistics[portfolio_name] = {
                'current_equity': current_equity,
                'max_equity': max_equity,
                'max_equity_time': max_equity_time,
                'current_drawdown': current_drawdown,
                'max_drawdown': max_drawdown,
                'drawdown_days': drawdown_days
            }
        
        # 整理时间序列
        sorted_times = sorted(all_times)
        
        # 整理曲线数据
        curves = {
            name: [curve.get(t, None) for t in sorted_times]
            for name, curve in curves_data.items()
        }
        
        return jsonify({
            'status': 'success',
            'data': {
                'times': sorted_times,
                'portfolios': list(portfolio_names.values()),
                'curves': curves,
                'statistics': statistics
            }
        })
        
    except Exception as e:
        print(f"Error getting portfolio curves: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/portfolios/<int:portfolio_id>/contracts/details')
def get_portfolio_contracts_details(portfolio_id):
    try:
        # 简化SQL查询，直接从 futures_portfolio_contract 表获取数据
        sql = """
        SELECT fut_code
        FROM futures_portfolio_contract
        WHERE portfolio_id = %s
        ORDER BY fut_code
        """
        
        results = futures_handler.db.execute_query(sql, (portfolio_id,))
        contracts = [{
            'fut_code': row[0].upper()  # 只返回品种代��，转换为大写
        } for row in results]
        
        return jsonify({
            'status': 'success',
            'data': contracts
        })
    except Exception as e:
        print(f"Error getting portfolio contracts: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/portfolio-history/<int:portfolio_id>')
def get_portfolio_history(portfolio_id):
    try:
        # 获取组合包含的品种
        contracts_sql = """
        SELECT fut_code
        FROM futures_portfolio_contract
        WHERE portfolio_id = %s
        """
        
        contracts = futures_handler.db.execute_query(contracts_sql, (portfolio_id,))
        contract_codes = [code[0].upper() for code in contracts]
        
        if not contract_codes:
            return jsonify({
                'status': 'success',
                'data': []
            })
        
        # 获取最近20条权益记录
        history_sql = """
        SELECT 
            t1.PriceTime,
            t1.ProductCode,
            t1.Equity
        FROM tbpricedata t1
        INNER JOIN (
            SELECT DISTINCT PriceTime
            FROM tbpricedata
            WHERE ProductCode IN %s
            AND TIME(PriceTime) = '14:30:00'
            ORDER BY PriceTime DESC
            LIMIT 20
        ) t2 ON t1.PriceTime = t2.PriceTime
        WHERE t1.ProductCode IN %s
        ORDER BY t1.PriceTime DESC, t1.ProductCode
        """
        
        results = futures_handler.db.execute_query(
            history_sql, 
            (tuple(contract_codes), tuple(contract_codes))
        )
        
        # 处理数据
        history_data = {}
        for row in results:
            time_str = row[0].strftime('%Y-%m-%d %H:%M:%S')
            equity = float(row[2] or 0)
            
            if time_str not in history_data:
                history_data[time_str] = 0
            history_data[time_str] += equity
        
        # 转换为列表格式
        history_list = [{
            'time': time_str,
            'total_equity': total_equity
        } for time_str, total_equity in history_data.items()]
        
        return jsonify({
            'status': 'success',
            'data': history_list
        })
        
    except Exception as e:
        print(f"Error getting portfolio history: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/initial-equity-data')
def get_initial_equity_data():
    try:
        # 1. 获取最新和次新的时间点
        time_sql = """
        SELECT DISTINCT PriceTime
        FROM tbpricedata
        WHERE TIME(PriceTime) = '14:30:00'
        ORDER BY PriceTime DESC
        LIMIT 2
        """
        
        time_points = futures_handler.db.execute_query(time_sql)
        if len(time_points) < 2:
            return jsonify({
                'status': 'success',
                'data': {
                    'latest_equity': {'time': None, 'equities': {}},
                    'previous_equity': {'time': None, 'equities': {}}
                }
            })
            
        latest_time = time_points[0][0]
        previous_time = time_points[1][0]
        
        # 2. 获取一年前的基准数据
        base_sql = """
        SELECT 
            ProductCode,
            Equity
        FROM tbpricedata
        WHERE PriceTime = (
            SELECT MAX(PriceTime)
            FROM tbpricedata
            WHERE TIME(PriceTime) = '14:30:00'
            AND PriceTime <= DATE_SUB(%s, INTERVAL 365 DAY)
        )
        AND Equity IS NOT NULL
        """
        
        base_results = futures_handler.db.execute_query(base_sql, (latest_time,))
        base_equities = {row[0]: float(row[1] or 0) for row in base_results}
        
        # 3. 获取最新和次新的权益数据
        data_sql = """
        SELECT 
            t1.PriceTime,
            t1.ProductCode,
            t1.Equity
        FROM tbpricedata t1
        WHERE t1.PriceTime IN (%s, %s)
        AND TIME(t1.PriceTime) = '14:30:00'
        AND t1.Equity IS NOT NULL
        ORDER BY t1.PriceTime DESC, t1.ProductCode
        """
        
        results = futures_handler.db.execute_query(
            data_sql, 
            (latest_time, previous_time)
        )
        
        # 4. 处理数据并进行归一化
        latest_data = {
            'time': latest_time.strftime('%Y-%m-%d %H:%M:%S'), 
            'equities': {}
        }
        previous_data = {
            'time': previous_time.strftime('%Y-%m-%d %H:%M:%S'), 
            'equities': {}
        }
        
        for row in results:
            time_str = row[0].strftime('%Y-%m-%d %H:%M:%S')
            code = row[1]
            equity = float(row[2] or 0)
            
            # 如果有基准值，进行归一化处理
            if code in base_equities:
                normalized_equity = equity - base_equities[code] + 1000000
            else:
                # 新品种直接使用原始值
                normalized_equity = equity
            
            if time_str == latest_data['time']:
                latest_data['equities'][code] = normalized_equity
            else:
                previous_data['equities'][code] = normalized_equity
        
        # 5. 按权益值从大到小排序
        latest_data['equities'] = dict(sorted(
            latest_data['equities'].items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        previous_data['equities'] = dict(sorted(
            previous_data['equities'].items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        print(f"Found {len(latest_data['equities'])} latest records and {len(previous_data['equities'])} previous records")
        
        return jsonify({
            'status': 'success',
            'data': {
                'latest_equity': latest_data,
                'previous_equity': previous_data
            }
        })
        
    except Exception as e:
        print(f"Error getting initial equity data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(
        host='127.0.0.1',  # 允许外部访问 1
        port=5000,       # 指定端口号
        debug=True       # 开发模式下保持 debug=True
    ) 