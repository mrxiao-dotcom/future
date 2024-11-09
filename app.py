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

@app.route('/api/fetch-data', methods=['POST'])
def fetch_data():
    data_type = request.form.get('data_type')
    date = request.form.get('date')
    
    try:
        if data_type == 'quote':
            data = futures_handler.get_futures_quotes(date)
        elif data_type == 'position':
            data = futures_handler.get_futures_positions(date)
        else:
            return jsonify({'status': 'error', 'message': '无效的数据类型'})
        
        # 转换为DataFrame后再转为字典列表
        df = pd.DataFrame(data)
        return jsonify({
            'status': 'success',
            'data': df.to_dict('records')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/filter-futures', methods=['POST'])
def filter_futures():
    filters = {
        'change_min': request.form.get('change_min', type=float),
        'change_max': request.form.get('change_max', type=float),
        'volume_min': request.form.get('volume_min', type=float),
        'volume_max': request.form.get('volume_max', type=float)
    }
    
    try:
        data = futures_handler.get_filtered_futures(filters)
        df = pd.DataFrame(data)
        return jsonify({
            'status': 'success',
            'data': df.to_dict('records')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/futures-data/<code>', methods=['GET'])
def get_futures_data(code):
    try:
        data = futures_handler.get_futures_history(code)
        df = pd.DataFrame(data)
        return jsonify({
            'status': 'success',
            'data': df.to_dict('records')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/update-futures', methods=['POST'])
def update_futures():
    try:
        futures_handler.update_futures_basic()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/update-progress')
def update_progress():
    def generate():
        while True:
            progress = futures_handler.get_update_progress()
            data = json.dumps({'progress': progress})
            yield f"data: {data}\n\n"
            if progress >= 100:
                break
            time.sleep(0.5)
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/cancel-update', methods=['POST'])
def cancel_update():
    try:
        if futures_handler.cancel_update_process():
            return jsonify({'status': 'success', 'message': '更新已取消'})
        return jsonify({'status': 'error', 'message': '当前没有正在进行的更新'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/update-status')
def get_update_status():
    status = futures_handler.get_update_status()
    return jsonify(status)

@app.route('/api/futures-by-exchange')
def get_futures_by_exchange():
    try:
        data = futures_handler.get_futures_by_exchange()
        return jsonify({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/contracts/<base_name>/<exchange>')
def get_contracts(base_name, exchange):
    try:
        data = futures_handler.get_contracts_by_base_name(base_name, exchange)
        return jsonify({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/fetch-futures-data', methods=['POST'])
def fetch_futures_data():
    try:
        futures_handler.fetch_futures_data()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/holdings/<ts_code>')
def get_holdings(ts_code):
    try:
        # 获取最近三个交易日的数据
        sql = """
        SELECT DISTINCT trade_date
        FROM futures_holding_rank
        WHERE ts_code LIKE %s
        ORDER BY trade_date DESC
        LIMIT 3
        """
        
        pattern = f"{ts_code.split('.')[0][:-4]}%"
        dates = futures_handler.db.execute_query(sql, (pattern,))
        
        if not dates:
            return jsonify({
                'status': 'success',
                'data': {
                    'dates': [],
                    'holdings': []
                }
            })
        
        # 获取新日期的持仓数据
        latest_date = dates[0][0]
        
        sql_holdings = """
        SELECT 
            broker,
            vol,
            vol_chg,
            long_hld,
            long_chg,
            short_hld,
            short_chg,
            trade_date,
            ts_code
        FROM futures_holding_rank
        WHERE ts_code LIKE %s
        AND trade_date = %s
        ORDER BY vol DESC
        """
        
        results = futures_handler.db.execute_query(sql_holdings, (pattern, latest_date))
        
        # 转换数据格式
        holdings = [{
            'broker': row[0],
            'vol': float(row[1]),
            'vol_chg': float(row[2]),
            'long_hld': float(row[3]),
            'long_chg': float(row[4]),
            'short_hld': float(row[5]),
            'short_chg': float(row[6]),
            'trade_date': row[7].strftime('%Y-%m-%d'),
            'ts_code': row[8]
        } for row in results]
        
        return jsonify({
            'status': 'success',
            'data': {
                'dates': [d[0].strftime('%Y-%m-%d') for d in dates],
                'holdings': holdings
            }
        })
        
    except Exception as e:
        print(f"Error getting holdings: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/holdings/<ts_code>/<trade_date>')
def get_holdings_by_date(ts_code, trade_date):
    try:
        sql = """
        SELECT 
            broker,
            vol,
            vol_chg,
            long_hld,
            long_chg,
            short_hld,
            short_chg,
            trade_date,
            ts_code
        FROM futures_holding_rank
        WHERE ts_code LIKE %s
        AND trade_date = %s
        ORDER BY vol DESC
        """
        
        pattern = f"{ts_code.split('.')[0][:-4]}%"
        results = futures_handler.db.execute_query(sql, (pattern, trade_date))
        
        holdings = [{
            'broker': row[0],
            'vol': float(row[1]),
            'vol_chg': float(row[2]),
            'long_hld': float(row[3]),
            'long_chg': float(row[4]),
            'short_hld': float(row[5]),
            'short_chg': float(row[6]),
            'trade_date': row[7].strftime('%Y-%m-%d'),
            'ts_code': row[8]
        } for row in results]
        
        return jsonify({
            'status': 'success',
            'data': holdings
        })
        
    except Exception as e:
        print(f"Error getting holdings: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/fetch-quotes', methods=['POST'])
def fetch_quotes():
    """获取行"""
    try:
        futures_handler.fetch_quotes_data()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/fetch-holdings', methods=['POST'])
def fetch_holdings():
    """获取机构成交持仓数据"""
    try:
        futures_handler.fetch_holdings_data()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

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
        
        # 转数据格式
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
        # 统一转换为大写
        contracts = [contract.upper() for contract in data.get('contracts', [])]
        
        if not contracts:
            return jsonify({
                'status': 'error',
                'message': '未选择合约'
            })
            
        # 1. 获取每天14:30的数据
        sql = """
        SELECT 
            CONCAT(DATE(PriceTime), ' 14:30:00') as PriceTime,
            ProductCode,
            Equity
        FROM tbPriceData
        WHERE ProductCode IN %s
        AND PriceTime >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
        AND TIME(PriceTime) = '14:30:00'
        ORDER BY PriceTime
        """
        
        print(f"Querying data for contracts: {contracts}")
        results = futures_handler.db.execute_query(sql, (tuple(contracts),))
        
        if not results:
            return jsonify({
                'status': 'success',
                'data': {
                    'equity_curve': [],
                    'statistics': None
                }
            })
        
        # 创建数据字典，用于快速查找
        equity_dict = {}
        last_equity = {code: 0 for code in contracts}  # 记录每个合约的最新净值
        first_equity = {code: None for code in contracts}  # 记录每个合约的首次出现时间
        
        # 记录每个合约的数据情况
        for row in results:
            time_point = row[0]  # 已经是格式化的字符串
            product_code = row[1].upper()  # 统一转换为大写
            equity = float(row[2] or 0)
            
            if time_point not in equity_dict:
                equity_dict[time_point] = {}
            
            equity_dict[time_point][product_code] = equity
            last_equity[product_code] = equity
            
            # 记录首次出现的净值
            if first_equity[product_code] is None:
                first_equity[product_code] = time_point
        
        # 生成净值曲线数据
        equity_data = []
        max_equity = float('-inf')
        min_equity = float('inf')
        current_equity = 0
        max_equity_time = None
        
        for time_point in sorted(equity_dict.keys()):
            total_equity = 0
            for contract in contracts:
                if first_equity[contract] is None:
                    # 合约未上市，使用初始资金
                    total_equity += 1000000
                elif time_point < first_equity[contract]:
                    # 合约尚未上市，使用初始资金
                    total_equity += 1000000
                else:
                    # 合约已上市，使用实际净值或最近的净值
                    equity = equity_dict[time_point].get(contract, last_equity[contract])
                    total_equity += equity
            
            equity_data.append({
                'time': time_point,  # 直接使用格式化的时间字符串
                'equity': total_equity
            })
            
            if total_equity > max_equity:
                max_equity = total_equity
                max_equity_time = time_point
            min_equity = min(min_equity, total_equity)
            current_equity = total_equity
        
        # 计算统计数据
        contract_count = len(contracts)
        base_value = contract_count * 1000000
        latest_time = sorted(equity_dict.keys())[-1]
        
        # 计算回撤天数（将字符串转为日期进行计算）
        from datetime import datetime
        max_equity_date = datetime.strptime(max_equity_time, '%Y-%m-%d %H:%M:%S')
        latest_date = datetime.strptime(latest_time, '%Y-%m-%d %H:%M:%S')
        drawdown_days = (latest_date - max_equity_date).days
        
        statistics = {
            'max_equity': max_equity,
            'min_equity': min_equity,
            'current_equity': current_equity,
            'current_drawdown': ((max_equity - current_equity) / base_value) * 100,
            'max_drawdown': ((max_equity - min_equity) / base_value) * 100,
            'max_equity_time': max_equity_time,
            'drawdown_days': drawdown_days,
            'y_axis_min': min_equity * 0.99,  # 留出1%的边距
            'y_axis_max': max_equity * 1.01
        }
        
        print(f"Found {len(equity_data)} data points for {len(contracts)} contracts")
        print(f"Statistics: {statistics}")
        
        return jsonify({
            'status': 'success',
            'data': {
                'equity_curve': equity_data,
                'statistics': statistics
            }
        })
        
    except Exception as e:
        print(f"Error getting equity data: {str(e)}")
        import traceback
        traceback.print_exc()
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
        
        # 开始事务
        conn = futures_handler.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查组合是否已存在
            check_sql = "SELECT id FROM futures_portfolio WHERE portfolio_name = %s"
            cursor.execute(check_sql, (name,))
            existing = cursor.fetchone()
            
            if existing:
                portfolio_id = existing[0]
                # 删除旧的约关系
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
            FROM tbPriceData t1
            INNER JOIN (
                SELECT 
                    ProductCode,
                    MAX(PriceTime) as max_time
                FROM tbPriceData
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
        
        # 获取最近20个时间点
        time_sql = """
        SELECT DISTINCT PriceTime
        FROM tbPriceData
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
                    FROM tbPriceData t2
                    WHERE t2.ProductCode = t1.ProductCode
                    AND t2.PriceTime < t1.PriceTime
                    AND t2.Equity IS NOT NULL
                    ORDER BY t2.PriceTime DESC
                    LIMIT 1
                )
            ) as Equity
        FROM tbPriceData t1
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
        
        # 按时间点组织数据
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
            
            # 计算回撤天数
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
        
        # 简化 SQL 查询，分两步获取数据
        # 1. 先获取所有合约基本信息
        basic_sql = """
        SELECT ts_code, name, exchange, fut_code
        FROM futures_basic
        WHERE delist_date >= %s
        """
        
        basic_data = futures_handler.db.execute_query(basic_sql, (today,))
        print(f"Found {len(basic_data)} basic contracts")
        
        # 2. 获取这些合约的行情数据
        contracts_data = {}
        for row in basic_data:
            ts_code = row[0]
            # 过滤掉连续合约和特殊合约
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
            
            # 获取最新行情数据
            latest_sql = """
            SELECT amount, high, low, pre_close, close, vol, oi
            FROM futures_daily_quotes
            WHERE ts_code = %s AND trade_date = %s
            """
            
            # 获取周数据
            week_sql = """
            SELECT 
                AVG(amount) as avg_amount,
                MAX(high) as max_high,
                MIN(low) as min_low,
                AVG(pre_close) as avg_pre_close
            FROM futures_daily_quotes
            WHERE ts_code = %s AND trade_date >= %s
            """
            
            # 获取月数据
            month_sql = """
            SELECT 
                AVG(amount) as avg_amount,
                MAX(high) as max_high,
                MIN(low) as min_low,
                AVG(pre_close) as avg_pre_close
            FROM futures_daily_quotes
            WHERE ts_code = %s AND trade_date >= %s
            """
            
            latest_data = futures_handler.db.execute_query(latest_sql, (ts_code, latest_date))
            week_data = futures_handler.db.execute_query(week_sql, (ts_code, week_ago))
            month_data = futures_handler.db.execute_query(month_sql, (ts_code, month_ago))
            
            if latest_data:
                latest = latest_data[0]
                week = week_data[0]
                month = month_data[0]
                
                # 计算振幅
                latest_amplitude = ((float(latest[1] or 0) - float(latest[2] or 0)) / float(latest[3] or 1)) * 100 if latest[3] else 0
                week_amplitude = ((float(week[1] or 0) - float(week[2] or 0)) / float(week[3] or 1)) * 100 if week[3] else 0
                month_amplitude = ((float(month[1] or 0) - float(month[2] or 0)) / float(month[3] or 1)) * 100 if month[3] else 0
                
                # 计算价格百分位
                price_position = 0
                if month[1] and month[2] and latest[4]:
                    month_high = float(month[1])
                    month_low = float(month[2])
                    current_price = float(latest[4])
                    if month_high > month_low:
                        price_position = ((current_price - month_low) / (month_high - month_low)) * 100
                
                contracts.append({
                    'ts_code': ts_code,
                    'name': contract['name'],
                    'exchange': contract['exchange'],
                    'fut_code': contract['fut_code'],
                    'latest_amount': float(latest[0] or 0) / 10000,  # 从万转换为亿
                    'latest_amplitude': latest_amplitude,
                    'close_price': float(latest[4] or 0),
                    'volume': float(latest[5] or 0),  # 成交量
                    'oi': float(latest[6] or 0),  # 持仓量
                    'week_amount': float(week[0] or 0) / 10000,  # 从万转换为亿
                    'week_amplitude': week_amplitude,
                    'month_amount': float(month[0] or 0) / 10000,  # 从万转换为亿
                    'month_amplitude': month_amplitude,
                    'month_low': float(month[2] or 0),
                    'month_high': float(month[1] or 0),
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
        SELECT DISTINCT trade_date
        FROM futures_daily_quotes
        WHERE ts_code = %s
        AND trade_date <= CURDATE()
        ORDER BY trade_date DESC
        LIMIT 10  # 确保获取10条记录
        """
        
        trade_dates = futures_handler.db.execute_query(history_sql, (ts_code,))
        if not trade_dates:
            return jsonify({
                'status': 'success',
                'data': {
                    'daily_data': [],
                    'related_contracts': []
                }
            })
        
        print(f"Found {len(trade_dates)} trading dates for {ts_code}")
        
        # 获取这些日期的行情数据
        quotes_sql = """
        SELECT 
            trade_date,
            close,
            pre_close,
            amount,
            oi
        FROM futures_daily_quotes
        WHERE ts_code = %s
        AND trade_date IN %s
        ORDER BY trade_date DESC
        """
        
        dates_tuple = tuple(row[0] for row in trade_dates)
        print(f"Querying quotes for dates: {dates_tuple}")
        
        history_data = futures_handler.db.execute_query(
            quotes_sql, 
            (ts_code, dates_tuple)
        )
        
        print(f"Found {len(history_data)} quote records")
        
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
        base_code = ts_code.split('.')[0]  # 完整合约代码（如 J2501）
        product_code = ''.join(c for c in base_code if not c.isdigit())  # 提取品种代码（如 J）
        exchange = ts_code.split('.')[1]  # 获取交易所代码
        today = datetime.datetime.now().strftime('%Y%m%d')
        
        # 获取最新交易日期
        latest_date = trade_dates[0][0] if trade_dates else None
        
        # 分两步获取相关合约
        # 1. 先获取所有同品种的合约代码
        contracts_sql = """
        SELECT ts_code 
        FROM futures_basic
        WHERE exchange = %s
        AND delist_date >= %s
        AND ts_code LIKE %s
        AND ts_code != %s
        """
        
        # 构建匹配模式
        pattern = f"{product_code}%"
        
        print(f"Querying contracts with pattern: {pattern}")
        contracts = futures_handler.db.execute_query(
            contracts_sql, 
            (exchange, today, pattern, ts_code)
        )
        print(f"Found {len(contracts)} related contracts")
        
        # 2. 获取这些合约的最新行情数据
        related_contracts = []
        if contracts and latest_date:
            contract_codes = tuple(row[0] for row in contracts)
            if contract_codes:  # 确保有合约代码
                quotes_sql = """
                SELECT 
                    ts_code,
                    close,
                    amount,
                    oi
                FROM futures_daily_quotes
                WHERE ts_code IN %s
                AND trade_date = %s
                AND ts_code NOT LIKE '%%L.%%'
                AND ts_code NOT LIKE '%%99.%%'
                """
                
                print(f"Querying quotes for contracts: {contract_codes}")
                quotes = futures_handler.db.execute_query(
                    quotes_sql,
                    (contract_codes, latest_date)
                )
                print(f"Found {len(quotes)} quotes")
                
                # 转换数据
                for row in quotes:
                    related_contracts.append({
                        'ts_code': row[0],
                        'close': float(row[1] or 0),
                        'amount': float(row[2] or 0) / 10000,  # 转换为亿
                        'oi': float(row[3] or 0)
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
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',  # 允许外部访问
        port=5000,       # 指定端口号
        debug=True       # 开发模式下保持 debug=True
    ) 