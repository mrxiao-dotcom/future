import sys
sys.path.append('.')
from comm.dboper import DBOperator

def clean_duplicate_holdings():
    """清理重复的持仓数据"""
    db = DBOperator()
    
    try:
        # 1. 找出重复记录
        find_duplicates_sql = """
        WITH duplicates AS (
            SELECT 
                trade_date,
                ts_code,
                CASE 
                    WHEN broker LIKE '%%（代客）' THEN LEFT(broker, LENGTH(broker) - 4)
                    WHEN broker LIKE '%%代客' THEN LEFT(broker, LENGTH(broker) - 2)
                    ELSE broker 
                END as base_broker,
                MAX(vol) as max_vol,
                COUNT(*) as record_count
            FROM futures_holding_rank
            GROUP BY 
                trade_date,
                ts_code,
                CASE 
                    WHEN broker LIKE '%%（代客）' THEN LEFT(broker, LENGTH(broker) - 4)
                    WHEN broker LIKE '%%代客' THEN LEFT(broker, LENGTH(broker) - 2)
                    ELSE broker 
                END
            HAVING COUNT(*) > 1
        )
        SELECT 
            h.id,
            h.trade_date,
            h.ts_code,
            h.broker,
            h.vol
        FROM futures_holding_rank h
        INNER JOIN duplicates d ON 
            h.trade_date = d.trade_date
            AND h.ts_code = d.ts_code
            AND (
                CASE 
                    WHEN h.broker LIKE '%%（代客）' THEN LEFT(h.broker, LENGTH(h.broker) - 4)
                    WHEN h.broker LIKE '%%代客' THEN LEFT(h.broker, LENGTH(h.broker) - 2)
                    ELSE h.broker 
                END = d.base_broker
            )
            AND h.vol < d.max_vol
        """
        
        # 2. 获取要删除的记录
        duplicates = db.execute_query(find_duplicates_sql)
        if not duplicates:
            print("No duplicate records found")
            return
            
        print(f"Found {len(duplicates)} duplicate records")
        
        # 3. 删除重复记录（保留持仓量最大的）
        delete_ids = [str(row[0]) for row in duplicates]
        delete_sql = f"""
        DELETE FROM futures_holding_rank 
        WHERE id IN ({','.join(delete_ids)})
        """
        
        affected_rows = db.execute_update(delete_sql)
        print(f"Deleted {affected_rows} duplicate records")
        
        # 4. 打印清理结果
        for row in duplicates:
            print(f"Deleted: Date={row[1]}, Code={row[2]}, Broker={row[3]}, Vol={row[4]}")
        
    except Exception as e:
        print(f"Error cleaning holdings: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    clean_duplicate_holdings() 