<!-- FRESHSERVICE CORE UTILITIES MODULE -->
<script>
// FreshService Core Utilities - Wrapper for all utility modules
window.FreshServiceUtils = {
    // Import all utility modules
    dom: window.FreshServiceDOMUtils || {},
    string: window.FreshServiceStringUtils || {},
    date: window.FreshServiceDateUtils || {},

    // Core utility functions
    core: {
        // Debounce function
        debounce: function(func, wait, immediate) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    timeout = null;
                    if (!immediate) func(...args);
                };
                const callNow = immediate && !timeout;
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
                if (callNow) func(...args);
            };
        },

        // Throttle function
        throttle: function(func, limit) {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        },

        // Deep clone object
        deepClone: function(obj) {
            if (obj === null || typeof obj !== 'object') return obj;
            if (obj instanceof Date) return new Date(obj.getTime());
            if (obj instanceof Array) return obj.map(item => this.deepClone(item));
            if (typeof obj === 'object') {
                const clonedObj = {};
                for (const key in obj) {
                    if (obj.hasOwnProperty(key)) {
                        clonedObj[key] = this.deepClone(obj[key]);
                    }
                }
                return clonedObj;
            }
        },

        // Merge objects
        merge: function(target, ...sources) {
            if (!target) target = {};
            sources.forEach(source => {
                if (source) {
                    Object.keys(source).forEach(key => {
                        if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                            target[key] = this.merge(target[key], source[key]);
                        } else {
                            target[key] = source[key];
                        }
                    });
                }
            });
            return target;
        },

        // Generate unique ID
        generateId: function(prefix = 'id') {
            return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        },

        // Check if value is empty
        isEmpty: function(value) {
            if (value === null || value === undefined) return true;
            if (typeof value === 'string') return value.trim().length === 0;
            if (Array.isArray(value)) return value.length === 0;
            if (typeof value === 'object') return Object.keys(value).length === 0;
            return false;
        },

        // Get nested object property safely
        get: function(obj, path, defaultValue = undefined) {
            const keys = path.split('.');
            let result = obj;
            
            for (const key of keys) {
                if (result && typeof result === 'object' && key in result) {
                    result = result[key];
                } else {
                    return defaultValue;
                }
            }
            
            return result;
        },

        // Set nested object property safely
        set: function(obj, path, value) {
            const keys = path.split('.');
            let current = obj;
            
            for (let i = 0; i < keys.length - 1; i++) {
                const key = keys[i];
                if (!(key in current) || typeof current[key] !== 'object') {
                    current[key] = {};
                }
                current = current[key];
            }
            
            current[keys[keys.length - 1]] = value;
            return obj;
        },

        // Retry function with exponential backoff
        retry: function(fn, maxAttempts = 3, delay = 1000) {
            return new Promise((resolve, reject) => {
                let attempts = 0;
                
                const attempt = () => {
                    attempts++;
                    fn()
                        .then(resolve)
                        .catch(error => {
                            if (attempts >= maxAttempts) {
                                reject(error);
                            } else {
                                setTimeout(attempt, delay * Math.pow(2, attempts - 1));
                            }
                        });
                };
                
                attempt();
            });
        },

        // Format bytes to human readable
        formatBytes: function(bytes, decimals = 2) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        },

        // Sleep function
        sleep: function(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        },

        // Validate URL
        isValidUrl: function(string) {
            try {
                new URL(string);
                return true;
            } catch (_) {
                return false;
            }
        },

        // Get query parameters from URL
        getQueryParams: function(url = window.location.href) {
            const params = {};
            const urlSearchParams = new URLSearchParams(url.split('?')[1]);
            for (const [key, value] of urlSearchParams) {
                params[key] = value;
            }
            return params;
        },

        // Build query string from object
        buildQueryString: function(params) {
            return Object.keys(params)
                .filter(key => params[key] !== null && params[key] !== undefined)
                .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
                .join('&');
        }
    }
};
</script> 