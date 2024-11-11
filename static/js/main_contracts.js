// 保存当前排序状态和选中的交易所
let currentSort = {
    column: null,
    direction: 'asc'
};
let selectedExchanges = new Set();

// 添加筛选条件状态
let filterConditions = {
    weekAmount: null,
    weekAmplitude: null,
    monthAmount: null,
    amount: null
};

// 初始化主力合约模块
function initializeMainContracts() {
    loadMainContracts();
    
    // 添加交易所筛选事件
    document.querySelectorAll('#exchangeFilter button').forEach(button => {
        if (button.dataset.exchange !== 'ALL') {  // 移除全部按钮的处理
            button.addEventListener('click', function() {
                // 切换选中状态
                this.classList.toggle('active');
                
                // 更新选中的交易所集合
                const exchange = this.dataset.exchange;
                if (this.classList.contains('active')) {
                    selectedExchanges.add(exchange);
                } else {
                    selectedExchanges.delete(exchange);
                }
                
                filterMainContracts();
            });
        }
    });
    
    // 添加排序事件
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', function() {
            const column = this.dataset.sort;
            sortMainContracts(column);
        });
    });
    
    // 添加合约点击事件
    document.querySelector('.main-contracts-list').addEventListener('click', function(e) {
        const row = e.target.closest('tr');
        if (row) {
            // 移除其他行的选中状态
            document.querySelectorAll('.main-contracts-list tr').forEach(tr => 
                tr.classList.remove('selected'));
            
            // 添加选中状态
            row.classList.add('selected');
            
            // 获取合约代码
            const tsCode = row.querySelector('td:nth-child(2)').textContent.trim();
            loadContractDetails(tsCode);
        }
    });
    
    // 添加筛选按钮事件
    document.getElementById('applyFilters').addEventListener('click', applyFilters);
    document.getElementById('resetFilters').addEventListener('click', resetFilters);
}

// 加载主力合约列表
async function loadMainContracts() {
    try {
        console.log('Loading main contracts...');
        const response = await fetch('/api/main-contracts');
        const data = await response.json();
        
        console.log('Response:', data);
        
        if (data.status === 'success') {
            window.mainContractsData = data.data;
            console.log('Loaded contracts:', window.mainContractsData.length);
            updateMainContractsList(data.data);
        } else {
            console.error('Failed to load contracts:', data.message);
        }
    } catch (error) {
        console.error('Error loading main contracts:', error);
    }
}

// 更新主力合约列表显示
function updateMainContractsList(contracts) {
    const tbody = document.querySelector('.main-contracts-list');
    tbody.innerHTML = contracts.map((contract, index) => `
        <tr data-exchange="${contract.exchange}" class="${index < 10 ? 'table-danger' : ''}">
            <td>${index + 1}</td>
            <td><strong>${contract.ts_code}</strong></td>
            <td>${contract.name}</td>
            <td><span class="badge bg-secondary">${contract.exchange}</span></td>
            <td>${formatNumber(contract.volume)}</td>
            <td>${formatNumber(contract.oi)}</td>
            <td>${formatNumber(contract.latest_amount)}</td>
            <td>${formatPercent(contract.latest_amplitude)}</td>
            <td>${formatNumber(contract.week_amount)}</td>
            <td>${formatPercent(contract.week_amplitude)}</td>
            <td>${formatNumber(contract.month_amount)}</td>
            <td>${formatPercent(contract.month_amplitude)}</td>
            <td>${formatNumber(contract.month_low)}</td>
            <td>${formatNumber(contract.month_high)}</td>
            <td>${formatNumber(contract.close_price)}</td>
            <td>${formatPercent(contract.price_position)}</td>
        </tr>
    `).join('');
}

// 格式化数字
function formatNumber(num) {
    return num ? num.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : '-';
}

// 格式化百分比
function formatPercent(num) {
    return num ? num.toFixed(2) + '%' : '-';
}

// 过滤主力合约列表
function filterMainContracts() {
    filterAndSortContracts();
}

