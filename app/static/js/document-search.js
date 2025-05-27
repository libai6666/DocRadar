/**
 * 文档内容搜索与高亮
 * 使用mark.js库实现高效的文本搜索和高亮
 */
document.addEventListener('DOMContentLoaded', function() {
    // 初始化变量
    let currentIndex = 0;
    let totalMatches = 0;
    let markInstance = null;
    
    // 获取DOM元素
    const searchInput = document.getElementById('search-input');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const closeBtn = document.getElementById('close-search');
    const matchInfo = document.getElementById('match-info');
    const contentElement = document.querySelector('.document-content');
    
    // 创建mark.js实例
    if (contentElement) {
        console.log('创建mark.js实例');
        // 使用更高级的配置初始化mark.js
        markInstance = new Mark(contentElement, {
            "element": "mark",
            "className": "mark-highlight",
            "exclude": [
                "script", 
                "style", 
                "iframe", 
                "canvas", 
                ".browser-search", 
                ".search-navigator"
            ],
            "iframes": false,
            "acrossElements": true,
            "debug": true
        });
        console.log('mark.js实例创建完成');
    } else {
        console.error('找不到文档内容元素');
    }
    
    /**
     * 检测当前文档页面的来源
     * @returns {Object} 包含来源信息的对象
     */
    function detectDocumentSource() {
        // 获取URL参数
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('q');
        const searchId = urlParams.get('search_id');
        
        // 如果URL中有查询参数和搜索ID，说明是从搜索结果页来的
        const isFromSearchResults = !!(query && searchId);
        
        console.log(`检测文档来源: 是否来自搜索结果页=${isFromSearchResults}, 查询参数="${query}", 搜索ID=${searchId}`);
        
        return {
            isFromSearchResults,
            query,
            searchId
        };
    }
    
    // 添加新函数：保存当前搜索状态
    function saveCurrentSearchState() {
        // 先检测文档来源
        const source = detectDocumentSource();
        
        // 只有当文档来自搜索结果页时，才保存搜索状态
        if (source.isFromSearchResults) {
            console.log(`保存当前搜索状态: query="${source.query}", searchId=${source.searchId}`);
            localStorage.setItem('docradar_current_active_query', source.query);
            localStorage.setItem('docradar_current_active_search_id', source.searchId);
        } else {
            console.log('文档不是来自搜索结果页，不保存搜索状态');
        }
    }
    
    // 添加页面刷新前的事件监听器
    window.addEventListener('beforeunload', function() {
        saveCurrentSearchState();
    });
    
    // 初始化搜索
    function initSearch() {
        // 检测文档来源
        const source = detectDocumentSource();
        
        console.log(`初始化搜索，来源检测结果: 是否来自搜索结果页=${source.isFromSearchResults}, 查询参数="${source.query}", 搜索ID="${source.searchId}"`);
        
        // 生成唯一的存储键，确保不同搜索标签之间不会相互干扰
        const storageKeyPrefix = 'docradar_search_';
        
        // 如果直接从文档列表访问，清除之前的搜索状态
        if (!source.isFromSearchResults) {
            console.log('当前文档不是从搜索结果页访问的，清除所有搜索存储');
            clearAllSearchStorage(true); // 传入参数true，表示清除localStorage中的状态
            return; // 直接返回，不执行搜索
        }
        
        // 如果URL中有查询参数和搜索ID，则使用它们
        if (source.query && source.searchId) {
            // 清除所有旧的搜索存储，防止干扰
            clearAllSearchStorage(false); // 只清除sessionStorage中的状态
            
            // 存储当前的搜索ID和查询词
            const storageKey = `${storageKeyPrefix}${source.searchId}`;
            sessionStorage.setItem(storageKey, source.query);
            
            // 同时存储当前活动的搜索ID，用于标记当前正在使用哪个搜索
            sessionStorage.setItem('docradar_active_search_id', source.searchId);
            
            console.log(`已存储搜索参数: searchId=${source.searchId}, query=${source.query}, storageKey=${storageKey}`);
            
            // 设置搜索框的值
            if (searchInput) {
                searchInput.value = source.query;
                console.log(`设置搜索框值为: "${source.query}"`);
            }
            
            // 稍微延迟执行搜索，确保DOM完全加载
            setTimeout(() => {
                console.log(`开始执行搜索: "${source.query}"`);
                performSearch(source.query);
            }, 500); // 500ms延迟
        } else {
            // 检测页面是否是刷新
            const pageLoadFlag = sessionStorage.getItem('docradar_page_loaded');
            const isRefresh = !!pageLoadFlag;
            console.log(`检测到页面加载类型: isRefresh=${isRefresh}`);
            
            // 如果是刷新，尝试从localStorage中恢复当前活动的搜索
            if (isRefresh) {
                const currentActiveQuery = localStorage.getItem('docradar_current_active_query');
                const currentActiveSearchId = localStorage.getItem('docradar_current_active_search_id');
                
                if (currentActiveQuery && currentActiveSearchId) {
                    console.log(`从本地存储中恢复当前活动的搜索: query="${currentActiveQuery}", searchId=${currentActiveSearchId}`);
                    
                    // 更新URL，但不刷新页面
                    const newUrl = new URL(window.location.href);
                    newUrl.searchParams.set('q', currentActiveQuery);
                    newUrl.searchParams.set('search_id', currentActiveSearchId);
                    window.history.replaceState({}, '', newUrl);
                    
                    // 使用存储的查询词
                    if (searchInput) {
                        searchInput.value = currentActiveQuery;
                    }
                    
                    // 同时更新sessionStorage
                    const storageKey = `${storageKeyPrefix}${currentActiveSearchId}`;
                    sessionStorage.setItem(storageKey, currentActiveQuery);
                    sessionStorage.setItem('docradar_active_search_id', currentActiveSearchId);
                    
                    // 延迟执行搜索
                    setTimeout(() => {
                        console.log(`使用当前活动的搜索词执行搜索: "${currentActiveQuery}"`);
                        performSearch(currentActiveQuery);
                    }, 500);
                    
                    return; // 已处理，退出函数
                } else {
                    console.log('未找到当前活动的搜索状态');
                }
            }
            
            // 如果不是刷新或没有找到当前活动的搜索状态，尝试从会话存储中获取最后一次活动的搜索
            const activeSearchId = sessionStorage.getItem('docradar_active_search_id');
            
            if (activeSearchId) {
                const storageKey = `${storageKeyPrefix}${activeSearchId}`;
                const storedQuery = sessionStorage.getItem(storageKey);
                
                if (storedQuery) {
                    console.log(`从会话存储中恢复搜索参数: searchId=${activeSearchId}, query=${storedQuery}`);
                    
                    // 更新URL，但不刷新页面
                    const newUrl = new URL(window.location.href);
                    newUrl.searchParams.set('q', storedQuery);
                    newUrl.searchParams.set('search_id', activeSearchId);
                    window.history.replaceState({}, '', newUrl);
                    
                    // 使用存储的查询词
                    if (searchInput) {
                        searchInput.value = storedQuery;
                    }
                    
                    // 延迟执行搜索
                    setTimeout(() => {
                        console.log(`使用存储的查询词执行搜索: "${storedQuery}"`);
                        performSearch(storedQuery);
                    }, 500);
                    
                    return; // 已处理，退出函数
                }
            }
            
            console.log('没有查询参数或搜索框不存在');
        }
    }
    
    // 清除所有搜索相关的会话存储
    function clearAllSearchStorage(clearLocalStorage = false) {
        // 获取所有以docradar_search_开头的键
        const keysToRemove = [];
        for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            if (key && key.startsWith('docradar_search_')) {
                keysToRemove.push(key);
            }
        }
        
        // 删除所有匹配的键
        keysToRemove.forEach(key => {
            sessionStorage.removeItem(key);
            console.log(`已删除会话存储项: ${key}`);
        });
        
        // 同时删除活动搜索ID
        sessionStorage.removeItem('docradar_active_search_id');
        
        // 如果需要，清除localStorage中的搜索状态
        if (clearLocalStorage) {
            localStorage.removeItem('docradar_current_active_query');
            localStorage.removeItem('docradar_current_active_search_id');
            console.log('已清除本地存储中的搜索状态');
        }
        
        console.log('已清除所有搜索相关的会话存储');
    }
    
    // 执行搜索
    function performSearch(query) {
        if (!query || !markInstance) return;
        
        // 重置计数器
        totalMatches = 0;
        currentIndex = 0;
        
        console.log(`执行搜索: "${query}"`);
        
        // 清除之前的高亮
        markInstance.unmark({
            done: function() {
                console.log('已清除之前的高亮');
                
                // 执行新的高亮，使用更适合中文的配置
                markInstance.mark(query, {
                    separateWordSearch: false,
                    accuracy: "partially", // 改为partially，更适合中文搜索
                    diacritics: true,
                    caseSensitive: false,
                    acrossElements: true,
                    each: function(element) {
                        // 为每个匹配项添加索引
                        element.setAttribute('data-match-index', totalMatches);
                        totalMatches++;
                    },
                    done: function(totalMarks) {
                        console.log(`第一次高亮完成，找到 ${totalMarks} 个匹配项`);
                        
                        // 如果没有找到匹配项，尝试使用更宽松的配置
                        if (totalMarks === 0) {
                            console.log('尝试使用更宽松的配置再次搜索...');
                            
                            // 使用更宽松的配置再次搜索
                            markInstance.mark(query, {
                                separateWordSearch: true, // 允许分词搜索
                                accuracy: "complementary", // 最宽松的匹配模式
                                wildcards: 'enabled', // 启用通配符
                                diacritics: true,
                                caseSensitive: false,
                                acrossElements: true,
                                each: function(element) {
                                    // 为每个匹配项添加索引
                                    element.setAttribute('data-match-index', totalMatches);
                                    totalMatches++;
                                },
                                done: function(fallbackTotalMarks) {
                                    console.log(`备用高亮完成，找到 ${fallbackTotalMarks} 个匹配项`);
                                    
                                    // 更新匹配信息
                                    updateMatchInfo();
                                    
                                    // 如果有匹配项，导航到第一个
                                    if (fallbackTotalMarks > 0) {
                                        navigateToMatch(0);
                                    }
                                }
                            });
                        }
                        // 更新匹配信息
                        updateMatchInfo();
                        
                        // 如果有匹配项，导航到第一个
                        if (totalMarks > 0) {
                            navigateToMatch(0);
                        }
                    }
                });
            }
        });
    }
    
    // 更新匹配信息
    function updateMatchInfo() {
        if (matchInfo) {
            if (totalMatches > 0) {
                matchInfo.textContent = `${currentIndex + 1}/${totalMatches}`;
                matchInfo.classList.remove('text-danger');
                matchInfo.classList.add('text-success');
            } else {
                matchInfo.textContent = '未找到匹配项';
                matchInfo.classList.remove('text-success');
                matchInfo.classList.add('text-danger');
            }
        }
    }
    
    // 导航到指定匹配项
    function navigateToMatch(index) {
        if (index < 0 || index >= totalMatches) return;
        
        console.log(`导航到匹配项 ${index + 1}/${totalMatches}`);
        
        // 移除当前高亮的活动状态
        document.querySelectorAll('mark.current-match').forEach(el => {
            el.classList.remove('current-match');
            el.classList.remove('blink');
        });
        
        // 设置新高亮
        const mark = document.querySelector(`mark[data-match-index="${index}"]`);
        if (mark) {
            mark.classList.add('current-match');
            mark.classList.add('blink');
            
            // 更新当前索引
            currentIndex = index;
            updateMatchInfo();
            
            // 滚动到视图
            mark.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
            
            // 一段时间后移除闪烁效果
            setTimeout(() => {
                mark.classList.remove('blink');
            }, 2000);
        }
    }
    
    // 上一个匹配
    function prevMatch() {
        if (totalMatches === 0) return;
        
        currentIndex = (currentIndex - 1 + totalMatches) % totalMatches;
        navigateToMatch(currentIndex);
    }
    
    // 下一个匹配
    function nextMatch() {
        if (totalMatches === 0) return;
        
        currentIndex = (currentIndex + 1) % totalMatches;
        navigateToMatch(currentIndex);
    }
    
    // 关闭搜索
    function closeSearch() {
        if (markInstance) {
            markInstance.unmark();
        }
        
        if (searchInput) {
            searchInput.value = '';
        }
        
        // 清除会话存储和本地存储中的搜索状态
        clearAllSearchStorage(true);
        
        // 更新URL，移除搜索参数
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('q');
        newUrl.searchParams.delete('search_id');
        window.history.replaceState({}, '', newUrl);
        
        totalMatches = 0;
        currentIndex = 0;
        
        if (matchInfo) {
            matchInfo.textContent = '0/0';
            matchInfo.classList.remove('text-success', 'text-danger');
        }
    }
    
    // 绑定事件
    if (searchInput) {
        // 搜索框输入事件 (使用防抖动)
        let debounceTimer;
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const query = searchInput.value.trim();
                
                if (query) {
                    performSearch(query);
                } else {
                    closeSearch();
                }
            }, 300); // 300ms延迟
        });
        
        // 键盘事件
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (e.shiftKey) {
                    prevMatch();
                } else {
                    nextMatch();
                }
            } else if (e.key === 'Escape') {
                closeSearch();
            }
        });
    }
    
    // 上一个匹配按钮
    if (prevBtn) {
        prevBtn.addEventListener('click', prevMatch);
    }
    
    // 下一个匹配按钮
    if (nextBtn) {
        nextBtn.addEventListener('click', nextMatch);
    }
    
    // 关闭搜索按钮
    if (closeBtn) {
        closeBtn.addEventListener('click', closeSearch);
    }
    
    // 点击高亮文本导航到该匹配项
    document.addEventListener('click', (e) => {
        if (e.target.tagName.toLowerCase() === 'mark') {
            const index = parseInt(e.target.getAttribute('data-match-index'), 10);
            if (!isNaN(index) && index >= 0 && index < totalMatches) {
                navigateToMatch(index);
            }
        }
    });
    
    // 添加全局键盘事件监听器
    document.addEventListener('keydown', function(e) {
        // 检测Ctrl+F
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault(); // 阻止浏览器默认的查找行为
            
            // 聚焦到搜索框
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
    });
    
    // 初始化搜索
    initSearch();

    /**
     * 保存文档的原始文件名到本地存储
     * @param {string} docId - 文档ID
     * @param {string} originalFilename - 原始文件名
     */
    function saveDocumentOriginalFilename(docId, originalFilename) {
        if (!docId || !originalFilename) return;
        
        try {
            // 获取现有的映射表
            let filenameMap = {};
            const storedMap = localStorage.getItem('docradar_original_filenames');
            if (storedMap) {
                filenameMap = JSON.parse(storedMap);
            }
            
            // 添加或更新映射
            filenameMap[docId] = originalFilename;
            
            // 保存回本地存储
            localStorage.setItem('docradar_original_filenames', JSON.stringify(filenameMap));
            console.log(`已保存文档ID ${docId} 的原始文件名: ${originalFilename}`);
        } catch (error) {
            console.error('保存文档原始文件名时出错:', error);
        }
    }

    /**
     * 从本地存储中获取文档的原始文件名
     * @param {string} docId - 文档ID
     * @returns {string|null} 原始文件名，如果不存在则返回null
     */
    function getDocumentOriginalFilename(docId) {
        if (!docId) return null;
        
        try {
            const storedMap = localStorage.getItem('docradar_original_filenames');
            if (storedMap) {
                const filenameMap = JSON.parse(storedMap);
                return filenameMap[docId] || null;
            }
        } catch (error) {
            console.error('获取文档原始文件名时出错:', error);
        }
        
        return null;
    }

    /**
     * 拦截文档链接点击，确保包含原始文件名参数
     */
    document.body.addEventListener('click', function(e) {
        // 检查是否点击了文档链接
        let target = e.target;
        while (target && target !== document.body) {
            if (target.tagName === 'A' && target.href && target.href.includes('/document/')) {
                // 从链接中提取文档ID
                const docRegex = /\/document\/(\d+)/;
                const match = target.href.match(docRegex);
                
                if (match && match[1]) {
                    const docId = match[1];
                    
                    // 检查链接是否已包含原始文件名参数
                    const url = new URL(target.href);
                    if (!url.searchParams.has('original_filename')) {
                        // 尝试从localStorage获取原始文件名
                        const originalFilename = getDocumentOriginalFilename(docId);
                        if (originalFilename) {
                            // 添加原始文件名参数
                            url.searchParams.set('original_filename', originalFilename);
                            target.href = url.toString();
                            console.log(`已为文档链接添加原始文件名参数: ${originalFilename}`);
                        }
                    }
                }
                break;
            }
            target = target.parentElement;
        }
    }, true);
}); 