/**
 * YAM Real-Time Development System
 * =================================
 * 
 * This script provides real-time development capabilities including:
 * - File change detection
 * - Browser auto-refresh
 * - Template hot-reload
 * - Static file cache busting
 * - Development notifications
 * - SocketIO integration
 */

(function() {
    'use strict';
    
    // YAM Real-Time Development System
    window.YAMRealTime = {
        // Configuration
        config: {
            socketUrl: window.location.origin,
            reconnectAttempts: 5,
            reconnectDelay: 1000,
            fileWatchEnabled: true,
            autoRefreshEnabled: true,
            notificationsEnabled: true,
            debugMode: true
        },
        
        // State
        state: {
            connected: false,
            socket: null,
            reconnectCount: 0,
            lastFileChange: null,
            watchingFiles: new Set(),
            refreshQueue: [],
            notificationQueue: []
        },
        
        // Initialize the real-time system
        init() {
            this.log('Initializing YAM Real-Time Development System...');
            
            // Check if we're in debugger mode
            this.checkDebuggerMode();
            
            // Initialize SocketIO connection
            this.initSocketIO();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Setup notification system
            this.setupNotifications();
            
            // Setup auto-refresh system
            this.setupAutoRefresh();
            
            this.log('YAM Real-Time Development System initialized');
        },
        
        // Check if we're in debugger mode
        checkDebuggerMode() {
            fetch('/debugger/status')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'running' && data.mode === 'debugger') {
                        this.log('Debugger mode detected - enabling real-time features');
                        this.config.fileWatchEnabled = true;
                        this.config.autoRefreshEnabled = true;
                        this.showNotification('Real-time development mode enabled', 'success');
                    }
                })
                .catch(error => {
                    this.log('Not in debugger mode - real-time features disabled');
                    this.config.fileWatchEnabled = false;
                    this.config.autoRefreshEnabled = false;
                });
        },
        
        // Initialize SocketIO connection
        initSocketIO() {
            if (typeof io === 'undefined') {
                this.log('SocketIO not available - real-time features disabled');
                return;
            }
            
            try {
                this.state.socket = io(this.config.socketUrl, {
                    transports: ['polling', 'websocket'],
                    reconnection: true,
                    reconnectionAttempts: this.config.reconnectAttempts,
                    reconnectionDelay: this.config.reconnectDelay,
                    timeout: 20000
                });
                
                this.setupSocketEvents();
                this.log('SocketIO connection initialized');
                
            } catch (error) {
                this.log('Failed to initialize SocketIO:', error);
            }
        },
        
        // Setup SocketIO event handlers
        setupSocketEvents() {
            if (!this.state.socket) return;
            
            // Connection events
            this.state.socket.on('connect', () => {
                this.state.connected = true;
                this.state.reconnectCount = 0;
                this.log('Connected to real-time server');
                this.showNotification('Real-time connection established', 'success');
                
                // Emit debugger connect event
                this.state.socket.emit('debugger_connect');
            });
            
            this.state.socket.on('disconnect', () => {
                this.state.connected = false;
                this.log('Disconnected from real-time server');
                this.showNotification('Real-time connection lost', 'warning');
            });
            
            this.state.socket.on('connect_error', (error) => {
                this.log('SocketIO connection error:', error);
                this.showNotification('Real-time connection error', 'error');
            });
            
            // File change events
            this.state.socket.on('file_changed', (data) => {
                this.handleFileChange(data);
            });
            
            this.state.socket.on('browser_refresh', (data) => {
                this.handleBrowserRefresh(data);
            });
            
            this.state.socket.on('template_reloaded', (data) => {
                this.handleTemplateReload(data);
            });
            
            this.state.socket.on('static_reloaded', (data) => {
                this.handleStaticReload(data);
            });
            
            this.state.socket.on('python_reloaded', (data) => {
                this.handlePythonReload(data);
            });
            
            // Debugger events
            this.state.socket.on('debugger_status', (data) => {
                this.handleDebuggerStatus(data);
            });
            
            this.state.socket.on('file_content', (data) => {
                this.handleFileContent(data);
            });
        },
        
        // Handle file change events
        handleFileChange(data) {
            this.log('File changed:', data);
            this.state.lastFileChange = data;
            
            // Show notification
            if (this.config.notificationsEnabled) {
                const fileType = this.getFileTypeDisplay(data.file_type);
                this.showNotification(`${fileType} file changed: ${this.getFileName(data.file_path)}`, 'info');
            }
            
            // Handle different file types
            switch (data.file_type) {
                case 'template':
                    this.handleTemplateChange(data);
                    break;
                case 'static':
                    this.handleStaticChange(data);
                    break;
                case 'python':
                    this.handlePythonChange(data);
                    break;
                default:
                    this.log('Unknown file type:', data.file_type);
            }
        },
        
        // Handle browser refresh events
        handleBrowserRefresh(data) {
            this.log('Browser refresh requested:', data);
            
            if (this.config.autoRefreshEnabled) {
                // Add to refresh queue to prevent multiple rapid refreshes
                this.state.refreshQueue.push(data);
                
                // Debounce refresh
                clearTimeout(this.refreshTimeout);
                this.refreshTimeout = setTimeout(() => {
                    this.performRefresh();
                }, 500);
            }
        },
        
        // Handle template reload events
        handleTemplateReload(data) {
            this.log('Template reloaded:', data);
            this.showNotification('Templates reloaded successfully', 'success');
            
            // Refresh the page to show template changes
            if (this.config.autoRefreshEnabled) {
                setTimeout(() => {
                    window.location.reload();
                }, 100);
            }
        },
        
        // Handle static file reload events
        handleStaticReload(data) {
            this.log('Static files reloaded:', data);
            this.showNotification('Static files reloaded successfully', 'success');
            
            // Clear cache and reload static resources
            this.clearStaticCache();
        },
        
        // Handle Python reload events
        handlePythonReload(data) {
            this.log('Python modules reloaded:', data);
            this.showNotification('Python modules reloaded (limited)', 'info');
        },
        
        // Handle debugger status events
        handleDebuggerStatus(data) {
            this.log('Debugger status:', data);
            this.updateDebuggerStatus(data);
        },
        
        // Handle file content events
        handleFileContent(data) {
            this.log('File content received:', data);
            // Could be used for live editing features
        },
        
        // Handle template changes
        handleTemplateChange(data) {
            this.log('Template change detected:', data);
            
            // For templates, we need to refresh the page
            if (this.config.autoRefreshEnabled) {
                this.queueRefresh('Template change detected');
            }
        },
        
        // Handle static file changes
        handleStaticChange(data) {
            this.log('Static file change detected:', data);
            
            // For CSS/JS files, we can try to reload without full page refresh
            const filePath = data.file_path;
            const fileExt = this.getFileExtension(filePath);
            
            if (fileExt === 'css') {
                this.reloadCSS(filePath);
            } else if (fileExt === 'js') {
                this.reloadJS(filePath);
            } else {
                // For other static files, refresh the page
                if (this.config.autoRefreshEnabled) {
                    this.queueRefresh('Static file change detected');
                }
            }
        },
        
        // Handle Python changes
        handlePythonChange(data) {
            this.log('Python file change detected:', data);
            
            // For Python files, we need to refresh the page
            if (this.config.autoRefreshEnabled) {
                this.queueRefresh('Python file change detected');
            }
        },
        
        // Queue a page refresh
        queueRefresh(reason) {
            this.log('Queueing refresh:', reason);
            this.state.refreshQueue.push({
                reason: reason,
                timestamp: new Date().toISOString()
            });
            
            // Debounce refresh
            clearTimeout(this.refreshTimeout);
            this.refreshTimeout = setTimeout(() => {
                this.performRefresh();
            }, 1000);
        },
        
        // Perform the actual refresh
        performRefresh() {
            if (this.state.refreshQueue.length === 0) return;
            
            const lastChange = this.state.refreshQueue[this.state.refreshQueue.length - 1];
            this.log('Performing refresh due to:', lastChange.reason);
            
            this.showNotification('Refreshing page due to file changes...', 'info');
            
            // Clear the queue
            this.state.refreshQueue = [];
            
            // Refresh the page
            setTimeout(() => {
                window.location.reload();
            }, 500);
        },
        
        // Reload CSS files without page refresh
        reloadCSS(filePath) {
            this.log('Reloading CSS:', filePath);
            
            // Find all link tags that match the file
            const links = document.querySelectorAll('link[rel="stylesheet"]');
            links.forEach(link => {
                if (link.href.includes(this.getFileName(filePath))) {
                    const newHref = link.href.split('?')[0] + '?v=' + Date.now();
                    link.href = newHref;
                    this.log('CSS reloaded:', newHref);
                }
            });
            
            this.showNotification('CSS file reloaded', 'success');
        },
        
        // Reload JS files without page refresh
        reloadJS(filePath) {
            this.log('Reloading JS:', filePath);
            
            // For JS files, we need to refresh the page as they're already loaded
            this.queueRefresh('JavaScript file change detected');
        },
        
        // Clear static file cache
        clearStaticCache() {
            this.log('Clearing static file cache');
            
            // Clear CSS cache
            const links = document.querySelectorAll('link[rel="stylesheet"]');
            links.forEach(link => {
                const newHref = link.href.split('?')[0] + '?v=' + Date.now();
                link.href = newHref;
            });
            
            // Clear JS cache (will be handled by page refresh)
            this.showNotification('Static file cache cleared', 'success');
        },
        
        // Setup event listeners
        setupEventListeners() {
            // Listen for page visibility changes
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden && this.state.connected) {
                    this.log('Page became visible - checking for updates');
                    this.checkForUpdates();
                }
            });
            
            // Listen for window focus
            window.addEventListener('focus', () => {
                if (this.state.connected) {
                    this.log('Window focused - checking for updates');
                    this.checkForUpdates();
                }
            });
            
            // Setup keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                // Ctrl+R to manually refresh
                if (e.ctrlKey && e.key === 'r') {
                    e.preventDefault();
                    this.manualRefresh();
                }
                
                // Ctrl+Shift+R to force refresh
                if (e.ctrlKey && e.shiftKey && e.key === 'R') {
                    e.preventDefault();
                    this.forceRefresh();
                }
            });
        },
        
        // Setup notification system
        setupNotifications() {
            // Create notification container if it doesn't exist
            if (!document.getElementById('yam-notifications')) {
                const container = document.createElement('div');
                container.id = 'yam-notifications';
                container.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 999999;
                    max-width: 400px;
                `;
                document.body.appendChild(container);
            }
        },
        
        // Setup auto-refresh system
        setupAutoRefresh() {
            // Create auto-refresh indicator if it doesn't exist
            if (!document.getElementById('yam-auto-refresh-indicator')) {
                const indicator = document.createElement('div');
                indicator.id = 'yam-auto-refresh-indicator';
                indicator.style.cssText = `
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: rgba(0, 0, 0, 0.8);
                    color: white;
                    padding: 10px 15px;
                    border-radius: 5px;
                    font-size: 12px;
                    z-index: 999999;
                    display: none;
                `;
                indicator.innerHTML = '🔄 Auto-refresh enabled';
                document.body.appendChild(indicator);
            }
        },
        
        // Show notification
        showNotification(message, type = 'info') {
            if (!this.config.notificationsEnabled) return;
            
            const container = document.getElementById('yam-notifications');
            if (!container) return;
            
            const notification = document.createElement('div');
            notification.style.cssText = `
                background: ${this.getNotificationColor(type)};
                color: white;
                padding: 12px 16px;
                margin-bottom: 8px;
                border-radius: 4px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
                animation: slideIn 0.3s ease-out;
                max-width: 100%;
                word-wrap: break-word;
            `;
            
            notification.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span>${this.getNotificationIcon(type)}</span>
                    <span>${message}</span>
                </div>
            `;
            
            container.appendChild(notification);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.style.animation = 'slideOut 0.3s ease-in';
                    setTimeout(() => {
                        if (notification.parentNode) {
                            notification.parentNode.removeChild(notification);
                        }
                    }, 300);
                }
            }, 5000);
        },
        
        // Get notification color
        getNotificationColor(type) {
            const colors = {
                success: '#10b981',
                error: '#ef4444',
                warning: '#f59e0b',
                info: '#3b82f6'
            };
            return colors[type] || colors.info;
        },
        
        // Get notification icon
        getNotificationIcon(type) {
            const icons = {
                success: '✅',
                error: '❌',
                warning: '⚠️',
                info: 'ℹ️'
            };
            return icons[type] || icons.info;
        },
        
        // Update debugger status
        updateDebuggerStatus(data) {
            const indicator = document.getElementById('yam-auto-refresh-indicator');
            if (indicator) {
                if (data.real_time_updates) {
                    indicator.style.display = 'block';
                    indicator.innerHTML = '🔄 Real-time mode active';
                } else {
                    indicator.style.display = 'none';
                }
            }
        },
        
        // Check for updates
        checkForUpdates() {
            if (this.state.socket && this.state.connected) {
                this.state.socket.emit('request_file_update', {
                    timestamp: new Date().toISOString()
                });
            }
        },
        
        // Manual refresh
        manualRefresh() {
            this.log('Manual refresh requested');
            this.showNotification('Manual refresh initiated', 'info');
            window.location.reload();
        },
        
        // Force refresh (clear cache)
        forceRefresh() {
            this.log('Force refresh requested');
            this.showNotification('Force refresh initiated (cache cleared)', 'info');
            
            // Clear cache
            if ('caches' in window) {
                caches.keys().then(names => {
                    names.forEach(name => {
                        caches.delete(name);
                    });
                });
            }
            
            // Force reload
            window.location.reload(true);
        },
        
        // Utility functions
        getFileTypeDisplay(type) {
            const types = {
                template: 'Template',
                static: 'Static',
                python: 'Python',
                other: 'File'
            };
            return types[type] || 'File';
        },
        
        getFileName(path) {
            return path.split('/').pop() || path.split('\\').pop() || path;
        },
        
        getFileExtension(path) {
            return path.split('.').pop().toLowerCase();
        },
        
        // Logging
        log(...args) {
            if (this.config.debugMode) {
                console.log('[YAM Real-Time]', ...args);
            }
        },
        
        // Error logging
        error(...args) {
            console.error('[YAM Real-Time]', ...args);
        }
    };
    
    // Add CSS animations for notifications
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.YAMRealTime.init();
        });
    } else {
        window.YAMRealTime.init();
    }
    
})(); 