/**
 * Session Monitor for YAM Application
 * 
 * Provides client-side session monitoring and management to prevent
 * session timeouts and maintain Socket.IO connection stability.
 */

// Prevent duplicate declarations
if (typeof window.SessionMonitor !== 'undefined') {
    console.log('SessionMonitor already exists, skipping initialization');
} else {
    class SessionMonitor {
        constructor() {
            this.isInitialized = false;
            this.isConnected = false;
            this.socket = null;
            this.sessionCheckTimer = null;
            this.heartbeatTimer = null;
            this.lastActivity = Date.now();
            // Track the last time we actually sent an /api/session/activity update
            this._lastSessionUpdate = 0; // epoch ms
            this._MIN_SESSION_UPDATE_INTERVAL = 3000; // 3 seconds
            this.warningThreshold = 300; // 5 minutes
            this.healthCheckInterval = 30000; // 30 seconds
            this.heartbeatInterval = 60000; // 1 minute
            this.healthCheckDebounce = 5000; // 5 seconds
            this.lastHealthCheck = 0;
            this.retryCount = 0;
            this.maxRetries = 3;
            this.retryDelay = 5000; // 5 seconds
            this.connectionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            // Resource management
            this.requestQueue = [];
            this.isProcessingQueue = false;
            this.maxConcurrentRequests = 2;
            this.activeRequests = 0;
        }

        init() {
            if (this.isInitialized) {
                console.log('Session Monitor already initialized');
                return;
            }

            console.log('Initializing Session Monitor...');
            
            try {
                this.initSocketIO();
                this.startSessionMonitoring();
                this.startHeartbeat();
                this.trackUserActivity();
                this.handlePageVisibility();
                
                this.isInitialized = true;
                console.log('Session Monitor initialized successfully');
            } catch (error) {
                console.error('Error initializing Session Monitor:', error);
            }
        }

        initSocketIO() {
            try {
                // Initialize Socket.IO with resource management
                this.socket = io({
                    transports: ['polling'],
                    upgrade: false,
                    rememberUpgrade: false,
                    timeout: 20000,
                    forceNew: true
                });

                this.socket.on('connect', () => {
                    console.log('Socket.IO connected for session monitoring');
                    this.isConnected = true;
                    this.retryCount = 0;
                });

                this.socket.on('disconnect', () => {
                    console.log('Socket.IO disconnected');
                    this.isConnected = false;
                });

                this.socket.on('connect_error', (error) => {
                    console.warn('Socket.IO connection error:', error);
                    this.isConnected = false;
                });

            } catch (error) {
                console.warn('Socket.IO initialization failed:', error);
            }
        }

        startSessionMonitoring() {
            // Clear existing timer
            if (this.sessionCheckTimer) {
                clearInterval(this.sessionCheckTimer);
            }

            // Start session health monitoring with reduced frequency
            this.sessionCheckTimer = setInterval(() => {
                this.checkSessionHealth();
            }, this.healthCheckInterval);
        }

        startHeartbeat() {
            // Clear existing timer
            if (this.heartbeatTimer) {
                clearInterval(this.heartbeatTimer);
            }

            // Start heartbeat with reduced frequency
            this.heartbeatTimer = setInterval(() => {
                this.sendHeartbeat();
            }, this.heartbeatInterval);
        }

        stopHeartbeat() {
            if (this.heartbeatTimer) {
                clearInterval(this.heartbeatTimer);
                this.heartbeatTimer = null;
            }
        }

        sendHeartbeat() {
            // Only send heartbeat if connected and not too frequent
            if (this.isConnected && this.socket) {
                try {
                    this.socket.emit('heartbeat', {
                        timestamp: Date.now(),
                        connectionId: this.connectionId
                    });
                } catch (error) {
                    console.warn('Heartbeat error:', error);
                }
            }
        }

        // Resource-managed request queue
        async queueRequest(requestFn) {
            return new Promise((resolve, reject) => {
                this.requestQueue.push({ requestFn, resolve, reject });
                this.processQueue();
            });
        }

        async processQueue() {
            if (this.isProcessingQueue || this.activeRequests >= this.maxConcurrentRequests) {
                return;
            }

            this.isProcessingQueue = true;

            while (this.requestQueue.length > 0 && this.activeRequests < this.maxConcurrentRequests) {
                const { requestFn, resolve, reject } = this.requestQueue.shift();
                this.activeRequests++;

                try {
                    const result = await requestFn();
                    resolve(result);
                } catch (error) {
                    reject(error);
                } finally {
                    this.activeRequests--;
                }

                // Add delay between requests to prevent resource exhaustion
                if (this.requestQueue.length > 0) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
            }

            this.isProcessingQueue = false;

            // Continue processing if there are more items
            if (this.requestQueue.length > 0) {
                setTimeout(() => this.processQueue(), 200);
            }
        }

        async checkSessionHealth() {
            // Check if we have a session coordinator
            if (window.sessionCoordinator && window.sessionCoordinator.isActive()) {
                try {
                    const healthStatus = await window.sessionCoordinator.checkHealth();
                    if (healthStatus.healthy) {
                        console.log('Session health check passed via coordinator');
                        return;
                    }
                } catch (error) {
                    console.warn('Session coordinator check failed:', error);
                }
            }
            
            // Fallback to direct check if coordinator not available
            // Debounce health checks to prevent rapid successive calls
            const now = Date.now();
            if (now - this.lastHealthCheck < this.healthCheckDebounce) {
                return;
            }
            this.lastHealthCheck = now;
            
            try {
                const response = await this.queueRequest(async () => {
                    return fetch('/api/session/time-remaining', {
                        headers: {
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'X-Connection-ID': this.connectionId
                        },
                        signal: AbortSignal.timeout(10000) // 10 second timeout
                    });
                });
                
                if (response.ok) {
                    try {
                        const data = await response.json();
                        
                        // Ensure data has required fields with fallbacks
                        const success = data.success !== undefined ? data.success : true;
                        const timeRemaining = data.time_remaining_seconds || 0;
                        const message = data.message || data.error || null;
                        
                        if (success && timeRemaining >= 0) {
                            // Show warning if session is about to expire
                            if (timeRemaining > 0 && timeRemaining < this.warningThreshold) {
                                this.showSessionWarning(timeRemaining);
                            }
                            
                            // Extend session if needed (but not too frequently)
                            if (timeRemaining < 600 && this.retryCount < this.maxRetries) { // Less than 10 minutes
                                await this.extendSession();
                            }
                            
                            // Reset retry count on success
                            this.retryCount = 0;
                            
                            // Log successful health check
                            console.log(`Session health check passed: ${timeRemaining}s remaining`);
                        } else {
                            console.warn('Session health check failed:', message || 'Unknown error');
                            this.handleSessionError();
                        }
                    } catch (jsonError) {
                        console.error('Error parsing session health response:', jsonError);
                        const responseText = await response.text();
                        console.log('Raw response:', responseText.substring(0, 200));
                        
                        // Don't treat JSON parsing errors as session failures
                        // The session might still be valid
                    }
                } else if (response.status === 401) {
                    console.log('Session health check: User not authenticated (401)');
                    this.handleSessionError();
                } else {
                    console.error('Session health check failed with status:', response.status);
                    this.handleSessionError();
                }
            } catch (error) {
                console.error('Error checking session health:', error);
                this.handleSessionError();
            }
        }

        handleSessionError() {
            this.retryCount++;
            
            if (this.retryCount >= this.maxRetries) {
                console.error('Session health check failed after maximum retries');
                this.showSessionError();
            } else {
                // Exponential backoff
                const delay = this.retryDelay * Math.pow(2, this.retryCount - 1);
                setTimeout(() => this.checkSessionHealth(), delay);
            }
        }

        showSessionError() {
            // Create or update error notification
            let error = document.getElementById('session-error');
            if (!error) {
                error = document.createElement('div');
                error.id = 'session-error';
                error.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #f44336;
                    color: white;
                    padding: 15px 20px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    z-index: 10000;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    font-size: 14px;
                    max-width: 300px;
                `;
                document.body.appendChild(error);
            }
            
            error.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="bi bi-exclamation-triangle-fill" style="font-size: 16px;"></i>
                    <div>
                        <div style="font-weight: 600; margin-bottom: 5px;">Session Error</div>
                        <div style="font-size: 12px; opacity: 0.9;">
                            Unable to verify session status. Please refresh the page.
                            <button onclick="window.location.reload()" 
                                    style="background: rgba(255,255,255,0.2); border: none; color: white; 
                                           padding: 4px 8px; border-radius: 4px; margin-left: 8px; cursor: pointer;">
                                Refresh
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            // Auto-hide after 30 seconds
            setTimeout(() => {
                if (error && error.parentNode) {
                    error.parentNode.removeChild(error);
                }
            }, 30000);
        }
        
        async extendSession() {
            try {
                const response = await this.queueRequest(async () => {
                    return fetch('/api/session/extend', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'X-Connection-ID': this.connectionId
                        },
                        signal: AbortSignal.timeout(10000) // 10 second timeout
                    });
                });
                
                if (response.ok) {
                    try {
                        const data = await response.json();
                        if (data.success) {
                            console.log('Session extended successfully');
                            this.lastActivity = Date.now();
                            this.retryCount = 0; // Reset retry count on success
                        } else {
                            console.warn('Session extension failed:', data.message || data.error);
                        }
                    } catch (jsonError) {
                        console.error('Error parsing session extension response:', jsonError);
                        const responseText = await response.text();
                        console.log('Raw response:', responseText.substring(0, 200));
                    }
                } else {
                    console.error('Session extension failed with status:', response.status);
                }
            } catch (error) {
                console.error('Error extending session:', error);
            }
        }
        
        showSessionWarning(timeRemaining) {
            const minutes = Math.ceil(timeRemaining / 60);
            
            // Create or update warning notification
            let warning = document.getElementById('session-warning');
            if (!warning) {
                warning = document.createElement('div');
                warning.id = 'session-warning';
                warning.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #ff6b35;
                    color: white;
                    padding: 15px 20px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    z-index: 10000;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    font-size: 14px;
                    max-width: 300px;
                `;
                document.body.appendChild(warning);
            }
            
            warning.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="bi bi-exclamation-triangle-fill" style="font-size: 16px;"></i>
                    <div>
                        <div style="font-weight: 600; margin-bottom: 5px;">Session Expiring Soon</div>
                        <div style="font-size: 12px; opacity: 0.9;">
                            Your session will expire in ${minutes} minute${minutes !== 1 ? 's' : ''}.
                            <button onclick="window.sessionMonitor.extendSession()" 
                                    style="background: rgba(255,255,255,0.2); border: none; color: white; 
                                           padding: 4px 8px; border-radius: 4px; margin-left: 8px; cursor: pointer;">
                                Extend
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            // Auto-hide after 10 seconds
            setTimeout(() => {
                if (warning && warning.parentNode) {
                    warning.parentNode.removeChild(warning);
                }
            }, 10000);
        }
        
        trackUserActivity() {
            const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
            
            // Debounce activity tracking to prevent excessive updates
            let activityTimeout;
            
            activityEvents.forEach(event => {
                document.addEventListener(event, () => {
                    this.lastActivity = Date.now();
                    
                    // Clear existing timeout
                    if (activityTimeout) {
                        clearTimeout(activityTimeout);
                    }
                    
                    // Update activity after a short delay to batch updates
                    activityTimeout = setTimeout(() => {
                        this.updateActivity();
                    }, 1000);
                }, { passive: true });
            });
        }

        async updateActivity() {
            // Throttle: avoid spamming the backend with activity pings
            const now = Date.now();
            if (now - this._lastSessionUpdate < this._MIN_SESSION_UPDATE_INTERVAL) {
                return; // too soon since last POST
            }

            try {
                await this.queueRequest(async () => {
                    return fetch('/api/session/activity', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'X-Connection-ID': this.connectionId
                        },
                        signal: AbortSignal.timeout(5000) // 5 second timeout
                    });
                });
                this._lastSessionUpdate = Date.now();
            } catch (error) {
                console.warn('Activity update failed:', error);
            }
        }
        
        handlePageVisibility() {
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'visible') {
                    // Page became visible, check session health with delay
                    setTimeout(() => {
                        this.checkSessionHealth();
                    }, 1000);
                    
                    // Reconnect Socket.IO if needed
                    if (this.socket && !this.isConnected) {
                        this.socket.connect();
                    }
                }
            });
        }
        
        destroy() {
            if (this.sessionCheckTimer) {
                clearInterval(this.sessionCheckTimer);
                this.sessionCheckTimer = null;
            }
            
            if (this.heartbeatTimer) {
                clearInterval(this.heartbeatTimer);
                this.heartbeatTimer = null;
            }
            
            if (this.socket) {
                this.socket.disconnect();
                this.socket = null;
            }
            
            // Clear request queue
            this.requestQueue = [];
            this.isProcessingQueue = false;
            this.activeRequests = 0;
            
            this.isInitialized = false;
            console.log('Session Monitor destroyed');
        }
    }

    // Initialize session monitor when DOM is ready
    let sessionMonitor;
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.sessionMonitor) {
            sessionMonitor = new SessionMonitor();
            window.sessionMonitor = sessionMonitor;
        }
    });

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        if (window.sessionMonitor) {
            window.sessionMonitor.destroy();
        }
    });

    // Export for global access
    window.SessionMonitor = SessionMonitor;
}

