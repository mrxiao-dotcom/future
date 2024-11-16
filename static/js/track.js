// 图表实例
let singleTrackChart = null;
let multiTrackChart = null;

// 选中的品种和组合
let selectedComponents = new Set();
let selectedPortfolios = new Set();

// 初始化资金追踪模块
function initializeTrackModule() {
    console.log('Initializing track module...');
    
    // 等待标签页显示后再初始化
    const trackTab = document.querySelector('[data-bs-target="#data-track"]');
    if (trackTab) {
        // 使用 Bootstrap 的 Tab 事件
        const tab = new bootstrap.Tab(trackTab);
        
        trackTab.addEventListener('shown.bs.tab', function() {
            console.log('Track tab shown, initializing components...');
            
            // 检查并初始化图表
            if (!singleTrackChart) {
                console.log('Initializing single track chart...');
                initializeSingleTrackChart();
            }
            if (!multiTrackChart) {
                console.log('Initializing multi track chart...');
                initializeMultiTrackChart();
            }
            
            // 加载组合列表
            loadTrackPortfolios();
            
            // 重新调整图表大小
            setTimeout(() => {
                if (singleTrackChart) {
                    console.log('Resizing single track chart...');
                    singleTrackChart.resize();
                }
                if (multiTrackChart) {
                    console.log('Resizing multi track chart...');
                    multiTrackChart.resize();
                }
            }, 100);
        });
    }
    
    // 监听子标签页切换
    const subTabs = document.querySelectorAll('#data-track .nav-tabs .nav-link');
    subTabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const targetId = event.target.getAttribute('data-bs-target').substring(1);
            handleTabSwitch(targetId);
        });
    });
}

// 初始化单品种图表
function initializeSingleTrackChart() {
    const chartDom = document.getElementById('singleTrackChart');
    if (!chartDom) {
        console.error('Single track chart container not found');
        return;
    }
    
    // 确保容器可见并且有尺寸
    chartDom.style.visibility = 'visible';
    chartDom.style.height = '100%';
    chartDom.style.minHeight = '300px';  // 添加最小高度
    
    console.log('Chart container dimensions:', {
        width: chartDom.clientWidth,
        height: chartDom.clientHeight
    });
    
    singleTrackChart = echarts.init(chartDom);
    
    const option = {
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                const date = params[0].axisValue;
                let html = `${date}<br/>`;
                params.forEach(param => {
                    html += `${param.seriesName}: ${formatNumber(param.value)}<br/>`;
                });
                return html;
            }
        },
        legend: {
            data: [],
            type: 'scroll',
            orient: 'horizontal',
            top: 0
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true,
            top: 30
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: []
        },
        yAxis: {
            type: 'value',
            scale: true
        },
        series: []
    };
    
    singleTrackChart.setOption(option);
    console.log('Single track chart initialized with options');
}

// 初始化多组合图表
function initializeMultiTrackChart() {
    const chartDom = document.getElementById('multiTrackChart');
    if (!chartDom) {
        console.error('Multi track chart container not found');
        return;
    }
    
    // 确保父容器有正确的高度
    const parentContainer = chartDom.closest('.flex-grow-1');
    if (parentContainer) {
        parentContainer.style.height = '100%';
        parentContainer.style.minHeight = '400px';  // 设置最小高度
    }
    
    // 设置图表容器的样式
    chartDom.style.width = '100%';
    chartDom.style.height = '100%';
    chartDom.style.minHeight = '400px';
    
    // 等待DOM更新后初始化图表
    setTimeout(() => {
        multiTrackChart = echarts.init(chartDom);
        
        const option = {
            tooltip: {
                trigger: 'axis',
                formatter: function(params) {
                    const date = params[0].axisValue;
                    let html = `${date}<br/>`;
                    params.forEach(param => {
                        html += `${param.seriesName}: ${formatNumber(param.value)}<br/>`;
                    });
                    return html;
                }
            },
            legend: {
                data: [],
                type: 'scroll',
                orient: 'horizontal',
                top: 0
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true,
                top: 30
            },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: []
            },
            yAxis: {
                type: 'value',
                scale: true
            },
            series: []
        };
        
        multiTrackChart.setOption(option);
        
        // 添加窗口大小变化的监听
        window.addEventListener('resize', () => {
            if (multiTrackChart) {
                multiTrackChart.resize();
            }
        });
        
        console.log('Multi track chart initialized with dimensions:', {
            containerWidth: chartDom.clientWidth,
            containerHeight: chartDom.clientHeight
        });
    }, 200);  // 增加延时确保DOM完全更新
}

