document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');
    
    // 初始化机会筛选模块（只在相关页面初始化）
    const filterTab = document.getElementById('data-filter');
    if (filterTab) {
        console.log('Initializing filter module...');
        initializeFilterModule();
    }
    
    // 初始化监控功能
    if (document.getElementById('data-display')) {
        console.log('Initializing monitor...');
        initializeMonitor();
    }
});

function initializeElements() {
    // 获取所有按钮和进度条元素
    const elements = {
        // 行情数据相关元素
        fetchQuotesBtn: document.getElementById('fetchQuotesBtn'),
        fetchMainQuotesBtn: document.getElementById('fetchMainQuotesBtn'),
        cancelQuotesFetchBtn: document.getElementById('cancelQuotesFetchBtn'),
        quotesProgress: document.getElementById('quotesProgress'),
        
        // 持仓数据相关元素
        fetchHoldingsBtn: document.getElementById('fetchHoldingsBtn'),
        cancelHoldingsFetchBtn: document.getElementById('cancelHoldingsFetchBtn'),
        holdingsProgress: document.getElementById('holdingsProgress'),
        
        // 共用元素
        fetchInfo: document.querySelector('.fetch-info'),
        fetchTime: document.getElementById('fetchTime'),
        fetchStatus: document.getElementById('fetchStatus'),
        currentProcess: document.getElementById('currentProcess'),
        processedCount: document.getElementById('processedCount'),
        fetchLog: document.getElementById('fetchLog')
    };

    // 检查所有必需的元素是否存在
    const missingElements = Object.entries(elements)
        .filter(([key, element]) => !element)
        .map(([key]) => key);

    if (missingElements.length > 0) {
        console.warn('Missing elements:', missingElements);
        return;  // 如果有缺失元素，不继续执行
    }

    // 添加行情数据获取按钮事件监听器
    if (elements.fetchQuotesBtn) {
        elements.fetchQuotesBtn.addEventListener('click', () => handleFetchData('quotes', elements));
    }

    // 添加行情数据获取按钮事件监听器
    if (elements.fetchMainQuotesBtn) {
        elements.fetchMainQuotesBtn.addEventListener('click', () => handleFetchData('mainquotes', elements));
    }

    // 添加持仓数据获取按钮事件监听器
    if (elements.fetchHoldingsBtn) {
        elements.fetchHoldingsBtn.addEventListener('click', () => handleFetchData('holdings', elements));
    }

    // 添加取消按钮事件监听器
    if (elements.cancelQuotesFetchBtn) {
        elements.cancelQuotesFetchBtn.addEventListener('click', () => handleCancelFetch('quotes', elements));
    }

    if (elements.cancelHoldingsFetchBtn) {
        elements.cancelHoldingsFetchBtn.addEventListener('click', () => handleCancelFetch('holdings', elements));
    }

    // 初始化页面加载时的显示
    loadFuturesDisplay();
}

// 处理数据获取
async function handleFetchData(type, elements) {
    const config = {
        quotes: {
            button: elements.fetchQuotesBtn,
            cancelButton: elements.cancelQuotesFetchBtn,
            progress: elements.quotesProgress,
            endpoint: '/api/update-quotes',
            cleanupFunction: () => cleanupFetchProcess('quotes', elements)
        },
        mainquotes: {
            button: elements.fetchMainQuotesBtn,
            endpoint: '/api/fetch-mainquotes',
            cleanupFunction: () => cleanupFetchProcess('mainquotes', elements)
        },
        holdings: {
            button: elements.fetchHoldingsBtn,
            cancelButton: elements.cancelHoldingsFetchBtn,
            progress: elements.holdingsProgress,
            endpoint: '/api/fetch-holdings',
            cleanupFunction: () => cleanupFetchProcess('holdings', elements)
        }
    };

    const currentConfig = config[type];

    try {
        // 更新UI状态
        currentConfig.button.disabled = true;
        currentConfig.button.querySelector('.spinner-border').classList.remove('d-none');
        currentConfig.cancelButton.classList.remove('d-none');
        currentConfig.progress.classList.remove('d-none');
        elements.fetchInfo.classList.remove('d-none');
        elements.fetchTime.textContent = `开始时间：${new Date().toLocaleString()}`;
        elements.fetchStatus.textContent = '运行中';
        elements.fetchStatus.className = 'badge bg-primary';

        // 发起数据获取请求
        const response = await fetch(currentConfig.endpoint, {
            method: 'POST'
        });

        // 启动状态更新定时器
        const statusInterval = setInterval(async () => {
            try {
                const statusResponse = await fetch('/api/update-status');
                const statusData = await statusResponse.json();
                
                if (statusData.status) {
                    // 更新状态显示
                    updateFetchStatus(statusData.status, elements);
                    
                    // 更新进度条
                    if (statusData.progress !== undefined) {
                        const progressBar = currentConfig.progress.querySelector('.progress-bar');
                        if (progressBar) {
                            progressBar.style.width = `${statusData.progress}%`;
                            progressBar.setAttribute('aria-valuenow', statusData.progress);
                            progressBar.textContent = `${statusData.progress}%`;
                        }
                    }
                    
                    // 检查是否完成
                    if (['completed', 'cancelled', 'error'].includes(statusData.status.status)) {
                        clearInterval(statusInterval);
                        currentConfig.cleanupFunction();
                    }
                }
            } catch (error) {
                console.error(`Error fetching ${type} status:`, error);
            }
        }, 1000);

    } catch (error) {
        console.error(`Error fetching ${type} data:`, error);
        currentConfig.cleanupFunction();
        alert(`${type} 数据获取失败`);
    }
}

