# 期货数据分析系统

## 项目概述
本项目是一个期货数据分析系统，主要用于期货数据的获取、筛选和展示。

## 核心功能
1. 期货基础数据获取
   - 期货行情数据获取
   - 期货持仓量数据获取
   - 机构净持仓数据获取

2. 期货数据筛选
   - 根据涨跌幅范围筛选
   - 根据成交额范围筛选
   - 根据机构持仓变化筛选

3. 期货信息展示
   - 展示近7个交易日的数据
   - 每日涨跌幅展示
   - 每日成交额展示
   - 持仓量变化展示
   - 机构持仓变化展示
   - 仓差情况展示

## 期货品种管理功能
### 期货品种展示
1. 数据组织
   - 按交易所分组展示
   - 同一品种合约集中显示
   - 支持多种合约类型

2. 数据更新
   - 自动获取最新品种信息
   - 增量更新数据
   - 自动清理过期数据

3. 数据展示
   - 分类展示各类合约
   - 突出显示主力合约
   - 显示合约状态

### 数据库设计
1. futures_basic 表字段说明
   - ts_code: 合约代码
   - symbol: 交易标识
   - name: 中文名称
   - exchange: 交易所代码
   - fut_code: 期货品种代码
   - multiplier: 合约乘数
   - trade_unit: 交易单位
   - per_unit: 每手单位
   - quote_unit: 报价单位
   - quote_unit_desc: 最小变动价位说明
   - list_date: 上市日期
   - delist_date: 退市日期

2. 索引设计
   - 主键：ts_code
   - 普通索引：exchange, fut_code

## 期货数据获取功能
### 数据获取范围
1. 日线行情数据
   - 所有未到期合约当日数据
   - 主力合约30天历史数据
   - 包含开高低收价格
   - 成交量和持仓量数据

2. 持仓排名数据
   - 主力合约当日持仓数据
   - 期货公司持仓明细
   - 多空持仓变化
   - 成交量变化数据

### 数据处理流程
1. 数据获取
   - 检查数据是否存在
   - 调用Tushare API
   - 数据格式转换
   - 空值处理

2. 数据存储
   - 批量数据插入
   - 避免重复数据
   - 事务管理
   - 数据完整性检查

3. 异常处理
   - API调用异常
   - 数据格式异常
   - 网络超时
   - 并发控制

### 性能优化
1. API调用优化
   - 请求频率限制
   - 避免重复请求
   - 批量数据处理
   - 错误重试

2. 数据库优化
   - 连接池管理
   - 索引优化
   - 批量操作
   - 事务控制

## 技术栈
- 后端：Flask + Python
- 前端：Bootstrap + ECharts
- 数据库：MySQL
- 其他：pandas, numpy等数据处理库

## 数据库设计
### 数据库配置
- 主机：10.17.31.47
- 端口：3306
- 用户名：root
- 数据库名：tbauto
- 字符集：utf8mb4

### 数据表结构
1. futures_basic（期货基础信息表）
   ```sql
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
       update_time TIMESTAMP
   )
   ```

2. futures_daily_quotes（日线行情数据表）
   ```sql
   CREATE TABLE futures_daily_quotes (
       id BIGINT AUTO_INCREMENT PRIMARY KEY,
       trade_date DATE,
       ts_code VARCHAR(20),
       open DECIMAL(20,4),
       high DECIMAL(20,4),
       low DECIMAL(20,4),
       close DECIMAL(20,4),
       pre_close DECIMAL(20,4),
       change_rate DECIMAL(20,4),
       vol DECIMAL(20,4),
       amount DECIMAL(20,4),
       oi DECIMAL(20,4),
       oi_chg DECIMAL(20,4),
       update_time TIMESTAMP
   )
   ```

3. futures_warehouse_stocks（仓单数据表）
   ```sql
   CREATE TABLE futures_warehouse_stocks (
       id BIGINT AUTO_INCREMENT PRIMARY KEY,
       trade_date DATE,
       ts_code VARCHAR(20),
       warehouse VARCHAR(50),
       area VARCHAR(50),
       stock DECIMAL(20,4),
       unit VARCHAR(20),
       update_time TIMESTAMP
   )
   ```

4. futures_institution_positions（机构持仓数据表）
   ```sql
   CREATE TABLE futures_institution_positions (
       id BIGINT AUTO_INCREMENT PRIMARY KEY,
       trade_date DATE,
       ts_code VARCHAR(20),
       broker VARCHAR(50),
       vol DECIMAL(20,4),
       vol_chg DECIMAL(20,4),
       long_hld DECIMAL(20,4),
       long_chg DECIMAL(20,4),
       short_hld DECIMAL(20,4),
       short_chg DECIMAL(20,4),
       update_time TIMESTAMP
   )
   ```

## 项目结构

## 系统功能更新说明
### 2024-11-06 更新
1. 机构持仓排名
   - 支持所有期货品种
   - 显示完整持仓信息
   - 优化数据查询逻辑
   - 处理重复数据问题

2. 界面优化
   - 优化左侧导航栏
   - 调整布局比例
   - 改进数据展示
   - 增强用户体验

3. 数据处理
   - 优化数据库查询
   - 处理特殊交易所代码
   - 合并同名机构数据
   - 自动清理重复记录

### 2024-11-22 更新
### 权益数据展示优化
1. 半小时净盈亏数据
   - [x] 数据居中显示
   - [x] 整数化处理
   - [x] 多空方向显示
   - [x] 颜色区分正负

2. 相对权益数据
   - [x] 优化时间周期
   - [x] 支持数据排序
   - [x] 数据补充机制
   - [x] 性能优化

### 数据处理优化
1. 查询优化
   - [x] 减少数据库访问
   - [x] 优化SQL语句
   - [x] 本地数据处理
   - [x] 异常处理完善

2. 显示优化
   - [x] 界面布局优化
   - [x] 数据格式统一
   - [x] 交互体验改进
   - [x] 性能提升