// 加载组合列表
async function loadTrackPortfolios() {
    try {
        const response = await fetch('/api/portfolios');
        const data = await response.json();
        
        if (data.status === 'success') {
            const container = document.querySelector('.portfolio-track-list');
            if (!container) {
                console.error('Portfolio track list container not found');
                return;
            }
            
            // 渲染组合列表
            container.innerHTML = data.data.map((portfolio, index) => `
                <div class="list-group-item d-flex justify-content-between align-items-center" 
                     data-portfolio-id="${portfolio.id}"
                     data-portfolio-name="${portfolio.name}">
                    <div>
                        <span class="badge bg-secondary me-2">${index + 1}</span>
                        ${portfolio.name}
                    </div>
                </div>
            `).join('');
            
            // 更新标题
            const header = container.closest('.card').querySelector('.card-header h6');
            if (header) {
                header.innerHTML = `组合列表 <span class="badge bg-primary">${data.data.length}</span>`;
            }
            
            // 添加点击事件
            container.querySelectorAll('.list-group-item').forEach(item => {
                item.addEventListener('click', function() {
                    // 检查当前激活的标签页
                    const multiTrackTab = document.getElementById('multi-track');
                    const singleTrackTab = document.getElementById('single-track');
                    
                    // 切换选中状态
                    this.classList.toggle('active');
                    const portfolioId = this.dataset.portfolioId;
                    
                    if (this.classList.contains('active')) {
                        selectedPortfolios.add(portfolioId);
                        // 只在单品种标签页激活时加载成分
                        if (singleTrackTab && singleTrackTab.classList.contains('active')) {
                            loadPortfolioComponents(portfolioId);
                        }
                    } else {
                        selectedPortfolios.delete(portfolioId);
                        // 如果是单品种标签页，可能需要清空相关成分的选择
                        if (singleTrackTab && singleTrackTab.classList.contains('active')) {
                            // 可以选择是否清空成分列表
                            // clearComponentsList();
                        }
                    }
                    
                    // 根据当前标签页更新相应的图表
                    if (multiTrackTab && multiTrackTab.classList.contains('active')) {
                        if (selectedPortfolios.size > 0) {
                            updateMultiTrackChart();
                        } else {
                            // 如果没有选中的组合，清空图表
                            if (multiTrackChart) {
                                multiTrackChart.setOption({
                                    legend: { data: [] },
                                    xAxis: { data: [] },
                                    series: []
                                });
                                // 清空统计表格
                                const multiTrackTable = document.getElementById('multiTrackTable');
                                if (multiTrackTable) {
                                    multiTrackTable.innerHTML = '';
                                }
                            }
                        }
                    }
                });
            });
        }
    } catch (error) {
        console.error('Error loading track portfolios:', error);
    }
}

// 加载组合成分
async function loadPortfolioComponents(portfolioId) {
    try {
        const response = await fetch(`/api/portfolios/${portfolioId}/contracts/details`);
        const data = await response.json();
        
        if (data.status === 'success') {
            const container = document.querySelector('.component-track-list');
            if (!container) {
                console.error('Component track list container not found');
                return;
            }
            
            // 清空现有的成分列表
            container.innerHTML = '';
            
            // 添加新的成分
            data.data.forEach((contract, index) => {
                const item = document.createElement('div');
                item.className = 'list-group-item d-flex justify-content-between align-items-center';
                item.dataset.componentCode = contract.fut_code;
                
                item.innerHTML = `
                    <div>
                        <span class="badge bg-secondary me-2">${index + 1}</span>
                        ${contract.fut_code}
                    </div>
                `;
                
                // 添加点击事件
                item.addEventListener('click', function() {
                    // 切换选中状态
                    this.classList.toggle('active');
                    
                    const componentCode = this.dataset.componentCode;
                    if (this.classList.contains('active')) {
                        selectedComponents.add(componentCode);
                    } else {
                        selectedComponents.delete(componentCode);
                    }
                    
                    // 检查当前激活的标签页
                    const singleTrackTab = document.getElementById('single-track');
                    if (singleTrackTab && singleTrackTab.classList.contains('active')) {
                        // 如果是单品种资金曲线标签页，则更新图表
                        updateSingleTrackChart();
                    }
                });
                
                container.appendChild(item);
            });
            
            // 更新成分列表标题中的总数
            const header = container.previousElementSibling;
            if (header) {
                header.innerHTML = `<h6 class="mb-0">成分列表 <span class="badge bg-primary">${data.data.length}</span></h6>`;
            }
        }
    } catch (error) {
        console.error('Error loading portfolio components:', error);
    }
}

