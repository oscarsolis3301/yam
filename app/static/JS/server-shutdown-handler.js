/**
 * Server Shutdown Handler for YAM Application
 * Handles server shutdown events and forces user re-authentication
 */

class ServerShutdownHandler {
    constructor() {
        this.isShutdown = false;
        this.shutdownMessage = 'Server has been shut down. Please re-authenticate.';
        this.init();
    }
    
    init() {
        // Listen for server shutdown events from SocketIO
        if (typeof io !== 'undefined' && io.socket) {
            io.socket.on('server_shutdown', (data) => {
                this.handleServerShutdown(data);
            });
        }
        
        // Also listen for disconnect events
        if (typeof io !== 'undefined' && io.socket) {
            io.socket.on('disconnect', (reason) => {
                if (reason === 'io server disconnect' || reason === 'transport close') {
                    this.handleServerDisconnect(reason);
                }
            });
        }
        
        // Check for shutdown marker on page load
        this.checkShutdownMarker();
        
        console.log('Server shutdown handler initialized');
    }
    
    handleServerShutdown(data) {
        console.log('Server shutdown detected:', data);
        this.isShutdown = true;
        
        // Show notification to user
        this.showShutdownNotification(data.message || this.shutdownMessage);
        
        // Clear all client-side data
        this.clearAllClientData();
        
        // Redirect to login page after a short delay
        setTimeout(() => {
            window.location.href = '/auth/login?shutdown=true';
        }, 3000);
    }
    
    handleServerDisconnect(reason) {
        console.log('Server disconnect detected:', reason);
        
        // If it's a server-initiated disconnect, treat as shutdown
        if (reason === 'io server disconnect') {
            this.handleServerShutdown({
                message: 'Server connection lost. Please re-authenticate.',
                require_relogin: true
            });
        }
    }
    
    showShutdownNotification(message) {
        // Create a prominent notification
        const notification = document.createElement('div');
        notification.id = 'server-shutdown-notification';
        notification.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            color: white;
            padding: 15px;
            text-align: center;
            font-weight: bold;
            font-size: 16px;
            z-index: 9999;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            animation: slideDown 0.5s ease-out;
        `;
        
        notification.innerHTML = `
            <div style="max-width: 800px; margin: 0 auto;">
                <span style="margin-right: 10px;">⚠️</span>
                ${message}
                <span style="margin-left: 10px;">⚠️</span>
            </div>
        `;
        
        // Add CSS animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideDown {
                from { transform: translateY(-100%); }
                to { transform: translateY(0); }
            }
        `;
        document.head.appendChild(style);
        
        // Add to page
        document.body.appendChild(notification);
        
        // Remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    clearAllClientData() {
        try {
            // Clear localStorage
            localStorage.clear();
            
            // Clear sessionStorage
            sessionStorage.clear();
            
            // Clear cookies (except essential ones)
            this.clearCookies();
            
            // Clear any cached data
            if ('caches' in window) {
                caches.keys().then(cacheNames => {
                    cacheNames.forEach(cacheName => {
                        caches.delete(cacheName);
                    });
                });
            }
            
            console.log('All client data cleared due to server shutdown');
        } catch (error) {
            console.error('Error clearing client data:', error);
        }
    }
    
    clearCookies() {
        try {
            const cookies = document.cookie.split(';');
            cookies.forEach(cookie => {
                const eqPos = cookie.indexOf('=');
                const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim();
                
                // Clear ALL cookies including session cookies
                document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
                document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${window.location.hostname};`;
                document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=.${window.location.hostname};`;
            });
            console.log('All cookies cleared');
        } catch (error) {
            console.error('Error clearing cookies:', error);
        }
    }
    
    checkShutdownMarker() {
        // Check if we're on the login page with shutdown parameter
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('shutdown') === 'true') {
            this.showShutdownNotification('Server was restarted. Please log in again.');
        }
        
        // REMOVED: Automatic force logout on every page load
        // This was causing random logouts. Force logout should only happen
        // when there's an actual server shutdown event, not on every page load.
    }
    
    // Method to manually trigger shutdown handling (for testing)
    triggerShutdown(message = 'Server shutdown detected') {
        this.handleServerShutdown({
            message: message,
            require_relogin: true
        });
    }
}

// Initialize the handler when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.serverShutdownHandler = new ServerShutdownHandler();
});

// Also initialize immediately if DOM is already loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.serverShutdownHandler = new ServerShutdownHandler();
    });
} else {
    window.serverShutdownHandler = new ServerShutdownHandler();
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ServerShutdownHandler;
} 