// 处理取消操作
async function handleCancelFetch(type, elements) {
    try {
        const response = await fetch('/api/cancel-update', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            if (type === 'quotes') {
                cleanupFetchProcess('quotes', elements);
            } else {
                cleanupFetchProcess('holdings', elements);
            }
            
            updateFetchStatus({
                status: 'cancelled',
                current_process: '-',
                updated_count: 0,
                logs: [`${type} 数据获取已取消`]
            }, elements);
        } else {
            alert(data.message);
        }
    } catch (error) {
        console.error(`Error cancelling ${type} fetch:`, error);
        alert(`取消${type}获取失败`);
    }
}

// 更新状态显示
function updateFetchStatus(status, elements) {
    if (!status) return;
    
    // 更新状态标签
    if (elements.fetchStatus) {
        elements.fetchStatus.textContent = getStatusText(status.status);
        elements.fetchStatus.className = `badge bg-${getStatusColor(status.status)}`;
    }
    
    // 更新当前处理信息
    if (elements.currentProcess) {
        elements.currentProcess.textContent = status.current_process || '-';
    }
    
    // 更新处理数量
    if (elements.processedCount) {
        elements.processedCount.textContent = status.updated_count || 0;
    }
    
    // 更新日志信息
    if (elements.fetchLog && status.logs) {
        // 保留最新的50条日志
        const logs = status.logs.slice(-50);
        elements.fetchLog.innerHTML = logs.map(log => 
            `<div class="log-entry">${log}</div>`
        ).join('');
        
        // 自动滚动到底部
        elements.fetchLog.scrollTop = elements.fetchLog.scrollHeight;
    }
}

// 更新进度条
function updateProgress(progress, progressElement) {
    const progressBar = progressElement.querySelector('.progress-bar');
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', progress);
    progressBar.textContent = `${progress}%`;
}

// 清理进程
function cleanupFetchProcess(type, elements) {
    const config = {
        quotes: {
            button: elements.fetchQuotesBtn,
            cancelButton: elements.cancelQuotesFetchBtn,
            progress: elements.quotesProgress
        },
        mainquotes: {
            button: elements.fetchMainQuotesBtn,
        },
        holdings: {
            button: elements.fetchHoldingsBtn,
            cancelButton: elements.cancelHoldingsFetchBtn,
            progress: elements.holdingsProgress
        }
    };

    const currentConfig = config[type];
    
    // 恢复钮状态
    currentConfig.button.disabled = false;
    currentConfig.button.querySelector('.spinner-border').classList.add('d-none');
    currentConfig.cancelButton.classList.add('d-none');
    
    // 隐藏进度条
    setTimeout(() => {
        currentConfig.progress.classList.add('d-none');
        const progressBar = currentConfig.progress.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = '0%';
            progressBar.setAttribute('aria-valuenow', '0');
            progressBar.textContent = '0%';
        }
    }, 1000);
}

// 获取状态文本
function getStatusText(status) {
    const statusTexts = {
        'running': '运行中',
        'completed': '完成',
        'cancelled': '已',
        'error': '错误',
        'waiting': '等待中'
    };
    return statusTexts[status] || status;
}

// 获取状态颜色
function getStatusColor(status) {
    switch(status) {
        case 'running': return 'primary';
        case 'completed': return 'success';
        case 'cancelled': return 'warning';
        case 'error': return 'danger';
        default: return 'secondary';
    }
}

