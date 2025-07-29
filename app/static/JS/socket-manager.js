/**
 * YAM Socket Manager
 * Handles all socket.io connections, user presence, and heartbeat management
 * Enhanced for comprehensive real-time user presence tracking
 */

// Prevent duplicate initialization
if (typeof window.yamSocketManager !== 'undefined') {
    console.log('YAM Socket Manager already exists, skipping initialization');
} else {
    class YAMSocketManager {
    constructor() {
        this.socket = null;
        this.heartbeatInterval = null;
        this.activityInterval = null;
        this.inactivityTimer = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this.isConnected = false;
        this.isAuthenticated = false;
        this.userId = null;
        this.lastActivity = Date.now();
        this.lastHeartbeat = null;
        this.isPageVisible = true;
        this.hasUserInteracted = false;
        this.isInitialized = false;
        
        // Enhanced configuration - OPTIMIZED FOR PERFORMANCE
        this.config = {
            heartbeatInterval: 120000,  // 2 minutes (increased from 45 seconds)
            activityInterval: 300000,   // 5 minutes (increased from 1 minute)
            inactivityTimeout: 600000,  // 10 minutes (increased from 5)
            reconnectDelay: 1000,       // 1 second
            maxReconnectAttempts: 15,   // More attempts (increased from 10)
            activityTimeout: 600000,    // 10 minutes (increased from 5)
            visibilityHeartbeat: 60000  // 1 minute when page visible (increased from 15 seconds)
        };
        
        // Activity types to track - OPTIMIZED (removed mousemove to reduce spam)
        this.activityTypes = ['click', 'keydown', 'scroll', 'touchstart', 'focus'];
        this.lastActivityType = null;
        this.activityCount = 0;
        
        // Event handlers
        this.eventHandlers = {
            connect: [],
            disconnect: [],
            onlineUsersUpdate: [],
            adminDashboardUpdate: [],
            presenceUpdate: [],
            heartbeatAck: [],
            error: []
        };
        
        this.init();
    }
    
    init() {
        if (this.isInitialized) {
            console.log('YAM Socket Manager already initialized');
            return;
        }
        
        // Initialize socket connection
        this.connect();
        
        // Set up enhanced activity tracking
        this.setupEnhancedActivityTracking();
        
        // Set up page visibility tracking
        this.setupVisibilityTracking();
        
        // Set up beforeunload handler
        this.setupBeforeUnload();
        
        // Set up inactivity detection
        this.setupInactivityDetection();
        
        this.isInitialized = true;
        console.log('YAM Socket Manager initialized with enhanced presence features');
    }
    
    connect() {
        // Prevent duplicate connections
        if (this.socket && this.socket.connected) {
            console.log('Socket already connected, skipping duplicate connection');
            return;
        }
        
        if (this.socket) {
            this.socket.disconnect();
        }
        
        // Generate unique connection ID
        const connectionId = 'socket_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        this.socket = io({
            withCredentials: true,
            reconnection: true,
            reconnectionAttempts: this.config.maxReconnectAttempts,
            reconnectionDelay: this.config.reconnectDelay,
            reconnectionDelayMax: 30000, // Increased max delay for better backoff
            timeout: 180000, // Increased timeout to 3 minutes for better stability
            transports: ['polling', 'websocket'], // Allow both transports for better compatibility
            forceNew: false,
            autoConnect: true,
            upgrade: true, // Allow transport upgrade
            rememberUpgrade: true, // Remember transport preference
            maxReconnectionAttempts: this.config.maxReconnectAttempts,
            query: {
                connection_id: connectionId,
                timestamp: Date.now()
            }
        });
        
        this.setupEnhancedSocketEventHandlers();
        console.log('Enhanced socket connection initialized with improved stability, ID:', connectionId);
    }
    
    setupEnhancedSocketEventHandlers() {
        if (!this.socket) return;
        
        // Connection events
        this.socket.on('connect', () => {
            console.log('Connected to YAM server');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = this.config.reconnectDelay;
            
            // Send initial presence information
            this.sendPresenceUpdate('connected');
            
            // Start enhanced heartbeat
            this.startEnhancedHeartbeat();
            
            // Start activity tracking
            this.startActivityTracking();
            
            // Update connection status in UI
            this.updateConnectionUI(true);
            
            // Emit events
            this.emitEvent('connect');
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('Disconnected from YAM server:', reason);
            this.isConnected = false;
            
            // Stop intervals
            this.stopEnhancedHeartbeat();
            this.stopActivityTracking();
            
            // Update connection status in UI
            this.updateConnectionUI(false);
            
            // Handle reconnection based on disconnect reason
            if (reason === 'io server disconnect') {
                console.log('Server initiated disconnect - will attempt reconnection');
                this.scheduleReconnect();
            } else if (reason === 'transport close') {
                console.log('Transport closed - will attempt reconnection');
                this.scheduleReconnect();
            } else if (reason === 'ping timeout') {
                console.log('Ping timeout - will attempt reconnection');
                this.scheduleReconnect();
            } else if (reason === 'transport error') {
                console.log('Transport error - will attempt reconnection');
                this.scheduleReconnect();
            } else {
                console.log('Disconnect reason:', reason, '- will attempt reconnection');
                this.scheduleReconnect();
            }
            
            // Emit events
            this.emitEvent('disconnect', reason);
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Socket connection error:', error);
            if (error && error.message && error.message.includes('timeout')) {
                this.reconnectAttempts = (this.reconnectAttempts || 0) + 1;
                if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
                    this.showConnectionError('Connection timed out repeatedly. Please check your network or refresh the page.');
                }
            }
            this.emitEvent('error', error);
        });
        
        // Enhanced presence events
        this.socket.on('online_users_update', (users) => {
            console.log('Online users update received:', users.length, 'users');
            this.emitEvent('onlineUsersUpdate', users);
            
            // Update UI if not handled by page-specific code
            if (typeof window.updateOnlineUsers === 'function' && !window.outageHandlersInitialized) {
                window.updateOnlineUsers(users);
            }
        });
        
        this.socket.on('presence_stats_update', (stats) => {
            console.log('Presence stats update received:', stats);
            this.emitEvent('presenceUpdate', stats);
        });
        
        this.socket.on('heartbeat_ack', (data) => {
            console.debug('Heartbeat acknowledged:', data);
            this.lastHeartbeat = new Date();
            this.emitEvent('heartbeatAck', data);
            
            // Update heartbeat indicator in UI
            this.updateHeartbeatUI();
        });
        
        this.socket.on('presence_connected', (data) => {
            console.log('Presence connected:', data);
            this.isAuthenticated = true;
            this.userId = data.user_id;
        });
        
        // Admin dashboard events
        this.socket.on('admin_dashboard_data', (data) => {
            console.log('Admin dashboard update received');
            this.emitEvent('adminDashboardUpdate', data);
            
            if (typeof window.updateAdminDashboard === 'function' && !window.outageHandlersInitialized) {
                window.updateAdminDashboard(data);
            }
        });
        
        // Error events
        this.socket.on('error', (error) => {
            console.error('Socket error received:', error);
            this.emitEvent('error', error);
        });
        
        // Force offline notification
        this.socket.on('force_offline_success', (data) => {
            console.log('User forced offline:', data);
            if (data.user_id === this.userId) {
                this.handleForcedOffline();
            }
        });
    }
    
    startEnhancedHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }
        
        this.heartbeatInterval = setInterval(() => {
            if (this.isConnected) {
                // Send heartbeat with activity information
                const heartbeatData = {
                    timestamp: Date.now(),
                    last_activity: this.lastActivity,
                    activity_type: this.lastActivityType,
                    activity_count: this.activityCount,
                    page_visible: this.isPageVisible,
                    user_interacted: this.hasUserInteracted
                };
                
                this.socket.emit('heartbeat', heartbeatData);
                console.debug('Enhanced heartbeat sent with activity data');
                
                // Reset activity count
                this.activityCount = 0;
            }
        }, this.config.heartbeatInterval);
        
        console.log('Enhanced heartbeat started');
    }
    
    stopEnhancedHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
            console.log('Enhanced heartbeat stopped');
        }
    }
    
    startActivityTracking() {
        if (this.activityInterval) {
            clearInterval(this.activityInterval);
        }
        
        // Track user activity more frequently when page is visible
        const interval = this.isPageVisible ? this.config.visibilityHeartbeat : this.config.activityInterval;
        
        this.activityInterval = setInterval(() => {
            if (this.isConnected && this.hasRecentActivity()) {
                this.sendActivityUpdate();
            }
        }, interval);
        
        console.log('Activity tracking started');
    }
    
    stopActivityTracking() {
        if (this.activityInterval) {
            clearInterval(this.activityInterval);
            this.activityInterval = null;
            console.log('Activity tracking stopped');
        }
    }
    
    setupEnhancedActivityTracking() {
        // Track multiple types of user activity
        const activityHandler = (event) => {
            this.lastActivity = Date.now();
            this.lastActivityType = event.type;
            this.activityCount++;
            this.hasUserInteracted = true;
            
            // Reset inactivity timer
            this.resetInactivityTimer();
            
            console.debug(`Activity detected: ${event.type}`);
        };
        
        // Add listeners for all activity types
        this.activityTypes.forEach(eventType => {
            document.addEventListener(eventType, activityHandler, { passive: true });
        });
        
        // Track focus/blur events specifically
        window.addEventListener('focus', () => {
            this.lastActivity = Date.now();
            this.lastActivityType = 'focus';
            this.sendPresenceUpdate('active');
        });
        
        window.addEventListener('blur', () => {
            this.sendPresenceUpdate('inactive');
        });
        
        console.log('Enhanced activity tracking setup completed');
    }
    
    setupVisibilityTracking() {
        // Enhanced visibility tracking
        document.addEventListener('visibilitychange', () => {
            this.isPageVisible = !document.hidden;
            
            if (this.isPageVisible) {
                console.log('Page became visible');
                this.lastActivity = Date.now();
                this.sendPresenceUpdate('visible');
                
                // Start more frequent heartbeats when visible
                this.startActivityTracking();
            } else {
                console.log('Page became hidden');
                this.sendPresenceUpdate('hidden');
                
                // Reduce heartbeat frequency when hidden
                this.startActivityTracking();
            }
        });
        
        // Handle focus/blur on window
        window.addEventListener('focus', () => {
            console.log('Window focused');
            this.isPageVisible = true;
            this.sendPresenceUpdate('focused');
        });
        
        window.addEventListener('blur', () => {
            console.log('Window blurred');
            this.sendPresenceUpdate('blurred');
        });
    }
    
    setupBeforeUnload() {
        // Enhanced beforeunload handling
        window.addEventListener('beforeunload', (event) => {
            console.log('Page unloading - sending offline status');
            
            // Send synchronous offline status
            if (this.isConnected) {
                // Use sendBeacon for reliable delivery during unload
                const data = JSON.stringify({
                    type: 'user_offline',
                    user_id: this.userId,
                    timestamp: Date.now(),
                    reason: 'page_unload'
                });
                
                // Try sendBeacon first (most reliable)
                if (navigator.sendBeacon) {
                    navigator.sendBeacon('/api/user/offline', data);
                } else {
                    // Fallback to synchronous socket emit
                    this.socket.emit('force_offline', { user_id: this.userId });
                }
            }
        });
        
        // Handle page visibility for mobile browsers
        document.addEventListener('pagehide', () => {
            console.log('Page hidden - potential app closure');
            this.sendPresenceUpdate('pagehide');
        });
        
        document.addEventListener('pageshow', () => {
            console.log('Page shown - app returned');
            this.sendPresenceUpdate('pageshow');
        });
    }
    
    setupInactivityDetection() {
        this.resetInactivityTimer();
    }
    
    resetInactivityTimer() {
        if (this.inactivityTimer) {
            clearTimeout(this.inactivityTimer);
        }
        
        this.inactivityTimer = setTimeout(() => {
            console.log('User inactive for extended period');
            this.sendPresenceUpdate('inactive_timeout');
        }, this.config.inactivityTimeout);
    }
    
    sendPresenceUpdate(status) {
        if (this.isConnected) {
            const presenceData = {
                status: status,
                timestamp: Date.now(),
                last_activity: this.lastActivity,
                page_visible: this.isPageVisible,
                user_agent: navigator.userAgent
            };
            
            this.socket.emit('presence_update', presenceData);
            console.debug(`Presence update sent: ${status}`);
        }
    }
    
    sendActivityUpdate() {
        if (this.isConnected) {
            const activityData = {
                type: 'activity_update',
                timestamp: Date.now(),
                last_activity: this.lastActivity,
                activity_type: this.lastActivityType,
                activity_count: this.activityCount,
                page_visible: this.isPageVisible
            };
            
            this.socket.emit('user_activity', activityData);
            console.debug('Activity update sent');
        }
    }
    
    hasRecentActivity() {
        const timeSinceActivity = Date.now() - this.lastActivity;
        return timeSinceActivity < this.config.activityTimeout;
    }
    
    updateConnectionUI(isConnected, message) {
        // Update connection status indicator
        if (typeof window.updateConnectionStatus === 'function') {
            window.updateConnectionStatus(isConnected, message);
        }
    }
    
    updateHeartbeatUI() {
        // Update heartbeat indicator
        if (typeof window.updateLastHeartbeatTime === 'function') {
            window.updateLastHeartbeatTime();
        }
    }
    
    handleForcedOffline() {
        console.log('User has been forced offline by admin');
        
        // Show notification
        if (typeof window.showToast === 'function') {
            window.showToast('You have been signed out by an administrator', 'warning');
        }
        
        // Redirect to login after delay
        setTimeout(() => {
            window.location.href = '/auth/login';
        }, 3000);
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts < this.config.maxReconnectAttempts) {
            this.reconnectAttempts++;
            
            // Exponential backoff with jitter to prevent thundering herd
            const baseDelay = this.reconnectDelay;
            const maxDelay = 30000; // 30 seconds max
            const jitter = Math.random() * 0.1; // 10% jitter
            const delay = Math.min(baseDelay * Math.pow(2, this.reconnectAttempts - 1) * (1 + jitter), maxDelay);
            
            console.log(`Reconnect attempt ${this.reconnectAttempts}/${this.config.maxReconnectAttempts} in ${Math.round(delay)}ms`);
            
            // Show reconnecting status to user
            this.updateConnectionUI(false, `Reconnecting... (${this.reconnectAttempts}/${this.config.maxReconnectAttempts})`);
            
            setTimeout(() => {
                if (!this.isConnected) {
                    console.log('Attempting to reconnect...');
                    this.connect();
                }
            }, delay);
        } else {
            console.error('Max reconnect attempts reached');
            this.updateConnectionUI(false, 'Connection failed - please refresh the page');
            this.showConnectionError('Unable to connect to the server after multiple attempts. Please refresh the page or check your network connection.');
        }
    }
    
    showConnectionError(message) {
        // Display a user-friendly error message (customize as needed)
        alert(message || 'Unable to connect to the server. Please try again later.');
    }
    
    // Public API methods
    getOnlineUsers() {
        if (this.isConnected) {
            this.socket.emit('get_online_users');
        }
    }
    
    getUserStatus(userIds) {
        if (this.isConnected) {
            this.socket.emit('user_status_request', { user_ids: userIds });
        }
    }
    
    requestAdminDashboard() {
        if (this.isConnected) {
            this.socket.emit('admin_dashboard_request');
        }
    }
    
    forceUserOffline(userId) {
        if (this.isConnected) {
            this.socket.emit('force_offline', { user_id: userId });
        }
    }
    
    getPresenceStats() {
        if (this.isConnected) {
            this.socket.emit('get_presence_stats');
        }
    }
    
    triggerManualCleanup() {
        if (this.isConnected) {
            this.socket.emit('manual_presence_cleanup');
        }
    }
    
    // Event handling
    on(event, handler) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(handler);
    }
    
    off(event, handler) {
        if (this.eventHandlers[event]) {
            const index = this.eventHandlers[event].indexOf(handler);
            if (index > -1) {
                this.eventHandlers[event].splice(index, 1);
            }
        }
    }
    
    emitEvent(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }
    
    // Status getters
    isUserOnline() {
        return this.isConnected && this.isAuthenticated;
    }
    
    getConnectionStatus() {
        return {
            connected: this.isConnected,
            authenticated: this.isAuthenticated,
            userId: this.userId,
            lastActivity: this.lastActivity,
            lastHeartbeat: this.lastHeartbeat,
            reconnectAttempts: this.reconnectAttempts
        };
    }
    
    destroy() {
        // Clean up all intervals and event listeners
        this.stopEnhancedHeartbeat();
        this.stopActivityTracking();
        
        if (this.inactivityTimer) {
            clearTimeout(this.inactivityTimer);
        }
        
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        
        console.log('YAM Socket Manager destroyed');
    }
}

    // Global instance
    window.yamSocketManager = new YAMSocketManager();

    // Export for modules
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = YAMSocketManager;
    }
} 