// 加载合约详情
async function loadContractDetails(tsCode) {
    try {
        const response = await fetch(`/api/contract-details/${tsCode}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            updateRecentQuotes(data.data.daily_data);
            updateRelatedContracts(data.data.related_contracts);
            document.getElementById('selectedContractCode').textContent = tsCode;
        }
    } catch (error) {
        console.error('Error loading contract details:', error);
    }
}

// 更新最近行情数据
function updateRecentQuotes(dailyData) {
    const tbody = document.getElementById('recentQuotesList');
    tbody.innerHTML = dailyData.map(item => `
        <tr>
            <td>${item.date}</td>
            <td>${formatNumber(item.close)}</td>
            <td class="${item.change_rate >= 0 ? 'text-success' : 'text-danger'}">
                ${formatPercent(item.change_rate)}
            </td>
            <td>${formatNumber(item.amount)}</td>
            <td>${formatNumber(item.oi)}</td>
        </tr>
    `).join('');
}

// 更新相关合约列表
function updateRelatedContracts(contracts) {
    const tbody = document.getElementById('relatedContractsList');
    tbody.innerHTML = contracts.map(contract => `
        <tr>
            <td>${contract.ts_code}</td>
            <td>${formatNumber(contract.close)}</td>
            <td>${formatNumber(contract.amount)}</td>
            <td>${formatNumber(contract.oi)}</td>
        </tr>
    `).join('');
}

// 排序主力合约
function sortMainContracts(column) {
    if (!window.mainContractsData) return;
    
    // 更新排序状态
    if (currentSort.column === column) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.direction = 'asc';
    }
    
    // 更新排序图标
    updateSortIcons(column);
    
    // 应用筛选和排序
    filterAndSortContracts();
}

// 更新排序图标
function updateSortIcons(column) {
    document.querySelectorAll('.sortable').forEach(header => {
        // 移除所有排序图标
        header.classList.remove('sort-asc', 'sort-desc');
        
        if (header.dataset.sort === column) {
            header.classList.add(
                currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc'
            );
        }
    });
}

// 应用筛选条件
function applyFilters() {
    // 获取筛选条件
    filterConditions.weekAmount = parseFloat(document.getElementById('weekAmountFilter').value) || null;
    filterConditions.weekAmplitude = parseFloat(document.getElementById('weekAmplitudeFilter').value) || null;
    filterConditions.monthAmount = parseFloat(document.getElementById('monthAmountFilter').value) || null;
    filterConditions.amount = parseFloat(document.getElementById('amountFilter').value) || null;
    
    // 应用筛选
    filterAndSortContracts();
}

// 重置筛选条件
function resetFilters() {
    // 清空输入框
    document.getElementById('weekAmountFilter').value = '';
    document.getElementById('weekAmplitudeFilter').value = '';
    document.getElementById('monthAmountFilter').value = '';
    document.getElementById('amountFilter').value = '';
    
    // 重置筛选条件
    filterConditions = {
        weekAmount: null,
        weekAmplitude: null,
        monthAmount: null,
        amount: null
    };
    
    // 重新应用筛选
    filterAndSortContracts();
}

// 过滤和排序合约
function filterAndSortContracts() {
    if (!window.mainContractsData) return;
    
    // 应用所有筛选条件
    let filteredData = window.mainContractsData;
    
    // 交易所筛选
    if (selectedExchanges.size > 0) {
        filteredData = filteredData.filter(contract => 
            selectedExchanges.has(contract.exchange)
        );
    }
    
    // 周总额筛选
    if (filterConditions.weekAmount !== null) {
        filteredData = filteredData.filter(contract => 
            contract.week_amount >= filterConditions.weekAmount
        );
    }
    
    // 周振幅筛选
    if (filterConditions.weekAmplitude !== null) {
        filteredData = filteredData.filter(contract => 
            contract.week_amplitude >= filterConditions.weekAmplitude
        );
    }
    
    // 月总额筛选
    if (filterConditions.monthAmount !== null) {
        filteredData = filteredData.filter(contract => 
            contract.month_amount >= filterConditions.monthAmount
        );
    }
    
    // 日成交额筛选
    if (filterConditions.amount !== null) {
        filteredData = filteredData.filter(contract => 
            contract.latest_amount >= filterConditions.amount
        );
    }
    
    // 应用排序（如果有）
    if (currentSort.column) {
        filteredData = [...filteredData].sort((a, b) => {
            const aValue = a[currentSort.column] || 0;
            const bValue = b[currentSort.column] || 0;
            return currentSort.direction === 'asc' ? 
                aValue - bValue : 
                bValue - aValue;
        });
    }
    
    // 更新显示
    updateMainContractsList(filteredData);
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('data-main')) {
        initializeMainContracts();
    }
}); 