import sys
import os
sys.path.append('.')
from dotenv import load_dotenv
from comm.dboper import DBOperator

load_dotenv()

def init_database():
    db = DBOperator()
    
    # 创建期货日线行情表
    create_daily_quotes = """
    CREATE TABLE IF NOT EXISTS futures_daily_quotes (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        trade_date DATE,                    -- 交易日期
        ts_code VARCHAR(20),                -- 合约代码
        open DECIMAL(20,4),                 -- 开盘价
        high DECIMAL(20,4),                 -- 最高价
        low DECIMAL(20,4),                  -- 最低价
        close DECIMAL(20,4),                -- 收盘价
        pre_close DECIMAL(20,4),            -- 昨收价
        change_rate DECIMAL(20,4),          -- 涨跌幅
        vol DECIMAL(20,4),                  -- 成交量
        amount DECIMAL(20,4),               -- 成交额
        oi DECIMAL(20,4),                   -- 持仓量
        oi_chg DECIMAL(20,4),              -- 持仓量变化
        update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY idx_code_date (ts_code, trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    
    # 创建期货持仓排名表
    create_holding_rank = """
    CREATE TABLE IF NOT EXISTS futures_holding_rank (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        trade_date DATE,                    -- 交易日期
        ts_code VARCHAR(20),                -- 合约代码
        broker VARCHAR(50),                 -- 期货公司会员简称
        vol DECIMAL(20,4),                  -- 成交量
        vol_chg DECIMAL(20,4),             -- 成交量变化
        long_hld DECIMAL(20,4),            -- 持买仓量
        long_chg DECIMAL(20,4),            -- 持买仓量变化
        short_hld DECIMAL(20,4),           -- 持卖仓量
        short_chg DECIMAL(20,4),           -- 持卖仓量变化
        update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY idx_code_date_broker (ts_code, trade_date, broker)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    
    # 创建组合表
    create_portfolio = """
    CREATE TABLE IF NOT EXISTS futures_portfolio (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        portfolio_name VARCHAR(100) NOT NULL,
        create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY idx_name (portfolio_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    
    # 创建组合-合约关系表
    create_portfolio_contract = """
    CREATE TABLE IF NOT EXISTS futures_portfolio_contract (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        portfolio_id BIGINT NOT NULL,
        fut_code VARCHAR(20) NOT NULL,
        create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY idx_portfolio_contract (portfolio_id, fut_code),
        FOREIGN KEY (portfolio_id) REFERENCES futures_portfolio(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    
    try:
        # 执行建表语句
        db.execute_update(create_daily_quotes)
        print("Created futures_daily_quotes table successfully")
        
        db.execute_update(create_holding_rank)
        print("Created futures_holding_rank table successfully")
        
        db.execute_update(create_portfolio)
        print("Created futures_portfolio table successfully")
        
        db.execute_update(create_portfolio_contract)
        print("Created futures_portfolio_contract table successfully")
        
    except Exception as e:
        print(f"Error creating tables: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    init_database() 