// 加载期货品种显示
async function loadFuturesDisplay() {
    try {
        const response = await fetch('/api/futures-by-exchange');
        const data = await response.json();
        
        if (data.status === 'success') {
            Object.entries(data.data).forEach(([exchange, info]) => {
                const buttonContainer = document.getElementById(`${exchange}-buttons`);
                if (buttonContainer) {
                    buttonContainer.innerHTML = info.products.map(product => `
                        <div class="col-6 col-md-4 col-lg-2">
                            <button class="btn btn-outline-primary w-100 product-btn" 
                                    data-base-name="${product.name}"
                                    data-exchange="${exchange}">
                                ${product.display_name}
                            </button>
                        </div>
                    `).join('');
                }
            });
            
            // 添加品种按钮点击事件
            document.querySelectorAll('.product-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const baseName = this.dataset.baseName;
                    const exchange = this.dataset.exchange;
                    loadContracts(baseName, exchange, this);
                });
            });
        }
    } catch (error) {
        console.error('Error loading futures:', error);
    }
}

// 加载合约列表
async function loadContracts(baseName, exchange, button) {
    try {
        // 移除其他按钮的活动状态
        document.querySelectorAll('.product-btn').forEach(btn => 
            btn.classList.remove('active'));
        // 添加当前按钮的活动状态
        button.classList.add('active');
        
        const response = await fetch(`/api/contracts/${encodeURIComponent(baseName)}/${exchange}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            // 显示合约列表区域
            const contractsDiv = button.closest('.tab-pane')
                .querySelector('.futures-contracts');
            contractsDiv.classList.remove('d-none');
            
            // 更新表格内容
            const tbody = contractsDiv.querySelector('tbody');
            tbody.innerHTML = data.data.map(contract => `
                <tr data-ts-code="${contract.ts_code}" data-contract-name="${contract.name}">
                    <td>${contract.ts_code}</td>
                    <td>${contract.name}</td>
                    <td>
                        <span class="badge bg-${getContractTypeColor(contract.contract_type)}">
                            ${getContractTypeText(contract.contract_type)}
                        </span>
                    </td>
                    <td>${contract.list_date}</td>
                    <td>${contract.delist_date}</td>
                    <td>
                        <span class="badge bg-${contract.status === '交易中' ? 'success' : 'secondary'}">
                            ${contract.status}
                        </span>
                    </td>
                </tr>
            `).join('');
            
            // 添加行点击事件
            tbody.querySelectorAll('tr').forEach(row => {
                row.addEventListener('click', async function() {
                    const tsCode = this.dataset.tsCode;
                    const contractName = this.dataset.contractName;
                    await loadInstitutionHoldings(tsCode, contractName);
                });
            });
            
            // 如果是主力合约，加载机构持仓数据
            const mainContract = data.data.find(contract => contract.contract_type === 'main');
            if (mainContract) {
                await loadInstitutionHoldings(mainContract.ts_code, mainContract.name);
            } else {
                clearInstitutionHoldings();
            }
        }
    } catch (error) {
        console.error('Error loading contracts:', error);
    }
}

// 获取合约类型颜色
function getContractTypeColor(type) {
    switch(type) {
        case 'main': return 'primary';
        case 'continuous': return 'success';
        case 'index': return 'warning';
        default: return 'secondary';
    }
}

// 获取合约类型文本
function getContractTypeText(type) {
    switch(type) {
        case 'main': return '主力(M)';
        case 'continuous': return '连续(C)';
        case 'index': return '指数(I)';
        default: return '普通';
    }
}

// 加载机构持仓数据
async function loadInstitutionHoldings(tsCode, contractName) {
    try {
        const response = await fetch(`/api/holdings/${tsCode}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            document.getElementById('holdingContractName').textContent = contractName;
            
            // 更新日期按钮
            const tradeDateButtons = document.getElementById('tradeDateButtons');
            tradeDateButtons.innerHTML = data.data.dates.map((date, index) => `
                <button type="button" class="btn btn-outline-secondary ${index === 0 ? 'active' : ''}" 
                        data-trade-date="${date}">
                    ${formatDate(date)}
                </button>
            `).join('');
            
            // 添加日期按钮点击事件
            tradeDateButtons.querySelectorAll('button').forEach(btn => {
                btn.addEventListener('click', async function() {
                    // 更新按钮状态
                    tradeDateButtons.querySelectorAll('button').forEach(b => 
                        b.classList.remove('active'));
                    this.classList.add('active');
                    
                    // 加载对应日期的数据
                    const dateResponse = await fetch(`/api/holdings/${tsCode}/${this.dataset.tradeDate}`);
                    const dateData = await dateResponse.json();
                    if (dateData.status === 'success') {
                        updateHoldingsTable(dateData.data, 'long');
                    }
                });
            });
            
            // 显示最新日期的数据
            updateHoldingsTable(data.data.holdings, 'long');
            
            // 添加持仓类型切换事件
            document.querySelectorAll('[data-holding-type]').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('[data-holding-type]').forEach(b => 
                        b.classList.remove('active'));
                    this.classList.add('active');
                    updateHoldingsTable(data.data.holdings, this.dataset.holdingType);
                });
            });
        }
    } catch (error) {
        console.error('Error loading holdings:', error);
    }
}

