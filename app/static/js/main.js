/**
 * DocRadar - 主JavaScript文件
 * 负责文件拖放上传和实时搜索功能
 */

// 全局状态变量，用于追踪文档浏览
let lastViewedDocId = null;
let lastViewedDocQuery = null;
let isDocumentPage = false;

/**
 * 检测页面加载类型（刷新、正常导航或从缓存恢复）
 * @returns {Object} 页面加载类型信息
 */
function detectPageLoadType() {
    // 检测是否为刷新
    let isRefresh = false;
    let refreshSource = '未检测到刷新';
    
    try {
        // 检查performance API
        if (performance && performance.navigation) {
            isRefresh = performance.navigation.type === 1;
            if (isRefresh) {
                refreshSource = 'performance.navigation.type';
                console.log('检测到页面刷新: performance.navigation.type');
            }
        } else if (window.performance && window.performance.getEntriesByType) {
            // 现代浏览器中的方法
            const navEntries = window.performance.getEntriesByType('navigation');
            if (navEntries.length > 0 && navEntries[0].type === 'reload') {
                isRefresh = true;
                refreshSource = 'performance.getEntriesByType';
                console.log('检测到页面刷新: performance.getEntriesByType');
            }
        }
        
        // 检查会话存储中的标记作为后备
        const pageLoadFlag = sessionStorage.getItem('docradar_page_loaded');
        if (pageLoadFlag) {
            // 如果标记存在，这很可能是刷新
            isRefresh = true;
            refreshSource = 'sessionStorage.docradar_page_loaded';
            console.log('检测到页面刷新: sessionStorage.docradar_page_loaded');
        }
        // 无论如何设置标记，以便下次可以检测
        sessionStorage.setItem('docradar_page_loaded', 'true');
        
        // 判断是否有之前保存的搜索状态，如果有，可能是刷新
        const savedQuery = localStorage.getItem('docradar_current_active_query');
        const savedSearchId = localStorage.getItem('docradar_current_active_search_id');
        if (savedQuery && savedSearchId) {
            // 进一步判断URL是否有搜索参数，如果没有更可能是刷新
            const urlParams = new URLSearchParams(window.location.search);
            const urlQuery = urlParams.get('q');
            const urlSearchId = urlParams.get('search_id');
            
            if (!urlQuery || !urlSearchId) {
                console.log('检测到保存的搜索状态，但URL中没有搜索参数，可能是刷新');
                isRefresh = true;
                refreshSource = 'localStorage搜索状态与URL不匹配';
            }
        }
        
        // 如果是搜索结果页面，输出更多信息
        if (window.location.pathname.includes('/search')) {
            console.log('当前是搜索结果页面，刷新检测结果:', isRefresh);
            if (isRefresh) {
                console.log('页面刷新识别来源:', refreshSource);
            }
        }
    } catch (error) {
        console.error('检测页面加载类型时出错:', error);
    }
    
    return {
        isRefresh: isRefresh,
        refreshSource: refreshSource
    };
}

// 添加全局错误处理函数
window.addEventListener('error', function(event) {
    // 记录错误信息到控制台
    console.error('捕获到全局JavaScript错误:', {
        message: event.message,
        source: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error
    });
    
    // 如果错误是来自第三方脚本，忽略它们，不阻止默认处理
    if (event.filename && (
        event.filename.includes('jquery') || 
        event.filename.includes('bootstrap') ||
        event.filename.includes('mark.js')
    )) {
        console.log('忽略第三方脚本错误');
        return;
    }
    
    // 记录自定义错误堆栈，更易于调试
    try {
        if (event.error && event.error.stack) {
            const stackLines = event.error.stack.split('\n');
            console.log('错误堆栈详情:', stackLines);
        }
    } catch (e) {
        console.error('处理错误堆栈时出错:', e);
    }
    
    // 不阻止默认错误处理，允许浏览器继续处理错误
    return false;
});

document.addEventListener('DOMContentLoaded', function() {
    // 初始化拖放上传功能
    initFileUpload();
    
    // 初始化实时搜索功能
    initLiveSearch();
    
    // 初始化文档搜索功能
    initDocumentSearch();
    
    // 初始化消息自动关闭功能
    initAutoCloseAlerts();
    
    // 初始化搜索历史按钮功能
    initSearchHistoryButtons();
    
    // 检测页面加载类型
    const pageLoadInfo = detectPageLoadType();
    console.log(`DOMContentLoaded: 页面加载类型检测结果 - 刷新=${pageLoadInfo.isRefresh}` + 
               (pageLoadInfo.isRefresh ? `, 来源=${pageLoadInfo.refreshSource}` : ''));
    
    // 初始化已浏览文档跟踪功能，传入刷新状态
    initVisitedDocumentsTracker(pageLoadInfo.isRefresh);
});

/**
 * 初始化搜索历史相关的按钮事件
 */
function initSearchHistoryButtons() {
    // 获取清空历史按钮
    const clearAllBtn = document.getElementById('clear-all-history');
    if (clearAllBtn) {
        // 已经在HTML中添加了onclick事件，这里不需要重复添加
        console.log('搜索历史按钮已初始化');
    }
}

// 添加pageshow事件处理，处理从浏览器缓存恢复页面的情况
// 这确保了当用户点击返回按钮时也能正确标记已浏览文档
window.addEventListener('pageshow', function(event) {
    // 从浏览历史返回(例如用户点击浏览器的返回按钮)
    if (event.persisted) {
        console.log('页面从浏览器缓存恢复，可能是用户点击了返回按钮');
        
        // 清除页面加载标记，确保这不会被错误地识别为刷新
        sessionStorage.removeItem('docradar_page_loaded');
        
        // 清除正常导航标记，因为这是浏览器返回操作
        sessionStorage.removeItem('docradar_normal_navigation');
        
        // 检查是否是从文档页面返回到搜索结果页面
        const docId = sessionStorage.getItem('docradar_last_viewed_doc_id');
        const docQuery = sessionStorage.getItem('docradar_last_viewed_doc_query');
        
        if (docId && window.location.pathname.includes('/search')) {
            console.log(`从文档页面(ID: ${docId})返回到搜索结果页面，设置返回标记`);
            sessionStorage.setItem('docradar_back_to_search', 'true');
            
            // 添加返回时间戳，用于识别返回后的刷新操作（仅适用于浏览器返回按钮）
            sessionStorage.setItem('docradar_back_to_search_time', new Date().getTime());
            console.log('已记录浏览器返回时间戳:', new Date().getTime());
            
            if (docQuery) {
                console.log(`恢复文档的搜索查询: "${docQuery}"`);
                sessionStorage.setItem('docradar_current_search', docQuery);
            }
        }
        
        // 检查是否在首页，如果是则刷新搜索历史
        if (window.location.pathname === '/' || window.location.pathname === '/index') {
            console.log('从其他页面返回到首页，刷新搜索历史');
            refreshSearchHistory();
        }
    }
    
    // 检查当前页面是否为搜索结果页面
    const isSearch = window.location.pathname.includes('/search');
    if (isSearch) {
        // 获取当前URL中的搜索查询
        const urlParams = new URLSearchParams(window.location.search);
        const currentQuery = urlParams.get('q') || '';
        
        // 检查是否有保存的当前活动搜索状态
        const savedQuery = localStorage.getItem('docradar_current_active_query');
        const savedSearchId = localStorage.getItem('docradar_current_active_search_id');
        
        // 如果URL中没有查询参数但有保存的搜索状态，说明可能是刷新
        if ((!currentQuery || !urlParams.get('search_id')) && savedQuery && savedSearchId) {
            console.log(`检测到页面刷新，从localStorage恢复搜索状态: query="${savedQuery}", searchId=${savedSearchId}`);
            
            // 更新URL参数
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.set('q', savedQuery);
            newUrl.searchParams.set('search_id', savedSearchId);
            window.history.replaceState({}, '', newUrl);
            
            // 激活对应的标签
            const tabSelector = `#search-tab-${savedSearchId}`;
            const tab = document.querySelector(tabSelector);
            if (tab) {
                tab.click();
                console.log(`已激活标签: ${tabSelector}`);
            }
            
            // 不继续执行后续代码
            return;
        }
        
        // 获取上次访问的搜索查询
        const previousQuery = sessionStorage.getItem('docradar_current_search');
        
        console.log(`搜索结果页面，当前搜索词: "${currentQuery}", 上次搜索词: "${previousQuery || ''}"`);
        
        // 保存当前搜索查询，用于下次页面加载时判断是否切换了查询
        sessionStorage.setItem('docradar_previous_search', currentQuery);
        
        // 检查是否切换了搜索查询
        const isQueryChanged = previousQuery && previousQuery !== currentQuery;
        
        // 如果是从文档页面返回，使用特殊处理
        const isBackFromDocument = sessionStorage.getItem('docradar_back_to_search') === 'true';
        
        if (isBackFromDocument) {
            console.log(`从文档页面返回到搜索页面，之前的搜索查询: "${previousQuery}"`);
            
            // 检查是否是正常导航
            const isNormalNavigation = sessionStorage.getItem('docradar_normal_navigation') === 'true';
            
            // 如果是正常导航，记录信息
            if (isNormalNavigation) {
                console.log('这是通过页面按钮的正常导航，保留浏览状态');
            }
            
            // 如果返回后搜索查询发生变化，则不显示之前的浏览状态
            if (isQueryChanged) {
                console.log(`搜索查询已变化(${previousQuery} -> ${currentQuery})，不恢复之前的浏览状态`);
                // 使用isRefresh=true参数调用标记函数，这将清除当前查询的浏览记录
                markVisitedDocumentsInResults(true);
            } else {
                // 使用之前的搜索查询重新标记已浏览文档
                console.log(`使用之前的搜索查询"${previousQuery}"标记已浏览文档`);
                markVisitedDocumentsInResults(false);
            }
            
            // 清除保存的搜索查询和返回标记
            sessionStorage.removeItem('docradar_current_search');
            sessionStorage.removeItem('docradar_back_to_search');
            sessionStorage.removeItem('docradar_normal_navigation');
        } else {
            // 如果不是从文档页面返回，但搜索查询变化了，模拟刷新行为
            if (isQueryChanged) {
                console.log(`检测到搜索查询变化(${previousQuery} -> ${currentQuery})，模拟刷新行为`);
                markVisitedDocumentsInResults(true); // 传递true以清除当前查询的浏览状态
            } else {
                // 正常标记已浏览文档
                console.log(`正常标记已浏览文档，搜索查询: "${currentQuery}"`);
                markVisitedDocumentsInResults(false);
            }
        }
    }
});

/**
 * 通过AJAX刷新首页的搜索历史
 * 当用户从其他页面返回到首页时调用此函数
 */
function refreshSearchHistory() {
    // 检查是否在首页
    if (window.location.pathname !== '/' && window.location.pathname !== '/index') {
        console.log('不在首页，不需要刷新搜索历史');
        return;
    }
    
    console.log('开始刷新首页搜索历史...');
    
    // 发送AJAX请求获取最新的搜索历史
    fetch('/search/history', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
        }
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        }
        throw new Error('获取搜索历史失败');
    })
    .then(data => {
        if (data.success) {
            // 更新搜索历史区域
            updateSearchHistoryUI(data.history);
            console.log('搜索历史已刷新，共', data.history.length, '条记录');
        } else {
            console.error('刷新搜索历史失败:', data.message);
        }
    })
    .catch(error => {
        console.error('刷新搜索历史出错:', error);
    });
}

/**
 * 更新搜索历史UI
 * @param {Array} history - 搜索历史数据
 */
