/**
 * 简单文档查找器
 * 模拟浏览器的Ctrl+F查找功能
 */
class SimpleFinder {
    constructor() {
        this.matches = [];
        this.currentIndex = 0;
        this.totalMatches = 0;
        this.activeClass = 'current-match';
        this.searchQuery = '';
        this.highlightAll = true; // 默认高亮所有匹配项
        this.initialized = false; // 标记是否已初始化
        this.autoCleanInput = false; // 修改为false，不自动清空搜索框
        this.debug = true; // 开启调试模式
        
        // 界面元素
        this.searchInput = document.getElementById('search-input');
        this.prevBtn = document.getElementById('prev-btn');
        this.nextBtn = document.getElementById('next-btn');
        this.closeBtn = document.getElementById('close-search');
        this.matchInfo = document.getElementById('match-info');
        this.searchBox = document.getElementById('browser-search');
        
        // 绑定事件
        this.bindEvents();
    }
    
    /**
     * 绑定事件处理程序
     */
    bindEvents() {
        if (!this.searchInput) return;
        
        // 搜索框输入事件 (使用防抖动)
        let debounceTimer;
        this.searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const query = this.searchInput.value.trim();
                if (query) {
                    this.search(query);
                } else {
                    this.clearHighlights();
                }
            }, 300); // 300ms延迟
        });
        
        // 上一个匹配
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', () => this.prev());
        }
        
        // 下一个匹配
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => this.next());
        }
        
        // 关闭搜索
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.close());
        }
        
        // 键盘事件
        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (e.shiftKey) {
                    this.prev();
                } else {
                    this.next();
                }
            } else if (e.key === 'Escape') {
                this.close();
            }
        });
        
        // 点击高亮文本导航到该匹配项
        document.addEventListener('click', (e) => {
            if (e.target.tagName.toLowerCase() === 'mark') {
                const index = parseInt(e.target.getAttribute('data-match-index'), 10);
                if (!isNaN(index) && index >= 0 && index < this.totalMatches) {
                    this.navigateToMatch(index);
                }
            }
        });
    }
    
    /**
     * 在搜索前预处理文档内容
     * 移除后端生成的高亮，但保留其内容
     */
    preProcessContent() {
        if (this.debug) console.log('预处理文档内容，移除后端生成的高亮');
        const contentElement = document.querySelector('.document-content');
        if (!contentElement) return;
        
        // 查找所有没有data-match-index属性的mark标签（后端生成的）
        const backendMarks = contentElement.querySelectorAll('mark:not([data-match-index])');
        if (backendMarks.length > 0) {
            if (this.debug) console.log(`找到 ${backendMarks.length} 个后端生成的高亮标签`);
            
            backendMarks.forEach(mark => {
                // 创建文本节点替换mark标签
                const textNode = document.createTextNode(mark.textContent);
                mark.parentNode.replaceChild(textNode, mark);
            });
            
            // 合并相邻的文本节点
            contentElement.normalize();
            if (this.debug) console.log('已移除后端生成的高亮标签');
        }
    }
    
    /**
     * 执行搜索
     * @param {string} query - 搜索关键词
     */
    search(query) {
        if (!query || query.trim() === '') {
            if (this.debug) console.log('搜索关键词为空，取消搜索');
            this.clearHighlights();
            return;
        }
        
        // 保存查询
        this.searchQuery = query;
        if (this.debug) console.log(`执行搜索: "${query}"`);
        
        // 清除先前的高亮
        this.clearHighlights();
        
        // 在首次搜索时预处理内容
        if (!this.initialized) {
            this.preProcessContent();
            this.initialized = true;
        }
        
        // 查找匹配项
        this.findMatches(query);
        
        // 更新UI
        this.updateMatchesInfo();
        
        // 如果有匹配项，导航到第一个
        if (this.totalMatches > 0) {
            if (this.debug) console.log(`搜索完成，找到 ${this.totalMatches} 个匹配项`);
            this.navigateToMatch(0);
            
            // 搜索完成后，根据autoCleanInput设置决定是否清空搜索框
            if (this.autoCleanInput && this.searchInput) {
                // 保存当前查询用于显示
                const currentQuery = this.searchQuery;
                
                // 清空搜索框
                this.searchInput.value = '';
                
                if (this.debug) console.log(`搜索框已清空，但保留了查询引用: "${currentQuery}"`);
            } else {
                // 不清空搜索框，保留搜索词以便继续搜索
                if (this.debug) console.log(`保留搜索框内容: "${query}"`);
            }
        } else {
            if (this.debug) console.log(`搜索完成，未找到匹配项`);
            // 可以在这里添加一个提示，告诉用户没有找到匹配项
            if (this.matchInfo) {
                this.matchInfo.textContent = '未找到匹配项';
                this.matchInfo.classList.add('text-danger');
            }
            
            // 未找到匹配项时，根据autoCleanInput设置决定是否清空搜索框
            if (this.autoCleanInput && this.searchInput) {
                this.searchInput.value = '';
            } else {
                // 不清空搜索框，保留搜索词以便修改后再次搜索
                if (this.debug) console.log(`未找到匹配项，但保留搜索框内容: "${query}"`);
            }
        }
    }
    
    /**
     * 清除高亮
     */
    clearHighlights() {
        // 移除当前所有由JavaScript添加的高亮元素
        const marks = document.querySelectorAll('.document-content mark[data-match-index]');
        marks.forEach(mark => {
            const parent = mark.parentNode;
            if (parent) {
                // 保留文本内容
                parent.replaceChild(document.createTextNode(mark.textContent), mark);
                // 合并相邻的文本节点
                parent.normalize();
            }
        });
        
        this.matches = [];
        this.currentIndex = 0;
        this.totalMatches = 0;
        this.updateMatchesInfo();
    }
    
    /**
     * 查找匹配项并高亮
     * @param {string} query - 搜索关键词
     */
    findMatches(query) {
        if (!query) return;
        
        const contentElement = document.querySelector('.document-content');
        if (!contentElement) {
            console.error('找不到文档内容元素');
            return;
        }
        
        if (this.debug) console.log(`开始查找匹配项: "${query}"`);
        
        // 分割查询词，处理多个关键字
        const queryTerms = this.getQueryTerms(query);
        if (this.debug) console.log(`查询词分割为: [${queryTerms.join(', ')}]`);
        
        // 创建树行者以遍历DOM树
        const treeWalker = document.createTreeWalker(
            contentElement,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: function(node) {
                    // 过滤<script>和<style>内容
                    if (node.parentNode.nodeName.toLowerCase() === 'script' || 
                        node.parentNode.nodeName.toLowerCase() === 'style') {
                        return NodeFilter.FILTER_REJECT;
                    }
                    // 过滤空文本节点或只有空白的节点
                    if (node.textContent.trim() === '') {
                        return NodeFilter.FILTER_REJECT;
                    }
                    return NodeFilter.FILTER_ACCEPT;
                }
            }
        );
        
        // 遍历文本节点
        let currentNode;
        let nodeCount = 0;
        let matchCount = 0;
        
        // 存储所有匹配项信息，用于调试
        const allMatches = [];
        
        // 创建一个Map来跟踪已处理的节点，避免重复处理
        const processedNodes = new Map();
        
        while (currentNode = treeWalker.nextNode()) {
            // 跳过已处理的节点
            if (processedNodes.has(currentNode)) {
                continue;
            }
            
            nodeCount++;
            const text = currentNode.nodeValue;
            
            // 记录节点信息用于调试
            if (this.debug) {
                console.log(`处理文本节点 #${nodeCount}: "${text.substring(0, 50)}${text.length > 50 ? '...' : ''}"`);
            }
            
            // 对每个查询词进行搜索
            let hasMatch = false;
            let fragments = null;
            
            for (const term of queryTerms) {
                if (!term.trim()) continue;
                
                // 创建正则表达式，支持中文和其他语言，使用g标志找到所有匹配项
                const regex = new RegExp(this.escapeRegExp(term), 'gi');
                
                // 重置正则表达式的lastIndex
                regex.lastIndex = 0;
                
                // 检查是否有匹配
                const matches = [];
                let match;
                
                // 使用exec方法找到所有匹配项
                while ((match = regex.exec(text)) !== null) {
                    matches.push({
                        start: match.index,
                        end: regex.lastIndex,
                        term: term,
                        text: match[0]
                    });
                    
                    if (this.debug) {
                        console.log(`在节点 #${nodeCount} 中找到匹配: "${match[0]}" 位置: ${match.index}-${regex.lastIndex}`);
                    }
                }
                
                // 如果找到匹配项
                if (matches.length > 0) {
                    // 如果还没有创建文档片段，创建一个
                    if (!fragments) {
                        fragments = document.createDocumentFragment();
                        
                        // 按位置排序匹配项
                        matches.sort((a, b) => a.start - b.start);
                        
                        // 处理所有匹配项
                        let currentPos = 0;
                        
                        // 创建文档片段存储高亮后的内容
                        const processText = (startPos, endPos, isMatch, matchTerm, matchText) => {
                            if (startPos < endPos) {
                                if (isMatch) {
                                    const mark = document.createElement('mark');
                                    mark.setAttribute('data-match-index', matchCount);
                                    mark.setAttribute('data-query-term', matchTerm);
                                    mark.textContent = text.substring(startPos, endPos);
                                    fragments.appendChild(mark);
                                    this.matches.push(mark);
                                    
                                    // 记录匹配信息用于调试
                                    allMatches.push({
                                        index: matchCount,
                                        term: matchTerm,
                                        text: text.substring(startPos, endPos),
                                        node: nodeCount,
                                        position: `${startPos}-${endPos}`
                                    });
                                    
                                    if (this.debug) {
                                        console.log(`创建匹配项 #${matchCount}: "${text.substring(startPos, endPos)}" 位置: ${startPos}-${endPos}`);
                                    }
                                    
                                    matchCount++;
                                } else {
                                    fragments.appendChild(document.createTextNode(
                                        text.substring(startPos, endPos)
                                    ));
                                }
                            }
                        };
                        
                        // 处理所有匹配项
                        for (const match of matches) {
                            // 添加匹配前的文本
                            processText(currentPos, match.start, false);
                            
                            // 添加匹配的文本
                            processText(match.start, match.end, true, match.term, match.text);
                            
                            currentPos = match.end;
                            hasMatch = true;
                        }
                        
                        // 添加最后一部分文本
                        processText(currentPos, text.length, false);
                    }
                }
            }
            
            // 如果有匹配，替换原始节点
            if (hasMatch && fragments) {
                currentNode.parentNode.replaceChild(fragments, currentNode);
                // 标记节点已处理
                processedNodes.set(currentNode, true);
            }
        }
        
        // 更新匹配总数
        this.totalMatches = this.matches.length;
        if (this.debug) {
            console.log(`处理了 ${nodeCount} 个文本节点，找到 ${this.totalMatches} 个匹配项`);
            if (this.totalMatches > 0) {
                console.log('匹配项详情:', allMatches);
            }
        }
    }
    
    /**
     * 将查询字符串分割为多个搜索词
     * @param {string} query - 原始查询字符串
     * @returns {Array} - 搜索词数组
     */
    getQueryTerms(query) {
        // 如果查询包含引号，则视为精确短语
        if (query.includes('"')) {
            const terms = [];
            const regex = /"([^"]*)"|(\S+)/g;
            let match;
            
            while ((match = regex.exec(query)) !== null) {
                const term = match[1] || match[2];
                if (term.trim()) {
                    terms.push(term.trim());
                }
            }
            
            return terms.length ? terms : [query];
        }
        
        // 对于所有查询，包括中文，保持完整查询
        return [query];
    }
    
    /**
     * 转义正则表达式特殊字符
     * @param {string} string - 要转义的字符串
     * @returns {string} - 转义后的字符串
     */
    escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    /**
     * 更新匹配信息显示
     */
    updateMatchesInfo() {
        if (this.matchInfo) {
            if (this.totalMatches > 0) {
                // 显示当前匹配位置和总匹配数
                this.matchInfo.textContent = `${this.currentIndex + 1}/${this.totalMatches}`;
                this.matchInfo.classList.remove('text-danger');
                this.matchInfo.classList.add('text-success');
            } else {
                // 显示未找到匹配项的信息
                if (this.searchQuery && this.searchQuery.trim() !== '') {
                    this.matchInfo.textContent = '未找到匹配项';
                    this.matchInfo.classList.remove('text-success');
                    this.matchInfo.classList.add('text-danger');
                } else {
                    this.matchInfo.textContent = '0/0';
                    this.matchInfo.classList.remove('text-success', 'text-danger');
                }
            }
        }
    }
    
    /**
     * 导航到上一个匹配
     */
    prev() {
        if (this.totalMatches === 0) return;
        
        this.currentIndex = (this.currentIndex - 1 + this.totalMatches) % this.totalMatches;
        this.navigateToMatch(this.currentIndex);
    }
    
    /**
     * 导航到下一个匹配
     */
    next() {
        if (this.totalMatches === 0) return;
        
        this.currentIndex = (this.currentIndex + 1) % this.totalMatches;
        this.navigateToMatch(this.currentIndex);
    }
    
    /**
     * 导航到指定匹配项
     * @param {number} index - 匹配项索引
     */
    navigateToMatch(index) {
        if (index < 0 || index >= this.totalMatches) {
            console.error(`无效的匹配项索引: ${index}, 总匹配数: ${this.totalMatches}`);
            return;
        }
        
        if (this.debug) console.log(`导航到匹配项 ${index+1}/${this.totalMatches}`);
        
        // 移除当前高亮的活动状态
        document.querySelectorAll(`.${this.activeClass}`).forEach(el => {
            el.classList.remove(this.activeClass);
            el.classList.remove('blink');
            el.classList.remove('super-highlight');
        });
        
        // 设置新高亮
        const match = this.matches[index];
        if (!match) {
            console.error(`找不到索引为 ${index} 的匹配项`);
            return;
        }
        
        // 添加当前匹配的活动状态
        match.classList.add(this.activeClass);
        match.classList.add('blink');
        match.classList.add('super-highlight'); // 添加更明显的高亮效果
        
        // 更新当前索引
        this.currentIndex = index;
        this.updateMatchesInfo();
        
        // 滚动到视图
        try {
            if (this.debug) console.log(`滚动到匹配项 ${index+1}`);
            match.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        } catch (error) {
            console.error(`滚动到匹配项错误: ${error}`);
            // 尝试使用备用方法滚动
            try {
                const rect = match.getBoundingClientRect();
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                const targetTop = rect.top + scrollTop - (window.innerHeight / 2);
                window.scrollTo({
                    top: targetTop,
                    behavior: 'smooth'
                });
            } catch (backupError) {
                console.error(`备用滚动方法也失败: ${backupError}`);
            }
        }
        
        // 一段时间后移除闪烁效果
        setTimeout(() => {
            if (match) {
                match.classList.remove('blink');
                // 保持super-highlight效果，使当前匹配项更明显
            }
        }, 2000);
    }
    
    /**
     * 初始化搜索
     * @param {string} initialQuery - 初始搜索关键词
     */
    initialize(initialQuery) {
        if (initialQuery && this.searchInput) {
            if (this.debug) console.log(`初始化搜索: "${initialQuery}"`);
            
            // 确保搜索框显示搜索关键字
            this.searchInput.value = initialQuery;
            
            // 保存搜索查询
            this.searchQuery = initialQuery;
            
            try {
                // 稍微延迟以确保DOM完全加载
                setTimeout(() => {
                    // 临时禁用自动清空搜索框，确保初始化搜索时不会清空搜索框
                    const originalAutoCleanInput = this.autoCleanInput;
                    this.autoCleanInput = false;
                    
                    // 预处理内容
                    this.preProcessContent();
                    this.initialized = true;
                    
                    // 执行搜索
                    this.search(initialQuery);
                    
                    // 恢复原始设置
                    this.autoCleanInput = originalAutoCleanInput;
                    
                    // 确保有匹配项时滚动到第一个匹配
                    if (this.totalMatches > 0) {
                        if (this.debug) console.log(`找到 ${this.totalMatches} 个匹配项，正在滚动到第一个...`);
                        this.navigateToMatch(0);
                    } else {
                        if (this.debug) console.log(`未找到匹配项: "${initialQuery}"`);
                    }
                }, 500); // 增加延迟时间，确保DOM完全加载
            } catch (error) {
                console.error(`搜索初始化错误: ${error}`);
            }
        }
    }
    
    /**
     * 关闭搜索
     */
    close() {
        // 不再隐藏搜索框，只清除高亮和搜索内容
        this.clearHighlights();
        
        // 清空搜索框
        if (this.searchInput) {
            this.searchInput.value = '';
        }
        
        // 重置匹配信息
        if (this.matchInfo) {
            this.matchInfo.textContent = '0/0';
            this.matchInfo.classList.remove('text-success', 'text-danger');
        }
    }
}

// 当文档加载完成时初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('文档加载完成，初始化搜索功能');
    
    // 获取URL中的查询参数
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');
    
    console.log('URL查询参数:', query ? `"${query}"` : '无');
    
    // 创建搜索实例
    window.finder = new SimpleFinder();
    
    // 搜索框应该始终可见，无需隐藏
    const searchBox = document.getElementById('browser-search');
    if (searchBox) {
        console.log('找到搜索框元素');
    } else {
        console.error('找不到搜索框元素');
    }
    
    // 如果有查询参数，初始化搜索
    if (query) {
        console.log(`检测到搜索参数: "${query}", 正在初始化搜索...`);
        // 初始化搜索
        window.finder.initialize(query);
    }
    
    // 添加全局键盘事件监听器
    document.addEventListener('keydown', function(e) {
        // 检测Ctrl+F
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault(); // 阻止浏览器默认的查找行为
            
            // 聚焦到搜索框
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
    });
}); 