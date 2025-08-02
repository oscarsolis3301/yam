<!-- FRESHSERVICE DATE UTILITIES MODULE -->
<script>
// FreshService Date Utilities
window.FreshServiceDateUtils = {
    // Get current date in ISO format
    getCurrentDate: function() {
        return new Date().toISOString();
    },

    // Format date for display
    formatDate: function(date, format = 'short') {
        if (!date) return '';
        
        const d = new Date(date);
        if (isNaN(d.getTime())) return '';

        switch (format) {
            case 'short':
                return d.toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric'
                });
            case 'long':
                return d.toLocaleDateString('en-US', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
            case 'time':
                return d.toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
            case 'datetime':
                return d.toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            default:
                return d.toLocaleDateString();
        }
    },

    // Get relative time (e.g., "2 hours ago")
    getRelativeTime: function(date) {
        if (!date) return '';
        
        const d = new Date(date);
        if (isNaN(d.getTime())) return '';

        const now = new Date();
        const diffMs = now - d;
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffSecs < 60) {
            return 'Just now';
        } else if (diffMins < 60) {
            return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        } else if (diffDays < 7) {
            return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
        } else {
            return this.formatDate(date, 'short');
        }
    },

    // Check if date is today
    isToday: function(date) {
        if (!date) return false;
        const d = new Date(date);
        const today = new Date();
        return d.toDateString() === today.toDateString();
    },

    // Check if date is yesterday
    isYesterday: function(date) {
        if (!date) return false;
        const d = new Date(date);
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        return d.toDateString() === yesterday.toDateString();
    },

    // Check if date is this week
    isThisWeek: function(date) {
        if (!date) return false;
        const d = new Date(date);
        const today = new Date();
        const startOfWeek = new Date(today);
        startOfWeek.setDate(today.getDate() - today.getDay());
        startOfWeek.setHours(0, 0, 0, 0);
        
        const endOfWeek = new Date(startOfWeek);
        endOfWeek.setDate(startOfWeek.getDate() + 6);
        endOfWeek.setHours(23, 59, 59, 999);
        
        return d >= startOfWeek && d <= endOfWeek;
    },

    // Check if date is this month
    isThisMonth: function(date) {
        if (!date) return false;
        const d = new Date(date);
        const today = new Date();
        return d.getMonth() === today.getMonth() && d.getFullYear() === today.getFullYear();
    },

    // Get date range for filter options
    getDateRange: function(range) {
        const now = new Date();
        const start = new Date();
        
        switch (range) {
            case 'today':
                start.setHours(0, 0, 0, 0);
                break;
            case 'yesterday':
                start.setDate(start.getDate() - 1);
                start.setHours(0, 0, 0, 0);
                break;
            case 'this_week':
                start.setDate(start.getDate() - start.getDay());
                start.setHours(0, 0, 0, 0);
                break;
            case 'last_week':
                start.setDate(start.getDate() - start.getDay() - 7);
                start.setHours(0, 0, 0, 0);
                break;
            case 'this_month':
                start.setDate(1);
                start.setHours(0, 0, 0, 0);
                break;
            case 'last_month':
                start.setMonth(start.getMonth() - 1);
                start.setDate(1);
                start.setHours(0, 0, 0, 0);
                break;
            default:
                return null;
        }
        
        return {
            start: start.toISOString(),
            end: now.toISOString()
        };
    },

    // Add days to date
    addDays: function(date, days) {
        const d = new Date(date);
        d.setDate(d.getDate() + days);
        return d;
    },

    // Add months to date
    addMonths: function(date, months) {
        const d = new Date(date);
        d.setMonth(d.getMonth() + months);
        return d;
    },

    // Get start of day
    startOfDay: function(date) {
        const d = new Date(date);
        d.setHours(0, 0, 0, 0);
        return d;
    },

    // Get end of day
    endOfDay: function(date) {
        const d = new Date(date);
        d.setHours(23, 59, 59, 999);
        return d;
    },

    // Check if date is overdue
    isOverdue: function(dueDate) {
        if (!dueDate) return false;
        const due = new Date(dueDate);
        const now = new Date();
        return due < now;
    },

    // Get days until due
    getDaysUntilDue: function(dueDate) {
        if (!dueDate) return null;
        const due = new Date(dueDate);
        const now = new Date();
        const diffTime = due - now;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        return diffDays;
    }
};
</script> 