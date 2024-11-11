// 监控状态
let monitoringPortfolioId = null;
let monitorInterval = null;

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
            
            // 添加双击事件
            container.querySelectorAll('.list-group-item').forEach(item => {
                item.addEventListener('dblclick', function() {
                    const portfolioId = this.dataset.portfolioId;
                    
                    // 更新选中状态
                    container.querySelectorAll('.list-group-item').forEach(i => 
                        i.classList.remove('active'));
                    this.classList.add('active');
                    
                    // 加载组合详情
                    loadPortfolioDetails(portfolioId);
                });
            });
        }
    } catch (error) {
        console.error('Error loading monitor portfolios:', error);
    }
}

// 加载组合详情
async function loadPortfolioDetails(portfolioId) {
    try {
        const response = await fetch(`/api/monitor/portfolio-details/${portfolioId}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            // 更新组合名称显示
            const selectedPortfolio = document.querySelector(`.portfolio-monitor-list .list-group-item[data-portfolio-id="${portfolioId}"]`);
            if (selectedPortfolio) {
                document.getElementById('selectedPortfolioName').textContent = selectedPortfolio.textContent;
            }
            
            // 更新品种详情表格
            const tbody = document.getElementById('portfolioDetails');
            tbody.innerHTML = data.data.map(contract => {
                // 计算止损空间
                let stopLossSpace = '-';
                let stopLossClass = '';
                
                // 如果有多空方向（权益不为0），且有最新价和止损价，才计算止损空间
                if (contract.current_equity !== 0 && contract.current_price && contract.stop_price) {
                    if (contract.current_equity > 0) {  // 多头
                        const space = ((contract.current_price - contract.stop_price) / contract.stop_price * 100);
                        stopLossSpace = space.toFixed(2) + '%';
                        stopLossClass = space > 0 ? 'positive' : 'negative';
                    } else if (contract.current_equity < 0) {  // 空头
                        const space = ((contract.stop_price - contract.current_price) / contract.current_price * 100);
                        stopLossSpace = space.toFixed(2) + '%';
                        stopLossClass = space > 0 ? 'positive' : 'negative';
                    }
                }
                
                return `
                    <tr>
                        <td>${contract.fut_code}</td>
                        <td>${getDealDirection(contract.current_equity)}</td>
                        <td>${formatNumber(contract.current_equity)}</td>
                        <td>${contract.current_equity !== 0 ? (contract.current_price ? formatNumber(contract.current_price) : '-') : '-'}</td>
                        <td>${contract.current_equity !== 0 ? (contract.stop_price ? formatNumber(contract.stop_price) : '-') : '-'}</td>
                        <td class="stop-loss-space ${stopLossClass}">${contract.current_equity !== 0 ? stopLossSpace : '-'}</td>
                        <td>${contract.update_time}</td>
                    </tr>
                `;
            }).join('');
            
            // 启用开始监测按钮
            document.getElementById('startMonitor').disabled = false;
        }
    } catch (error) {
        console.error('Error loading portfolio details:', error);
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

// 更新监控数据
async function updateMonitorData() {
    if (!monitoringPortfolioId) return;
    
    try {
        // 更新组合详情
        await loadPortfolioDetails(monitoringPortfolioId);
        
        // 更新统计数据
        const response = await fetch(`/api/monitor/portfolio-stats/${monitoringPortfolioId}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            updateMonitorTable(data.data);
        }
    } catch (error) {
        console.error('Error updating monitor data:', error);
    }
}

// 更新监控表格
function updateMonitorTable(data) {
    // 更新表头
    const headerRow = document.getElementById('monitorTableHeader');
    headerRow.innerHTML = `
        <th style="width: 150px;">指标</th>
        ${data.map(point => `
            <th>${formatDateTime(point.time)}</th>
        `).join('')}
    `;
    
    // 更新数据行
    const tbody = document.getElementById('monitorTableBody');
    const rows = tbody.querySelectorAll('tr');
    
    // 预处理数据，避免重复计算
    const processedData = data.map(point => {
        // 计算多空数量
        let longCount = 0;
        let shortCount = 0;
        Object.values(point.positions || {}).forEach(equity => {
            if (equity > 0) longCount++;
            else if (equity < 0) shortCount++;
        });
        
        return {
            time: point.time,
            current_equity: point.current_equity,
            contracts_count: point.contracts_count,
            long_count: longCount,
            short_count: shortCount,
            net_position: longCount - shortCount,
            max_equity: point.max_equity,
            max_equity_time: point.max_equity_time,
            drawdown_days: point.drawdown_days,
            current_drawdown: point.current_drawdown,
            max_drawdown: point.max_drawdown
        };
    });
    
    // 更新表格内容
    // 当前权益
    rows[0].innerHTML = `
        <td>当前权益</td>
        ${processedData.map(stat => `
            <td>${formatNumber(stat.current_equity)}</td>
        `).join('')}
    `;
    
    // 过去一年最高权益
    rows[1].innerHTML = `
        <td>过去一年最高权益</td>
        ${processedData.map(stat => `
            <td>${formatNumber(stat.max_equity)}</td>
        `).join('')}
    `;
    
    // 发生时间
    rows[2].innerHTML = `
        <td>发生时间</td>
        ${processedData.map(stat => `
            <td>${formatDateTime(stat.max_equity_time)}</td>
        `).join('')}
    `;
    
    // 当前回撤
    rows[3].innerHTML = `
        <td>当前回撤</td>
        ${processedData.map(stat => `
            <td>${formatPercent(stat.current_drawdown)}</td>
        `).join('')}
    `;
    
    // 回撤时间
    rows[4].innerHTML = `
        <td>回撤时间</td>
        ${processedData.map(stat => `
            <td class="${stat.drawdown_days > 90 ? 'text-danger' : ''}">${stat.drawdown_days}天</td>
        `).join('')}
    `;
    
    // 过去一年最大回撤
    rows[5].innerHTML = `
        <td>过去一年最大回撤</td>
        ${processedData.map(stat => `
            <td>${formatPercent(stat.max_drawdown)}</td>
        `).join('')}
    `;
    
    // 品种总数
    rows[6].innerHTML = `
        <td>品种总数</td>
        ${processedData.map(stat => `
            <td>${stat.contracts_count}</td>
        `).join('')}
    `;
    
    // 品种多空
    rows[7].innerHTML = `
        <td>品种多空</td>
        ${processedData.map(stat => `
            <td>${stat.long_count}/${stat.short_count}</td>
        `).join('')}
    `;
    
    // 净多空
    rows[8].innerHTML = `
        <td>净多空</td>
        ${processedData.map(stat => `
            <td>${stat.net_position}</td>
        `).join('')}
    `;
}

// 格式化数字
function formatNumber(num) {
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

// 初始化监控功能
document.addEventListener('DOMContentLoaded', initializeMonitor); 