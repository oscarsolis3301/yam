<!-- FRESHSERVICE CORE JAVASCRIPT MODULE -->
<script>
// Global state management
window.FreshServiceApp = {
    // Global state
    state: {
        currentPage: 1,
        currentFilters: {
            status: 'all',
            priority: 'all',
            agent: 'all',
            search: '',
            category: 'all',
            subCategory: 'all',
            itemCategory: 'all',
            created: 'any',
            requester: '',
            department: 'select',
            group: 'select',
            overdue: false
        },
        requesterSuggestions: [],
        allTickets: [],
        currentTicketIndex: 0,
        lastDatabaseCheck: Date.now(),
        databaseCheckInterval: null
    },

    // Initialize the application
    init: function() {
        console.log('Initializing FreshService App...');
        
        // Load initial data
        this.loadTickets();
        this.loadRequesterSuggestions();
        
        // Start database monitoring
        this.startDatabaseMonitoring();
        
        // Initialize event listeners
        this.initEventListeners();
        
        console.log('FreshService App initialized successfully');
    },

    // Initialize all event listeners
    initEventListeners: function() {
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', this.handleSearch.bind(this));
        }

        // Sort functionality
        const sortBy = document.getElementById('sortBy');
        if (sortBy) {
            sortBy.addEventListener('change', this.handleSort.bind(this));
        }

        // Pagination
        const prevPage = document.getElementById('prevPage');
        const nextPage = document.getElementById('nextPage');
        if (prevPage) {
            prevPage.addEventListener('click', this.handlePrevPage.bind(this));
        }
        if (nextPage) {
            nextPage.addEventListener('click', this.handleNextPage.bind(this));
        }

        // Reset filters
        const resetFilters = document.querySelector('.reset-filters');
        if (resetFilters) {
            resetFilters.addEventListener('click', this.handleResetFilters.bind(this));
        }

        // Filter inputs
        this.initFilterListeners();
    },

    // Initialize filter event listeners
    initFilterListeners: function() {
        // Status filter
        const statusFilter = document.querySelector('select[data-filter="status"]');
        if (statusFilter) {
            statusFilter.addEventListener('change', this.handleFilterChange.bind(this));
        }

        // Priority filter
        const priorityFilter = document.querySelector('select[data-filter="priority"]');
        if (priorityFilter) {
            priorityFilter.addEventListener('change', this.handleFilterChange.bind(this));
        }

        // Agent filter
        const agentFilter = document.querySelector('input[data-filter="agent"]');
        if (agentFilter) {
            agentFilter.addEventListener('input', this.handleFilterChange.bind(this));
        }

        // Created filter
        const createdFilter = document.querySelector('select[data-filter="created"]');
        if (createdFilter) {
            createdFilter.addEventListener('change', this.handleFilterChange.bind(this));
        }

        // Requester filter
        const requesterFilter = document.getElementById('requesterFilter');
        if (requesterFilter) {
            requesterFilter.addEventListener('input', this.handleRequesterFilter.bind(this));
        }

        // Department filter
        const departmentFilter = document.querySelector('select[data-filter="department"]');
        if (departmentFilter) {
            departmentFilter.addEventListener('change', this.handleFilterChange.bind(this));
        }

        // Group filter
        const groupFilter = document.querySelector('select[data-filter="group"]');
        if (groupFilter) {
            groupFilter.addEventListener('change', this.handleFilterChange.bind(this));
        }

        // Overdue filter
        const overdueFilter = document.getElementById('overdue');
        if (overdueFilter) {
            overdueFilter.addEventListener('change', this.handleFilterChange.bind(this));
        }
    },

    // Handle search input
    handleSearch: function(event) {
        const searchValue = event.target.value.trim();
        this.state.currentFilters.search = searchValue;
        this.state.currentPage = 1;
        
        // Real-time search with immediate feedback
        if (searchValue.length >= 1) {
            this.loadTickets();
        } else if (searchValue.length === 0) {
            this.loadTickets();
        }
        
        // Update placeholder based on search type
        if (searchValue.match(/^\d+$/)) {
            event.target.placeholder = `Searching for ticket number: ${searchValue}`;
        } else if (searchValue) {
            event.target.placeholder = `Searching for: "${searchValue}"`;
        } else {
            event.target.placeholder = 'Search tickets by number, subject, or content...';
        }
    },

    // Handle sort change
    handleSort: function() {
        this.loadTickets();
    },

    // Handle previous page
    handlePrevPage: function() {
        if (this.state.currentPage > 1) {
            this.state.currentPage--;
            this.loadTickets();
        }
    },

    // Handle next page
    handleNextPage: function() {
        this.state.currentPage++;
        this.loadTickets();
    },

    // Handle filter changes
    handleFilterChange: function(event) {
        const filterType = event.target.getAttribute('data-filter');
        const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
        
        this.state.currentFilters[filterType] = value;
        this.state.currentPage = 1;
        this.loadTickets();
    },

    // Handle requester filter specifically
    handleRequesterFilter: function(event) {
        const value = event.target.value.trim();
        this.state.currentFilters.requester = value;
        this.state.currentPage = 1;
        
        // Show/hide suggestions
        this.toggleRequesterSuggestions(value);
        
        this.loadTickets();
    },

    // Handle reset filters
    handleResetFilters: function() {
        // Reset all filter inputs
        document.querySelectorAll('.filter-content input, .filter-content select').forEach(input => {
            if (input.type === 'checkbox') {
                input.checked = false;
            } else if (input.tagName === 'SELECT') {
                input.selectedIndex = 0;
            } else {
                input.value = '';
            }
        });
        
        // Reset requester filter specifically
        const requesterFilter = document.getElementById('requesterFilter');
        if (requesterFilter) {
            requesterFilter.value = '';
        }
        
        // Reset current filters
        this.state.currentFilters = {
            status: 'all',
            priority: 'all',
            agent: 'all',
            search: '',
            category: 'all',
            subCategory: 'all',
            itemCategory: 'all',
            created: 'any',
            requester: '',
            department: 'select',
            group: 'select',
            overdue: false
        };
        
        this.state.currentPage = 1;
        this.loadTickets();
    },

    // Toggle requester suggestions
    toggleRequesterSuggestions: function(searchValue) {
        const suggestionsContainer = document.getElementById('requesterSuggestions');
        if (!suggestionsContainer) return;

        if (searchValue.length >= 2) {
            const filteredSuggestions = this.state.requesterSuggestions.filter(suggestion =>
                suggestion.name.toLowerCase().includes(searchValue.toLowerCase()) ||
                suggestion.email.toLowerCase().includes(searchValue.toLowerCase())
            );
            
            this.displayRequesterSuggestions(filteredSuggestions);
            suggestionsContainer.style.display = 'block';
        } else {
            suggestionsContainer.style.display = 'none';
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.FreshServiceApp.init();
});
</script> 