// === Browser Console Session Monitor ===
// This function can be run directly in the browser console to monitor session health
window.monitorSessionHealth = function(intervalSeconds = 30, durationMinutes = 5) {
    console.log('🔍 Starting browser-based session health monitoring...');
    console.log(`⏱️  Monitoring for ${durationMinutes} minutes, checking every ${intervalSeconds} seconds`);
    
    const startTime = Date.now();
    const endTime = startTime + (durationMinutes * 60 * 1000);
    let checkCount = 0;
    
    const monitor = async () => {
        const now = new Date();
        const elapsed = Math.floor((now.getTime() - startTime) / 1000);
        const remaining = Math.floor((endTime - now.getTime()) / 1000);
        
        checkCount++;
        console.log(`\n[${now.toLocaleTimeString()}] 🔍 Session Health Check #${checkCount} (${elapsed}s elapsed, ${remaining}s remaining)`);
        
        try {
            // Check session health
            const healthResponse = await fetch('/api/health', {
                headers: { 'Accept': 'application/json' }
            });
            if (healthResponse.ok) {
                try {
                    const healthData = await healthResponse.json();
                    console.log(`✅ Health: ${healthData.session_healthy ? 'HEALTHY' : 'UNHEALTHY'} (Client: ${healthData.client_type})`);
                } catch (e) {
                    console.log(`❌ Health check - Invalid JSON response`);
                }
            } else {
                console.log(`❌ Health check failed: ${healthResponse.status}`);
            }
            
            // Check session time remaining
            const timeResponse = await fetch('/api/session/time-remaining', {
                headers: { 'Accept': 'application/json' }
            });
            if (timeResponse.ok) {
                try {
                    const timeData = await timeResponse.json();
                    const minutes = Math.floor(timeData.time_remaining_seconds / 60);
                    const seconds = timeData.time_remaining_seconds % 60;
                    console.log(`⏰ Session time: ${minutes}m ${seconds}s remaining`);
                } catch (e) {
                    console.log(`❌ Session time - Invalid JSON response`);
                }
            } else if (timeResponse.status === 401) {
                console.log(`❌ Session time: 401 Unauthorized (not logged in)`);
            } else {
                console.log(`❌ Session time check failed: ${timeResponse.status}`);
            }
            
            // Check Socket.IO status
            const socketResponse = await fetch('/api/socketio-test', {
                headers: { 'Accept': 'application/json' }
            });
            if (socketResponse.ok) {
                try {
                    const socketData = await socketResponse.json();
                    console.log(`🔌 Socket.IO: ${socketData.socketio_configured ? 'CONFIGURED' : 'NOT CONFIGURED'}`);
                } catch (e) {
                    console.log(`❌ Socket.IO - Invalid JSON response`);
                }
            } else {
                console.log(`❌ Socket.IO check failed: ${socketResponse.status}`);
            }
            
        } catch (error) {
            console.error(`❌ Monitoring error: ${error.message}`);
        }
        
        console.log('─'.repeat(50));
        
        // Continue monitoring if time hasn't expired
        if (now.getTime() < endTime) {
            setTimeout(monitor, intervalSeconds * 1000);
        } else {
            console.log('✅ Session monitoring completed!');
            console.log(`📊 Total checks performed: ${checkCount}`);
        }
    };
    
    // Start monitoring
    monitor();
    
    // Return a function to stop monitoring
    return () => {
        console.log('🛑 Session monitoring stopped by user');
    };
};

