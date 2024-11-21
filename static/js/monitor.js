// 监控状态
let monitoringPortfolioId = null;
let monitorInterval = null;

// 初始化监控图表
let monitorChart = null;

function initMonitorChart() {
    const chartContainer = document.getElementById('monitorChart');
    if (!chartContainer) {
        console.error('Chart container not found!');
        return;
    }
    console.log('Initializing chart with container:', chartContainer);
    
    monitorChart = echarts.init(chartContainer);
    console.log('Chart initialized:', monitorChart);
    
    const option = {
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                const date = params[0].axisValue;
                return `${date}<br/>权益: ${formatNumber(params[0].value)}`;
            }
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: [],
            axisLabel: {
                fontSize: 10,
                formatter: function(value) {
                    return value.substring(5, 10);  // 只显示月/日
                }
            }
        },
        yAxis: {
            type: 'value',
            scale: true,
            axisLabel: {
                fontSize: 10,
                formatter: function(value) {
                    return formatNumber(value);
                }
            }
        },
        series: [{
            name: '组合权益',
            type: 'line',
            data: [],
            smooth: true,
            showSymbol: false,
            lineStyle: {
                width: 1
            },
            areaStyle: {
                opacity: 0.1
            }
        }]
    };
    
    monitorChart.setOption(option);
    console.log('Chart option set');
    
    // 监听容器大小变化
    window.addEventListener('resize', () => {
        monitorChart && monitorChart.resize();
    });
}

// 更新图表数据
async function updateMonitorChart(portfolioId) {
    try {
        console.log('Fetching chart data for portfolio:', portfolioId);
        const response = await fetch(`/api/monitor/chart-data/${portfolioId}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            console.log('Received chart data:', data);
            
            if (!data.data || !data.data.chart_data) {
                console.warn('No chart data received');
                return;
            }
            
            // 更新图表数据
            const times = data.data.chart_data.map(item => item.time);
            const values = data.data.chart_data.map(item => item.equity);
            
            if (!monitorChart) {
                console.warn('Chart not initialized, initializing now');
                initMonitorChart();
            }
            
            monitorChart.setOption({
                xAxis: {
                    data: times
                },
                series: [{
                    data: values
                }]
            });
            console.log('Chart updated with new data');
            
            // 更新统计指标
            if (data.data.statistics) {
                console.log('Updating statistics');
                updateStatistics(data.data.statistics);
            }
        }
    } catch (error) {
        console.error('Error updating monitor chart:', error);
    }
}

// 更新统计指标
function updateStatistics(stats) {
    console.log('Updating statistics:', stats);  // 调试日志
    
    // 更新表格中的统计数据
    const tbody = document.getElementById('monitorTableBody');
    if (!tbody) {
        console.error('Monitor table body not found');
        return;
    }
    
    const rows = tbody.getElementsByTagName('tr');
    
    // 当前权益
    if (rows[0]) {
        const cells = rows[0].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = formatNumber(stats.current_equity);
    }
    
    // 过去一年最高权益
    if (rows[1]) {
        const cells = rows[1].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = formatNumber(stats.max_equity);
    }
    
    // 发生时间
    if (rows[2]) {
        const cells = rows[2].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = formatDateTime(stats.max_equity_time);
    }
    
    // 当前回撤
    if (rows[3]) {
        const cells = rows[3].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = formatPercent(stats.current_drawdown);
    }
    
    // 回撤时间
    if (rows[4]) {
        const cells = rows[4].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = `${stats.drawdown_days}天`;
        if (stats.drawdown_days > 90) {
            cells[1].classList.add('text-danger');
        } else {
            cells[1].classList.remove('text-danger');
        }
    }
    
    // 过去一年最大回撤
    if (rows[5]) {
        const cells = rows[5].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = formatPercent(stats.max_drawdown);
    }
}

// 初始化监控功能
function initializeMonitor() {
    // 监听开始监测按钮
    document.getElementById('startMonitor').addEventListener('click', startMonitoring);
    
    // 监听停止监测按钮
    document.getElementById('stopMonitor').addEventListener('click', stopMonitoring);
    
    // 加载组合列表
    loadMonitorPortfolios();
}

// 加载可监控的组合列表
async function loadMonitorPortfolios() {
    try {
        const response = await fetch('/api/portfolios');
        const data = await response.json();
        
        if (data.status === 'success') {
            const container = document.querySelector('.portfolio-monitor-list');
            container.innerHTML = data.data.map(portfolio => `
                <div class="list-group-item" data-portfolio-id="${portfolio.id}">
                    ${portfolio.name}
                </div>
            `).join('');
            
            // 修改双击事件为单击事件，并添加调试日志
            container.querySelectorAll('.list-group-item').forEach(item => {
                item.addEventListener('click', async function() {
                    console.log('Portfolio clicked:', this.dataset.portfolioId);
                    const portfolioId = this.dataset.portfolioId;
                    
                    // 更新选中状态
                    container.querySelectorAll('.list-group-item').forEach(i => 
                        i.classList.remove('active'));
                    this.classList.add('active');
                    
                    // 启用开始监测按钮
                    document.getElementById('startMonitor').disabled = false;
                    
                    try {
                        // 加载组合详情
                        await loadPortfolioDetails(portfolioId);
                        console.log('Portfolio details loaded');
                        
                        // 加载组合统计数据
                        await loadPortfolioStats(portfolioId);
                        console.log('Portfolio stats loaded');
                        
                        // 更新图表数据
                        await updateMonitorChart(portfolioId);
                        console.log('Monitor chart updated');
                    } catch (error) {
                        console.error('Error loading portfolio data:', error);
                    }
                });
            });
        }
    } catch (error) {
        console.error('Error loading monitor portfolios:', error);
    }
}

// 更新组合详情表格
function updatePortfolioTable(details) {
    const tbody = document.getElementById('portfolioDetails');
    if (!tbody) {
        console.error('Portfolio details table body not found');
        return;
    }
    
    tbody.innerHTML = details.map(contract => `
        <tr>
            <td>${contract.fut_code}</td>
            <td>${getDealDirection(contract.current_equity)}</td>
            <td>${formatNumber(contract.current_equity)}</td>
            <td>${contract.current_price ? formatNumber(contract.current_price) : '-'}</td>
            <td>${contract.stop_price ? formatNumber(contract.stop_price) : '-'}</td>
            <td class="${getStopLossClass(contract.current_price, contract.stop_price)}">
                ${calculateStopLossSpace(contract.current_price, contract.stop_price)}
            </td>
            <td>${contract.update_time}</td>
        </tr>
    `).join('');
}

// 修改 loadPortfolioDetails 函数
async function loadPortfolioDetails(portfolioId) {
    try {
        console.log('Loading portfolio details for ID:', portfolioId);
        const response = await fetch(`/api/monitor/portfolio-details/${portfolioId}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            // 更新组合名称显示
            const selectedPortfolio = document.querySelector(`.portfolio-monitor-list .list-group-item[data-portfolio-id="${portfolioId}"]`);
            if (selectedPortfolio) {
                document.getElementById('selectedPortfolioName').textContent = selectedPortfolio.textContent;
            }
            
            // 使用新的更新表格函数
            updatePortfolioTable(data.data);
            console.log('Portfolio details updated');
        }
    } catch (error) {
        console.error('Error loading portfolio details:', error);
    }
}