function updateSearchHistoryUI(history) {
    // 获取搜索历史容器
    const historyContainer = document.querySelector('.col-md-4 .card-body');
    if (!historyContainer) {
        console.error('未找到搜索历史容器');
        return;
    }
    
    // 获取搜索历史计数标签
    const historyCountBadge = document.querySelector('.col-md-4 .card-header .badge');
    if (historyCountBadge) {
        historyCountBadge.textContent = history.length;
    }
    
    // 获取搜索历史卡片头部
    const cardHeader = document.querySelector('.col-md-4 .card-header .d-flex');
    
    // 获取清空历史按钮
    let clearHistoryBtn = document.getElementById('clear-all-history');
    
    // 如果没有历史记录
    if (!history || history.length === 0) {
        // 隐藏或移除清空按钮
        if (clearHistoryBtn) {
            clearHistoryBtn.style.display = 'none';
        }
        
        // 显示无历史记录提示
        historyContainer.innerHTML = `
            <div class="alert alert-info">
                <div class="text-center py-3">
                    <i class="bi bi-clock-history display-4 text-muted"></i>
                    <h5 class="mt-3">暂无搜索历史</h5>
                    <p>您还没有进行过任何搜索。</p>
                    <a href="#search-input" class="btn btn-outline-primary" onclick="document.getElementById('search-input').focus()">
                        <i class="bi bi-search"></i> 开始搜索
                    </a>
                </div>
            </div>
        `;
        return;
    }
    
    // 如果有搜索历史
    if (history && history.length > 0) {
        // 如果清空按钮不存在但有卡片头部，则创建一个新的清空按钮
        if (!clearHistoryBtn && cardHeader) {
            clearHistoryBtn = document.createElement('a');
            clearHistoryBtn.href = '/search/clear?return_to=/';
            clearHistoryBtn.className = 'btn btn-sm btn-outline-danger';
            clearHistoryBtn.title = '清空所有搜索记录';
            clearHistoryBtn.id = 'clear-all-history';
            clearHistoryBtn.innerHTML = '<i class="bi bi-trash"></i> 清空历史';
            
            // 添加确认对话框
            clearHistoryBtn.onclick = function() {
                return confirm('确定要清空所有搜索记录吗？');
            };
            
            // 添加到卡片头部
            cardHeader.appendChild(clearHistoryBtn);
            console.log('已创建并添加清空历史按钮');
        }
        
        // 显示清空按钮（如果存在）
        if (clearHistoryBtn) {
            clearHistoryBtn.style.display = '';
        }
    }
    
    // 创建历史记录列表
    let historyHTML = '<div class="list-group">';
    
    history.forEach(item => {
        historyHTML += `
            <div class="list-group-item list-group-item-action">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <a href="/search?q=${encodeURIComponent(item.query)}" class="text-decoration-none">
                            <h6 class="mb-1">
                                <i class="bi bi-search text-primary me-2"></i>
                                "${item.query}"
                            </h6>
                        </a>
                        <p class="mb-1 text-muted small">
                            <span class="me-3">
                                <i class="bi bi-clock"></i> 
                                ${item.timestamp}
                            </span>
                            <span>
                                <i class="bi bi-file-text"></i> 
                                ${item.results_count} 个结果
                            </span>
                        </p>
                    </div>
                    <div>
                        <a href="/search/delete/${item.id}?return_to=/" 
                           class="btn btn-sm btn-outline-danger"
                           title="删除此搜索记录"
                           onclick="return confirm('确定要删除此搜索记录吗？');">
                            <i class="bi bi-x"></i>
                        </a>
                    </div>
                </div>
            </div>
        `;
    });
    
    historyHTML += '</div>';
    historyContainer.innerHTML = historyHTML;
}

// 添加页面离开处理，确保在离开文档页面时保存浏览状态
window.addEventListener('pagehide', function(e) {
    // 检查是否从文档页面离开
    if (isDocumentPage && lastViewedDocId) {
        console.log(`页面离开事件(pagehide)，当前查看的文档ID: ${lastViewedDocId}`);
        
        // 强制保存浏览状态
        markDocumentAsVisited(lastViewedDocId, true, lastViewedDocQuery);
        
        // 设置会话标记，告知页面不要在下一个搜索页面加载时重置访问状态
        console.log(`在页面离开时设置返回标记，下一页面加载时将恢复浏览状态`);
        sessionStorage.setItem('docradar_back_to_search', 'true');
        
        // 保存当前搜索查询
        if (lastViewedDocQuery) {
            console.log(`保存当前搜索查询: "${lastViewedDocQuery}"`);
            sessionStorage.setItem('docradar_current_search', lastViewedDocQuery);
        }
    }
});

/**
 * 初始化所有页面的消息自动关闭功能
 */
function initAutoCloseAlerts() {
    // 获取所有的提示消息元素
    const alerts = document.querySelectorAll('.alert');
    
    if (alerts.length > 0) {
        // 设置3秒后自动关闭所有提示消息
        setTimeout(function() {
            alerts.forEach(function(alert) {
                // 检查Bootstrap版本，使用适当的方法关闭提示框
                if (typeof bootstrap !== 'undefined') {
                    // Bootstrap 5
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                } else {
                    // 手动关闭（添加淡出效果）
                    alert.style.transition = 'opacity 0.5s';
                    alert.style.opacity = '0';
                    setTimeout(function() {
                        alert.style.display = 'none';
                    }, 500);
                }
            });
        }, 3000);
    }
}

/**
 * 初始化文档搜索功能
 */
function initDocumentSearch() {
    const searchForm = document.getElementById('document-search-form');
    const searchInput = document.getElementById('document-search');
    
    if (!searchForm || !searchInput) return;
    
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const searchQuery = searchInput.value.trim();
        const currentUrl = new URL(window.location.href);
        
        // 更新URL参数
        if (searchQuery) {
            currentUrl.searchParams.set('search', searchQuery);
        } else {
            currentUrl.searchParams.delete('search');
        }
        
        // 重置到第一页
        currentUrl.searchParams.set('page', '1');
        
        // 导航到新URL
        window.location.href = currentUrl.toString();
    });
}

/**
 * 初始化文件上传功能
 */