// === Quick Session Status Check ===
// This function provides a quick one-time status check
window.checkSessionStatus = async function() {
    console.log('🔍 Quick session status check...');
    
    try {
        const healthResponse = await fetch('/api/health', {
            headers: { 'Accept': 'application/json' }
        });
        const timeResponse = await fetch('/api/session/time-remaining', {
            headers: { 'Accept': 'application/json' }
        });
        const socketResponse = await fetch('/api/socketio-test', {
            headers: { 'Accept': 'application/json' }
        });
        
        console.log('📊 Session Status Summary:');
        console.log('─'.repeat(40));
        
        if (healthResponse.ok) {
            try {
                const healthData = await healthResponse.json();
                console.log(`✅ Health: ${healthData.session_healthy ? 'HEALTHY' : 'UNHEALTHY'}`);
            } catch (e) {
                console.log(`❌ Health: Invalid JSON response`);
            }
        } else {
            console.log(`❌ Health: Failed (${healthResponse.status})`);
        }
        
        if (timeResponse.ok) {
            try {
                const timeData = await timeResponse.json();
                const minutes = Math.floor(timeData.time_remaining_seconds / 60);
                const seconds = timeData.time_remaining_seconds % 60;
                console.log(`⏰ Time: ${minutes}m ${seconds}s remaining`);
            } catch (e) {
                console.log(`❌ Time: Invalid JSON response`);
            }
        } else if (timeResponse.status === 401) {
            console.log(`❌ Time: Not authenticated (401)`);
        } else {
            console.log(`❌ Time: Failed (${timeResponse.status})`);
        }
        
        if (socketResponse.ok) {
            try {
                const socketData = await socketResponse.json();
                console.log(`🔌 Socket.IO: ${socketData.socketio_configured ? 'CONFIGURED' : 'NOT CONFIGURED'}`);
            } catch (e) {
                console.log(`❌ Socket.IO: Invalid JSON response`);
            }
        } else {
            console.log(`❌ Socket.IO: Failed (${socketResponse.status})`);
        }
        
        console.log('─'.repeat(40));
        
    } catch (error) {
        console.error(`❌ Status check error: ${error.message}`);
    }
};

// === Usage Instructions ===
console.log('🔧 Session Monitor Functions Available:');
console.log('• monitorSessionHealth(intervalSeconds, durationMinutes) - Monitor session for specified duration');
console.log('• checkSessionStatus() - Quick one-time status check');
console.log('');
console.log('💡 Examples:');
console.log('• monitorSessionHealth(30, 5) - Monitor for 5 minutes, check every 30 seconds');
console.log('• checkSessionStatus() - Quick status check');
console.log('• monitorSessionHealth(60, 10) - Monitor for 10 minutes, check every minute'); 