# 数据库设计文档

## 期货基础数据表
### futures_basic
期货合约基础信息表
| 字段名 | 类型 | 说明 | 示例 |
|-------|------|------|------|
| ts_code | varchar(20) | 合约代码 | cu2401.SHFE |
| name | varchar(50) | 合约名称 | 沪铜2401 |
| exchange | varchar(20) | 交易所代码 | SHFE |
| fut_code | varchar(20) | 期货品种代码 | cu |
| delist_date | date | 退市日期 | 2024-01-15 |

### futures_daily_quotes
期货日线行情数据表
| 字段名 | 类型 | 说明 | 示例 |
|-------|------|------|------|
| ts_code | varchar(20) | 合约代码 | cu2401.SHFE |
| trade_date | date | 交易日期 | 2023-11-08 |
| open | decimal(20,4) | 开盘价 | 67890.0000 |
| high | decimal(20,4) | 最高价 | 68100.0000 |
| low | decimal(20,4) | 最低价 | 67800.0000 |
| close | decimal(20,4) | 收盘价 | 68000.0000 |
| pre_close | decimal(20,4) | 昨收价 | 67900.0000 |
| change_rate | decimal(20,4) | 涨跌幅(%) | 0.1475 |
| vol | decimal(20,4) | 成交量(手) | 89123.0000 |
| amount | decimal(20,4) | 成交额(万元) | 303751.4350 |
| oi | decimal(20,4) | 持仓量(手) | 270845.0000 |

### futures_holding_rank
期货持仓排名数据表
| 字段名 | 类型 | 说明 | 示例 |
|-------|------|------|------|
| ts_code | varchar(20) | 合约代码 | cu2401.SHFE |
| trade_date | date | 交易日期 | 2023-11-08 |
| broker | varchar(100) | 期货公司 | 永安期货 |
| vol | decimal(20,4) | 成交量 | 12345.0000 |
| vol_chg | decimal(20,4) | 成交量变化 | 234.0000 |
| long_hld | decimal(20,4) | 多头持仓量 | 5678.0000 |
| long_chg | decimal(20,4) | 多头持仓变化 | 123.0000 |
| short_hld | decimal(20,4) | 空头持仓量 | 4567.0000 |
| short_chg | decimal(20,4) | 空头持仓变化 | -89.0000 |

## 组合管理相关表
### futures_portfolio
组合信息表
| 字段名 | 类型 | 说明 | 示例 |
|-------|------|------|------|
| id | int | 组合ID | 1 |
| portfolio_name | varchar(100) | 组合名称 | 铜铝组合 |
| create_time | datetime | 创建时间 | 2023-11-08 14:30:00 |

### futures_portfolio_contract
组合持仓合约表
| 字段名 | 类型 | 说明 | 示例 |
|-------|------|------|------|
| portfolio_id | int | 组合ID | 1 |
| fut_code | varchar(20) | 期货品种代码 | cu |

## 实时价格数据表
### tbPriceData
实时价格数据表
| 字段名 | 类型 | 说明 | 示例 |
|-------|------|------|------|
| PriceTime | datetime | 价格时间 | 2023-11-08 14:30:00 |
| ProductCode | varchar(20) | 品种代码 | cu |
| Equity | decimal(20,4) | 权益 | 1234567.8900 |
| ClosePrice | decimal(20,4) | 收盘价 | 68000.0000 |
| StopPrice | decimal(20,4) | 止损价 | 67500.0000 |

## 索引设计
1. futures_basic
   - 主键: ts_code
   - 索引: exchange, fut_code

2. futures_daily_quotes
   - 主键: ts_code, trade_date
   - 索引: trade_date

3. futures_holding_rank
   - 主键: ts_code, trade_date, broker
   - 索引: trade_date

4. futures_portfolio
   - 主键: id
   - 索引: portfolio_name

5. futures_portfolio_contract
   - 主键: portfolio_id, fut_code
   - 外键: portfolio_id 关联 futures_portfolio(id)

6. tbPriceData
   - 主键: PriceTime, ProductCode
   - 索引: ProductCode, PriceTime

## 数据关系
1. futures_portfolio_contract 通过 portfolio_id 关联 futures_portfolio
2. futures_portfolio_contract 通过 fut_code 关联 futures_basic
3. futures_daily_quotes 通过 ts_code 关联 futures_basic
4. futures_holding_rank 通过 ts_code 关联 futures_basic
5. tbPriceData 通过 ProductCode 关联 futures_basic 的 fut_code

## 数据维护
1. 定时任务
   - 每日更新 futures_daily_quotes
   - 每日更新 futures_holding_rank
   - 实时更新 tbPriceData (每30分钟)

2. 数据清理
   - 自动清理超过30天的历史数据
   - 保留主力合约的历史数据
   - 定期清理已退市合约数据

3. 数据备份
   - 每日备份全量数据
   - 实时备份重要数据
   - 定期归档历史数据

## 数据查询优化
### 权益数据查询
1. 半小时净盈亏数据
   - [x] 获取最近3天数据
   - [x] 按品种和时间排序
   - [x] 处理空值情况
   - [x] 优化查询性能

2. 相对权益数据
   - [x] 支持多个时间周期
   - [x] 使用时间范围查询
   - [x] 处理数据缺失
   - [x] 优化JOIN性能

3. 多空方向数据
   - [x] 获取最新持仓方向
   - [x] 按品种分组查询
   - [x] 处理空值情况
   - [x] 优化查询效率

### 查询性能优化
1. SQL优化
   - [x] 使用WITH子句
   - [x] 优化JOIN条件
   - [x] 添加适当索引
   - [x] 减少子查询

2. 数据处理
   - [x] 本地数据缓存
   - [x] 批量数据处理
   - [x] 异常值处理
   - [x] 数据补充机制 