function initFileUpload() {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('fileInput');
    const fileForm = document.getElementById('file-form');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadStatus = document.getElementById('upload-status');
    const fileList = document.getElementById('file-list');
    const fileCounter = document.getElementById('file-counter');
    const progressBar = document.getElementById('upload-progress-bar');
    const progressText = document.getElementById('upload-progress-text');
    const uploadResult = document.getElementById('upload-result');
    
    // 顶部进度条相关元素
    const topProgressContainer = document.getElementById('top-progress-container');
    const topProgressBar = document.getElementById('top-upload-progress-bar');
    const topProgressText = document.getElementById('top-upload-progress-text');
    const topCurrentFile = document.getElementById('top-upload-current-file');
    
    // 覆盖确认模态框元素
    const overwriteModalEl = document.getElementById('overwriteConfirmModal');
    const batchOverwriteModalEl = document.getElementById('batchOverwriteModal');
    const uploadResultModalEl = document.getElementById('uploadResultModal');
    const existingFilename = document.getElementById('existing-filename');
    const confirmFilename = document.getElementById('confirm-filename');
    const confirmOverwrite = document.getElementById('confirm-overwrite');
    const selectAllFiles = document.getElementById('select-all-files');
    const existingFilesList = document.getElementById('existing-files-list');
    const confirmBatchOverwrite = document.getElementById('confirm-batch-overwrite');
    const uploadResultContent = document.getElementById('upload-result-content');
    const uploadResultClose = document.getElementById('upload-result-close');
    
    // 初始化模态框对象
    let overwriteModal, batchOverwriteModal, uploadResultModal;
    
    // 直接初始化模态框，不使用嵌套的DOMContentLoaded事件
    console.log('初始化模态框');
    
    // 确保模态框元素存在后再初始化
    if (overwriteModalEl) {
        try {
            overwriteModal = new bootstrap.Modal(overwriteModalEl);
            console.log('单文件覆盖模态框初始化成功');
            
            // 为取消按钮添加事件处理
            const cancelOverwriteBtn = overwriteModalEl.querySelector('button[data-bs-dismiss="modal"]');
            if (cancelOverwriteBtn) {
                cancelOverwriteBtn.addEventListener('click', function() {
                    console.log('取消覆盖按钮被点击');
                    removeExistingFilesFromQueue();
                });
            }
            
            // 为模态框关闭事件添加处理
            overwriteModalEl.addEventListener('hidden.bs.modal', function() {
                console.log('覆盖确认模态框被关闭');
                removeExistingFilesFromQueue();
            });
        } catch (error) {
            console.error('单文件覆盖模态框初始化失败:', error);
        }
    } else {
        console.error('覆盖确认模态框元素不存在');
    }
    
    if (batchOverwriteModalEl) {
        try {
            batchOverwriteModal = new bootstrap.Modal(batchOverwriteModalEl);
            console.log('批量覆盖模态框初始化成功');
            
            // 为取消按钮添加事件处理
            const cancelBatchOverwriteBtn = batchOverwriteModalEl.querySelector('button[data-bs-dismiss="modal"]');
            if (cancelBatchOverwriteBtn) {
                cancelBatchOverwriteBtn.addEventListener('click', function() {
                    console.log('取消批量覆盖按钮被点击');
                    removeExistingFilesFromQueue();
                });
            }
            
            // 为模态框关闭事件添加处理
            batchOverwriteModalEl.addEventListener('hidden.bs.modal', function() {
                console.log('批量覆盖模态框被关闭');
                removeExistingFilesFromQueue();
            });
        } catch (error) {
            console.error('批量覆盖模态框初始化失败:', error);
        }
    } else {
        console.error('批量覆盖模态框元素不存在');
    }
    
    if (uploadResultModalEl) {
        try {
            uploadResultModal = new bootstrap.Modal(uploadResultModalEl);
            console.log('上传结果模态框初始化成功');
        } catch (error) {
            console.error('上传结果模态框初始化失败:', error);
        }
    } else {
        console.error('上传结果模态框元素不存在');
    }
    
    if (!dropArea || !fileInput) return;
    
    // 存储选择的文件
    let selectedFiles = [];
    
    // 存储已存在的文件
    let existingFiles = [];
    
    // 初始化上传统计
    let uploadStats = {
        success: 0,
        overwritten: 0,
        skipped: 0,
        failed: 0,
        failedFiles: [] // 添加失败文件列表
    };
    
    // 阻止浏览器默认拖放行为
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // 添加高亮效果
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropArea.classList.add('highlight');
    }
    
    function unhighlight() {
        dropArea.classList.remove('highlight');
    }
    
    // 处理文件拖放
    dropArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        handleFiles(files);
    }
    
    // 文件输入变化处理
    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });
    
    // 处理选择的文件
    function handleFiles(files) {
        if (files.length > 0) {
            // 将FileList转换为数组并添加到选择的文件中
            selectedFiles = Array.from(files);
            updateFileList();
            showUploadUI();
        }
    }
    
    // 更新文件列表UI
    function updateFileList() {
        fileList.innerHTML = '';
        fileCounter.textContent = selectedFiles.length;
        
        // 添加批量操作按钮
        if (selectedFiles.length > 0) {
            const batchActionsDiv = document.createElement('div');
            batchActionsDiv.className = 'd-flex justify-content-between align-items-center mb-2';
            
            // 全选复选框
            const selectAllDiv = document.createElement('div');
            selectAllDiv.className = 'form-check';
            
            const selectAllCheckbox = document.createElement('input');
            selectAllCheckbox.type = 'checkbox';
            selectAllCheckbox.className = 'form-check-input';
            selectAllCheckbox.id = 'select-all-queue-files';
            
            const selectAllLabel = document.createElement('label');
            selectAllLabel.className = 'form-check-label';
            selectAllLabel.htmlFor = 'select-all-queue-files';
            selectAllLabel.textContent = '全选';
            
            selectAllDiv.appendChild(selectAllCheckbox);
            selectAllDiv.appendChild(selectAllLabel);
            
            // 批量删除按钮
            const batchDeleteBtn = document.createElement('button');
            batchDeleteBtn.type = 'button';
            batchDeleteBtn.className = 'btn btn-sm btn-danger';
            batchDeleteBtn.id = 'batch-delete-queue';
            batchDeleteBtn.innerHTML = '<i class="bi bi-trash"></i> 批量删除';
            batchDeleteBtn.disabled = true; // 默认禁用，直到选择了文件
            
            batchActionsDiv.appendChild(selectAllDiv);
            batchActionsDiv.appendChild(batchDeleteBtn);
            
            fileList.appendChild(batchActionsDiv);
            
            // 全选事件
            selectAllCheckbox.addEventListener('change', function() {
                const checkboxes = fileList.querySelectorAll('.file-checkbox');
                checkboxes.forEach(checkbox => {
                    checkbox.checked = this.checked;
                });
                updateQueueDeleteButtonState();
            });
            
            // 批量删除事件
            batchDeleteBtn.addEventListener('click', function() {
                const checkedFiles = fileList.querySelectorAll('.file-checkbox:checked');
                if (checkedFiles.length === 0) {
                    alert('请选择要删除的文件');
                    return;
                }
                
                if (confirm(`确定要删除选中的 ${checkedFiles.length} 个文件吗？`)) {
                    const indexesToRemove = [];
                    checkedFiles.forEach(checkbox => {
                        indexesToRemove.push(parseInt(checkbox.dataset.index));
                    });
                    
                    // 从大到小排序，避免删除时索引变化
                    indexesToRemove.sort((a, b) => b - a);
                    
                    // 删除选中的文件
                    indexesToRemove.forEach(index => {
                        selectedFiles.splice(index, 1);
                    });
                    
                    // 更新文件列表
                    updateFileList();
                    
                    if (selectedFiles.length === 0) {
                        hideUploadUI();
                    }
                }
            });
        }
        
        // 添加文件列表
        selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item d-flex justify-content-between align-items-center';
            
            // 添加复选框
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'form-check me-2';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'form-check-input file-checkbox';
            checkbox.dataset.index = index;
            
            // 添加复选框变化事件
            checkbox.addEventListener('change', updateQueueDeleteButtonState);
            
            checkboxDiv.appendChild(checkbox);
            
            const fileInfo = document.createElement('div');
            fileInfo.className = 'file-info d-flex align-items-center flex-grow-1';
            
            // 文件类型图标
            const fileIcon = document.createElement('i');
            let iconClass = 'bi bi-file-earmark';
            const ext = file.name.split('.').pop().toLowerCase();
            
            if (ext === 'pdf') {
                iconClass = 'bi bi-file-earmark-pdf';
            } else if (['doc', 'docx'].includes(ext)) {
                iconClass = 'bi bi-file-earmark-word';
            } else if (ext === 'txt') {
                iconClass = 'bi bi-file-earmark-text';
            }
            
            fileIcon.className = iconClass + ' me-2 text-primary';
            
            // 文件名
            const fileName = document.createElement('div');
            fileName.className = 'file-name';
            fileName.textContent = file.name;
            
            // 文件大小
            const fileSize = document.createElement('small');
            fileSize.className = 'text-muted ms-2';
            fileSize.textContent = formatFileSize(file.size);
            
            // 删除按钮
            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn btn-sm btn-outline-danger';
            removeBtn.innerHTML = '<i class="bi bi-x"></i>';
            removeBtn.addEventListener('click', function() {
                selectedFiles.splice(index, 1);
                updateFileList();
                
                if (selectedFiles.length === 0) {
                    hideUploadUI();
                }
            });
            
            fileInfo.appendChild(fileIcon);
            fileInfo.appendChild(fileName);
            fileInfo.appendChild(fileSize);
            
            fileItem.appendChild(checkboxDiv);
            fileItem.appendChild(fileInfo);
            fileItem.appendChild(removeBtn);
            fileList.appendChild(fileItem);
        });
        
        // 初始化批量删除按钮状态
        updateQueueDeleteButtonState();
    }
    
    // 更新上传队列批量删除按钮状态
    function updateQueueDeleteButtonState() {
        const batchDeleteBtn = document.getElementById('batch-delete-queue');
        if (!batchDeleteBtn) return;
        
        const checkedFiles = fileList.querySelectorAll('.file-checkbox:checked');
        batchDeleteBtn.disabled = checkedFiles.length === 0;
        
        // 更新全选框状态
        const selectAllCheckbox = document.getElementById('select-all-queue-files');
        if (selectAllCheckbox) {
            const allCheckboxes = fileList.querySelectorAll('.file-checkbox');
            if (allCheckboxes.length > 0) {
                if (checkedFiles.length === 0) {
                    selectAllCheckbox.checked = false;
                    selectAllCheckbox.indeterminate = false;
                } else if (checkedFiles.length === allCheckboxes.length) {
                    selectAllCheckbox.checked = true;
                    selectAllCheckbox.indeterminate = false;
                } else {
                    selectAllCheckbox.checked = false;
                    selectAllCheckbox.indeterminate = true;
                }
            }
        }
    }
    
    // 显示上传UI
    function showUploadUI() {
        uploadStatus.style.display = 'block';
        uploadBtn.classList.remove('d-none');
        resetProgress();
    }
    
    // 隐藏上传UI
    function hideUploadUI() {
        uploadStatus.style.display = 'none';
        uploadBtn.classList.add('d-none');
    }
    
    // 重置进度显示
    function resetProgress() {
        // 保存之前的失败文件列表（如果有）
        const previousFailedFiles = uploadStats.failedFiles ? [...uploadStats.failedFiles] : [];
        
        uploadStats = {
            success: 0,
            overwritten: 0,
            skipped: 0,
            failed: 0,
            failedFiles: previousFailedFiles // 保留之前的失败文件列表
        };
        
        // 重置原始进度条
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', 0);
        progressText.textContent = '0%';
        
        // 移除动画效果（如果有）
        progressBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
        
        // 重置顶部进度条
        if (topProgressBar && topProgressText) {
            topProgressBar.style.width = '0%';
            topProgressBar.setAttribute('aria-valuenow', 0);
            topProgressText.textContent = '0%';
            
            // 隐藏顶部进度条容器
            if (topProgressContainer) {
                topProgressContainer.style.display = 'none';
            }
            
            // 重置当前文件显示
            if (topCurrentFile) {
                topCurrentFile.textContent = '正在传输文件...';
            }
        }
        
        // 清空已存在文件列表
        existingFiles = [];
    }
    
    // "全选"复选框处理
    if (selectAllFiles) {
        selectAllFiles.addEventListener('change', function() {
            const checkboxes = existingFilesList.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
        });
    }
    
    // 单文件覆盖确认处理
    if (confirmOverwrite) {
        confirmOverwrite.addEventListener('click', async function() {
            console.log('单文件覆盖确认按钮被点击');
            const filename = confirmFilename ? confirmFilename.value : '';
            if (!filename) {
                console.error('确认文件名为空');
                alert('错误：文件名为空，无法继续上传');
                return;
            }
            
            // 找到文件对象
            console.log('尝试查找文件信息，文件名:', filename);
            console.log('现有文件列表:', existingFiles);
            
            // 尝试多种方式查找文件信息
            let fileInfo = null;
            
            // 方法1: 通过filename精确匹配
            fileInfo = existingFiles.find(f => f.filename === filename);
            
            // 方法2: 如果没找到，尝试通过file.name匹配
            if (!fileInfo) {
                fileInfo = existingFiles.find(f => f.file && f.file.name === filename);
            }
            
            // 方法3: 如果还没找到，尝试使用original_filename
            if (!fileInfo) {
                fileInfo = existingFiles.find(f => f.original_filename === filename);
            }
            
            // 方法4: 如果existingFiles只有一个元素，直接使用它
            if (!fileInfo && existingFiles.length === 1) {
                fileInfo = existingFiles[0];
                console.log('使用唯一的文件信息:', fileInfo);
            }
            
            if (!fileInfo || !fileInfo.file) {
                console.error('找不到对应的文件信息', {
                    filename,
                    existingFiles
                });
                alert('错误：找不到对应的文件信息，无法继续上传');
                return;
            }
            
            console.log('找到文件信息:', fileInfo);
            
            // 隐藏模态框 - 使用多种方法尝试确保模态框被隐藏
            try {
                console.log('尝试隐藏覆盖确认模态框');
                const modalElement = document.getElementById('overwriteConfirmModal');
                
                // 方法1: 使用Bootstrap API
                if (typeof bootstrap !== 'undefined') {
                    try {
                        const modalInstance = bootstrap.Modal.getInstance(modalElement);
                        if (modalInstance) {
                            modalInstance.hide();
                            console.log('使用Bootstrap API隐藏模态框成功');
                        } else {
                            console.log('未找到模态框实例，尝试创建新实例');
                            const newModal = new bootstrap.Modal(modalElement);
                            newModal.hide();
                        }
                    } catch (err) {
                        console.error('使用Bootstrap API隐藏模态框失败:', err);
                    }
                }
                
                // 方法2: 使用jQuery (如果可用)
                if (typeof $ !== 'undefined') {
                    try {
                        $('#overwriteConfirmModal').modal('hide');
                        console.log('使用jQuery隐藏模态框');
                    } catch (err) {
                        console.error('使用jQuery隐藏模态框失败:', err);
                    }
                }
                
                // 方法3: 使用data-bs-dismiss属性触发关闭
                if (modalElement) {
                    const closeButton = modalElement.querySelector('[data-bs-dismiss="modal"]');
                    if (closeButton) {
                        closeButton.click();
                        console.log('通过点击关闭按钮隐藏模态框');
                    }
                }
                
                // 方法4: 直接修改DOM (最后手段)
                if (modalElement) {
                    modalElement.classList.remove('show');
                    modalElement.style.display = 'none';
                    document.body.classList.remove('modal-open');
                    const backdrop = document.querySelector('.modal-backdrop');
                    if (backdrop) {
                        backdrop.parentNode.removeChild(backdrop);
                    }
                    console.log('通过直接修改DOM隐藏模态框');
                }
            } catch (error) {
                console.error('所有隐藏模态框的方法都失败:', error);
                // 继续执行上传，即使模态框隐藏失败
            }
            
            // 执行文件上传操作，设置overwrite=true
            console.log('开始上传文件并覆盖:', fileInfo.file.name);
            try {
                // 显示上传状态
                if (uploadStatus) {
                    uploadStatus.classList.remove('d-none');
                    progressBar.style.width = '0%';
                    progressBar.setAttribute('aria-valuenow', 0);
                    progressText.textContent = '0%';
                }
                
                // 上传文件
                const result = await uploadSingleFile(fileInfo.file, true);
                console.log('文件上传结果:', result);
                
                if (!result.success && result.error) {
                    console.error('上传失败:', result.error);
                    alert('上传失败: ' + result.error);
                    return;
                }
                
                // 更新上传统计
                updateUploadStats(result, fileInfo.file.name);
                
                // 显示上传结果
                if (uploadStatus) {
                    progressBar.style.width = '100%';
                    progressBar.setAttribute('aria-valuenow', 100);
                    progressText.textContent = '100%';
                }
                
                // 显示最终结果
                showFinalResult();
            } catch (error) {
                console.error('上传文件时出错:', error);
                alert('上传文件时出错: ' + error.message);
                if (uploadStatus) {
                    uploadStatus.classList.add('d-none');
                }
            }
        });
    } else {
        console.error('确认覆盖按钮元素不存在');
    }
    
    // 批量覆盖确认处理
    if (confirmBatchOverwrite) {
        confirmBatchOverwrite.addEventListener('click', async function() {
            console.log('批量覆盖确认按钮被点击');
            
            // 获取所有选中的文件
            const checkboxes = existingFilesList ? existingFilesList.querySelectorAll('input[type="checkbox"]:checked') : [];
            console.log(`选中了${checkboxes.length}个文件进行覆盖`);
            
            // 收集更多的文件标识信息
            const filesToOverwrite = Array.from(checkboxes).map(cb => {
                // 优先使用 fileName 属性，这是文件对象的实际名称
                if (cb.dataset.fileName) {
                    console.log(`使用 fileName 属性: ${cb.dataset.fileName}`);
                    return cb.dataset.fileName;
                }
                
                // 如果没有 fileName 属性，使用 filename 属性
                console.log(`使用 filename 属性: ${cb.dataset.filename}`);
                return cb.dataset.filename;
            });
            
            console.log('要覆盖的文件列表:', filesToOverwrite);
            
            // 隐藏模态框
            try {
                // 获取当前显示的模态框实例并隐藏
                const modalElement = document.getElementById('batchOverwriteModal');
                if (modalElement) {
                    const modalInstance = bootstrap.Modal.getInstance(modalElement);
                    if (modalInstance) {
                        modalInstance.hide();
                        console.log('隐藏批量覆盖模态框成功');
                    } else {
                        console.log('未找到模态框实例，尝试使用jQuery隐藏');
                        // 尝试使用jQuery隐藏
                        if (typeof $ !== 'undefined') {
                            $('#batchOverwriteModal').modal('hide');
                        }
                    }
                }
            } catch (error) {
                console.error('隐藏批量覆盖模态框时出错:', error);
            }
            
            // 确保上传状态区域可见并显示进度条 - 使用更明确的方式显示
            if (uploadStatus) {
                // 先确保元素完全可见
                uploadStatus.style.display = 'block';
                uploadStatus.classList.remove('d-none');
                
                // 重置进度条状态
                resetProgress();
                
                // 显式设置进度条为初始状态
                progressBar.style.width = '0%';
                progressBar.setAttribute('aria-valuenow', 0);
                progressText.textContent = '0%';
                
                // 滚动到上传状态区域，确保用户可以看到
                uploadStatus.scrollIntoView({ behavior: 'smooth', block: 'start' });
                
                console.log('上传状态区域和进度条已显示');
            } else {
                console.error('找不到上传状态区域元素');
            }
            
            // 显示正在处理的信息
            uploadResult.innerHTML = '<div class="alert alert-info">' +
                '<div class="d-flex align-items-center">' +
                '<div class="spinner-border spinner-border-sm me-2" role="status"></div>' +
                '<div>正在准备覆盖操作，处理 ' + filesToOverwrite.length + ' 个文件...</div>' +
                '</div></div>';
            
            // 标记未选中的文件为跳过
            const unselectedFiles = existingFiles.filter(fileInfo => {
                // 如果文件对象存在，使用文件对象的名称进行匹配
                if (fileInfo.file) {
                    return !filesToOverwrite.includes(fileInfo.file.name);
                }
                // 否则使用 filename 属性进行匹配
                return !filesToOverwrite.includes(fileInfo.filename);
            });
            
            console.log(`${unselectedFiles.length}个文件被标记为跳过`);
            uploadStats.skipped += unselectedFiles.length;
            
            // 处理批量覆盖文件
            await processBatchOverwrite(filesToOverwrite);
            
            // 显示最终结果
            showFinalResult();
        });
    }
    
    // 上传结果模态框关闭处理
    if (uploadResultClose) {
        uploadResultClose.addEventListener('click', function() {
            // 重置文件输入框，确保可以重新选择相同文件
            if (fileInput) {
                fileInput.value = '';
            }
            // 刷新页面以显示新上传的文件
            window.location.reload();
        });
    }
    
    // 上传按钮点击事件
    uploadBtn.addEventListener('click', () => {
        if (selectedFiles.length === 0) return;
        
        console.log('开始上传按钮被点击');
        uploadFiles();
    });
    
    // 上传文件
    async function uploadFiles() {
        console.log('开始执行uploadFiles函数');
        resetProgress();
        uploadBtn.disabled = true;
        
        // 禁用批量删除按钮
        const batchDeleteBtn = document.getElementById('batch-delete-queue');
        if (batchDeleteBtn) {
            batchDeleteBtn.disabled = true;
        }
        
        // 显示顶部进度条
        if (topProgressContainer) {
            topProgressContainer.style.display = 'block';
            if (topCurrentFile) {
                topCurrentFile.textContent = '正在检查文件...';
            }
            if (topProgressBar && topProgressText) {
                topProgressBar.style.width = '0%';
                topProgressBar.setAttribute('aria-valuenow', 0);
                topProgressText.textContent = '0%';
            }
        }
        
        uploadResult.innerHTML = '<div class="alert alert-info">检查文件中，请稍候...</div>';
        
        // 重置文件列表
        let newFiles = []; // 存储新文件
        existingFiles = []; // 存储已存在文件
        
        console.log(`准备检查 ${selectedFiles.length} 个文件是否存在`);
        
        // 第一阶段: 检查所有文件是否存在
        for (const file of selectedFiles) {
            try {
                console.log(`检查文件是否存在: ${file.name}`);
                // 检查文件是否存在
                const checkResult = await checkFileExists(file.name);
                console.log(`文件 ${file.name} 检查结果:`, checkResult);
                
                if (checkResult.exists) {
                    // 详细记录服务器返回的数据结构
                    console.log('服务器返回的文件信息:', JSON.stringify(checkResult));
                    
                    // 收集已存在的文件信息，确保关键字段存在
                    const fileInfo = {
                        ...checkResult,
                        file: file,
                        // 确保filename字段存在，优先使用服务器返回的filename，如果没有则使用文件名
                        filename: file.name
                    };
                    
                    // 如果服务器返回了文件ID，确保它被正确保存
                    if (checkResult.doc_id) {
                        fileInfo.id = checkResult.doc_id;
                    }
                    
                    existingFiles.push(fileInfo);
                    console.log(`文件 ${file.name} 已存在，添加到existingFiles。完整信息:`, fileInfo);
                } else {
                    // 收集新文件
                    newFiles.push(file);
                    console.log(`文件 ${file.name} 不存在，添加到newFiles`);
                }
            } catch (error) {
                console.error(`检查文件 ${file.name} 时出错:`, error);
            }
            
            // 更新检查进度
            updateProgress((newFiles.length + existingFiles.length) / selectedFiles.length);
        }
        
        console.log(`检查完成: ${newFiles.length}个新文件, ${existingFiles.length}个已存在文件`);
        console.log('新文件列表:', newFiles.map(f => f.name));
        console.log('已存在文件列表:', existingFiles.map(f => f.filename));
        
        // 修改逻辑：先上传新文件，再处理覆盖
        
        // 第一步：如果有新文件，先上传新文件
        if (newFiles.length > 0) {
            console.log('先上传新文件，数量:', newFiles.length);
            await uploadAllNewFiles(newFiles);
            // 注意：此时不调用showFinalResult()，因为还有可能需要处理覆盖文件
        }
        
        // 第二步：如果有已存在的文件，显示覆盖确认对话框
        if (existingFiles.length > 0) {
            console.log(`发现${existingFiles.length}个已存在的文件，准备显示覆盖确认对话框`);
            
            // 如果只有一个文件，显示单文件覆盖确认
            if (existingFiles.length === 1) {
                const fileInfo = existingFiles[0];
                console.log('准备显示单文件覆盖确认模态框');
                
                // 确保元素存在
                if (!existingFilename || !confirmFilename) {
                    console.error('覆盖确认模态框的必要元素不存在');
                    uploadBtn.disabled = false;
                    
                    // 恢复批量删除按钮
                    if (batchDeleteBtn) {
                        batchDeleteBtn.disabled = false;
                    }
                    
                    // 如果已经上传了新文件，显示最终结果
                    if (newFiles.length > 0) {
                        showFinalResult();
                    }
                    return;
                }
                
                // 显示原始文件名（如果有）
                console.log('准备设置模态框显示的文件名，文件信息:', fileInfo);
                
                // 确定要显示的文件名
                const displayFilename = fileInfo.original_filename || fileInfo.filename || fileInfo.file.name;
                
                // 确定要用于确认的文件名（用于后续查找）
                const confirmValue = fileInfo.file.name; // 使用实际文件对象的名称
                
                if (fileInfo.original_filename && fileInfo.original_filename !== fileInfo.filename) {
                    existingFilename.innerHTML = `${displayFilename}<br><small class="text-muted">存储为: ${fileInfo.filename}</small>`;
                } else {
                    existingFilename.textContent = displayFilename;
                }
                
                // 设置确认文件名为文件对象的名称，确保后续能找到
                confirmFilename.value = confirmValue;
                console.log(`设置显示文件名: ${displayFilename}, 确认文件名: ${confirmValue}`);
                
                // 确保模态框对象已初始化
                if (!overwriteModal) {
                    console.log('覆盖确认模态框未初始化，尝试重新初始化');
                    if (overwriteModalEl) {
                        try {
                            overwriteModal = new bootstrap.Modal(overwriteModalEl);
                            console.log('重新初始化覆盖确认模态框成功');
                        } catch (error) {
                            console.error('重新初始化覆盖确认模态框失败:', error);
                            // 如果无法初始化模态框，但已经上传了新文件，显示最终结果
                            if (newFiles.length > 0) {
                                showFinalResult();
                            }
                            uploadBtn.disabled = false;
                            
                            // 恢复批量删除按钮
                            if (batchDeleteBtn) {
                                batchDeleteBtn.disabled = false;
                            }
                            return;
                        }
                    } else {
                        console.error('覆盖确认模态框元素不存在');
                        // 如果模态框元素不存在，但已经上传了新文件，显示最终结果
                        if (newFiles.length > 0) {
                            showFinalResult();
                        }
                        uploadBtn.disabled = false;
                        
                        // 恢复批量删除按钮
                        if (batchDeleteBtn) {
                            batchDeleteBtn.disabled = false;
                        }
                        return;
                    }
                }
                
                try {
                    console.log('尝试显示覆盖确认模态框');
                    // 确保bootstrap已加载
                    if (typeof bootstrap === 'undefined') {
                        console.error('Bootstrap未加载');
                        alert('系统错误: Bootstrap库未加载，无法显示确认对话框');
                        // 如果已经上传了新文件，显示最终结果
                        if (newFiles.length > 0) {
                            showFinalResult();
                        }
                        uploadBtn.disabled = false;
                        
                        // 恢复批量删除按钮
                        if (batchDeleteBtn) {
                            batchDeleteBtn.disabled = false;
                        }
                        return;
                    }
                    
                    // 手动创建新的Modal实例
                    const modal = new bootstrap.Modal(overwriteModalEl);
                    modal.show();
                    console.log('显示单文件覆盖确认模态框成功');
                } catch (error) {
                    console.error('显示单文件覆盖确认模态框时出错:', error);
                    // 如果无法显示模态框，但已经上传了新文件，显示最终结果
                    if (newFiles.length > 0) {
                        showFinalResult();
                    }
                    
                    // 恢复批量删除按钮
                    if (batchDeleteBtn) {
                        batchDeleteBtn.disabled = false;
                    }
                }
            } 
            // 如果有多个文件，显示批量覆盖选择界面
            else {
                console.log('准备显示批量覆盖选择界面');
                showBatchOverwriteModal();
            }
        } else if (newFiles.length > 0) {
            // 如果没有已存在的文件，但已经上传了新文件，显示最终结果
            showFinalResult();
        } else {
            // 如果既没有新文件也没有已存在的文件，显示提示
            uploadResult.innerHTML = '<div class="alert alert-warning">没有文件需要上传</div>';
        }
        
        uploadBtn.disabled = false;
    }
    
    // 上传所有新文件
    async function uploadAllNewFiles(files) {
        if (files.length === 0) {
            // 不显示最终结果，因为可能还有覆盖操作
            return;
        }
        
        uploadResult.innerHTML = '<div class="alert alert-info">上传新文件中，请稍候...</div>';
        
        // 确保上传状态区域可见
        if (uploadStatus) {
            uploadStatus.style.display = 'block';
            uploadStatus.classList.remove('d-none');
            
            // 重置进度条状态
            progressBar.style.width = '0%';
            progressBar.setAttribute('aria-valuenow', 0);
            progressText.textContent = '0%';
            
            // 添加动画效果，使进度条更明显
            progressBar.classList.add('progress-bar-striped', 'progress-bar-animated');
        }
        
        // 上传所有新文件，使用分批处理
        const batchSize = 3; // 每批处理3个文件（减小批次大小）
        
        // 分批处理上传
        const processBatch = async (files, startIndex, batchSize) => {
            const endIndex = Math.min(startIndex + batchSize, files.length);
            console.log(`处理批次: ${startIndex + 1} 到 ${endIndex} (共 ${files.length} 个文件)`);
            
            // 处理当前批次的文件
            for (let i = startIndex; i < endIndex; i++) {
                const file = files[i];
                console.log(`上传文件 ${i + 1}/${files.length}: ${file.name}`);
                
                // 更新上传状态显示
                uploadResult.innerHTML = `<div class="alert alert-info">
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                        <div>
                            正在上传新文件 (${i + 1}/${files.length}): ${file.name}
                        </div>
                    </div>
                </div>`;
                
                // 更新顶部进度条状态
                if (topProgressContainer && topCurrentFile) {
                    topProgressContainer.style.display = 'block';
                    topCurrentFile.textContent = `正在上传文件 (${i + 1}/${files.length}): ${file.name}`;
                }
                
                // 添加重试机制
                let success = false;
                const maxAttempts = 3;
                
                for (let attempt = 0; attempt < maxAttempts; attempt++) {
                    try {
                        // 如果不是第一次尝试，添加延迟
                        if (attempt > 0) {
                            console.log(`尝试第 ${attempt + 1} 次上传文件: ${file.name}`);
                            await new Promise(resolve => setTimeout(resolve, 2000 * attempt)); // 递增延迟
                        }
                        
                        const result = await uploadSingleFile(file, false);
                        
                        if (result.success) {
                            success = true;
                            updateUploadStats(result);
                            
                            // 更新进度条
                            const progress = Math.round(((i + 1) / files.length) * 100);
                            progressBar.style.width = `${progress}%`;
                            progressBar.setAttribute('aria-valuenow', progress);
                            progressText.textContent = `${progress}%`;
                            
                            // 同时更新顶部进度条
                            if (topProgressBar && topProgressText) {
                                topProgressBar.style.width = `${progress}%`;
                                topProgressBar.setAttribute('aria-valuenow', progress);
                                topProgressText.textContent = `${progress}%`;
                            }
                            
                            break; // 成功后跳出重试循环
                        } else {
                            console.error(`上传文件失败: ${file.name}`, result);
                            // 如果是最后一次尝试，记录失败
                            if (attempt === maxAttempts - 1) {
                                uploadStats.failed++;
                                uploadStats.failedFiles.push({
                                    name: file.name,
                                    error: result.error || '未知错误'
                                });
                            }
                        }
                    } catch (error) {
                        console.error(`上传文件出错: ${file.name}`, error);
                        // 如果是最后一次尝试，记录失败
                        if (attempt === maxAttempts - 1) {
                            uploadStats.failed++;
                            uploadStats.failedFiles.push({
                                name: file.name,
                                error: error.message || '未知错误'
                            });
                        }
                    }
                }
                
                // 文件之间添加短暂延迟，避免并发问题
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            // 处理下一批次
            if (endIndex < files.length) {
                // 批次之间添加更长的延迟
                await new Promise(resolve => setTimeout(resolve, 2000)); // 增加到2秒
                await processBatch(files, endIndex, batchSize);
            }
        };
        
        // 开始分批处理
        await processBatch(files, 0, batchSize);
        
        // 完成后移除进度条动画效果
        if (progressBar) {
            progressBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
        }
        
        // 注意：不调用showFinalResult()，因为可能还有覆盖操作
        console.log('新文件上传完成');
    }
    
    // 获取CSRF令牌的辅助函数
    function getCSRFToken() {
        // 尝试多种方法获取CSRF令牌
        
        // 方法1: 从表单中获取CSRF令牌
        const tokenField = document.querySelector('input[name="csrf_token"]');
        if (tokenField && tokenField.value) {
            console.log('从表单字段获取到CSRF令牌');
            return tokenField.value;
        }
        
        // 方法2: 从meta标签获取
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken && metaToken.getAttribute('content')) {
            console.log('从meta标签获取到CSRF令牌');
            return metaToken.getAttribute('content');
        }
        
        // 方法3: 从cookie获取
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith('csrf_token=')) {
                const token = cookie.substring('csrf_token='.length, cookie.length);
                if (token) {
                    console.log('从cookie获取到CSRF令牌');
                    return decodeURIComponent(token);
                }
            }
        }
        
        // 方法4: 从任何隐藏的csrf_token字段获取
        const allHiddenInputs = document.querySelectorAll('input[type="hidden"]');
        for (let input of allHiddenInputs) {
            if (input.name && input.name.includes('csrf') && input.value) {
                console.log(`从隐藏字段 ${input.name} 获取到可能的CSRF令牌`);
                return input.value;
            }
        }
        
        // 如果没有找到，记录错误并返回空字符串
        console.error('未找到CSRF令牌，这可能导致请求被服务器拒绝');
        return '';
    }

    // 检查文件是否存在
    async function checkFileExists(filename) {
        try {
            console.log(`检查文件是否存在: ${filename}`);
            
            // 构建URL，包含CSRF令牌作为查询参数
            const csrfToken = getCSRFToken();
            let url = `/api/check-file?filename=${encodeURIComponent(filename)}`;
            if (csrfToken) {
                url += `&csrf_token=${encodeURIComponent(csrfToken)}`;
            }
            
            const response = await fetch(url);
            const result = await response.json();
            console.log(`文件 ${filename} 检查结果:`, result);
            return result;
        } catch (error) {
            console.error('检查文件存在失败:', error);
            return { exists: false, error: error.message };
        }
    }
    
    // 显示批量覆盖选择模态框
    function showBatchOverwriteModal() {
        console.log('准备显示批量覆盖选择模态框', existingFiles.length);
        console.log('已存在文件列表:', existingFiles);
        
        // 确保模态框元素和对象存在
        if (!batchOverwriteModalEl) {
            console.error('找不到批量覆盖模态框元素');
            // 如果无法显示模态框，显示最终结果
            showFinalResult();
            return;
        }
        
        // 确保existingFilesList元素存在
        if (!existingFilesList) {
            console.error('找不到existingFilesList元素');
            // 如果无法显示模态框，显示最终结果
            showFinalResult();
            return;
        }
        
        // 清空列表
        existingFilesList.innerHTML = '';
        
        // 添加文件到列表
        existingFiles.forEach(fileInfo => {
            console.log(`添加文件到批量覆盖列表: ${fileInfo.filename}`, fileInfo);
            const row = document.createElement('tr');
            
            // 复选框
            const checkboxCell = document.createElement('td');
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'form-check';
            const checkbox = document.createElement('input');
            checkbox.className = 'form-check-input';
            checkbox.type = 'checkbox';
            checkbox.checked = true; // 默认选中
            
            // 存储更多的文件标识信息
            checkbox.dataset.filename = fileInfo.filename;
            
            // 存储原始文件名（如果有）
            if (fileInfo.original_filename) {
                checkbox.dataset.originalFilename = fileInfo.original_filename;
            }
            
            // 存储文件ID（如果有）
            if (fileInfo.id || fileInfo.doc_id) {
                checkbox.dataset.id = fileInfo.id || fileInfo.doc_id;
            }
            
            // 如果有文件对象，存储文件对象名称（这是最重要的，用于后续匹配）
            if (fileInfo.file && fileInfo.file.name) {
                checkbox.dataset.fileName = fileInfo.file.name;
            }
            
            checkboxDiv.appendChild(checkbox);
            checkboxCell.appendChild(checkboxDiv);
            
            // 文件名
            const filenameCell = document.createElement('td');
            // 显示原始文件名和数据库中的文件名
            if (fileInfo.file && fileInfo.file.name !== fileInfo.filename) {
                filenameCell.innerHTML = `
                    <div>${fileInfo.file.name}</div>
                    <small class="text-muted">将覆盖: ${fileInfo.original_filename || fileInfo.filename}</small>
                `;
            } else if (fileInfo.original_filename && fileInfo.original_filename !== fileInfo.filename) {
                filenameCell.innerHTML = `
                    <div>${fileInfo.original_filename}</div>
                    <small class="text-muted">存储为: ${fileInfo.filename}</small>
                `;
            } else {
                filenameCell.textContent = fileInfo.filename;
            }
            
            // 标题
            const titleCell = document.createElement('td');
            titleCell.textContent = fileInfo.title || fileInfo.filename;
            
            // 类型
            const typeCell = document.createElement('td');
            const fileType = fileInfo.file_type ? fileInfo.file_type.split('/').pop().toUpperCase() : '未知';
            typeCell.textContent = fileType;
            
            // 大小
            const sizeCell = document.createElement('td');
            sizeCell.textContent = fileInfo.file_size ? formatFileSize(fileInfo.file_size) : '未知';
            
            row.appendChild(checkboxCell);
            row.appendChild(filenameCell);
            row.appendChild(titleCell);
            row.appendChild(typeCell);
            row.appendChild(sizeCell);
            
            existingFilesList.appendChild(row);
        });
        
        // 确保bootstrap已加载
        if (typeof bootstrap === 'undefined') {
            console.error('Bootstrap未加载');
            alert('系统错误: Bootstrap库未加载，无法显示确认对话框');
            // 显示最终结果
            showFinalResult();
            return;
        }
        
        try {
            console.log('尝试显示批量覆盖模态框');
            // 手动创建新的Modal实例
            const modal = new bootstrap.Modal(batchOverwriteModalEl);
            modal.show();
            console.log('批量覆盖模态框已显示');
        } catch (error) {
            console.error('显示批量覆盖模态框时出错:', error);
            // 如果无法显示模态框，显示最终结果
            showFinalResult();
        }
    }
    
    // 上传单个文件
    async function uploadSingleFile(file, overwrite = false) {
        console.log(`准备上传文件: ${file.name}, 覆盖模式: ${overwrite}`);
        
        // 显示顶部进度条并更新当前文件信息
        if (topProgressContainer && topCurrentFile) {
            topProgressContainer.style.display = 'block';
            topCurrentFile.textContent = `正在传输文件: ${file.name}`;
            topProgressBar.style.width = '0%';
            topProgressBar.setAttribute('aria-valuenow', 0);
            topProgressText.textContent = '0%';
        }
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('overwrite', overwrite ? 'true' : 'false');
        
        // 添加CSRF令牌
        const csrfToken = getCSRFToken();
        if (csrfToken) {
            console.log('已添加CSRF令牌到请求');
            formData.append('csrf_token', csrfToken);
        } else {
            console.warn('未能获取CSRF令牌，尝试继续上传');
        }
        
        try {
            console.log('发送文件上传请求...');
            
            // 添加请求超时处理 - 根据文件大小动态调整超时时间
            const controller = new AbortController();
            
            // 计算超时时间：基础30秒 + 每MB增加5秒，最长5分钟
            const fileSizeMB = file.size / (1024 * 1024);
            const baseTimeout = 30000; // 30秒基础时间
            const timePerMB = 5000; // 每MB增加5秒
            const maxTimeout = 5 * 60 * 1000; // 最长5分钟
            
            // 计算实际超时时间
            const calculatedTimeout = baseTimeout + (fileSizeMB * timePerMB);
            const timeout = Math.min(calculatedTimeout, maxTimeout);
            
            console.log(`文件大小: ${fileSizeMB.toFixed(2)}MB, 设置超时时间: ${(timeout/1000).toFixed(1)}秒`);
            
            const timeoutId = setTimeout(() => {
                console.warn(`上传文件 ${file.name} 超时，中断请求`);
                controller.abort();
            }, timeout);
            
            const response = await fetch('/upload/batch', {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });
            
            // 清除超时计时器
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                console.error(`服务器响应错误: ${response.status} ${response.statusText}`);
                return { 
                    success: false, 
                    error: `服务器响应错误: ${response.status} ${response.statusText}` 
                };
            }
            
            const result = await response.json();
            console.log(`文件 ${file.name} 上传结果:`, result);
            
            // 检查结果中是否包含嵌套的结果数组
            if (result.results && Array.isArray(result.results) && result.results.length > 0) {
                // 返回第一个结果项
                return result.results[0];
            }
            
            return result;
        } catch (error) {
            console.error(`上传文件 ${file.name} 时发生错误:`, error);
            
            // 检查是否是超时错误
            if (error.name === 'AbortError') {
                return { 
                    success: false, 
                    error: '请求超时，文件可能过大或网络连接不稳定' 
                };
            }
            
            return { 
                success: false, 
                error: error.message || '未知错误' 
            };
        }
    }
    
    // 更新上传统计
    function updateUploadStats(result, filename) {
        if (result.success) {
            if (result.overwritten) {
                uploadStats.overwritten++;
            } else {
                uploadStats.success++;
            }
        } else if (result.exists) {
            uploadStats.skipped++;
        } else {
            uploadStats.failed++;
            
            // 初始化失败文件列表（如果不存在）
            if (!uploadStats.failedFiles) {
                uploadStats.failedFiles = [];
            }
            
            // 确保有文件名信息
            let failedFileName = result.filename || filename || '未知文件';
            let errorMessage = result.error || '未知错误';
            
            // 获取详细的错误信息
            if (result.message && result.message !== result.error) {
                errorMessage += ` (${result.message})`;
            }
            
            // 如果结果中包含文件名和错误信息，添加到失败文件列表
            const failedFile = {
                name: failedFileName,
                error: errorMessage
            };
            
            // 检查是否已经存在相同的失败记录，避免重复
            const exists = uploadStats.failedFiles.some(file => 
                file.name === failedFile.name && file.error === failedFile.error
            );
            
            if (!exists) {
                console.error(`记录失败文件: ${failedFile.name}, 错误: ${failedFile.error}`);
                uploadStats.failedFiles.push(failedFile);
            }
        }
    }
    
    // 显示最终结果
    function showFinalResult() {
        console.log('显示上传结果', uploadStats);
        
        // 恢复批量删除按钮
        const batchDeleteBtn = document.getElementById('batch-delete-queue');
        if (batchDeleteBtn) {
            batchDeleteBtn.disabled = false;
        }
        
        // 确保uploadResultContent元素存在
        if (!uploadResultContent) {
            console.error('找不到上传结果内容元素');
            // 即使找不到上传结果内容元素，也在控制台显示失败文件信息
            if (uploadStats.failedFiles && uploadStats.failedFiles.length > 0) {
                console.error('失败文件列表:', uploadStats.failedFiles);
            }
            alert(`上传完成: 成功 ${uploadStats.success}, 覆盖 ${uploadStats.overwritten}, 跳过 ${uploadStats.skipped}, 失败 ${uploadStats.failed}`);
            return;
        }
        
        let resultHTML = '<ul class="list-group mb-3">';
        
        if (uploadStats.success > 0) {
            resultHTML += `<li class="list-group-item list-group-item-success">
                <i class="bi bi-check-circle-fill me-2"></i>
                新上传成功: ${uploadStats.success} 个文件
            </li>`;
        }
        
        if (uploadStats.overwritten > 0) {
            resultHTML += `<li class="list-group-item list-group-item-warning">
                <i class="bi bi-arrow-repeat me-2"></i>
                成功覆盖: ${uploadStats.overwritten} 个文件
                <div class="mt-1 small text-success"><i class="bi bi-check-circle"></i> 覆盖操作已成功完成</div>
            </li>`;
        }
        
        if (uploadStats.skipped > 0) {
            resultHTML += `<li class="list-group-item list-group-item-info">
                <i class="bi bi-skip-forward-fill me-2"></i>
                跳过上传: ${uploadStats.skipped} 个文件
            </li>`;
        }
        
        if (uploadStats.failed > 0) {
            resultHTML += `<li class="list-group-item list-group-item-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                上传失败: ${uploadStats.failed} 个文件`;
            
            // 添加失败文件详情，确保始终显示
            if (uploadStats.failedFiles && uploadStats.failedFiles.length > 0) {
                resultHTML += `<div class="mt-2">
                    <strong>失败详情:</strong>
                    <ul class="mt-1 mb-0 small">`;
                
                // 确保所有失败文件都被显示
                uploadStats.failedFiles.forEach(file => {
                    resultHTML += `<li><strong>${file.name || '未知文件'}</strong> - <span class="text-danger">${file.error || '未知错误'}</span></li>`;
                });
                
                resultHTML += `</ul>
                </div>`;
            } else {
                // 如果 failedFiles 数组不存在或为空，但 failed 计数大于0，显示通用错误信息
                resultHTML += `<div class="mt-2">
                    <span class="text-danger">发生错误，但未能获取详细信息</span>
                </div>`;
            }
            
            resultHTML += `</li>`;
        }
        
        resultHTML += '</ul>';
        
        // 根据是否有成功上传决定显示提示
        if (uploadStats.success > 0 || uploadStats.overwritten > 0) {
            resultHTML += '<div class="alert alert-success"><i class="bi bi-info-circle-fill me-2"></i>系统将在关闭此窗口后刷新页面，显示最新上传的文件。</div>';
        }
        
        // 如果有跳过的文件，添加提示信息
        if (uploadStats.skipped > 0) {
            resultHTML += '<div class="alert alert-info"><i class="bi bi-info-circle-fill me-2"></i>如需覆盖跳过的文件，请重新选择这些文件并选择覆盖选项。</div>';
        }
        
        // 如果有失败的文件，添加重试提示和批量覆盖建议
        if (uploadStats.failed > 0) {
            resultHTML += `<div class="alert alert-warning">
                <i class="bi bi-arrow-clockwise me-2"></i>如需重新上传失败的文件，请在关闭此窗口后重新选择这些文件。
                <div class="mt-2 small text-muted">
                    <strong>提示:</strong> 对于批量覆盖失败的文件，建议尝试单个文件逐一覆盖，或者在系统较空闲时再次尝试。
                </div>
            </div>`;
        }
        
        // 如果所有文件都被跳过，显示特殊提示
        if (uploadStats.success === 0 && uploadStats.overwritten === 0 && uploadStats.skipped > 0 && uploadStats.failed === 0) {
            resultHTML += '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle-fill me-2"></i>所有文件都已跳过上传，没有任何文件被添加或覆盖。</div>';
        }
        
        uploadResultContent.innerHTML = resultHTML;
        
        // 确保bootstrap已加载
        if (typeof bootstrap === 'undefined') {
            console.error('Bootstrap未加载');
            alert(`上传完成: 成功 ${uploadStats.success}, 覆盖 ${uploadStats.overwritten}, 跳过 ${uploadStats.skipped}, 失败 ${uploadStats.failed}`);
            // 在控制台显示失败文件信息
            if (uploadStats.failedFiles && uploadStats.failedFiles.length > 0) {
                console.error('失败文件列表:', uploadStats.failedFiles);
            }
            return;
        }
        
        try {
            console.log('尝试显示上传结果模态框');
            // 手动创建新的Modal实例
            const modal = new bootstrap.Modal(document.getElementById('uploadResultModal'));
            modal.show();
            console.log('上传结果模态框已显示');
            
            // 重置文件输入框，确保可以重新选择相同文件
            if (fileInput) {
                fileInput.value = '';
            }
        } catch (error) {
            console.error('显示上传结果模态框时出错:', error);
            alert(`上传完成: 成功 ${uploadStats.success}, 覆盖 ${uploadStats.overwritten}, 跳过 ${uploadStats.skipped}, 失败 ${uploadStats.failed}`);
            // 在控制台显示失败文件信息
            if (uploadStats.failedFiles && uploadStats.failedFiles.length > 0) {
                console.error('失败文件列表:', uploadStats.failedFiles);
            }
        }
        
        // 清空文件列表
        if (uploadStats.success > 0 || uploadStats.overwritten > 0) {
            selectedFiles = [];
            updateFileList();
            hideUploadUI();
        }
    }
    
    // 更新进度条
    function updateProgress(percentage) {
        const percent = Math.round(percentage * 100);
        
        // 更新原始进度条
        progressBar.style.width = `${percent}%`;
        progressText.textContent = `${percent}%`;
        
        // 同时更新顶部进度条
        if (topProgressBar && topProgressText) {
            topProgressBar.style.width = `${percent}%`;
            topProgressText.textContent = `${percent}%`;
            
            // 确保顶部进度条容器可见
            if (topProgressContainer) {
                topProgressContainer.style.display = 'block';
            }
        }
    }
    
    // 格式化文件大小
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // 从上传队列中移除已存在的文件
    function removeExistingFilesFromQueue() {
        if (!existingFiles || existingFiles.length === 0) return;
        
        console.log(`准备从队列中移除 ${existingFiles.length} 个已存在的文件`);
        
        // 获取要移除的文件名
        const filesToRemove = existingFiles.map(fileInfo => fileInfo.file.name);
        
        // 从selectedFiles中移除这些文件
        selectedFiles = selectedFiles.filter(file => !filesToRemove.includes(file.name));
        console.log(`移除后队列中还剩 ${selectedFiles.length} 个文件`);
        
        // 更新文件列表UI
        updateFileList();
        
        // 如果没有文件了，隐藏上传UI
        if (selectedFiles.length === 0) {
            hideUploadUI();
        }
        
        // 隐藏顶部进度条
        if (topProgressContainer) {
            topProgressContainer.style.display = 'none';
        }
        
        // 清空existingFiles数组
        existingFiles = [];
    }
    
    // 显示上传进度结果
    function showUploadResult() {
        // 更新进度条为100%
        if (progressBar && progressText) {
            progressBar.style.width = '100%';
            progressBar.setAttribute('aria-valuenow', 100);
            progressText.textContent = '100%';
        }
        
        // 同时更新顶部进度条
        if (topProgressBar && topProgressText) {
            topProgressBar.style.width = '100%';
            topProgressBar.setAttribute('aria-valuenow', 100);
            topProgressText.textContent = '100%';
            
            // 更新当前处理文件提示
            if (topCurrentFile) {
                topCurrentFile.textContent = '上传完成';
            }
            
            // 3秒后自动隐藏顶部进度条
            setTimeout(() => {
                if (topProgressContainer) {
                    topProgressContainer.style.display = 'none';
                }
            }, 3000);
        }
        
        // 显示临时上传结果
        if (uploadResult) {
            uploadResult.innerHTML = '<div class="alert alert-info">上传完成，正在处理结果...</div>';
        }
    }

    // 处理批量覆盖文件
    async function processBatchOverwrite(filesToOverwrite) {
        console.log(`开始处理批量覆盖: ${filesToOverwrite.length} 个文件`);
        console.log('要覆盖的文件列表:', filesToOverwrite);
        console.log('当前选中的文件列表:', selectedFiles.map(f => f.name));
        console.log('已存在的文件列表:', existingFiles);
        
        // 重要：创建文件信息的副本，避免在处理过程中被修改
        const existingFilesCopy = JSON.parse(JSON.stringify(existingFiles.map(info => {
            // 只复制必要的信息，file对象不能被JSON序列化，需要单独处理
            return {
                filename: info.filename,
                original_filename: info.original_filename,
                id: info.id || info.doc_id,
                file_name: info.file ? info.file.name : null
            };
        })));
        
        // 创建文件对象的映射，用于快速查找
        const fileMap = new Map();
        selectedFiles.forEach(file => {
            fileMap.set(file.name, file);
        });
        
        // 确保进度条区域完全可见
        uploadStatus.style.display = 'block';
        uploadStatus.classList.remove('d-none');
        
        // 使用更明显的进度条样式
        progressBar.classList.add('progress-bar-striped', 'progress-bar-animated');
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', 0);
        progressText.textContent = '0%';
        
        // 显示正在处理的信息
        uploadResult.innerHTML = '<div class="alert alert-info">' +
            '<div class="d-flex align-items-center">' +
            '<div class="spinner-border spinner-border-sm me-2" role="status"></div>' +
            '<div>正在准备覆盖文件，总计: ' + filesToOverwrite.length + ' 个文件</div>' +
            '</div></div>';
        
        // 分批处理覆盖，适当增加批次大小
        const batchSize = 2; // 增加到每批处理2个文件，提高效率
        
        const processBatch = async (files, startIndex, batchSize) => {
            const endIndex = Math.min(startIndex + batchSize, files.length);
            console.log(`处理覆盖批次: ${startIndex + 1} 到 ${endIndex} (共 ${files.length} 个文件)`);
            
            // 更新总体进度显示
            const batchProgress = Math.round((startIndex / files.length) * 100);
            progressBar.style.width = `${batchProgress}%`;
            progressBar.setAttribute('aria-valuenow', batchProgress);
            progressText.textContent = `${batchProgress}%`;
            
            for (let i = startIndex; i < endIndex; i++) {
                const filename = files[i];
                console.log(`尝试查找文件对象: ${filename}`);
                
                // 更新进度条显示当前处理的文件
                const currentProgress = Math.round(((i + 0.5) / files.length) * 100);
                progressBar.style.width = `${currentProgress}%`;
                progressBar.setAttribute('aria-valuenow', currentProgress);
                progressText.textContent = `${currentProgress}%`;
                
                // 同时更新顶部进度条
                if (topProgressBar && topProgressText) {
                    topProgressBar.style.width = `${currentProgress}%`;
                    topProgressBar.setAttribute('aria-valuenow', currentProgress);
                    topProgressText.textContent = `${currentProgress}%`;
                    
                    // 确保顶部进度条容器可见
                    if (topProgressContainer) {
                        topProgressContainer.style.display = 'block';
                    }
                    
                    // 更新当前处理文件信息
                    if (topCurrentFile) {
                        topCurrentFile.textContent = `正在传输文件 (${i + 1}/${files.length}): ${filename}`;
                    }
                }
                
                // 增强文件名匹配逻辑
                let file = null;
                
                // 方法1: 直接从文件映射中获取
                file = fileMap.get(filename);
                if (file) {
                    console.log(`方法1成功: 直接从文件映射中获取文件对象: ${file.name}`);
                }
                
                // 方法2: 如果方法1失败，尝试通过文件名匹配
                if (!file) {
                    file = selectedFiles.find(f => f.name === filename);
                    if (file) {
                        console.log(`方法2成功: 直接通过文件名匹配到文件对象: ${file.name}`);
                    }
                }
                
                // 方法3: 尝试通过存储的文件信息查找
                if (!file) {
                    console.log(`直接匹配失败，尝试通过存储的文件信息查找: ${filename}`);
                    const fileInfo = existingFilesCopy.find(info => info.filename === filename);
                    if (fileInfo && fileInfo.file_name) {
                        file = fileMap.get(fileInfo.file_name) || selectedFiles.find(f => f.name === fileInfo.file_name);
                        if (file) {
                            console.log(`方法3成功: 通过存储的文件信息找到文件对象: ${file.name}`);
                        }
                    }
                }
                
                // 方法4: 尝试不区分大小写匹配
                if (!file) {
                    console.log(`尝试不区分大小写匹配: ${filename}`);
                    const lowerFilename = filename.toLowerCase();
                    file = selectedFiles.find(f => f.name.toLowerCase() === lowerFilename);
                    if (file) {
                        console.log(`方法4成功: 通过不区分大小写匹配到文件对象: ${file.name}`);
                    }
                }
                
                // 方法5: 尝试匹配原始文件名
                if (!file) {
                    console.log(`尝试匹配原始文件名: ${filename}`);
                    // 在原始存储的文件信息中查找
                    const matchingFileInfo = existingFilesCopy.find(info => 
                        info.original_filename === filename || 
                        (info.original_filename && info.original_filename.toLowerCase() === filename.toLowerCase())
                    );
                    if (matchingFileInfo && matchingFileInfo.file_name) {
                        file = fileMap.get(matchingFileInfo.file_name) || selectedFiles.find(f => f.name === matchingFileInfo.file_name);
                        if (file) {
                            console.log(`方法5成功: 通过原始文件名找到文件对象: ${file.name}`);
                        }
                    }
                }
                
                // 方法6: 最后尝试，遍历所有文件对象
                if (!file) {
                    console.log(`尝试遍历所有文件对象进行匹配`);
                    for (const f of selectedFiles) {
                        console.log(`检查文件: ${f.name}`);
                        // 检查文件名是否部分匹配
                        if (f.name.includes(filename) || filename.includes(f.name)) {
                            file = f;
                            console.log(`方法6成功: 通过部分匹配找到文件对象: ${file.name}`);
                            break;
                        }
                    }
                }
                
                if (!file) {
                    console.error(`找不到要覆盖的文件: ${filename}`);
                    console.error('当前选中的文件列表:', selectedFiles.map(f => f.name));
                    console.error('已存在的文件列表副本:', existingFilesCopy);
                    console.error('文件映射:', Array.from(fileMap.entries()));
                    uploadStats.failed++;
                    uploadStats.failedFiles.push({
                        name: filename,
                        error: '找不到文件对象'
                    });
                    
                    // 更新进度条
                    const progress = Math.round(((i + 1) / files.length) * 100);
                    progressBar.style.width = `${progress}%`;
                    progressBar.setAttribute('aria-valuenow', progress);
                    progressText.textContent = `${progress}%`;
                    
                    continue;
                }
                
                console.log(`覆盖文件 ${i + 1}/${files.length}: ${file.name}`);
                
                // 更新处理状态显示
                uploadResult.innerHTML = `<div class="alert alert-info">
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                        <div>
                            正在覆盖文件 (${i + 1}/${files.length}): ${file.name}
                        </div>
                    </div>
                </div>`;
                
                // 添加重试机制
                let success = false;
                const maxAttempts = 3;
                
                for (let attempt = 0; attempt < maxAttempts; attempt++) {
                    try {
                        // 如果不是第一次尝试，添加延迟
                        if (attempt > 0) {
                            const retryDelay = 2000 * attempt; // 减少到2秒的基础延迟
                            console.log(`尝试第 ${attempt + 1} 次覆盖文件: ${file.name}，等待 ${retryDelay/1000} 秒...`);
                            await new Promise(resolve => setTimeout(resolve, retryDelay));
                            
                            // 更新重试状态显示
                            uploadResult.innerHTML = `<div class="alert alert-warning">
                                <div class="d-flex align-items-center">
                                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                                    <div>
                                        正在覆盖文件 (${i + 1}/${files.length}): ${file.name}
                                        <span class="badge bg-warning ms-2">第 ${attempt + 1} 次尝试</span>
                                    </div>
                                </div>
                            </div>`;
                        }
                        
                        const result = await uploadSingleFile(file, true);
                        
                        if (result.success) {
                            success = true;
                            updateUploadStats(result, file.name);
                            
                            // 更新进度条
                            const progress = Math.round(((i + 1) / files.length) * 100);
                            progressBar.style.width = `${progress}%`;
                            progressBar.setAttribute('aria-valuenow', progress);
                            progressText.textContent = `${progress}%`;
                            
                            // 同时更新顶部进度条
                            if (topProgressBar && topProgressText) {
                                topProgressBar.style.width = `${progress}%`;
                                topProgressBar.setAttribute('aria-valuenow', progress);
                                topProgressText.textContent = `${progress}%`;
                            }
                            
                            break; // 成功后跳出重试循环
                        } else {
                            console.error(`覆盖文件失败: ${file.name}`, result);
                            // 如果是最后一次尝试，记录失败
                            if (attempt === maxAttempts - 1) {
                                uploadStats.failed++;
                                uploadStats.failedFiles.push({
                                    name: file.name,
                                    error: result.error || '未知错误'
                                });
                                
                                // 更新进度条
                                const progress = Math.round(((i + 1) / files.length) * 100);
                                progressBar.style.width = `${progress}%`;
                                progressBar.setAttribute('aria-valuenow', progress);
                                progressText.textContent = `${progress}%`;
                                
                                // 同时更新顶部进度条
                                if (topProgressBar && topProgressText) {
                                    topProgressBar.style.width = `${progress}%`;
                                    topProgressBar.setAttribute('aria-valuenow', progress);
                                    topProgressText.textContent = `${progress}%`;
                                }
                            }
                        }
                    } catch (error) {
                        console.error(`覆盖文件出错: ${file.name}`, error);
                        // 如果是最后一次尝试，记录失败
                        if (attempt === maxAttempts - 1) {
                            uploadStats.failed++;
                            uploadStats.failedFiles.push({
                                name: file.name,
                                error: error.message || '未知错误'
                            });
                            
                            // 更新进度条
                            const progress = Math.round(((i + 1) / files.length) * 100);
                            progressBar.style.width = `${progress}%`;
                            progressBar.setAttribute('aria-valuenow', progress);
                            progressText.textContent = `${progress}%`;
                            
                            // 同时更新顶部进度条
                            if (topProgressBar && topProgressText) {
                                topProgressBar.style.width = `${progress}%`;
                                topProgressBar.setAttribute('aria-valuenow', progress);
                                topProgressText.textContent = `${progress}%`;
                            }
                        }
                    }
                }
                
                // 文件之间添加短暂延迟，避免并发问题
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            // 处理下一批次
            if (endIndex < files.length) {
                // 批次之间添加更长的延迟
                await new Promise(resolve => setTimeout(resolve, 2000)); // 增加到2秒
                await processBatch(files, endIndex, batchSize);
            }
        };
        
        // 开始分批处理
        if (filesToOverwrite.length > 0) {
            await processBatch(filesToOverwrite, 0, batchSize);
            console.log('批量覆盖处理完成');
        } else {
            console.log('没有文件需要覆盖');
        }
        
        // 不在这里调用showFinalResult，让调用方决定何时显示最终结果
        // 这样可以在处理完所有文件（包括新文件）后再显示最终结果
    }
}

