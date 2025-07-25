/**
 * DocRadar - 会话监控模块
 * 用于定期检查会话状态，确保登录状态的一致性
 */

// 会话监控类
class SessionMonitor {
    constructor(options = {}) {
        // 默认配置
        this.config = {
            checkInterval: options.checkInterval || 60000, // 默认每60秒检查一次
            checkEndpoint: options.checkEndpoint || '/session_check',
            onSessionExpired: options.onSessionExpired || this.defaultSessionExpiredHandler,
            onSessionValid: options.onSessionValid || (() => {}),
            onError: options.onError || console.error,
            debug: options.debug || false
        };
        
        this.isMonitoring = false;
        this.intervalId = null;
        this.lastKnownState = null;
    }
    
    /**
     * 开始监控会话状态
     */
    start() {
        if (this.isMonitoring) {
            this.log('会话监控已经在运行中');
            return;
        }
        
        this.isMonitoring = true;
        this.log('开始会话监控');
        
        // 立即执行一次检查
        this.checkSession();
        
        // 设置定期检查
        this.intervalId = setInterval(() => {
            this.checkSession();
        }, this.config.checkInterval);
    }
    
    /**
     * 停止监控会话状态
     */
    stop() {
        if (!this.isMonitoring) {
            return;
        }
        
        clearInterval(this.intervalId);
        this.intervalId = null;
        this.isMonitoring = false;
        this.log('停止会话监控');
    }
    
    /**
     * 检查会话状态
     */
    checkSession() {
        this.log('检查会话状态...');
        
        fetch(this.config.checkEndpoint)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`会话检查失败: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                this.log('会话状态:', data);
                
                // 检查会话状态变化
                if (this.lastKnownState !== null) {
                    // 如果之前是登录状态，现在变成未登录，则触发会话过期处理
                    if (this.lastKnownState.logged_in && !data.logged_in) {
                        this.config.onSessionExpired(data);
                    } else if (data.logged_in) {
                        // 会话有效
                        this.config.onSessionValid(data);
                    }
                }
                
                // 更新最后已知状态
                this.lastKnownState = data;
            })
            .catch(error => {
                this.config.onError(error);
            });
    }
    
    /**
     * 默认的会话过期处理函数
     */
    defaultSessionExpiredHandler(data) {
        console.warn('会话已过期或无效，请重新登录');
        
        // 显示会话过期提示
        const expiredAlert = document.createElement('div');
        expiredAlert.className = 'alert alert-warning alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
        expiredAlert.setAttribute('role', 'alert');
        expiredAlert.style.zIndex = '9999';
        expiredAlert.innerHTML = `
            <strong>会话已过期!</strong> 您的登录状态已失效，请<a href="/login" class="alert-link">重新登录</a>。
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        document.body.appendChild(expiredAlert);
        
        // 5秒后自动跳转到登录页面
        setTimeout(() => {
            window.location.href = '/login?expired=1';
        }, 5000);
    }
    
    /**
     * 调试日志
     */
    log(...args) {
        if (this.config.debug) {
            console.log('[SessionMonitor]', ...args);
        }
    }
}

// 在页面加载完成后初始化会话监控
document.addEventListener('DOMContentLoaded', () => {
    // 只在需要登录的页面上启用会话监控
    const needsMonitoring = document.body.getAttribute('data-needs-session-monitoring') === 'true';
    
    if (needsMonitoring) {
        // 创建并启动会话监控
        window.sessionMonitor = new SessionMonitor({
            debug: false,  // 生产环境设置为false
            checkInterval: 30000  // 每30秒检查一次
        });
        window.sessionMonitor.start();
    }
}); 