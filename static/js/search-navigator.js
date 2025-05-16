/**
 * 文档搜索导航器
 * 用于在文档中的搜索匹配项之间导航
 */
class SearchNavigator {
    constructor() {
        this.currentIndex = 0;
        this.totalMatches = 0;
        this.matches = [];
        this.query = '';
        this.isActive = false;
        
        // 导航控件
        this.container = null;
        this.counter = null;
        this.prevButton = null;
        this.nextButton = null;
        this.closeButton = null;
        
        // 高亮元素的特殊类名
        this.activeClass = 'current-match';
    }
    
    /**
     * 初始化导航器
     * @param {string} query - 搜索查询
     */
    init(query) {
        if (!query) return;
        
        this.query = query;
        console.log('SearchNavigator初始化，查询词:', query);
        
        // 如果没有预先高亮的匹配项，自己查找并高亮
        const hasExistingHighlights = document.querySelectorAll('.document-content mark').length > 0;
        if (!hasExistingHighlights) {
            console.log('没有找到预先高亮的匹配项，尝试自己高亮');
            this.highlightMatches();
        }
        
        this.findMatches();
        
        if (this.totalMatches > 0) {
            console.log(`找到 ${this.totalMatches} 个匹配项`);
            this.createNavigation();
            this.navigateToMatch(0);
            this.isActive = true;
        } else {
            console.log('未找到匹配项');
        }
    }
    
    /**
     * 在文档中查找并高亮显示匹配项
     */
    highlightMatches() {
        const contentElement = document.querySelector('.document-content');
        if (!contentElement) return;
        
        let content = contentElement.innerHTML;
        // 如果内容是HTML，需要解析和处理
        const isHtml = content.indexOf('<') >= 0 && content.indexOf('>') >= 0;
        
        if (isHtml) {
            // 创建临时元素保存内容
            const tempElement = document.createElement('div');
            tempElement.innerHTML = content;
            
            // 高亮处理文本节点
            this.highlightTextNodes(tempElement, this.query);
            
            // 替换原始内容
            contentElement.innerHTML = tempElement.innerHTML;
        } else {
            // 纯文本内容，直接替换
            const terms = this.query.split(/\s+/);
            let highlightedContent = content;
            
            terms.forEach(term => {
                if (term.length < 2) return;
                
                const regex = new RegExp(this.escapeRegExp(term), 'gi');
                highlightedContent = highlightedContent.replace(regex, match => 
                    `<mark>${match}</mark>`
                );
            });
            
            contentElement.innerHTML = highlightedContent;
        }
    }
    
    /**
     * 递归处理文本节点，高亮匹配内容
     */
    highlightTextNodes(element, query) {
        if (!element) return;
        
        const terms = query.split(/\s+/);
        const childNodes = [...element.childNodes];
        
        for (const node of childNodes) {
            if (node.nodeType === Node.TEXT_NODE) {
                let text = node.nodeValue;
                let hasMatch = false;
                
                for (const term of terms) {
                    if (term.length < 2) continue;
                    
                    const regex = new RegExp(this.escapeRegExp(term), 'gi');
                    if (regex.test(text)) {
                        hasMatch = true;
                        text = text.replace(regex, match => 
                            `<mark>${match}</mark>`
                        );
                    }
                }
                
                if (hasMatch) {
                    const tempSpan = document.createElement('span');
                    tempSpan.innerHTML = text;
                    element.replaceChild(tempSpan, node);
                    // 展开span，将其内容移到父元素中
                    while (tempSpan.firstChild) {
                        element.insertBefore(tempSpan.firstChild, tempSpan);
                    }
                    element.removeChild(tempSpan);
                }
            } else if (node.nodeType === Node.ELEMENT_NODE && 
                       !['script', 'style', 'mark'].includes(node.nodeName.toLowerCase())) {
                this.highlightTextNodes(node, query);
            }
        }
    }
    
    /**
     * 查找所有匹配项
     */
    findMatches() {
        // 获取所有mark元素（已高亮的匹配项）
        this.matches = Array.from(document.querySelectorAll('.document-content mark'));
        this.totalMatches = this.matches.length;
        
        console.log(`发现 ${this.totalMatches} 个已高亮的匹配项`);
        
        // 为每个匹配项添加ID以便定位
        this.matches.forEach((match, index) => {
            match.id = `match-${index}`;
            match.setAttribute('data-match-index', index);
        });
    }
    
