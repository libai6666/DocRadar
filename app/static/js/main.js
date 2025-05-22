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
    
    // 初始化消息自动关闭功能
    initAutoCloseAlerts();
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
                updateUploadStats(result);
                
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
            
            // 上传其他新文件
            const newFiles = selectedFiles.filter(file => 
                !existingFiles.some(existing => existing.filename === file.name)
            );
            
            if (newFiles.length > 0) {
                console.log('上传其他新文件:', newFiles.length);
                uploadAllNewFiles(newFiles);
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
            
            const filesToOverwrite = Array.from(checkboxes).map(cb => cb.dataset.filename);
            
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
            
            // 获取所有新文件(不在existingFiles中的文件)
            const newFiles = selectedFiles.filter(file => 
                !existingFiles.some(existing => existing.filename === file.name)
            );
            
            // 标记未选中的文件为跳过
            const unselectedFiles = existingFiles.filter(fileInfo => 
                !filesToOverwrite.includes(fileInfo.filename)
            );
            
            console.log(`${unselectedFiles.length}个文件被标记为跳过`);
            uploadStats.skipped += unselectedFiles.length;
            
            // 然后上传需要覆盖的文件
            uploadResult.innerHTML = '<div class="alert alert-info">上传覆盖文件中，请稍候...</div>';
            
            // 修改确认覆盖文件的处理逻辑，添加延迟和重试机制
            const processBatch = async (files, startIndex, batchSize) => {
                const endIndex = Math.min(startIndex + batchSize, files.length);
                console.log(`处理批次: ${startIndex}-${endIndex-1} / ${files.length}`);
                
                for (let i = startIndex; i < endIndex; i++) {
                    const filename = files[i];
                    const fileInfo = existingFiles.find(f => f.filename === filename);
                    
                    if (!fileInfo || !fileInfo.file) {
                        console.error(`未找到文件信息: ${filename}`);
                        uploadStats.failed++;
                        continue;
                    }
                    
                    // 添加重试逻辑
                    let success = false;
                    let attempts = 0;
                    const maxAttempts = 3;
                    
                    while (!success && attempts < maxAttempts) {
                        attempts++;
                        try {
                            // 添加尝试信息和延迟
                            if (attempts > 1) {
                                console.log(`重试上传文件 (${attempts}/${maxAttempts}): ${filename}`);
                                // 重试前等待一段时间，避免文件锁定
                                await new Promise(resolve => setTimeout(resolve, 1500 * attempts));
                            } else {
                                console.log(`准备覆盖文件: ${filename}`);
                            }
                            
                            const result = await uploadSingleFile(fileInfo.file, true);
                            
                            if (result && result.success) {
                                success = true;
                                updateUploadStats(result);
                                console.log(`文件覆盖成功: ${filename}`);
                            } else {
                                console.warn(`文件覆盖失败 (${attempts}/${maxAttempts}): ${filename}, 错误: ${result?.error || '未知错误'}`);
                            }
                        } catch (error) {
                            console.error(`上传文件时出错 (${attempts}/${maxAttempts}): ${filename}`, error);
                        }
                    }
                    
                    if (!success) {
                        console.error(`文件在${maxAttempts}次尝试后仍然失败: ${filename}`);
                        uploadStats.failed++;
                    }
                    
                    // 更新进度
                    updateProgress((i + 1) / files.length);
                    
                    // 文件之间添加小延迟，避免并发问题
                    await new Promise(resolve => setTimeout(resolve, 200));
                }
                
                // 处理下一批次
                if (endIndex < files.length) {
                    // 批次之间添加更长的延迟
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    await processBatch(files, endIndex, batchSize);
                }
            };
            
            // 开始分批处理，每批次3个文件
            await processBatch(filesToOverwrite, 0, 3);
            
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
        
        // 如果有已存在的文件，显示覆盖确认对话框
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
                            // 如果无法初始化模态框，直接上传新文件
                            uploadAllNewFiles(newFiles);
                            uploadBtn.disabled = false;
                            
                            // 恢复批量删除按钮
                            if (batchDeleteBtn) {
                                batchDeleteBtn.disabled = false;
                            }
                            return;
                        }
                    } else {
                        console.error('覆盖确认模态框元素不存在');
                        // 如果模态框元素不存在，直接上传新文件
                        uploadAllNewFiles(newFiles);
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
                        uploadAllNewFiles(newFiles);
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
                    // 如果无法显示模态框，直接上传新文件
                    uploadAllNewFiles(newFiles);
                    
                    // 恢复批量删除按钮
                    if (batchDeleteBtn) {
                        batchDeleteBtn.disabled = false;
                    }
                }
            } 
            // 如果有多个文件，显示批量覆盖选择界面
            else {
                console.log('准备显示批量覆盖选择界面');
                showBatchOverwriteModal(newFiles);
            }
        } else {
            // 如果没有已存在的文件，直接上传所有新文件
            console.log('没有已存在的文件，直接上传所有新文件');
            uploadAllNewFiles(newFiles);
        }
        
        uploadBtn.disabled = false;
    }
    
    // 上传所有新文件
    async function uploadAllNewFiles(files) {
        if (files.length === 0) {
            showFinalResult();
            return;
        }
        
        uploadResult.innerHTML = '<div class="alert alert-info">上传新文件中，请稍候...</div>';
        
        // 上传所有新文件
        for (let i = 0; i < files.length; i++) {
            try {
                const result = await uploadSingleFile(files[i], false);
                updateUploadStats(result);
            } catch (error) {
                console.error(`上传文件 ${files[i].name} 时出错:`, error);
                uploadStats.failed++;
            }
            
            // 更新上传进度
            updateProgress((i + 1) / files.length);
        }
        
        showFinalResult();
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
    function showBatchOverwriteModal(newFiles) {
        console.log('准备显示批量覆盖选择模态框', existingFiles.length);
        console.log('已存在文件列表:', existingFiles);
        
        // 确保模态框元素和对象存在
        if (!batchOverwriteModalEl) {
            console.error('找不到批量覆盖模态框元素');
            // 如果无法显示模态框，直接上传新文件
            if (newFiles && newFiles.length > 0) {
                uploadAllNewFiles(newFiles);
            }
            return;
        }
        
        // 确保existingFilesList元素存在
        if (!existingFilesList) {
            console.error('找不到existingFilesList元素');
            // 如果无法显示模态框，直接上传新文件
            if (newFiles && newFiles.length > 0) {
                uploadAllNewFiles(newFiles);
            }
            return;
        }
        
        // 清空列表
        existingFilesList.innerHTML = '';
        
        // 添加文件到列表
        existingFiles.forEach(fileInfo => {
            console.log(`添加文件到批量覆盖列表: ${fileInfo.filename}`);
            const row = document.createElement('tr');
            
            // 复选框
            const checkboxCell = document.createElement('td');
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'form-check';
            const checkbox = document.createElement('input');
            checkbox.className = 'form-check-input';
            checkbox.type = 'checkbox';
            checkbox.checked = true; // 默认选中
            checkbox.dataset.filename = fileInfo.filename;
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
            if (newFiles && newFiles.length > 0) {
                uploadAllNewFiles(newFiles);
            }
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
            // 如果无法显示模态框，直接上传新文件
            if (newFiles && newFiles.length > 0) {
                uploadAllNewFiles(newFiles);
            }
        }
    }
    
    // 上传单个文件
    async function uploadSingleFile(file, overwrite = false) {
        console.log(`准备上传文件: ${file.name}, 覆盖模式: ${overwrite}`);
        
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
            
            // 添加请求超时处理
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30秒超时
            
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
                    error: '请求超时，请检查网络连接或稍后重试' 
                };
            }
            
            return { 
                success: false, 
                error: error.message || '未知错误' 
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
        console.log('显示上传结果', uploadStats);
        
        // 恢复批量删除按钮
        const batchDeleteBtn = document.getElementById('batch-delete-queue');
        if (batchDeleteBtn) {
            batchDeleteBtn.disabled = false;
        }
        
        // 确保uploadResultContent元素存在
        if (!uploadResultContent) {
            console.error('找不到上传结果内容元素');
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
                上传失败: ${uploadStats.failed} 个文件
            </li>`;
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
        
        // 如果所有文件都被跳过，显示特殊提示
        if (uploadStats.success === 0 && uploadStats.overwritten === 0 && uploadStats.skipped > 0 && uploadStats.failed === 0) {
            resultHTML += '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle-fill me-2"></i>所有文件都已跳过上传，没有任何文件被添加或覆盖。</div>';
        }
        
        uploadResultContent.innerHTML = resultHTML;
        
        // 确保bootstrap已加载
        if (typeof bootstrap === 'undefined') {
            console.error('Bootstrap未加载');
            alert(`上传完成: 成功 ${uploadStats.success}, 覆盖 ${uploadStats.overwritten}, 跳过 ${uploadStats.skipped}, 失败 ${uploadStats.failed}`);
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
        
        // 显示临时上传结果
        if (uploadResult) {
            uploadResult.innerHTML = '<div class="alert alert-info">上传完成，正在处理结果...</div>';
        }
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