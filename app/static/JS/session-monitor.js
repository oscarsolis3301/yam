/**
 * YAM Enhanced Session Monitor - SPAM-FREE VERSION
 * Prevents disconnections and maintains stable user sessions
 * Enhanced with proper throttling and duplicate prevention
 */

// Global throttling to prevent ANY session activity spam
window.YAM_SESSION_ACTIVITY_THROTTLE = window.YAM_SESSION_ACTIVITY_THROTTLE || {
    lastCall: 0,
    minInterval: 600000, // 10 minutes minimum between calls
    isBlocked: false
};

// Global function to safely call session activity (with extreme throttling)
window.safeUpdateSessionActivity = function() {
    const now = Date.now();
    const throttle = window.YAM_SESSION_ACTIVITY_THROTTLE;
    
    if (throttle.isBlocked || (now - throttle.lastCall) < throttle.minInterval) {
        console.debug('Session activity update blocked by global throttle');
        return Promise.resolve();
    }
    
    throttle.lastCall = now;
    throttle.isBlocked = true;
    
    // Unblock after minimum interval
    setTimeout(() => {
        throttle.isBlocked = false;
    }, throttle.minInterval);
    
    try {
        return fetch('/api/session/activity', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                timestamp: now,
                throttled: true
            })
        });
    } catch (error) {
        console.debug('Session activity error (non-critical):', error);
        return Promise.resolve();
    }
};

