<!-- FRESHSERVICE CONFIGURATION MODULE -->
<script>
// FreshService Component Configuration
window.FreshServiceConfig = {
    // API Configuration
    api: {
        baseUrl: '/api/freshservice',
        endpoints: {
            tickets: '/tickets',
            ticketDetails: '/tickets/{id}',
            requesters: '/requesters',
            checkUpdates: '/check-updates'
        },
        timeout: 30000, // 30 seconds
        retryAttempts: 3
    },

    // UI Configuration
    ui: {
        itemsPerPage: 32,
        searchDelay: 300, // milliseconds
        databaseCheckInterval: 30000, // 30 seconds
        suggestionLimit: 5,
        modalAnimationDuration: 300
    },

    // Status Configuration
    statuses: {
        open: { label: 'Open', class: 'status-open', color: '#28a745' },
        pending: { label: 'Pending', class: 'status-pending', color: '#ffc107' },
        resolved: { label: 'Resolved', class: 'status-resolved', color: '#007bff' },
        closed: { label: 'Closed', class: 'status-closed', color: '#6c757d' }
    },

    // Priority Configuration
    priorities: {
        low: { label: 'Low', class: 'priority-low', color: '#28a745' },
        medium: { label: 'Medium', class: 'priority-medium', color: '#ffc107' },
        high: { label: 'High', class: 'priority-high', color: '#dc3545' },
        urgent: { label: 'Urgent', class: 'priority-urgent', color: '#dc3545' }
    },

    // Filter Configuration
    filters: {
        createdOptions: [
            { value: 'any', label: 'Any' },
            { value: 'today', label: 'Today' },
            { value: 'yesterday', label: 'Yesterday' },
            { value: 'this_week', label: 'This Week' },
            { value: 'last_week', label: 'Last Week' },
            { value: 'this_month', label: 'This Month' },
            { value: 'last_month', label: 'Last Month' }
        ],
        statusOptions: [
            { value: 'all', label: 'All Statuses' },
            { value: 'Open', label: 'Open' },
            { value: 'Pending', label: 'Pending' },
            { value: 'Resolved', label: 'Resolved' },
            { value: 'Closed', label: 'Closed' }
        ],
        priorityOptions: [
            { value: 'all', label: 'All Priorities' },
            { value: 'Low', label: 'Low' },
            { value: 'Medium', label: 'Medium' },
            { value: 'High', label: 'High' },
            { value: 'Urgent', label: 'Urgent' }
        ]
    },

    // Sort Configuration
    sortOptions: [
        { value: 'updated_date', label: 'Sort by: Created Date' },
        { value: 'created_date', label: 'Created Date' },
        { value: 'priority', label: 'Priority' },
        { value: 'status', label: 'Status' },
        { value: 'requester', label: 'Requester' }
    ],

    // Theme Configuration
    theme: {
        colors: {
            primary: '#007bff',
            success: '#28a745',
            warning: '#ffc107',
            danger: '#dc3545',
            muted: '#6c757d',
            background: {
                primary: '#0f0f23',
                secondary: '#1a1a2e',
                tertiary: '#16213e'
            },
            text: {
                primary: '#ffffff',
                secondary: 'rgba(255, 255, 255, 0.8)',
                muted: 'rgba(255, 255, 255, 0.6)'
            }
        },
        fonts: {
            primary: "'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
            monospace: "'Courier New', monospace"
        },
        spacing: {
            xs: '0.25rem',
            sm: '0.5rem',
            md: '1rem',
            lg: '1.5rem',
            xl: '2rem'
        },
        borderRadius: {
            sm: '3px',
            md: '5px',
            lg: '8px',
            xl: '15px',
            pill: '25px'
        }
    },

    // Feature Flags
    features: {
        realTimeSearch: true,
        databaseMonitoring: true,
        requesterSuggestions: true,
        ticketSelection: true,
        modalNavigation: true,
        exportFunctionality: false, // Disabled by default
        bulkActions: false // Disabled by default
    },

    // Localization
    localization: {
        language: 'en',
        messages: {
            loading: 'Loading tickets...',
            noTickets: 'No tickets found',
            noTicketsSubtext: 'Try adjusting your filters or search terms.',
            error: 'Error',
            errorLoadingTickets: 'Failed to load tickets. Please try again.',
            errorLoadingDetails: 'Failed to load ticket details.',
            databaseUpdating: 'Database updated, refreshing...',
            selectAll: 'Select all',
            export: 'Export',
            reset: 'Reset',
            search: 'Search tickets by number, subject, or content...',
            filter: 'Filter'
        }
    },

    // Debug Configuration
    debug: {
        enabled: false,
        logLevel: 'error', // 'debug', 'info', 'warn', 'error'
        showPerformanceMetrics: false
    }
};

// Utility function to get configuration value
window.FreshServiceConfig.get = function(path) {
    return path.split('.').reduce((obj, key) => obj && obj[key], this);
};

// Utility function to set configuration value
window.FreshServiceConfig.set = function(path, value) {
    const keys = path.split('.');
    const lastKey = keys.pop();
    const target = keys.reduce((obj, key) => obj[key] = obj[key] || {}, this);
    target[lastKey] = value;
};
</script> 