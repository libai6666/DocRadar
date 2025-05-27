/**
 * 文档ID映射器
 * 用于处理旧文档ID到新文档ID的映射，确保链接始终指向最新的文档
 */
(function() {
    // 存储键名
    const STORAGE_KEY = 'docradar_doc_id_mappings';
    
    /**
     * 保存文档ID映射
     * @param {string} oldId - 旧文档ID
     * @param {string} newId - 新文档ID
     */
    function saveDocIdMapping(oldId, newId) {
        if (!oldId || !newId || oldId === newId) return;
        
        try {
            // 获取现有的映射表
            let mappings = {};
            const storedMappings = localStorage.getItem(STORAGE_KEY);
            if (storedMappings) {
                mappings = JSON.parse(storedMappings);
            }
            
            // 添加或更新映射
            mappings[oldId] = newId;
            
            // 保存回本地存储
            localStorage.setItem(STORAGE_KEY, JSON.stringify(mappings));
            console.log(`已保存文档ID映射: ${oldId} -> ${newId}`);
        } catch (error) {
            console.error('保存文档ID映射时出错:', error);
        }
    }
    
    /**
     * 获取映射后的文档ID
     * @param {string} docId - 原始文档ID
     * @returns {string} 映射后的文档ID，如果没有映射则返回原始ID
     */
    function getMappedDocId(docId) {
        if (!docId) return docId;
        
        try {
            const storedMappings = localStorage.getItem(STORAGE_KEY);
            if (storedMappings) {
                const mappings = JSON.parse(storedMappings);
                // 递归查找，处理链式映射 (A->B->C)
                let currentId = docId;
                let visited = new Set();
                
                while (mappings[currentId] && !visited.has(currentId)) {
                    visited.add(currentId);
                    currentId = mappings[currentId];
                }
                
                return currentId;
            }
        } catch (error) {
            console.error('获取文档ID映射时出错:', error);
        }
        
        return docId;
    }
    
    /**
     * 检测URL中的重定向参数并保存映射
     */
    function detectRedirect() {
        const urlParams = new URLSearchParams(window.location.search);
        const fromDocId = urlParams.get('from_doc_id');
        
        if (fromDocId) {
            // 从URL路径中提取当前文档ID
            const pathMatch = window.location.pathname.match(/\/document\/(\d+)/);
            if (pathMatch && pathMatch[1]) {
                const currentDocId = pathMatch[1];
                
                // 保存映射关系
                saveDocIdMapping(fromDocId, currentDocId);
                
                // 移除URL中的from_doc_id参数，保持URL整洁
                urlParams.delete('from_doc_id');
                const newUrl = new URL(window.location.href);
                newUrl.search = urlParams.toString();
                window.history.replaceState({}, '', newUrl.toString());
            }
        }
    }
    
    /**
     * 更新页面上的文档链接
     */
    function updateDocumentLinks() {
        // 查找所有文档链接
        const docLinks = document.querySelectorAll('a[href*="/document/"]');
        let updatedCount = 0;
        
        docLinks.forEach(link => {
            // 从链接中提取文档ID
            const href = link.getAttribute('href');
            const docRegex = /\/document\/(\d+)/;
            const match = href.match(docRegex);
            
            if (match && match[1]) {
                const oldDocId = match[1];
                const newDocId = getMappedDocId(oldDocId);
                
                // 如果有映射，更新链接
                if (newDocId !== oldDocId) {
                    // 更新href属性
                    const newHref = href.replace(`/document/${oldDocId}`, `/document/${newDocId}`);
                    link.setAttribute('href', newHref);
                    
                    // 更新显示的文档ID（如果有）
                    const idDisplays = link.parentElement.parentElement.querySelectorAll('.result-meta .me-3');
                    idDisplays.forEach(span => {
                        if (span.textContent.includes(`ID: ${oldDocId}`)) {
                            span.innerHTML = span.innerHTML.replace(
                                `ID: ${oldDocId}`, 
                                `ID: ${newDocId}`
                                //`ID: ${newDocId} <small class="text-muted">(原ID: ${oldDocId})</small>`
                            );
                        }
                    });
                    
                    updatedCount++;
                }
            }
        });
        
        if (updatedCount > 0) {
            console.log(`已更新 ${updatedCount} 个文档链接的ID映射`);
        }
    }
    
    // 导出公共API
    window.DocIdMapper = {
        saveMapping: saveDocIdMapping,
        getMappedId: getMappedDocId,
        detectRedirect: detectRedirect,
        updateLinks: updateDocumentLinks
    };
    
    // 页面加载时自动运行
    document.addEventListener('DOMContentLoaded', function() {
        // 检测重定向并保存映射
        detectRedirect();
        
        // 更新页面上的链接
        updateDocumentLinks();
    });
})(); 