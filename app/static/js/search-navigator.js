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
        
        // 保存上次滚动位置
        this.lastScrollPosition = 0;
        
        // 初始化状态跟踪
        this.initialized = false;
    }
    
    /**
     * 初始化导航器
     * @param {string} query - 搜索查询
     */
    init(query) {
        if (!query) return;
        
        this.query = query;
        console.log('SearchNavigator初始化，查询词:', query);
        
        // 检测是否有预先高亮的匹配项
        const hasExistingHighlights = document.querySelectorAll('.document-content mark').length > 0;
        if (!hasExistingHighlights) {
            console.log('没有找到预先高亮的匹配项，尝试自己高亮');
            this.highlightMatches();
        } else {
            console.log('发现预先高亮的匹配项');
        }
        
        this.findMatches();
        
        if (this.totalMatches > 0) {
            console.log(`找到 ${this.totalMatches} 个匹配项`);
            this.createNavigation();
            
            // 延长等待时间并添加更多日志
            setTimeout(() => {
                console.log('准备导航到第一个匹配项');
                this.navigateToMatch(0);
                console.log('已导航到第一个匹配项');
                this.initialized = true;
            }, 1000); // 从500ms增加到1000ms
            
            this.isActive = true;
            
            // 添加滚动事件监听器
            window.addEventListener('scroll', this.handleScroll.bind(this));
        } else {
            console.log('未找到匹配项');
            // 如果没有找到匹配项，但是有查询词，尝试更宽松的匹配
            if (query && query.length > 1) {
                console.log('尝试更宽松的匹配');
                this.highlightMatchesLoose();
                this.findMatches();
                
                if (this.totalMatches > 0) {
                    console.log(`使用宽松匹配找到 ${this.totalMatches} 个匹配项`);
                    this.createNavigation();
                    
                    // 延长等待时间并添加更多日志
                    setTimeout(() => {
                        console.log('准备导航到第一个匹配项（宽松匹配）');
                        this.navigateToMatch(0);
                        console.log('已导航到第一个匹配项（宽松匹配）');
                        this.initialized = true;
                    }, 1000); // 从500ms增加到1000ms
                    
                    this.isActive = true;
                    
                    // 添加滚动事件监听器
                    window.addEventListener('scroll', this.handleScroll.bind(this));
                } else {
                    console.log('即使使用宽松匹配也未找到匹配项');
                    this.showNoMatchesMessage();
                }
            } else {
                this.showNoMatchesMessage();
            }
        }
    }
    
    /**
     * 显示未找到匹配项的消息
     */
    showNoMatchesMessage() {
        const contentElement = document.querySelector('.document-content');
        if (!contentElement) return;
        
        // 创建一个提示元素
        const messageElement = document.createElement('div');
        messageElement.className = 'alert alert-info mt-3';
        messageElement.innerHTML = `
            <i class="bi bi-info-circle"></i> 
            未在文档中找到匹配 "<strong>${this.escapeHtml(this.query)}</strong>" 的内容。
        `;
        
        // 添加到文档内容之前
        contentElement.parentNode.insertBefore(messageElement, contentElement);
    }
    
    /**
     * 处理页面滚动事件
     */
    handleScroll() {
        if (!this.isActive || this.matches.length === 0) return;
        
        // 获取当前滚动位置
        const scrollPosition = window.scrollY;
        
        // 如果是用户手动滚动（而不是由navigateToMatch触发的滚动）
        if (Math.abs(scrollPosition - this.lastScrollPosition) > 50) {
            // 查找当前视口中的匹配项
            const viewportTop = scrollPosition;
            const viewportBottom = viewportTop + window.innerHeight;
            
            let closestIndex = 0;
            let closestDistance = Infinity;
            
            this.matches.forEach((match, index) => {
                const rect = match.getBoundingClientRect();
                const matchTop = rect.top + scrollPosition;
                
                // 如果匹配项在视口中，或者是最接近视口的匹配项
                if (matchTop >= viewportTop && matchTop <= viewportBottom) {
                    const distance = Math.abs(matchTop - (viewportTop + window.innerHeight / 2));
                    if (distance < closestDistance) {
                        closestDistance = distance;
                        closestIndex = index;
                    }
                }
            });
            
            // 更新当前索引和UI（但不滚动）
            if (this.currentIndex !== closestIndex) {
                this.updateCurrentMatch(closestIndex, false);
            }
            
            // 更新最后滚动位置
            this.lastScrollPosition = scrollPosition;
        }
    }
    
    /**
     * 在文档中查找并高亮显示匹配项
     */
    highlightMatches() {
        const contentElement = document.querySelector('.document-content');
        if (!contentElement) return;
        
        // 获取查询词
        const terms = this.query.split(/\s+/).filter(term => term.length > 0);
        
        // 处理HTML内容
        const tempElement = document.createElement('div');
        tempElement.innerHTML = contentElement.innerHTML;
            
        // 高亮处理文本节点
        this.highlightTextNodes(tempElement, terms);
            
        // 替换原始内容
        contentElement.innerHTML = tempElement.innerHTML;
    }
    
    /**
     * 使用更宽松的匹配规则高亮显示匹配项
     */
    highlightMatchesLoose() {
        const contentElement = document.querySelector('.document-content');
        if (!contentElement) return;
        
        // 获取查询词并分解为单个字符
        const terms = this.query.split('');
        
        // 处理HTML内容
        const tempElement = document.createElement('div');
        tempElement.innerHTML = contentElement.innerHTML;
            
        // 高亮处理文本节点，使用更宽松的匹配
        this.highlightTextNodesLoose(tempElement, this.query);
            
        // 替换原始内容
        contentElement.innerHTML = tempElement.innerHTML;
    }
    
    /**
     * 递归处理文本节点，高亮匹配内容
     * @param {Element} element - DOM元素
     * @param {Array} terms - 搜索词数组
     */
    highlightTextNodes(element, terms) {
        if (!element) return;
        
        const childNodes = [...element.childNodes];
        
        for (const node of childNodes) {
            if (node.nodeType === Node.TEXT_NODE) {
                let text = node.nodeValue;
                let hasMatch = false;
                
                // 首先尝试完整短语匹配
                if (this.query.length > 1) {
                    const regex = new RegExp(this.escapeRegExp(this.query), 'gi');
                    if (regex.test(text)) {
                        hasMatch = true;
                        text = text.replace(regex, match => 
                            `<mark data-match="true">${match}</mark>`
                        );
                    }
                }
                
                // 如果完整短语没有匹配，尝试单词匹配
                if (!hasMatch && terms.length > 0) {
                    for (const term of terms) {
                        if (term.length < 2) continue;
                        
                        const regex = new RegExp(this.escapeRegExp(term), 'gi');
                        if (regex.test(text)) {
                            hasMatch = true;
                            text = text.replace(regex, match => 
                                `<mark data-match="true">${match}</mark>`
                            );
                        }
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
                this.highlightTextNodes(node, terms);
            }
        }
    }
    
    /**
     * 使用更宽松的匹配规则递归处理文本节点
     * @param {Element} element - DOM元素
     * @param {string} query - 完整的搜索查询
     */
    highlightTextNodesLoose(element, query) {
        if (!element) return;
        
        const childNodes = [...element.childNodes];
        
        for (const node of childNodes) {
            if (node.nodeType === Node.TEXT_NODE) {
                let text = node.nodeValue;
                let hasMatch = false;
                
                // 检查文本是否包含查询词的任何部分（不区分大小写）
                const lowerText = text.toLowerCase();
                const lowerQuery = query.toLowerCase();
                
                if (lowerText.includes(lowerQuery)) {
                    hasMatch = true;
                    // 使用正则表达式高亮匹配部分
                    const regex = new RegExp(this.escapeRegExp(query), 'gi');
                    text = text.replace(regex, match => 
                        `<mark data-match="true">${match}</mark>`
                    );
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
                this.highlightTextNodesLoose(node, query);
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
            
            // 添加点击事件
            match.addEventListener('click', () => {
                this.navigateToMatch(index);
            });
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
                    <button class="btn btn-sm btn-outline-secondary prev-match" title="上一个匹配 (Shift+Enter)">
                        <i class="bi bi-arrow-up"></i>
                    </button>
                    <span class="match-counter">1/${this.totalMatches}</span>
                    <button class="btn btn-sm btn-outline-secondary next-match" title="下一个匹配 (Enter)">
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
     * 更新当前匹配项的UI（不滚动）
     * @param {number} index - 匹配项索引
     * @param {boolean} shouldScroll - 是否应该滚动到匹配项
     */
    updateCurrentMatch(index, shouldScroll = true) {
        if (index < 0 || index >= this.totalMatches) return;
        
        // 更新当前索引
        this.currentIndex = index;
        
        // 移除之前的当前匹配项标记
        const currentMatch = document.querySelector(`.${this.activeClass}`);
        if (currentMatch) {
            currentMatch.classList.remove(this.activeClass);
        }
        
        // 标记新的当前匹配项
        const match = this.matches[index];
        match.classList.add(this.activeClass);
        
        // 更新计数器
        if (this.counter) {
            this.counter.textContent = `${index + 1}/${this.totalMatches}`;
        }
        
        // 如果需要，滚动到视图中
        if (shouldScroll) {
            this.scrollToMatch(match);
        }
    }
    
    /**
     * 导航到特定匹配项
     * @param {number} index - 匹配项索引
     */
    navigateToMatch(index) {
        this.updateCurrentMatch(index, true);
    }
    
    /**
     * 滚动到匹配项
     * @param {Element} match - 要滚动到的匹配元素
     */
    scrollToMatch(match) {
        if (!match) {
            console.log('无法滚动：匹配项为null');
            return;
        }
        
        // 记录当前滚动位置
        this.lastScrollPosition = window.scrollY;
        
        // 先记录匹配项的位置信息用于调试
        const rect = match.getBoundingClientRect();
        console.log(`匹配项位置: top=${rect.top}, left=${rect.left}, bottom=${rect.bottom}, right=${rect.right}`);
        
        // 添加更强的视觉指示
        match.classList.add('super-highlight');
        
        // 强制滚动到视图并居中
        try {
            match.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
            console.log('执行了scrollIntoView');
        } catch (e) {
            console.error('scrollIntoView失败:', e);
            
            // 后备滚动方法
            const yPosition = rect.top + window.scrollY - (window.innerHeight / 2);
            window.scrollTo({
                top: yPosition,
                behavior: 'smooth'
            });
            console.log('使用后备滚动方法scrollTo');
        }
        
        // 添加更强的闪烁效果
        match.classList.add('blink');
        setTimeout(() => {
            match.classList.remove('blink');
            setTimeout(() => {
                match.classList.remove('super-highlight');
            }, 500);
        }, 2000); // 增加动画时间
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
        
        // 移除滚动事件监听器
        window.removeEventListener('scroll', this.handleScroll);
        
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
    
    // 添加闪烁效果的CSS
    const style = document.createElement('style');
    style.textContent = `
        @keyframes blink {
            0% { background-color: #fff5b1; }
            50% { background-color: #ffc107; }
            100% { background-color: #fff5b1; }
        }
        mark.blink {
            animation: blink 0.5s 2;
        }
        mark {
            background-color: #fff5b1;
            padding: 0.1em 0.2em;
            border-radius: 2px;
            box-shadow: 0 0 2px rgba(0,0,0,0.2);
            transition: all 0.2s;
        }
        mark.current-match {
            background-color: #ffc107;
            box-shadow: 0 0 0 2px #ffc107;
            font-weight: bold;
        }
    `;
    document.head.appendChild(style);
}); 