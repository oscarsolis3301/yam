<!-- FRESHSERVICE STRING UTILITIES MODULE -->
<script>
// FreshService String Utilities
window.FreshServiceStringUtils = {
    // Capitalize first letter
    capitalize: function(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    },

    // Truncate string with ellipsis
    truncate: function(str, length = 50) {
        if (!str || str.length <= length) return str;
        return str.substring(0, length) + '...';
    },

    // Escape HTML
    escapeHtml: function(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    // Generate initials from name
    getInitials: function(name) {
        if (!name) return '';
        return name.split(' ')
            .map(word => word.charAt(0).toUpperCase())
            .join('')
            .substring(0, 2);
    },

    // Format date string
    formatDate: function(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    // Format datetime string
    formatDateTime: function(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Convert to title case
    toTitleCase: function(str) {
        if (!str) return '';
        return str.replace(/\w\S*/g, function(txt) {
            return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
        });
    },

    // Remove HTML tags
    stripHtml: function(str) {
        if (!str) return '';
        return str.replace(/<[^>]*>/g, '');
    },

    // Generate slug from string
    slugify: function(str) {
        if (!str) return '';
        return str.toLowerCase()
            .replace(/[^\w\s-]/g, '')
            .replace(/[\s_-]+/g, '-')
            .replace(/^-+|-+$/g, '');
    },

    // Check if string is empty or whitespace
    isEmpty: function(str) {
        return !str || str.trim().length === 0;
    },

    // Count words in string
    wordCount: function(str) {
        if (!str) return 0;
        return str.trim().split(/\s+/).length;
    },

    // Extract email from string
    extractEmail: function(str) {
        if (!str) return '';
        const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
        const match = str.match(emailRegex);
        return match ? match[0] : '';
    },

    // Validate email format
    isValidEmail: function(email) {
        if (!email) return false;
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        return emailRegex.test(email);
    },

    // Generate random string
    randomString: function(length = 8) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }
};
</script> 