// 加载组合统计数据
async function loadPortfolioStats(portfolioId) {
    try {
        const response = await fetch(`/api/monitor/portfolio-stats/${portfolioId}`);
        const data = await response.json();
        
        if (data.status === 'success' && data.data.length > 0) {
            const latestStats = data.data[0];  // 获取最新的统计数据
            
            // 更新组合数据表格
            updateMonitorTable([{
                time: latestStats.time,
                current_equity: latestStats.current_equity,
                max_equity: latestStats.max_equity,
                max_equity_time: latestStats.max_equity_time,
                current_drawdown: latestStats.current_drawdown,
                drawdown_days: latestStats.drawdown_days,
                max_drawdown: latestStats.max_drawdown,
                contracts_count: latestStats.contracts_count,
                long_count: latestStats.long_count,
                short_count: latestStats.short_count
            }]);
        }
    } catch (error) {
        console.error('Error loading portfolio stats:', error);
    }
}

// 获取多空方向显示
function getDealDirection(equity) {
    if (equity > 0) return '<span class="text-success">多</span>';
    if (equity < 0) return '<span class="text-danger">空</span>';
    return '<span class="text-secondary">-</span>';  // 修改这里，始终显示方向
}

// 开始监控
function startMonitoring() {
    const selectedPortfolio = document.querySelector('.portfolio-monitor-list .active');
    if (!selectedPortfolio) {
        alert('请先选择要监控的组合');
        return;
    }
    
    monitoringPortfolioId = selectedPortfolio.dataset.portfolioId;
    
    // 更新按钮状态
    document.getElementById('startMonitor').classList.add('d-none');
    document.getElementById('stopMonitor').classList.remove('d-none');
    
    // 立即执行一次更新，不受时间限制
    updateMonitorData();
    
    // 设置定时更新
    monitorInterval = setInterval(checkUpdateTime, 1000);
}

// 停止监控
function stopMonitoring() {
    if (monitorInterval) {
        clearInterval(monitorInterval);
        monitorInterval = null;
    }
    
    monitoringPortfolioId = null;
    
    // 更新按钮状态
    document.getElementById('startMonitor').classList.remove('d-none');
    document.getElementById('stopMonitor').classList.add('d-none');
    document.getElementById('nextUpdateTime').textContent = '';
}