// 格式化期显示
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', {
        month: 'numeric',
        day: 'numeric'
    });
}

// 更新持仓排名表格
function updateHoldingsTable(data, type) {
    const tbody = document.getElementById('holdingRankBody');
    let sortedData;
    
    switch(type) {
        case 'long':
            sortedData = [...data].sort((a, b) => b.long_hld - a.long_hld)
                .map(row => ({
                    value: row.long_hld,
                    change: row.long_chg,
                    broker: row.broker,
                    ts_code: row.ts_code,
                    trade_date: row.trade_date
                }));
            break;
        case 'short':
            sortedData = [...data].sort((a, b) => b.short_hld - a.short_hld)
                .map(row => ({
                    value: row.short_hld,
                    change: row.short_chg,
                    broker: row.broker,
                    ts_code: row.ts_code,
                    trade_date: row.trade_date
                }));
            break;
        case 'vol':
            sortedData = [...data].sort((a, b) => b.vol - a.vol)
                .map(row => ({
                    value: row.vol,
                    change: row.vol_chg,
                    broker: row.broker,
                    ts_code: row.ts_code,
                    trade_date: row.trade_date
                }));
            break;
    }
    
    // 显示所有记录
    tbody.innerHTML = sortedData.map((row, index) => `
        <tr>
            <td>${index + 1}</td>
            <td>${row.broker}</td>
            <td>${formatNumber(row.value)}</td>
            <td>
                <span class="badge bg-${row.change > 0 ? 'success' : row.change < 0 ? 'danger' : 'secondary'}">
                    ${row.change > 0 ? '+' : ''}${formatNumber(row.change)}
                </span>
            </td>
            <td>${row.ts_code}</td>
            <td>${row.trade_date}</td>
        </tr>
    `).join('');
}

// 清空机构持仓显示
function clearInstitutionHoldings() {
    const holdingContractName = document.getElementById('holdingContractName');
    const holdingRankBody = document.getElementById('holdingRankBody');
    if (holdingContractName) holdingContractName.textContent = '';
    if (holdingRankBody) holdingRankBody.innerHTML = '';
}

// 格式化数字显示
function formatNumber(num) {
    // 如果是 0，直接返回 "0"
    if (num === 0) return "0";
    
    // 如果是 undefined, null 或者 NaN，直接返回 "0"
    if (num === undefined || num === null || isNaN(num)) return "0";
    
    // 四舍五入到整数
    return Math.round(num).toLocaleString('zh-CN');
}

// 初始化机会筛选模块
function initializeFilterModule() {
    // 加载所有交易所的合约
    document.querySelectorAll('.available-contracts').forEach(container => {
        const exchange = container.dataset.exchange;
        loadAvailableContracts(exchange);
    });

    // 添加按钮点击事件
    document.querySelector('.add-contract').addEventListener('click', () => moveSelectedContracts('add'));
    document.querySelector('.remove-contract').addEventListener('click', () => moveSelectedContracts('remove'));
    document.querySelector('.clear-selected').addEventListener('click', clearSelectedContracts);
    
    // 初始化组合管理功能
    initializePortfolioManagement();

    // 添加标签页切换事件
    document.querySelectorAll('#filterExchangeTabs button[data-bs-toggle="tab"]').forEach(button => {
        button.addEventListener('click', function (event) {
            event.preventDefault();
            const targetId = this.dataset.bsTarget;
            const newExchange = targetId.replace('#filter-', '');
            
            document.querySelectorAll('#filterExchangeTabs button').forEach(btn => {
                btn.classList.remove('active');
            });
            this.classList.add('active');
            
            document.querySelectorAll('#filterExchangeContent .tab-pane').forEach(pane => {
                pane.classList.remove('show', 'active');
            });
            document.querySelector(targetId).classList.add('show', 'active');
            
            loadAvailableContracts(newExchange);
        });
    });

    // 添加筛选按钮事件监听
    document.querySelector('.filter-equity').addEventListener('click', () => {
        const selectedContracts = Array.from(
            document.querySelectorAll('.selected-contracts .list-group-item')
        ).map(item => item.dataset.contractCode);

        if (selectedContracts.length === 0) {
            // 如果没有选择合约，显示所有数据
            loadInitialEquityData();
        } else {
            // 有选择合约时才进行筛选
            filterEquityData();
        }
    });

    // 最后加载初始权益数据（显示所有数据）
    loadInitialEquityData();
}

// 保存最新获取的权益数据
let currentEquityData = null;

