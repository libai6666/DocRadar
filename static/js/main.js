/**
 * DocRadar - 主JavaScript文件
 * 负责文件拖放上传和实时搜索功能
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化拖放上传功能
    initFileUpload();
    
    // 初始化实时搜索功能
    initLiveSearch();
    
    // 初始化文档搜索功能
    initDocumentSearch();
});

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
    
    // 覆盖确认模态框
    const overwriteModal = new bootstrap.Modal(document.getElementById('overwriteConfirmModal'));
    const batchOverwriteModal = new bootstrap.Modal(document.getElementById('batchOverwriteModal'));
    const uploadResultModal = new bootstrap.Modal(document.getElementById('uploadResultModal'));
    const existingFilename = document.getElementById('existing-filename');
    const confirmFilename = document.getElementById('confirm-filename');
    const confirmOverwrite = document.getElementById('confirm-overwrite');
    const selectAllFiles = document.getElementById('select-all-files');
    const existingFilesList = document.getElementById('existing-files-list');
    const confirmBatchOverwrite = document.getElementById('confirm-batch-overwrite');
    const uploadResultContent = document.getElementById('upload-result-content');
    const uploadResultClose = document.getElementById('upload-result-close');
    
    if (!dropArea || !fileInput) return;
    
    // 存储选择的文件
    let selectedFiles = [];
    
    // 存储已存在的文件
    let existingFiles = [];
    
    // 上传结果统计
    let uploadStats = {
        success: 0,
        failed: 0,
        skipped: 0,
        overwritten: 0
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
        
        selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item d-flex justify-content-between align-items-center';
            
            const fileInfo = document.createElement('div');
            fileInfo.className = 'file-info d-flex align-items-center';
            
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
            
            fileItem.appendChild(fileInfo);
            fileItem.appendChild(removeBtn);
            fileList.appendChild(fileItem);
        });
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
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
        uploadResult.innerHTML = '';
        
        // 重置统计
        uploadStats = {
            success: 0,
            failed: 0,
            skipped: 0,
            overwritten: 0
        };
        
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
        confirmOverwrite.addEventListener('click', function() {
            const filename = confirmFilename.value;
            if (!filename) return;
            
            // 找到文件对象
            const file = selectedFiles.find(f => f.name === filename);
            if (!file) return;
            
            // 隐藏模态框
            overwriteModal.hide();
            
            // 带覆盖标志上传文件
            uploadSingleFile(file, true);
        });
    }
    
    // 批量覆盖确认处理
    if (confirmBatchOverwrite) {
        confirmBatchOverwrite.addEventListener('click', async function() {
            // 获取所有选中的文件
            const checkboxes = existingFilesList.querySelectorAll('input[type="checkbox"]:checked');
            const filesToOverwrite = Array.from(checkboxes).map(cb => cb.dataset.filename);
            
            // 隐藏模态框
            batchOverwriteModal.hide();
            
            // 上传选中的文件（带覆盖标志）
            for (const filename of filesToOverwrite) {
                const file = selectedFiles.find(f => f.name === filename);
                if (file) {
                    try {
                        const result = await uploadSingleFile(file, true);
                        updateUploadStats(result);
                    } catch (error) {
                        console.error(`上传文件 ${file.name} 时出错:`, error);
                        uploadStats.failed++;
                    }
                    
                    // 更新进度
                    updateProgress((uploadStats.success + uploadStats.failed + uploadStats.skipped + uploadStats.overwritten) / selectedFiles.length);
                }
            }
            
            // 显示最终结果
            showFinalResult();
        });
    }
    
    // 上传结果模态框关闭处理
    if (uploadResultClose) {
        uploadResultClose.addEventListener('click', function() {
            // 刷新页面以显示新上传的文件
            window.location.reload();
        });
    }
    
    // 上传按钮点击事件
    uploadBtn.addEventListener('click', () => {
        if (selectedFiles.length === 0) return;
        
        uploadFiles();
    });
    
    // 上传文件
    async function uploadFiles() {
        resetProgress();
        uploadBtn.disabled = true;
        uploadResult.innerHTML = '<div class="alert alert-info">检查文件并上传中，请稍候...</div>';
        
        // 重置已存在文件列表
        existingFiles = [];
        
        for (const file of selectedFiles) {
            try {
                // 检查文件是否存在
                const checkResult = await checkFileExists(file.name);
                
                if (checkResult.exists) {
                    // 收集已存在的文件信息
                    existingFiles.push({
                        ...checkResult,
                        file: file
                    });
                } else {
                    // 文件不存在，直接上传
                    const result = await uploadSingleFile(file, false);
                    updateUploadStats(result);
                }
            } catch (error) {
                console.error(`检查文件 ${file.name} 时出错:`, error);
                uploadStats.failed++;
            }
            
            // 更新进度（基于检查进度）
            updateProgress((uploadStats.success + uploadStats.failed + uploadStats.skipped) / selectedFiles.length);
        }
        
        // 如果有已存在的文件
        if (existingFiles.length > 0) {
            // 如果只有一个文件，显示单文件覆盖确认
            if (existingFiles.length === 1) {
                const fileInfo = existingFiles[0];
                existingFilename.textContent = fileInfo.filename;
                confirmFilename.value = fileInfo.filename;
                overwriteModal.show();
            } 
            // 如果有多个文件，显示批量覆盖选择界面
            else {
                showBatchOverwriteModal();
            }
        } else {
            // 所有文件都已上传，显示结果
            showFinalResult();
        }
        
        uploadBtn.disabled = false;
    }
    
    // 检查文件是否存在
    async function checkFileExists(filename) {
        try {
            const response = await fetch(`/api/check-file?filename=${encodeURIComponent(filename)}`);
            return await response.json();
        } catch (error) {
            console.error('检查文件存在失败:', error);
            return { exists: false, error: error.message };
        }
    }
    
    // 显示批量覆盖选择模态框
    function showBatchOverwriteModal() {
        existingFilesList.innerHTML = '';
        
        existingFiles.forEach(fileInfo => {
            const row = document.createElement('tr');
            
            // 复选框
            const checkboxCell = document.createElement('td');
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'form-check';
            const checkbox = document.createElement('input');
            checkbox.className = 'form-check-input';
            checkbox.type = 'checkbox';
            checkbox.checked = true;
            checkbox.dataset.filename = fileInfo.filename;
            checkboxDiv.appendChild(checkbox);
            checkboxCell.appendChild(checkboxDiv);
            
            // 文件名
            const filenameCell = document.createElement('td');
            filenameCell.textContent = fileInfo.filename;
            
            // 标题
            const titleCell = document.createElement('td');
            titleCell.textContent = fileInfo.title;
            
            // 类型
            const typeCell = document.createElement('td');
            typeCell.textContent = fileInfo.file_type.split('/').pop().toUpperCase();
            
            // 大小
            const sizeCell = document.createElement('td');
            sizeCell.textContent = formatFileSize(fileInfo.file_size);
            
            row.appendChild(checkboxCell);
            row.appendChild(filenameCell);
            row.appendChild(titleCell);
            row.appendChild(typeCell);
            row.appendChild(sizeCell);
            
            existingFilesList.appendChild(row);
        });
        
        batchOverwriteModal.show();
    }
    
    // 上传单个文件
    async function uploadSingleFile(file, overwrite = false) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('overwrite', overwrite ? 'true' : 'false');
        
        try {
            const response = await fetch('/upload/batch', {
                method: 'POST',
                body: formData
            });
            
            return await response.json();
        } catch (error) {
            return { 
                success: false, 
                error: error.message 
            };
        }
    }
    
    // 更新上传统计
    function updateUploadStats(result) {
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
        }
    }
    
    // 显示最终结果
    function showFinalResult() {
        let resultHTML = '<ul class="list-group mb-3">';
        
        if (uploadStats.success > 0) {
            resultHTML += `<li class="list-group-item list-group-item-success">
                新上传成功: ${uploadStats.success} 个文件
            </li>`;
        }
        
        if (uploadStats.overwritten > 0) {
            resultHTML += `<li class="list-group-item list-group-item-warning">
                成功覆盖: ${uploadStats.overwritten} 个文件
            </li>`;
        }
        
        if (uploadStats.skipped > 0) {
            resultHTML += `<li class="list-group-item list-group-item-info">
                跳过上传: ${uploadStats.skipped} 个文件
            </li>`;
        }
        
        if (uploadStats.failed > 0) {
            resultHTML += `<li class="list-group-item list-group-item-danger">
                上传失败: ${uploadStats.failed} 个文件
            </li>`;
        }
        
        resultHTML += '</ul>';
        
        // 根据是否有成功上传决定显示提示
        if (uploadStats.success > 0 || uploadStats.overwritten > 0) {
            resultHTML += '<div class="alert alert-success">系统将在关闭此窗口后刷新页面，显示最新上传的文件。</div>';
        }
        
        uploadResultContent.innerHTML = resultHTML;
        uploadResultModal.show();
        
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
        progressBar.style.width = `${percent}%`;
        progressText.textContent = `${percent}%`;
    }
    
    // 格式化文件大小
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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