    /**
     * 创建导航界面
     */
    createNavigation() {
        // 如果已存在则移除
        if (this.container) {
            this.container.remove();
        }
        
        // 创建导航容器
        this.container = document.createElement('div');
        this.container.className = 'search-navigator';
        this.container.innerHTML = `
            <div class="search-navigator-inner">
                <div class="search-query">
                    <i class="bi bi-search"></i>
                    <span class="query-text">${this.escapeHtml(this.query)}</span>
                </div>
                <div class="search-navigator-controls">
                    <button class="btn btn-sm btn-outline-secondary prev-match" title="上一个匹配">
                        <i class="bi bi-arrow-up"></i>
                    </button>
                    <span class="match-counter">1/${this.totalMatches}</span>
                    <button class="btn btn-sm btn-outline-secondary next-match" title="下一个匹配">
                        <i class="bi bi-arrow-down"></i>
                    </button>
                </div>
                <button class="btn btn-sm btn-outline-secondary close-navigator" title="关闭">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `;
        
        // 添加到文档
        const contentCard = document.querySelector('.card-body');
        if (contentCard) {
            contentCard.insertBefore(this.container, contentCard.firstChild);
        }
        
        // 获取导航元素
        this.counter = this.container.querySelector('.match-counter');
        this.prevButton = this.container.querySelector('.prev-match');
        this.nextButton = this.container.querySelector('.next-match');
        this.closeButton = this.container.querySelector('.close-navigator');
        
        // 添加事件监听器
        this.prevButton.addEventListener('click', () => this.previousMatch());
        this.nextButton.addEventListener('click', () => this.nextMatch());
        this.closeButton.addEventListener('click', () => this.close());
        
        // 添加键盘快捷键
        document.addEventListener('keydown', this.handleKeyPress.bind(this));
    }
    
    /**
     * 处理键盘快捷键
     * @param {Event} e - 键盘事件
     */
    handleKeyPress(e) {
        if (!this.isActive) return;
        
        // F3或Enter: 下一个匹配
        if (e.key === 'F3' || e.key === 'Enter') {
            e.preventDefault();
            this.nextMatch();
        }
        
        // Shift+F3或Shift+Enter: 上一个匹配
        if (e.key === 'F3' && e.shiftKey || e.key === 'Enter' && e.shiftKey) {
            e.preventDefault();
            this.previousMatch();
        }
        
        // Escape: 关闭导航
        if (e.key === 'Escape') {
            e.preventDefault();
            this.close();
        }
    }
    
    /**
     * 导航到上一个匹配项
     */
    previousMatch() {
        if (this.totalMatches === 0) return;
        
        this.currentIndex = (this.currentIndex - 1 + this.totalMatches) % this.totalMatches;
        this.navigateToMatch(this.currentIndex);
    }
    
    /**
     * 导航到下一个匹配项
     */
    nextMatch() {
        if (this.totalMatches === 0) return;
        
        this.currentIndex = (this.currentIndex + 1) % this.totalMatches;
        this.navigateToMatch(this.currentIndex);
    }
    
    /**
     * 导航到特定匹配项
     * @param {number} index - 匹配项索引
     */
    navigateToMatch(index) {
        if (index < 0 || index >= this.totalMatches) return;
        
        // 移除之前的当前匹配项标记
        const currentMatch = document.querySelector(`.${this.activeClass}`);
        if (currentMatch) {
            currentMatch.classList.remove(this.activeClass);
        }
        
        // 标记新的当前匹配项
        const match = this.matches[index];
        match.classList.add(this.activeClass);
        
        // 更新计数器
        this.counter.textContent = `${index + 1}/${this.totalMatches}`;
        
        // 滚动到视图中
        match.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
    }
    
    /**
     * 关闭导航器
     */
    close() {
        if (this.container) {
            this.container.remove();
        }
        
        // 移除所有当前匹配项标记
        document.querySelectorAll(`.${this.activeClass}`).forEach(el => {
            el.classList.remove(this.activeClass);
        });
        
        // 移除键盘事件监听器
        document.removeEventListener('keydown', this.handleKeyPress);
        
        this.isActive = false;
    }
    
    /**
     * HTML转义
     * @param {string} html - 需要转义的HTML
     * @returns {string} 转义后的字符串
     */
    escapeHtml(html) {
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }
    
    /**
     * 转义正则表达式特殊字符
     */
    escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
}

// 当文档加载完成时初始化
document.addEventListener('DOMContentLoaded', function() {
    // 获取URL中的查询参数
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');
    
    console.log('文档加载完成，查询参数:', query);
    
    if (query) {
        // 创建搜索导航器并初始化
        window.searchNavigator = new SearchNavigator();
        window.searchNavigator.init(query);
    }
    
    // 监听mark元素的点击事件，允许用户手动选择匹配项
    document.addEventListener('click', function(e) {
        if (e.target.tagName.toLowerCase() === 'mark' && window.searchNavigator) {
            const index = e.target.getAttribute('data-match-index');
            if (index !== null) {
                window.searchNavigator.navigateToMatch(parseInt(index, 10));
            }
        }
    });
}); 