// 修改加载初始权益数据函数
async function loadInitialEquityData() {
    try {
        console.log('Loading initial equity data...');
        
        const response = await fetch('/api/initial-equity-data');
        const data = await response.json();
        
        if (data.status === 'success') {
            // 保存数据到全局变量
            currentEquityData = data.data;
            // 显示所有数据
            updateEquityTables(currentEquityData);
        } else {
            console.error('Failed to load equity data:', data.message);
        }
    } catch (error) {
        console.error('Error loading initial equity data:', error);
    }
}

// 修改筛选权益数据的函数
function filterEquityData() {
    if (!currentEquityData) {
        console.error('No equity data available');
        return;
    }

    // 获取已选合约列表
    const selectedContracts = Array.from(
        document.querySelectorAll('.selected-contracts .list-group-item')
    ).map(item => item.dataset.contractCode.toUpperCase());  // 转换为大写

    console.log('Selected contracts for filtering:', selectedContracts);

    if (selectedContracts.length === 0) {
        // 如果没有选择合约，显示所有数据
        updateEquityTables(currentEquityData);
        return;
    }

    // 在前端筛选数据
    const filteredData = {
        latest_equity: {
            times: currentEquityData.latest_equity.times,
            equities: {}
        },
        previous_equity: {
            dates: currentEquityData.previous_equity.dates,
            equities: {}
        }
    };

    // 筛选半小时净盈亏数据
    for (const [code, data] of Object.entries(currentEquityData.latest_equity.equities)) {
        if (selectedContracts.includes(code.toUpperCase())) {
            filteredData.latest_equity.equities[code] = {
                position: data.position,
                profits: data.profits
            };
        }
    }

    // 筛选相对权益数据
    for (const [code, data] of Object.entries(currentEquityData.previous_equity.equities)) {
        if (selectedContracts.includes(code.toUpperCase())) {
            filteredData.previous_equity.equities[code] = data;
        }
    }

    console.log('Filtered data:', filteredData);

    // 更新表格显示
    updateEquityTables(filteredData);
}

// 修改更新表格的通用函数
function updateEquityTables(data) {
    if (!data) return;
    console.log('Updating tables with data:', data);
    updateLatestEquityTable(data.latest_equity);
    updatePreviousEquityTable(data.previous_equity);
    addSortingFunctionality();
}

// 修改移动合约的函数
function moveSelectedContracts(action) {
    const currentExchange = document.querySelector('#filterExchangeTabs .active').dataset.bsTarget.replace('#filter-', '');
    const sourceContainer = action === 'add' 
        ? document.querySelector(`.available-contracts[data-exchange="${currentExchange}"]`)
        : document.querySelector('.selected-contracts');
        
    const targetContainer = action === 'add'
        ? document.querySelector('.selected-contracts')
        : document.querySelector(`.available-contracts[data-exchange="${currentExchange}"]`);
    
    const selectedItems = sourceContainer.querySelectorAll('.list-group-item.active');
    
    selectedItems.forEach(item => {
        // 检查目标容器中是否已存在该品种
        const existingItem = targetContainer.querySelector(`[data-contract-name="${item.dataset.contractName}"]`);
        if (!existingItem) {
            // 移除选中状态
            item.classList.remove('active');
            // 移动到目标容器
            const newItem = item.cloneNode(true);
            targetContainer.appendChild(newItem);
            // 为移动后的项目加点击事件
            newItem.addEventListener('click', function() {
                this.classList.toggle('active');
            });
        }
    });
    
    // 移除原始选中项的选中状态或删除
    if (action === 'add') {
        selectedItems.forEach(item => item.classList.remove('active'));
    } else {
        selectedItems.forEach(item => item.remove());
    }
}

// 修改清空合约的函数
function clearSelectedContracts() {
    const selectedContainer = document.querySelector('.selected-contracts');
    if (selectedContainer) {
        selectedContainer.innerHTML = '';
        
        // 重新加载当前交易所的备选合约列表
        const currentExchange = document.querySelector('#filterExchangeTabs .active')
            .dataset.bsTarget.replace('#filter-', '');
        loadAvailableContracts(currentExchange);

        // 显示所有权益数据
        updateEquityTables(currentEquityData);
    }
}

