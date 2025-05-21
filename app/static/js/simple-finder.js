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
        
        // 搜索框输入事件
        this.searchInput.addEventListener('input', () => {
            const query = this.searchInput.value.trim();
            if (query) {
                this.search(query);
            } else {
                this.clearHighlights();
            }
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
    }
    
    /**
     * 执行搜索
     * @param {string} query - 搜索关键词
     */
    search(query) {
        // 保存查询
        this.searchQuery = query;
        
        // 清除先前的高亮
        this.clearHighlights();
        
        // 查找匹配项
        this.findMatches(query);
        
        // 更新UI
        this.updateMatchesInfo();
        
        // 如果有匹配项，导航到第一个
        if (this.totalMatches > 0) {
            this.navigateToMatch(0);
        }
    }
    
    /**
     * 清除高亮
     */
    clearHighlights() {
        // 移除当前所有高亮元素
        const marks = document.querySelectorAll('.document-content mark');
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
        if (!contentElement) return;
        
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
                    return NodeFilter.FILTER_ACCEPT;
                }
            }
        );
        
        // 正则表达式用于查找
        const escapeRegExp = (string) => 
            string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(escapeRegExp(query), 'gi');
        
        // 遍历文本节点
        let currentNode;
        while (currentNode = treeWalker.nextNode()) {
            const text = currentNode.nodeValue;
            
            // 重置正则表达式的lastIndex
            regex.lastIndex = 0;
            
            if (regex.test(text)) {
                // 如果找到匹配，重置lastIndex再次使用
                regex.lastIndex = 0;
                
                // 创建文档片段存储高亮后的内容
                const fragment = document.createDocumentFragment();
                let lastIndex = 0;
                let match;
                
                // 查找所有匹配并高亮
                while ((match = regex.exec(text)) !== null) {
                    // 添加匹配前的文本
                    if (match.index > lastIndex) {
                        fragment.appendChild(document.createTextNode(
                            text.substring(lastIndex, match.index)
                        ));
                    }
                    
                    // 创建高亮元素
                    const mark = document.createElement('mark');
                    mark.setAttribute('data-match-index', this.matches.length);
                    mark.textContent = match[0];
                    
                    // 添加到片段
                    fragment.appendChild(mark);
                    
                    // 更新索引
                    lastIndex = regex.lastIndex;
                    
                    // 存储匹配引用
                    this.matches.push(mark);
                }
                
                // 添加匹配后的剩余文本
                if (lastIndex < text.length) {
                    fragment.appendChild(document.createTextNode(
                        text.substring(lastIndex)
                    ));
                }
                
                // 用高亮后的内容替换原始节点
                currentNode.parentNode.replaceChild(fragment, currentNode);
            }
        }
        
        // 更新匹配总数
        this.totalMatches = this.matches.length;
    }
    
    /**
     * 更新匹配信息显示
     */
    updateMatchesInfo() {
        if (this.matchInfo) {
            if (this.totalMatches > 0) {
                this.matchInfo.textContent = `${this.currentIndex + 1}/${this.totalMatches}`;
            } else {
                this.matchInfo.textContent = '0/0';
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
        if (index < 0 || index >= this.totalMatches) return;
        
        // 移除当前高亮
        document.querySelectorAll(`.${this.activeClass}`).forEach(el => {
            el.classList.remove(this.activeClass);
            el.classList.remove('blink');
        });
        
        // 设置新高亮
        const match = this.matches[index];
        match.classList.add(this.activeClass);
        match.classList.add('blink');
        
        // 更新当前索引
        this.currentIndex = index;
        this.updateMatchesInfo();
        
        // 滚动到视图
        match.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
        
        // 一段时间后移除闪烁效果
        setTimeout(() => {
            if (match) match.classList.remove('blink');
        }, 2000);
    }
    
    /**
     * 初始化搜索
     * @param {string} initialQuery - 初始搜索关键词
     */
    initialize(initialQuery) {
        if (initialQuery && this.searchInput) {
            this.searchInput.value = initialQuery;
            // 稍微延迟以确保DOM完全加载
            setTimeout(() => {
                this.search(initialQuery);
            }, 300);
        }
    }
    
    /**
     * 关闭搜索
     */
    close() {
        if (this.searchBox) {
            this.searchBox.style.display = 'none';
        }
        this.clearHighlights();
    }
}

// 当文档加载完成时初始化
document.addEventListener('DOMContentLoaded', function() {
    // 获取URL中的查询参数
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');
    
    if (query) {
        // 创建并初始化搜索
        window.finder = new SimpleFinder();
        window.finder.initialize(query);
    }
}); 