// 更新单品种图表
async function updateSingleTrackChart() {
    if (selectedComponents.size === 0) {
        // 如果没有选中的品种，清空图表
        if (singleTrackChart) {
            singleTrackChart.setOption({
                legend: { data: [] },
                xAxis: { data: [] },
                series: []
            });
        }
        return;
    }
    
    try {
        const response = await fetch('/api/track/component-curves', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                components: Array.from(selectedComponents)
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // 更新图表
            const option = {
                tooltip: {
                    trigger: 'axis',
                    formatter: function(params) {
                        const date = params[0].axisValue;
                        let html = `${date}<br/>`;
                        params.forEach(param => {
                            html += `${param.seriesName}: ${formatNumber(param.value)}<br/>`;
                        });
                        return html;
                    }
                },
                legend: {
                    data: data.data.components,
                    type: 'scroll',
                    orient: 'horizontal',
                    top: 0
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    containLabel: true,
                    top: 30
                },
                xAxis: {
                    type: 'category',
                    boundaryGap: false,
                    data: data.data.times,
                    axisLabel: {
                        formatter: function(value) {
                            return value.substring(5, 16);  // 只显示月-日 时:分
                        }
                    }
                },
                yAxis: {
                    type: 'value',
                    scale: true,
                    axisLabel: {
                        formatter: function(value) {
                            return formatNumber(value);
                        }
                    }
                },
                series: data.data.components.map(component => ({
                    name: component,
                    type: 'line',
                    data: data.data.curves[component],
                    smooth: true,
                    showSymbol: false,
                    lineStyle: {
                        width: 2
                    }
                }))
            };
            
            singleTrackChart.setOption(option, true);  // 使用 true 清除之前的配置
            
            // 更新表格
            updateSingleTrackTable(data.data.statistics);
        }
    } catch (error) {
        console.error('Error updating single track chart:', error);
    }
}

// 更新多组合图表
async function updateMultiTrackChart() {
    if (selectedPortfolios.size === 0) {
        // 如果没有选中的组合，清空图表
        if (multiTrackChart) {
            multiTrackChart.setOption({
                legend: { data: [] },
                xAxis: { data: [] },
                series: []
            });
            // 清空统计表格
            const multiTrackTable = document.getElementById('multiTrackTable');
            if (multiTrackTable) {
                multiTrackTable.innerHTML = '';
            }
        }
        return;
    }
    
    try {
        const response = await fetch('/api/track/portfolio-curves', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                portfolios: Array.from(selectedPortfolios)
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // 更新图表
            const option = {
                tooltip: {
                    trigger: 'axis',
                    formatter: function(params) {
                        const date = params[0].axisValue;
                        let html = `${date}<br/>`;
                        params.forEach(param => {
                            html += `${param.seriesName}: ${formatNumber(param.value)}<br/>`;
                        });
                        return html;
                    }
                },
                legend: {
                    data: data.data.portfolios,
                    type: 'scroll',
                    orient: 'horizontal',
                    top: 0
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    containLabel: true,
                    top: 30
                },
                xAxis: {
                    type: 'category',
                    boundaryGap: false,
                    data: data.data.times,
                    axisLabel: {
                        formatter: function(value) {
                            return value.substring(5, 16);  // 只显示月-日 时:分
                        }
                    }
                },
                yAxis: {
                    type: 'value',
                    scale: true,
                    axisLabel: {
                        formatter: function(value) {
                            return formatNumber(value);
                        }
                    }
                },
                series: data.data.portfolios.map(portfolio => ({
                    name: portfolio,
                    type: 'line',
                    data: data.data.curves[portfolio],
                    smooth: true,
                    showSymbol: false,
                    lineStyle: {
                        width: 2
                    }
                }))
            };
            
            multiTrackChart.setOption(option, true);  // 使用 true 清除之前的配置
            
            // 更新表格
            updateMultiTrackTable(data.data.statistics);
        }
    } catch (error) {
        console.error('Error updating multi track chart:', error);
    }
}