// 更新最新权益数据表格
function updateLatestEquityTable(data) {
    if (!data || !data.times || !data.equities) return;
    
    // 更新表头时间
    data.times.forEach((time, index) => {
        const th = document.getElementById(`time-${index}`);
        if (th) th.textContent = time;
    });
    
    // 转换为数组并按最新时间点的盈亏排序
    const latestTime = data.times[0];
    const sortedData = Object.entries(data.equities)
        .map(([code, info]) => ({
            code,
            position: info.position || 0,  // 添加position字段
            profits: data.times.map(time => {
                const value = info.profits ? info.profits[time] : 0;
                return typeof value === 'number' ? value : 0;
            })
        }))
        .sort((a, b) => (b.profits[0] || 0) - (a.profits[0] || 0));
    
    const tbody = document.getElementById('latestEquityTable');
    tbody.innerHTML = sortedData.map((item, index) => {
        const bgClass = index < 30 && index % 5 === 0 ? 'bg-info bg-opacity-10' : '';
        
        // 添加方向显示
        const positionText = item.position === 1 ? '多' : 
                           item.position === -1 ? '空' : '-';
        const positionClass = item.position === 1 ? 'text-success' : 
                            item.position === -1 ? 'text-danger' : '';
        
        return `
            <tr class="${bgClass}">
                <td>${item.code}</td>
                <td class="${positionClass}">${positionText}</td>
                ${item.profits.map(profit => {
                    const profitClass = profit > 0 ? 'text-success' : profit < 0 ? 'text-danger' : '';
                    return `<td class="text-end ${profitClass}">${formatNumber(profit)}</td>`;
                }).join('')}
            </tr>
        `;
    }).join('');
}

// 更新历史权益数据表格（显示最近5个交易日14:30的相对权益）
function updatePreviousEquityTable(data) {
    if (!data || !data.dates || !data.equities) return;
    
    // 更新表头日期
    data.dates.forEach((date, index) => {
        const th = document.getElementById(`date-${index}`);
        if (th) th.textContent = date;
    });
    
    // 转换为数组并按最新日期的权益排序
    const latestDate = data.dates[0];
    const sortedData = Object.entries(data.equities)
        .map(([code, equities]) => ({
            code,
            equities: data.dates.map(date => {
                const value = equities[date];
                // 确保返回数字，包括0
                return typeof value === 'number' ? value : 0;
            })
        }))
        .sort((a, b) => (b.equities[0] || 0) - (a.equities[0] || 0));
    
    const tbody = document.getElementById('previousEquityTable');
    tbody.innerHTML = sortedData.map((item, index) => {
        const bgClass = index < 30 && index % 5 === 0 ? 'bg-info bg-opacity-10' : '';
        
        return `
            <tr class="${bgClass}">
                <td>${item.code}</td>
                ${item.equities.map(equity => 
                    `<td class="text-end">${formatNumber(equity)}</td>`
                ).join('')}
            </tr>
        `;
    }).join('');
}

// 修改排序功能以保持背景色
function addSortingFunctionality() {
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', function() {
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const column = this.cellIndex;
            const isAsc = !this.classList.contains('sort-asc');
            
            // 移除所有排序标记
            table.querySelectorAll('.sortable').forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            
            // 添加新的排序标记
            this.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
            
            // 排序行
            rows.sort((a, b) => {
                const aValue = parseFloat(a.cells[column].textContent.replace(/[^\d.-]/g, ''));
                const bValue = parseFloat(b.cells[column].textContent.replace(/[^\d.-]/g, ''));
                return isAsc ? aValue - bValue : bValue - aValue;
            });
            
            // 重新插入排序后的行，并更新背景色
            tbody.innerHTML = '';
            rows.forEach((row, index) => {
                // 每5行使用一次浅蓝色背景
                const bgClass = index < 30 && index % 5 === 0 ? 'bg-info bg-opacity-10' : '';
                row.className = bgClass;
                tbody.appendChild(row);
            });
        });
    });
}

// 初始化组合管理功能
function initializePortfolioManagement() {
    console.log('Initializing portfolio management...');
    
    // 加载组合列表
    loadPortfolios();
    
    // 添加保存组合按钮的事件监听
    const saveButton = document.getElementById('savePortfolio');
    if (saveButton) {
        saveButton.addEventListener('click', savePortfolio);
        console.log('Save portfolio button listener added');
    }
}

// 加载组合列表
async function loadPortfolios() {
    try {
        const response = await fetch('/api/portfolios');
        const data = await response.json();
        
        if (data.status === 'success') {
            const container = document.querySelector('.portfolio-list');
            container.innerHTML = data.data.map(portfolio => `
                <div class="list-group-item d-flex justify-content-between align-items-center"
                     data-portfolio-id="${portfolio.id}"
                     data-portfolio-name="${portfolio.name}">
                    <span class="portfolio-name" style="cursor: pointer;">${portfolio.name}</span>
                    <button class="btn btn-sm btn-danger delete-portfolio">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `).join('');
            
            // 添加双击事件
            container.querySelectorAll('.portfolio-name').forEach(item => {
                item.addEventListener('dblclick', async function() {
                    console.log('Portfolio double clicked');
                    const portfolioId = this.parentElement.dataset.portfolioId;
                    const portfolioName = this.parentElement.dataset.portfolioName;
                    
                    // 加载组合合约
                    loadPortfolioContracts(portfolioId);
                    
                    // 加载组合历史权益数据
                    await loadPortfolioEquityHistory(portfolioId);
                    
                    // 更新组合名称输入框
                    document.getElementById('portfolioName').value = portfolioName;
                });
            });
            
            // 添加删除按钮事件
            container.querySelectorAll('.delete-portfolio').forEach(btn => {
                btn.addEventListener('click', function() {
                    const portfolioId = this.parentElement.dataset.portfolioId;
                    const portfolioName = this.parentElement.dataset.portfolioName;
                    deletePortfolio(portfolioId, portfolioName);
                });
            });
        }
    } catch (error) {
        console.error('Error loading portfolios:', error);
    }
}

