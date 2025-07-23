/**
 * YAM Enhanced Session Monitor
 * Prevents disconnections and maintains stable user sessions
 * Enhanced with connection deduplication and improved stability
 */

class YAMSessionMonitor {
    constructor() {
        this.sessionCheckInterval = null;
        this.sessionExtendInterval = null;
        this.lastSessionCheck = Date.now();
        this.sessionHealthStatus = 'unknown';
        this.isMonitoring = false;
        this.lastActivity = Date.now();
        this.autoExtendEnabled = true;
        this.connectionId = null;
        this.isConnected = false;
        
        // Configuration for 2-hour sessions (matching server config)
        this.config = {
            sessionCheckInterval: 60000,    // Check session every 60 seconds (increased)
            sessionExtendInterval: 120000,   // Extend session every 2 minutes (increased)
            sessionWarningThreshold: 600,   // Warn when 10 minutes remaining (increased)
            sessionCriticalThreshold: 120,   // Critical when 2 minutes remaining (increased)
            maxSessionAge: 7200,            // 2 hours max session age (matching server)
            autoExtendThreshold: 1800,       // Auto-extend when 30 minutes remaining (increased)
            gracePeriod: 600,               // 10 minute grace period for reconnection (increased)
            heartbeatInterval: 90000        // 90 second heartbeat (increased)
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
        
        // Start monitoring
        this.startMonitoring();
        
        // Set up activity tracking
        this.setupActivityTracking();
        
        // Set up visibility tracking
        this.setupVisibilityTracking();
        
        // Set up beforeunload handler
        this.setupBeforeUnload();
        
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
        
        // Start session health checks
        this.sessionCheckInterval = setInterval(() => {
            this.checkSessionHealth();
        }, this.config.sessionCheckInterval);
        
        // Start automatic session extension
        this.sessionExtendInterval = setInterval(() => {
            this.extendSessionIfNeeded();
        }, this.config.sessionExtendInterval);
        
        // Start heartbeat
        this.startHeartbeat();
        
        console.log('YAM Session Monitor: Started monitoring');
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
        // Track user activity to prevent premature timeouts
        const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        
        activityEvents.forEach(event => {
            document.addEventListener(event, () => {
                this.lastActivity = Date.now();
                this.updateSessionActivity();
            }, { passive: true });
        });
        
        // Track focus events
        window.addEventListener('focus', () => {
            this.lastActivity = Date.now();
            this.updateSessionActivity();
            this.checkSessionHealth();
        });
        
        window.addEventListener('blur', () => {
            // Don't immediately check on blur, but update activity
            this.lastActivity = Date.now();
            this.updateSessionActivity();
        });
    }
    
    setupVisibilityTracking() {
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                // Page became visible - check session and update activity
                this.lastActivity = Date.now();
                this.updateSessionActivity();
                this.checkSessionHealth();
            } else {
                // Page hidden - just update activity
                this.lastActivity = Date.now();
                this.updateSessionActivity();
            }
        });
    }
    
    setupBeforeUnload() {
        // Handle page unload gracefully
        window.addEventListener('beforeunload', (event) => {
            // Try to send a final activity update
            this.updateSessionActivity();
            
            // Don't show confirmation dialog - just log
            console.log('YAM Session Monitor: Page unloading');
        });
    }
    
    async checkSessionHealth() {
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
                
                // Update session status
                this.sessionHealthStatus = timeRemaining > 0 ? 'healthy' : 'expired';
                
                // Show warning if session is about to expire
                if (timeRemaining > 0 && timeRemaining < this.config.sessionWarningThreshold) {
                    this.showSessionWarning(timeRemaining);
                }
                
                // Auto-extend if session is getting close to expiry
                if (timeRemaining > 0 && timeRemaining <= this.config.autoExtendThreshold) {
                    await this.extendSession();
                }
                
                // Handle expired session
                if (timeRemaining <= 0) {
                    this.handleSessionExpired();
                }
                
            } else if (response.status === 401) {
                // User not authenticated - redirect to login
                this.handleSessionExpired();
            } else {
                console.warn('Session health check failed with status:', response.status);
            }
            
        } catch (error) {
            console.error('Session health check error:', error);
            // Don't fail completely on network errors
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
                
                // Auto-extend if session is getting close to expiry
                if (timeRemaining > 0 && timeRemaining <= this.config.autoExtendThreshold) {
                    await this.extendSession();
                }
            }
        } catch (error) {
            console.error('Session extension check error:', error);
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
                // Session expired, redirect to login
                this.handleSessionExpired();
            } else {
                console.warn('Session extension failed with status:', response.status);
            }
        } catch (error) {
            console.error('Session extension error:', error);
        }
    }
    
    async updateSessionActivity() {
        try {
            const response = await fetch('/api/session/activity', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Connection-ID': this.connectionId
                },
                body: JSON.stringify({
                    timestamp: Date.now(),
                    connection_id: this.connectionId,
                    last_activity: this.lastActivity
                })
            });
            
            if (!response.ok && response.status !== 401) {
                console.warn('Activity update failed with status:', response.status);
            }
        } catch (error) {
            // Silently fail on network errors for activity updates
            console.debug('Activity update error (non-critical):', error);
        }
    }
    
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
                    timestamp: Date.now(),
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
        
        // Only show warning if not already shown
        if (!this.warningShown) {
            this.warningShown = true;
            
            // Create or update warning element
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
                    z-index: 10000;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    max-width: 300px;
                    font-family: Arial, sans-serif;
                `;
                document.body.appendChild(warningElement);
            }
            
            warningElement.innerHTML = `
                <strong>Session Expiring Soon</strong><br>
                Your session will expire in ${minutes} minute${minutes !== 1 ? 's' : ''}.<br>
                <button onclick="window.yamSessionMonitor.extendSession()" 
                        style="margin-top: 10px; padding: 5px 10px; background: white; color: #ff9800; border: none; border-radius: 3px; cursor: pointer;">
                    Extend Session
                </button>
            `;
            
            // Auto-hide after 10 seconds
            setTimeout(() => {
                if (warningElement && warningElement.parentNode) {
                    warningElement.parentNode.removeChild(warningElement);
                    this.warningShown = false;
                }
            }, 10000);
        }
    }
    
    handleSessionExpired() {
        console.log('Session expired, redirecting to login');
        
        // Clear all client-side data
        this.clearAllClientData();
        
        // Redirect to login page
        window.location.href = '/auth/login?expired=true';
    }
    
    clearAllClientData() {
        try {
            // Clear localStorage
            localStorage.clear();
            
            // Clear sessionStorage
            sessionStorage.clear();
            
            // Clear cookies (except essential ones)
            this.clearCookies();
            
            console.log('Client data cleared');
        } catch (error) {
            console.error('Error clearing client data:', error);
        }
    }
    
    clearCookies() {
        try {
            const cookies = document.cookie.split(';');
            
            for (let cookie of cookies) {
                const eqPos = cookie.indexOf('=');
                const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim();
                
                // Don't clear essential cookies
                if (!['session', 'yam_session', 'csrf_token'].includes(name)) {
                    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
                }
            }
        } catch (error) {
            console.error('Error clearing cookies:', error);
        }
    }
    
    forceLogout() {
        try {
            // Send logout request
            fetch('/auth/logout', {
                method: 'POST',
                credentials: 'include'
            }).finally(() => {
                this.clearAllClientData();
                window.location.href = '/auth/login';
            });
        } catch (error) {
            console.error('Error during force logout:', error);
            this.clearAllClientData();
            window.location.href = '/auth/login';
        }
    }
    
    forceExtend() {
        return this.extendSession();
    }
    
    getStatus() {
        return {
            isMonitoring: this.isMonitoring,
            sessionHealthStatus: this.sessionHealthStatus,
            lastActivity: this.lastActivity,
            connectionId: this.connectionId,
            isConnected: this.isConnected,
            config: this.config
        };
    }
    
    enableAutoExtend() {
        this.autoExtendEnabled = true;
    }
    
    disableAutoExtend() {
        this.autoExtendEnabled = false;
    }
    
    destroy() {
        this.stopMonitoring();
        this.stopHeartbeat();
        
        // Remove warning element if it exists
        const warningElement = document.getElementById('session-warning');
        if (warningElement && warningElement.parentNode) {
            warningElement.parentNode.removeChild(warningElement);
        }
        
        // Clear global reference
        if (window.yamSessionMonitor === this) {
            window.yamSessionMonitor = null;
        }
        
        console.log('YAM Session Monitor destroyed');
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new YAMSessionMonitor();
    });
} else {
    new YAMSessionMonitor();
} 