// Prevent duplicate session monitors from running
if (typeof window.YAMSessionMonitor !== 'undefined') {
    console.log('YAMSessionMonitor already exists, skipping initialization');
} else {
    
class YAMSessionMonitor {
    constructor() {
        this.sessionCheckInterval = null;
        this.sessionExtendInterval = null;
        this.heartbeatInterval = null;
        this.lastSessionCheck = Date.now();
        this.sessionHealthStatus = 'unknown';
        this.isMonitoring = false;
        this.lastActivity = Date.now();
        this.autoExtendEnabled = true;
        this.connectionId = null;
        this.isConnected = false;
        this.warningShown = false;
        
        // PROPERLY INITIALIZE THROTTLING VARIABLES
        this._lastActivityUpdate = 0;
        this._lastHeartbeat = 0;
        this._lastSessionCheck = 0;
        
        // Configuration for 2-hour sessions - EXTREMELY CONSERVATIVE TO PREVENT SPAM
        this.config = {
            sessionCheckInterval: 1800000,   // Check session every 30 minutes
            sessionExtendInterval: 3600000,  // Extend session every 60 minutes  
            heartbeatInterval: 1800000,      // 30 minute heartbeat
            sessionWarningThreshold: 600,   // Warn when 10 minutes remaining
            sessionCriticalThreshold: 120,   // Critical when 2 minutes remaining
            maxSessionAge: 7200,            // 2 hours max session age
            autoExtendThreshold: 1800,       // Auto-extend when 30 minutes remaining
            gracePeriod: 600                // 10 minute grace period
        };
        
        this.init();
    }
    
    init() {
        // Check if we're on a page that needs session monitoring
        if (this.shouldSkipSessionMonitoring()) {
            console.log('YAM Session Monitor: Skipping session monitoring on this page');
            return;
        }
        
        // Check if session monitor already exists and prevent duplicates
        if (window.yamSessionMonitor) {
            console.log('YAM Session Monitor: Already exists, destroying old instance');
            window.yamSessionMonitor.destroy();
        }
        
        // Generate unique connection ID
        this.connectionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        // Set up global instance
        window.yamSessionMonitor = this;
        
        // Start monitoring with CONSERVATIVE intervals
        this.startMonitoring();
        
        // Set up MINIMAL activity tracking (no session activity calls on events)
        this.setupActivityTracking();
        
        // Set up visibility tracking (no session activity calls)
        this.setupVisibilityTracking();
        
        console.log('YAM Session Monitor: Initialized successfully with ID:', this.connectionId);
    }
    
    shouldSkipSessionMonitoring() {
        // Skip session monitoring on login page and other unauthenticated pages
        const currentPath = window.location.pathname;
        const skipPaths = [
            '/auth/login',
            '/auth/windows-login', 
            '/auth/unauthorized',
            '/login',
            '/signin',
            '/sign-in'
        ];
        
        // Check if current path should skip session monitoring
        for (const skipPath of skipPaths) {
            if (currentPath.includes(skipPath)) {
                return true;
            }
        }
        
        // Check if user is authenticated by looking for auth indicators
        const hasAuthToken = document.cookie.includes('session=') || 
                           document.cookie.includes('yam_session=') ||
                           localStorage.getItem('user_authenticated') === 'true';
        
        // Skip if no authentication indicators found
        if (!hasAuthToken) {
            return true;
        }
        
        return false;
    }
    
    startMonitoring() {
        if (this.isMonitoring) {
            console.log('YAM Session Monitor: Already monitoring');
            return;
        }
        
        this.isMonitoring = true;
        
        // VERY CONSERVATIVE intervals to prevent spam
        this.sessionCheckInterval = setInterval(() => {
            this.checkSessionHealth();
        }, this.config.sessionCheckInterval);
        
        this.sessionExtendInterval = setInterval(() => {
            this.extendSessionIfNeeded();
        }, this.config.sessionExtendInterval);
        
        this.startHeartbeat();
        
        console.log('YAM Session Monitor: Started monitoring with conservative intervals');
    }
    
    stopMonitoring() {
        if (!this.isMonitoring) {
            return;
        }
        
        this.isMonitoring = false;
        
        if (this.sessionCheckInterval) {
            clearInterval(this.sessionCheckInterval);
            this.sessionCheckInterval = null;
        }
        
        if (this.sessionExtendInterval) {
            clearInterval(this.sessionExtendInterval);
            this.sessionExtendInterval = null;
        }
        
        this.stopHeartbeat();
        
        console.log('YAM Session Monitor: Stopped monitoring');
    }
    
    setupActivityTracking() {
        // MINIMAL activity tracking - NEVER call session activity API on events
        const activityEvents = ['click', 'keypress'];
        
        activityEvents.forEach(event => {
            document.addEventListener(event, () => {
                this.lastActivity = Date.now();
                // NO API CALLS HERE - just update timestamp
            }, { passive: true });
        });
        
        // Focus events - NO API CALLS
        window.addEventListener('focus', () => {
            this.lastActivity = Date.now();
            // Just update timestamp, no API calls
        });
        
        window.addEventListener('blur', () => {
            this.lastActivity = Date.now();
            // Just update timestamp, no API calls
        });
    }
    
    setupVisibilityTracking() {
        // Visibility changes - NO API CALLS
        document.addEventListener('visibilitychange', () => {
            this.lastActivity = Date.now();
            // Just update timestamp, no API calls
        });
    }
    
    async checkSessionHealth() {
        // Throttle session health checks
        const now = Date.now();
        if ((now - this._lastSessionCheck) < 300000) { // 5 minutes minimum
            return;
        }
        this._lastSessionCheck = now;
        
        try {
            const response = await fetch('/api/session/time-remaining', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Connection-ID': this.connectionId
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                const timeRemaining = data.time_remaining_seconds || 0;
                
                this.sessionHealthStatus = timeRemaining > 0 ? 'healthy' : 'expired';
                
                if (timeRemaining > 0 && timeRemaining < this.config.sessionWarningThreshold) {
                    this.showSessionWarning(timeRemaining);
                }
                
                if (timeRemaining > 0 && timeRemaining <= this.config.autoExtendThreshold) {
                    await this.extendSession();
                }
                
                if (timeRemaining <= 0) {
                    this.handleSessionExpired();
                }
                
            } else if (response.status === 401) {
                this.handleSessionExpired();
            }
            
        } catch (error) {
            console.debug('Session health check error (non-critical):', error);
        }
    }
    
    async extendSessionIfNeeded() {
        try {
            const response = await fetch('/api/session/time-remaining', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Connection-ID': this.connectionId
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                const timeRemaining = data.time_remaining_seconds || 0;
                
                if (timeRemaining > 0 && timeRemaining <= this.config.autoExtendThreshold) {
                    await this.extendSession();
                }
            }
        } catch (error) {
            console.debug('Session extension check error (non-critical):', error);
        }
    }
    
    async extendSession() {
        try {
            const response = await fetch('/api/session/extend', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Connection-ID': this.connectionId
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Session extended successfully:', data);
                this.sessionHealthStatus = 'healthy';
            } else if (response.status === 401) {
                this.handleSessionExpired();
            }
        } catch (error) {
            console.debug('Session extension error (non-critical):', error);
        }
    }
    
    // REMOVED updateSessionActivity() - use global safeUpdateSessionActivity() instead
    
    startHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }
        
        this.heartbeatInterval = setInterval(() => {
            this.sendHeartbeat();
        }, this.config.heartbeatInterval);
        
        // Send initial heartbeat
        this.sendHeartbeat();
    }
    
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    async sendHeartbeat() {
        // Throttle heartbeats
        const now = Date.now();
        if ((now - this._lastHeartbeat) < 600000) { // 10 minutes minimum
            return;
        }
        this._lastHeartbeat = now;
        
        try {
            const response = await fetch('/api/session/heartbeat', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Connection-ID': this.connectionId
                },
                body: JSON.stringify({
                    timestamp: now,
                    connection_id: this.connectionId,
                    last_activity: this.lastActivity
                })
            });
            
            if (response.ok) {
                this.isConnected = true;
            } else if (response.status === 401) {
                this.isConnected = false;
                this.handleSessionExpired();
            }
        } catch (error) {
            console.debug('Heartbeat error (non-critical):', error);
            this.isConnected = false;
        }
    }
    
    showSessionWarning(timeRemaining) {
        const minutes = Math.ceil(timeRemaining / 60);
        
        if (!this.warningShown) {
            this.warningShown = true;
            
            let warningElement = document.getElementById('session-warning');
            if (!warningElement) {
                warningElement = document.createElement('div');
                warningElement.id = 'session-warning';
                warningElement.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #ff9800;
                    color: white;
                    padding: 15px;
                    border-radius: 5px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
                    z-index: 10000;
                    max-width: 300px;
                    font-family: Arial, sans-serif;
                `;
                document.body.appendChild(warningElement);
            }
            
            warningElement.innerHTML = `
                <div style="margin-bottom: 10px;">
                    <strong>Session Expiring Soon!</strong>
                </div>
                <div style="margin-bottom: 10px;">
                    Your session will expire in ${minutes} minute${minutes > 1 ? 's' : ''}.
                </div>
                <button onclick="window.yamSessionMonitor.extendSession(); this.parentElement.remove();" 
                        style="background: white; color: #ff9800; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">
                    Extend Session
                </button>
            `;
            
            setTimeout(() => {
                if (warningElement && warningElement.parentElement) {
                    warningElement.remove();
                }
                this.warningShown = false;
            }, 30000);
        }
    }
    
    handleSessionExpired() {
        console.log('Session expired - redirecting to login');
        this.stopMonitoring();
        
        // Clear any existing warning
        const warning = document.getElementById('session-warning');
        if (warning) {
            warning.remove();
        }
        
        // Redirect to login
        window.location.href = '/auth/login?reason=session_expired';
    }
    
    destroy() {
        this.stopMonitoring();
        
        // Clear any warnings
        const warning = document.getElementById('session-warning');
        if (warning) {
            warning.remove();
        }
        
        console.log('YAM Session Monitor: Destroyed');
    }
}

// Set the global class
window.YAMSessionMonitor = YAMSessionMonitor;

// Auto-initialize when DOM is ready (with duplicate prevention)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.yamSessionMonitor) {
            window.yamSessionMonitor = new YAMSessionMonitor();
        }
    });
} else {
    if (!window.yamSessionMonitor) {
        window.yamSessionMonitor = new YAMSessionMonitor();
    }
}

// Close the duplicate prevention check
} 