// 加载组合历史权益数据
async function loadPortfolioEquityHistory(portfolioId) {
    try {
        console.log('Loading equity history for portfolio:', portfolioId);
        const response = await fetch(`/api/portfolio-history/${portfolioId}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            const tbody = document.getElementById('portfolioHistoryTable');
            if (!tbody) {
                console.error('Portfolio history table not found');
                return;
            }
            
            // 按时间倒序排列
            const sortedHistory = data.data.sort((a, b) => 
                new Date(b.time) - new Date(a.time)
            );
            
            // 更新表格内容
            tbody.innerHTML = sortedHistory.map(record => `
                <tr>
                    <td>${formatDateTime(record.time)}</td>
                    <td class="text-end">${formatNumber(record.total_equity)}</td>
                </tr>
            `).join('');
            
            console.log(`Updated history table with ${sortedHistory.length} records`);
        }
    } catch (error) {
        console.error('Error loading portfolio equity history:', error);
    }
}

// 格式化日期时间
function formatDateTime(dateStr) {
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

// 格式化数字
function formatNumber(num) {
    if (!num) return '-';
    return num.toLocaleString('zh-CN', { maximumFractionDigits: 0 });
}

// 保存组合
async function savePortfolio() {
    const portfolioName = document.getElementById('portfolioName').value.trim();
    
    // 获取已选合约列表
    const selectedContracts = Array.from(
        document.querySelectorAll('.selected-contracts .list-group-item')
    ).map(item => item.dataset.contractCode);
    
    // 获取手动输入的合约
    const manualInput = document.getElementById('manualContracts').value.trim();
    let manualContracts = [];
    if (manualInput) {
        // 处理多种分隔符：半角逗号、全角逗号、空格
        manualContracts = manualInput
            .replace(/，/g, ',')  // 替换全角逗号为半角逗号
            .split(/[,\s]+/)      // 按逗号或空格分割
            .map(code => code.trim().toUpperCase())  // 转换为大写并去除空格
            .filter(code => code); // 过滤空值
    }
    
    // 合并合约列表，去重
    const allContracts = [...new Set([...selectedContracts, ...manualContracts])];
    
    if (!portfolioName) {
        alert('请输入组合名称');
        return;
    }
    
    if (allContracts.length === 0) {
        alert('请至少选择或输入一个合约');
        return;
    }
    
    console.log('Saving portfolio:', {
        name: portfolioName,
        contracts: allContracts
    });
    
    try {
        const response = await fetch('/api/portfolios', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: portfolioName,
                contracts: allContracts
            })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            alert(data.message);  // 显示成功消息
            document.getElementById('portfolioName').value = '';  // 组合名称
            document.getElementById('manualContracts').value = '';  // 清空手动输入
            loadPortfolios();  // 重新加载组合列表
        } else {
            alert(data.message || '保存失败');
        }
    } catch (error) {
        console.error('Error saving portfolio:', error);
        alert('保存组合失败');
    }
}

// 加载组合合约时直接填充已选列表
async function loadPortfolioContracts(portfolioId) {
    try {
        const response = await fetch(`/api/portfolios/${portfolioId}/contracts`);
        const data = await response.json();
        
        if (data.status === 'success') {
            // 清空已选列表
            const selectedContainer = document.querySelector('.selected-contracts');
            selectedContainer.innerHTML = '';
            
            // 将合约添加到已选列表
            data.data.forEach(contract => {
                const item = document.createElement('div');
                item.className = 'list-group-item';
                item.dataset.contractCode = contract.fut_code;
                item.dataset.contractName = contract.fut_code;
                item.textContent = contract.fut_code;
                selectedContainer.appendChild(item);
                
                // 添加点击事件
                item.addEventListener('click', function() {
                    this.classList.toggle('active');
                });
            });
            
            // 新手输入框，使用半角逗号分隔
            document.getElementById('manualContracts').value = 
                data.data.map(contract => contract.fut_code).join(', ');
                
            // 重新加载当前交易所的备选合约列表
            const currentExchange = document.querySelector('#filterExchangeTabs .active')
                .dataset.bsTarget.replace('#filter-', '');
            loadAvailableContracts(currentExchange);
        }
    } catch (error) {
        console.error('Error loading portfolio contracts:', error);
    }
}

// 除组合
async function deletePortfolio(portfolioId, portfolioName) {
    if (!confirm(`确定要删除组合"${portfolioName}"吗？`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/portfolios/${portfolioId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            alert('组合删除成��');
            loadPortfolios();
        } else {
            alert(data.message || '删除失败');
        }
    } catch (error) {
        console.error('Error deleting portfolio:', error);
        alert('删除组合失败');
    }
}

// 添加CSS样式
const style = document.createElement('style');
style.textContent = `
    .log-entry {
        padding: 2px 4px;
        border-bottom: 1px solid #eee;
        font-size: 12px;
    }
    .log-entry:last-child {
        border-bottom: none;
    }
    #fetchLog {
        padding: 8px;
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 4px;
    }
`;
document.head.appendChild(style);

// 添加生成净值曲线按钮的事件监听
document.addEventListener('DOMContentLoaded', function() {
    const generateButton = document.querySelector('.generate-equity');
    if (generateButton) {
        generateButton.addEventListener('click', generateEquityCurve);
        console.log('Added click handler for generate equity button');
    }
});

// 更新按钮事件监听
//document.getElementById('updateBasic').addEventListener('click', function() {
//    startUpdate('/api/update-basic');
//});


//document.getElementById('updateHoldings').addEventListener('click', function() {
//    startUpdate('/api/update-holdings');
//});

// 取消按钮事件监听
//document.getElementById('cancelUpdate').addEventListener('click', function() {
//    fetch('/api/cancel-update')
//        .then(response => response.json())
//        .then(data => {
//            if (data.status === 'success') {
//                console.log('Update cancelled');
//            }
//        })
//        .catch(error => console.error('Error cancelling update:', error));
//});

// 通用的更新
function startUpdate(url) {
    // 更新按钮状态
    updateButtons.forEach(btn => btn.classList.add('d-none'));
    cancelButton.classList.remove('d-none');
    
    // 显示进度条
    progressBar.style.width = '0%';
    progressBar.textContent = '0%';
    progressContainer.classList.remove('d-none');
    
    // 清空日志
    fetchLog.innerHTML = '';
    
    // 发起更新请求，使用 POST 方法
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'error') {
            throw new Error(data.message);
        }
        // 开始轮询更新状态
        pollUpdateStatus();
    })
    .catch(error => {
        console.error('Error starting update:', error);
        showError(error.message);
        resetUpdateButtons();
    });
}

// 加载备选合约列表
async function loadAvailableContracts(exchange) {
    try {
        const response = await fetch(`/api/filter-contracts/${exchange}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            const container = document.querySelector(`.available-contracts[data-exchange="${exchange}"]`);
            const selectedContainer = document.querySelector('.selected-contracts');
            
            // 获取已合约的代码列表
            const selectedCodes = Array.from(selectedContainer.querySelectorAll('.list-group-item'))
                .map(item => item.dataset.contractCode);
            
            // 过滤掉已选的合约
            const availableContracts = data.data.filter(contract => 
                !selectedCodes.includes(contract.code)
            );
            
            // 更新备选列表
            container.innerHTML = availableContracts.map(contract => `
                <div class="list-group-item" 
                     data-contract-code="${contract.code}"
                     data-contract-name="${contract.name}">
                    ${contract.name}
                </div>
            `).join('');
            
            // 添加点击事件
            container.querySelectorAll('.list-group-item').forEach(item => {
                item.addEventListener('click', function() {
                    this.classList.toggle('active');
                });
            });
        }
    } catch (error) {
        console.error('Error loading contracts:', error);
    }
}

// 生成权益数据
async function generateEquityCurve() {
    try {
        console.log('Generating equity data...');
        // 获取已选合约列表
        const selectedItems = document.querySelectorAll('.selected-contracts .list-group-item');
        const contracts = Array.from(selectedItems).map(item => item.dataset.contractCode);
        
        if (contracts.length === 0) {
            alert('请先选择合约');
            return;
        }
        
        console.log('Selected contracts:', contracts);
        
        // 获取权益数据
        const response = await fetch('/api/equity-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ contracts })
        });
        
        const data = await response.json();
        console.log('Received data:', data);
        
        if (data.status === 'success') {
            // 更新最新权益数据表格
            updateLatestEquityTable(data.data.latest_equity);
            
            // 更新上一时间权益数据表格
            updatePreviousEquityTable(data.data.previous_equity);
            
            // 添加表头点击排序功能
            addSortingFunctionality();
        } else {
            alert(data.message || '获取数据失败');
        }
        
    } catch (error) {
        console.error('Error generating equity data:', error);
        alert('生成权益数据失败');
    }
}