/**
 * 初始化实时搜索功能
 */
function initLiveSearch() {
    const searchInput = document.getElementById('search-input');
    const liveResults = document.getElementById('live-search-results');
    const resultsContainer = document.getElementById('results-container');
    
    if (!searchInput || !liveResults) return;
    
    let searchTimeout;
    
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        
        // 清除之前的搜索计时器
        clearTimeout(searchTimeout);
        
        if (query.length >= 2) {
            // 添加加载指示器
            liveResults.classList.remove('d-none');
            resultsContainer.innerHTML = '<div class="text-center p-3"><div class="spinner-border text-primary" role="status"></div><span class="ms-2">搜索中...</span></div>';
            
            // 设置延迟，避免频繁请求
            searchTimeout = setTimeout(function() {
                fetchSearchResults(query);
            }, 300);
        } else {
            liveResults.classList.add('d-none');
        }
    });
    
    // 点击页面其他位置时隐藏结果
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !liveResults.contains(e.target)) {
            liveResults.classList.add('d-none');
        }
    });
    
    // 获取搜索结果
    function fetchSearchResults(query) {
        fetch(`/api/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    resultsContainer.innerHTML = `<div class="text-danger p-3">搜索出错: ${data.error}</div>`;
                } else if (data.results.length === 0) {
                    resultsContainer.innerHTML = '<div class="text-muted p-3">没有找到匹配结果</div>';
                } else {
                    displayResults(data.results, query);
                }
            })
            .catch(error => {
                resultsContainer.innerHTML = `<div class="text-danger p-3">搜索请求失败: ${error}</div>`;
            });
    }
    
    // 显示搜索结果
    function displayResults(results, query) {
        resultsContainer.innerHTML = '';
        
        results.slice(0, 5).forEach(result => {
            const resultItem = document.createElement('a');
            resultItem.href = `/document/${result.id}?q=${encodeURIComponent(query)}`;
            resultItem.className = 'list-group-item list-group-item-action';
            
            const title = document.createElement('div');
            title.className = 'fw-bold';
            title.textContent = result.title;
            
            const preview = document.createElement('div');
            preview.className = 'small text-muted';
            preview.innerHTML = result.snippet;
            
            resultItem.appendChild(title);
            resultItem.appendChild(preview);
            resultsContainer.appendChild(resultItem);
        });
        
        if (results.length > 5) {
            const moreResults = document.createElement('a');
            moreResults.href = `/search?q=${encodeURIComponent(query)}`;
            moreResults.className = 'list-group-item list-group-item-action text-center';
            moreResults.textContent = `查看全部 ${results.length} 个结果`;
            resultsContainer.appendChild(moreResults);
        }
    }
}

/**
 * 初始化已浏览文档跟踪功能
 * @param {boolean} [isRefresh=false] - 是否是页面刷新
 */
function initVisitedDocumentsTracker(isRefresh = false) {
    console.log('初始化已浏览文档跟踪功能');
    
    try {
        // 在当前页面URL中查找文档ID
        const urlPath = window.location.pathname;
        const docRegex = /\/document\/(\d+)/;
        const match = urlPath.match(docRegex);
        
        if (match) {
            // 当前页面是文档查看页面，记录已浏览
            const docId = match[1];
            console.log(`当前正在查看文档ID: ${docId}`);
            
            // 获取URL查询参数中的搜索关键词
            const urlParams = new URLSearchParams(window.location.search);
            const searchQuery = urlParams.get('q') || '';
            const searchId = urlParams.get('search_id') || '';
            
            // 更新全局状态变量
            isDocumentPage = true;
            lastViewedDocId = docId;
            lastViewedDocQuery = searchQuery;
            
            // 保存到会话存储，用于从缓存恢复时使用
            sessionStorage.setItem('docradar_last_viewed_doc_id', docId);
            sessionStorage.setItem('docradar_last_viewed_doc_query', searchQuery);
            sessionStorage.setItem('docradar_last_viewed_doc_search_id', searchId);
            
            // 如果是页面刷新，先记录这个信息
            if (isRefresh) {
                console.log(`检测到页面刷新，文档页面的刷新不会清空浏览记录`);
            }
            
            // 标记文档为已浏览，传递搜索关键词
            markDocumentAsVisited(docId, false, searchQuery);
            
            // 为返回搜索结果按钮添加点击事件
            const backToSearchBtn = document.getElementById('back-to-search');
            if (backToSearchBtn) {
                backToSearchBtn.addEventListener('click', function(e) {
                    // 不阻止默认行为，但强制确保已浏览状态已保存
                    console.log('点击返回搜索结果按钮，确保已浏览状态已保存');
                    markDocumentAsVisited(docId, true, searchQuery);
                    
                    // 设置正常导航标记，与浏览器返回按钮区分
                    sessionStorage.setItem('docradar_normal_navigation', 'true');
                    
                    // 设置会话标记，告知页面不要在下一个搜索页面加载时重置访问状态
                    sessionStorage.setItem('docradar_back_to_search', 'true');
                    
                    // 保存当前搜索查询，确保返回后仍使用同一个查询
                    if (searchQuery) {
                        console.log(`保存当前搜索查询: "${searchQuery}"`);
                        sessionStorage.setItem('docradar_current_search', searchQuery);
                    } else {
                        // 如果没有搜索查询参数，清除之前保存的查询
                        sessionStorage.removeItem('docradar_current_search');
                    }
                });
            }
        } else {
            // 是搜索结果页面
            isDocumentPage = false;
            
            // 检查是否为刷新
            if (isRefresh) {
                console.log(`检测到页面刷新，将清空所有关键词的浏览记录`);
            } else {
                console.log(`正常页面加载，将保留并标记已浏览文档`);
            }
            
            // 调用标记函数，传递刷新状态
            markVisitedDocumentsInResults(isRefresh);
        }
    } catch (error) {
        console.error('初始化已浏览文档跟踪功能时发生错误:', error);
    }
}

/**
 * 将文档标记为已浏览
 * @param {string} docId - 文档ID
 * @param {boolean} [force=false] - 是否强制更新时间戳
 * @param {string} [searchQuery=''] - 搜索关键词
 */
function markDocumentAsVisited(docId, force = false, searchQuery = '') {
    if (!docId) return;
    
    try {
        // 获取URL中的搜索查询参数
        if (!searchQuery) {
            const urlParams = new URLSearchParams(window.location.search);
            searchQuery = urlParams.get('q') || '';
        }
        
        console.log(`标记文档 ${docId} 为已浏览，关联搜索词: "${searchQuery}"`);
        
        // 从localStorage中获取已浏览文档映射表
        let visitedDocsMap = {};
        const visitedDocsMapStr = localStorage.getItem('docradar_visited_docs_map');
        if (visitedDocsMapStr) {
            try {
                visitedDocsMap = JSON.parse(visitedDocsMapStr);
            } catch (e) {
                console.error('解析已浏览文档映射表失败:', e);
                // 重置为空对象
                visitedDocsMap = {};
            }
        }
        
        // 确保搜索查询键存在
        if (!visitedDocsMap[searchQuery]) {
            visitedDocsMap[searchQuery] = [];
        }
        
        // 检查文档是否已在对应查询的列表中
        if (!visitedDocsMap[searchQuery].includes(docId) || force) {
            // 如果不在列表中或强制更新
            if (!visitedDocsMap[searchQuery].includes(docId)) {
                // 添加到列表
                visitedDocsMap[searchQuery].push(docId);
            }
            
            // 如果列表过长，删除较早的记录（保留最新的50条）
            if (visitedDocsMap[searchQuery].length > 50) {
                visitedDocsMap[searchQuery] = visitedDocsMap[searchQuery].slice(-50);
            }
            
            // 保存到localStorage
            localStorage.setItem('docradar_visited_docs_map', JSON.stringify(visitedDocsMap));
            
            // 添加最后访问时间戳，用于后续控制刷新时是否恢复样式
            const visitTime = new Date().getTime();
            localStorage.setItem(`docradar_visit_time_${searchQuery}_${docId}`, visitTime);
            
            console.log(`文档 ${docId} 已标记为已浏览，关联搜索词: "${searchQuery}", 时间戳: ${visitTime}`);
            
            // 更新全局状态变量
            lastViewedDocId = docId;
            lastViewedDocQuery = searchQuery;
            
            // 将此文档ID和查询保存到sessionStorage，用于浏览器返回时识别
            sessionStorage.setItem('docradar_last_viewed_doc_id', docId);
            sessionStorage.setItem('docradar_last_viewed_doc_query', searchQuery);
        } else {
            console.log(`文档 ${docId} 之前已在搜索 "${searchQuery}" 中浏览过`);
        }
    } catch (error) {
        console.error('标记文档为已浏览时发生错误:', error);
    }
}

/**
 * 获取已浏览文档列表
 * @param {string} [searchQuery=''] - 搜索关键词，如果提供则返回该搜索下的已浏览文档
 * @returns {Array} 已浏览文档ID数组
 */
function getVisitedDocuments(searchQuery = '') {
    try {
        // 如果没有指定搜索关键词，尝试从URL获取
        if (!searchQuery) {
            const urlParams = new URLSearchParams(window.location.search);
            searchQuery = urlParams.get('q') || '';
        }
        
        // 使用搜索关键词从映射表中获取已浏览文档列表
        const visitedDocsMapStr = localStorage.getItem('docradar_visited_docs_map');
        if (visitedDocsMapStr) {
            try {
                const visitedDocsMap = JSON.parse(visitedDocsMapStr);
                
                // 如果指定了搜索查询且该查询存在于映射表中，返回对应的文档列表
                if (searchQuery && visitedDocsMap[searchQuery]) {
                    console.log(`获取搜索"${searchQuery}"的已浏览文档列表: ${JSON.stringify(visitedDocsMap[searchQuery])}`);
                    return visitedDocsMap[searchQuery];
                }
                
                // 如果没有指定搜索查询或该查询不存在，返回空数组
                console.log(`搜索"${searchQuery}"没有已浏览文档记录，返回空数组`);
                return [];
            } catch (e) {
                console.error('解析已浏览文档映射表失败:', e);
                return [];
            }
        }
        
        // 如果没有映射表，返回空数组
        return [];
        
        // 移除以下回退到全局文档列表的逻辑
        /*
        // 兼容旧版存储方式
        const visitedDocsStr = localStorage.getItem('docradar_visited_docs');
        return visitedDocsStr ? JSON.parse(visitedDocsStr) : [];
        */
    } catch (error) {
        console.error('获取已浏览文档列表时发生错误:', error);
        return [];
    }
}

/**
 * 在搜索结果页面标记已浏览的文档
 * @param {boolean} [isRefresh=false] - 是否是页面刷新
 * @param {boolean} [isTabSwitch=false] - 是否是标签切换
 */
function markVisitedDocumentsInResults(isRefresh = false, isTabSwitch = false) {
    try {
        // 确认当前是搜索结果页面
        if (!window.location.pathname.includes('/search')) {
            console.log('不是搜索结果页面，跳过标记');
            return;
        }
        
        console.log(`===== 开始标记已浏览文档 =====`);
        console.log(`页面加载状态: 刷新=${isRefresh}, 标签切换=${isTabSwitch}`);
        
        // 获取当前搜索查询
        const urlParams = new URLSearchParams(window.location.search);
        const currentQuery = urlParams.get('q') || '';
        console.log(`当前搜索查询: "${currentQuery}"`);
        
        // 获取搜索结果列表
        const resultItems = document.querySelectorAll('.search-result-item');
        if (!resultItems.length) {
            console.log('页面上没有搜索结果元素');
            return;
        }
        
        console.log(`找到 ${resultItems.length} 个搜索结果元素`);
        
        // 检查是否从文档查看页面返回
        const isBackFromDocument = sessionStorage.getItem('docradar_back_to_search') === 'true';
        console.log(`是否从文档查看页面返回: ${isBackFromDocument}`);
        
        // 获取返回时间戳
        const backToSearchTime = sessionStorage.getItem('docradar_back_to_search_time');
        const currentTime = new Date().getTime();
        const isNormalNavigation = sessionStorage.getItem('docradar_normal_navigation') === 'true';
        
        // 检查是否是从文档返回后的刷新操作
        // 如果有返回时间戳，且在5秒内刷新，且不是正常导航，则视为返回后的刷新操作
        const isRefreshAfterBack = isRefresh && backToSearchTime && 
            (currentTime - parseInt(backToSearchTime)) < 5000 && 
            !isNormalNavigation;
        
        if (isRefreshAfterBack) {
            console.log('检测到从文档返回后的刷新操作，清除当前关键词的浏览记录');
            // 清除时间戳和返回标记
            sessionStorage.removeItem('docradar_back_to_search');
            sessionStorage.removeItem('docradar_back_to_search_time');
            
            // 清除当前关键词的浏览记录
            clearCurrentQueryVisitedDocs(currentQuery);
            return;
        }
        
        // 在任何情况下，首先清除所有已浏览标记
        // 这确保不同关键词结果列表的浏览状态不会互相干扰
        resultItems.forEach(item => {
            if (item.classList.contains('visited')) {
                item.classList.remove('visited');
            }
        });
        console.log('已清除所有结果项的已浏览标记');
        
        // 如果是刷新页面且不是从文档返回，清除所有关键词的浏览记录
        if (isRefresh && !isBackFromDocument && !isTabSwitch) {
            console.log('检测到页面刷新，清除所有关键词的浏览记录');
            
            // 清空整个浏览记录映射表
            const visitedDocsMapStr = localStorage.getItem('docradar_visited_docs_map');
            if (visitedDocsMapStr) {
                try {
                    const visitedDocsMap = JSON.parse(visitedDocsMapStr);
                    
                    // 记录清除了多少个关键词的记录
                    const keywordCount = Object.keys(visitedDocsMap).length;
                    
                    if (keywordCount > 0) {
                        // 清空整个映射表
                        localStorage.setItem('docradar_visited_docs_map', JSON.stringify({}));
                        console.log(`已清空所有关键词(${keywordCount}个)的浏览记录`);
                    } else {
                        console.log('浏览记录映射表中没有记录，无需清空');
                    }
                } catch (e) {
                    console.error('解析已浏览文档映射表失败:', e);
                    // 出错时也尝试重置
                    localStorage.setItem('docradar_visited_docs_map', JSON.stringify({}));
                }
            } else {
                console.log('没有找到浏览记录映射表');
            }
            
            // 清除会话标记
            sessionStorage.removeItem('docradar_back_to_search');
            
            console.log('已清除所有关键词的浏览记录');
            return;
        }
        
        // 根据当前搜索查询获取已浏览文档列表
        const visitedDocs = getVisitedDocuments(currentQuery);
        console.log(`当前搜索"${currentQuery}"的已浏览文档列表: ${JSON.stringify(visitedDocs)}`);
        
        if (!visitedDocs.length) {
            console.log(`搜索"${currentQuery}"没有已浏览的文档记录`);
            return;
        }
        
        // 记录成功标记的数量，用于调试
        let markedCount = 0;
        
        // 遍历搜索结果，检查每个结果是否已浏览
        resultItems.forEach(item => {
            try {
                // 获取文档链接元素
                const linkElement = item.querySelector('a[href*="/document/"]');
                if (!linkElement) {
                    console.log('结果项中没有找到文档链接');
                    return;
                }
                
                // 从链接中提取文档ID
                const href = linkElement.getAttribute('href');
                const docRegex = /\/document\/(\d+)/;
                const match = href.match(docRegex);
                
                if (match && match[1]) {
                    const resultDocId = match[1];
                    
                    // 检查文档是否已浏览 - 只检查当前搜索查询的浏览记录
                    if (visitedDocs.includes(resultDocId)) {
                        // 标记为已浏览
                        item.classList.add('visited');
                        console.log(`标记文档 ${resultDocId} 为已浏览`);
                        markedCount++;
                    }
                }
            } catch (itemError) {
                console.error('处理单个结果项时出错:', itemError);
            }
        });
        
        // 如果从文档页面返回，清除标记
        if (isBackFromDocument) {
            sessionStorage.removeItem('docradar_back_to_search');
            console.log('已清除从文档返回的会话标记');
        }
        
        console.log(`==== 标记完成，共标记 ${markedCount} 个已浏览文档 ====`);
    } catch (error) {
        console.error('标记已浏览文档时发生错误:', error);
    }
} 

/**
 * 清除特定搜索查询的已浏览文档记录
 * @param {string} searchQuery - 要清除记录的搜索查询
 */
function clearCurrentQueryVisitedDocs(searchQuery) {
    if (!searchQuery) return;
    
    try {
        console.log(`清除搜索"${searchQuery}"的浏览记录`);
        
        // 尝试获取并更新映射表
        const visitedDocsMapStr = localStorage.getItem('docradar_visited_docs_map');
        if (visitedDocsMapStr) {
            try {
                const visitedDocsMap = JSON.parse(visitedDocsMapStr);
                
                // 如果存在该查询的记录，删除它
                if (visitedDocsMap[searchQuery]) {
                    delete visitedDocsMap[searchQuery];
                    localStorage.setItem('docradar_visited_docs_map', JSON.stringify(visitedDocsMap));
                    console.log(`已清除搜索"${searchQuery}"的浏览记录`);
                } else {
                    console.log(`搜索"${searchQuery}"没有浏览记录，无需清除`);
                }
            } catch (e) {
                console.error('解析已浏览文档映射表失败:', e);
            }
        } else {
            console.log('没有找到浏览记录映射表');
        }
    } catch (error) {
        console.error('清除浏览记录时发生错误:', error);
    }
}