// 更新单品种统计表格
function updateSingleTrackTable(statistics) {
    const tbody = document.getElementById('singleTrackTable');
    tbody.innerHTML = Object.entries(statistics).map(([code, stats]) => `
        <tr>
            <td>${code}</td>
            <td>${formatNumber(stats.current_equity)}</td>
            <td>${formatNumber(stats.max_equity)}</td>
            <td>${formatDateTime(stats.max_equity_time)}</td>
            <td>${formatPercent(stats.current_drawdown)}</td>
            <td>${formatPercent(stats.max_drawdown)}</td>
            <td class="${stats.drawdown_days > 90 ? 'text-danger' : ''}">${stats.drawdown_days}天</td>
        </tr>
    `).join('');
}

// 更新多组合统计表格
function updateMultiTrackTable(statistics) {
    const tbody = document.getElementById('multiTrackTable');
    tbody.innerHTML = Object.entries(statistics).map(([name, stats]) => `
        <tr>
            <td>${name}</td>
            <td>${formatNumber(stats.current_equity)}</td>
            <td>${formatNumber(stats.max_equity)}</td>
            <td>${formatDateTime(stats.max_equity_time)}</td>
            <td>${formatPercent(stats.current_drawdown)}</td>
            <td>${formatPercent(stats.max_drawdown)}</td>
            <td class="${stats.drawdown_days > 90 ? 'text-danger' : ''}">${stats.drawdown_days}天</td>
        </tr>
    `).join('');
}

// 清空所有选择和图表数据
function clearAllSelections() {
    // 清空选中的组合和成分
    selectedComponents.clear();
    selectedPortfolios.clear();
    
    // 清空组合列表的选中状态
    document.querySelectorAll('.portfolio-track-list .list-group-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 清空成分列表的选中状态
    document.querySelectorAll('.component-track-list .list-group-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 清空统计表格
    const singleTrackTable = document.getElementById('singleTrackTable');
    if (singleTrackTable) {
        singleTrackTable.innerHTML = '';
    }
    
    const multiTrackTable = document.getElementById('multiTrackTable');
    if (multiTrackTable) {
        multiTrackTable.innerHTML = '';
    }
}

// 清空成分列表
function clearComponentsList() {
    const container = document.querySelector('.component-track-list');
    if (container) {
        container.innerHTML = '';
        // 更新标题
        const header = container.previousElementSibling;
        if (header) {
            header.innerHTML = `<h6 class="mb-0">成分列表 <span class="badge bg-primary">0</span></h6>`;
        }
    }
    // 清空选中的成分
    selectedComponents.clear();
    // 清空单品种图表
    if (singleTrackChart) {
        singleTrackChart.setOption({
            legend: { data: [] },
            xAxis: { data: [] },
            series: []
        });
    }
}

// 在标签页切换时的处理
function handleTabSwitch(targetId) {
    // ���空所有选择���图表
    clearAllSelections();
    
    // 根据目标标签页执行不同的操作
    setTimeout(() => {
        if (targetId === 'single-track') {
            if (singleTrackChart) {
                singleTrackChart.resize();
            }
            // 切换到单品种标签页时，可能需要重新加载当前选中组合的成分
            const selectedPortfolio = document.querySelector('.portfolio-track-list .list-group-item.active');
            if (selectedPortfolio) {
                loadPortfolioComponents(selectedPortfolio.dataset.portfolioId);
            }
        } else if (targetId === 'multi-track') {
            if (multiTrackChart) {
                multiTrackChart.resize();
            }
            // 切换到多组合标签页时，根据选中的组合更新图表
            if (selectedPortfolios.size > 0) {
                updateMultiTrackChart();
            }
        }
    }, 200);  // 增加延时确保DOM更新完成
}

// 在文档加载完成后初始化模块
document.addEventListener('DOMContentLoaded', () => {
    console.log('Starting track module initialization...');
    initializeTrackModule();
}); 