// 检查是否需要更新
function checkUpdateTime() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const seconds = now.getSeconds();
    
    // 检查是否在交易时间内
    const isTradeTime = (
        // 日盘：9:00-15:30
        (hours >= 9 && hours < 15) || 
        (hours === 15 && minutes <= 30) ||
        // 夜盘：21:00-23:59, 00:00-03:00
        (hours >= 21) || 
        (hours < 3)
    );
    
    if (!isTradeTime) {
        document.getElementById('nextUpdateTime').textContent = '非交易时间';
        return;
    }
    
    // 计算下次更新时间
    let nextMinutes, nextHours;
    
    if (minutes <= 5) {
        nextMinutes = 5;
        nextHours = hours;
    } else if (minutes <= 35) {
        nextMinutes = 35;
        nextHours = hours;
    } else {
        nextMinutes = 5;
        nextHours = (hours + 1) % 24;
    }
    
    const nextUpdate = new Date(now);
    nextUpdate.setHours(nextHours);
    nextUpdate.setMinutes(nextMinutes);
    nextUpdate.setSeconds(0);
    
    // 如果下次更新时间在非交易时间，则调整到下一个交易时段
    if (nextHours >= 3 && nextHours < 9) {
        nextUpdate.setHours(9);
        nextUpdate.setMinutes(5);
    } else if (nextHours >= 15 && nextHours < 21) {
        nextUpdate.setHours(21);
        nextUpdate.setMinutes(5);
    }
    
    // 显示倒计时
    const timeLeft = Math.floor((nextUpdate - now) / 1000);
    document.getElementById('nextUpdateTime').textContent = 
        `下次更新: ${Math.floor(timeLeft / 60)}分${timeLeft % 60}秒`;
    
    // 检查是否需要更新（只在交易时间内的指定时间点更新）
    if ((minutes === 5 || minutes === 35) && seconds === 0) {
        updateMonitorData();
    }
}

// 更新监数据
async function updateMonitorData() {
    if (!monitoringPortfolioId) return;
    
    try {
        // 现有的代码...
        
        // 更新图表
        await updateMonitorChart(monitoringPortfolioId);
        
    } catch (error) {
        console.error('Error updating monitor data:', error);
    }
}

// 格式化数字
function formatNumber(num) {
    if (!num) return '-';
    return num.toLocaleString('zh-CN', { maximumFractionDigits: 0 });
}

// 格式化百分比
function formatPercent(value) {
    return value.toFixed(2) + '%';
}

// 格式化日期时间
function formatDateTime(dateStr) {
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

// 获取止损空间的样式类
function getStopLossClass(currentPrice, stopPrice) {
    if (!currentPrice || !stopPrice) return '';
    const space = ((currentPrice - stopPrice) / stopPrice) * 100;
    return space > 0 ? 'text-success' : 'text-danger';
}

// 计算止损空间
function calculateStopLossSpace(currentPrice, stopPrice) {
    if (!currentPrice || !stopPrice) return '-';
    const space = ((currentPrice - stopPrice) / stopPrice) * 100;
    return space.toFixed(2) + '%';
}

// 更新监控表格
function updateMonitorTable(data) {
    const tbody = document.getElementById('monitorTableBody');
    if (!tbody) {
        console.error('Monitor table body not found');
        return;
    }

    const rows = tbody.getElementsByTagName('tr');
    
    // 当前权益
    if (rows[0]) {
        const cells = rows[0].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = formatNumber(data[0].current_equity);
    }
    
    // 过去一年最高权益
    if (rows[1]) {
        const cells = rows[1].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = formatNumber(data[0].max_equity);
    }
    
    // 发生时间
    if (rows[2]) {
        const cells = rows[2].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = formatDateTime(data[0].max_equity_time);
    }
    
    // 当前回撤
    if (rows[3]) {
        const cells = rows[3].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = formatPercent(data[0].current_drawdown);
    }
    
    // 回撤时间
    if (rows[4]) {
        const cells = rows[4].getElementsByTagName('td');
        if (cells[1]) {
            cells[1].textContent = `${data[0].drawdown_days}天`;
            if (data[0].drawdown_days > 90) {
                cells[1].classList.add('text-danger');
            } else {
                cells[1].classList.remove('text-danger');
            }
        }
    }
    
    // 过去一年最大回撤
    if (rows[5]) {
        const cells = rows[5].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = formatPercent(data[0].max_drawdown);
    }
    
    // 品种总数
    if (rows[6]) {
        const cells = rows[6].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = data[0].contracts_count;
    }
    
    // 品种多空
    if (rows[7]) {
        const cells = rows[7].getElementsByTagName('td');
        if (cells[1]) cells[1].textContent = `多:${data[0].long_count} 空:${data[0].short_count}`;
    }
    
    // 净多空
    if (rows[8]) {
        const cells = rows[8].getElementsByTagName('td');
        if (cells[1]) {
            const netPosition = data[0].long_count - data[0].short_count;
            cells[1].textContent = netPosition;
            cells[1].className = netPosition > 0 ? 'text-success' : netPosition < 0 ? 'text-danger' : '';
        }
    }
}

// 初始化监控功能
document.addEventListener('DOMContentLoaded', initializeMonitor); 