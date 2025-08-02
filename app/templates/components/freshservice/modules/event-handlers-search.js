<!-- FRESHSERVICE SEARCH EVENT HANDLERS MODULE -->
<script>
// Search functionality handlers for FreshService component
window.FreshServiceSearchHandlers = {
    
    // Initialize search handlers
    init: function() {
        this.initSearchInput();
        this.initSearchSuggestions();
        this.initSearchFilters();
    },

    // Search input functionality
    initSearchInput: function() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', function() {
                const searchValue = this.value.trim();
                window.FreshServiceApp.state.currentFilters.search = searchValue;
                window.FreshServiceApp.state.currentPage = 1;
                
                // Real-time search with immediate feedback
                if (searchValue.length >= 1) {
                    window.FreshServiceApp.loadTickets();
                } else if (searchValue.length === 0) {
                    window.FreshServiceApp.loadTickets();
                }
                
                // Update placeholder based on search type
                if (searchValue.match(/^\d+$/)) {
                    this.placeholder = `Searching for ticket number: ${searchValue}`;
                } else if (searchValue) {
                    this.placeholder = `Searching for: "${searchValue}"`;
                } else {
                    this.placeholder = 'Search tickets by number, subject, or content...';
                }
            });

            // Add keyboard shortcuts
            searchInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    window.FreshServiceApp.loadTickets();
                } else if (e.key === 'Escape') {
                    this.value = '';
                    window.FreshServiceApp.state.currentFilters.search = '';
                    window.FreshServiceApp.loadTickets();
                }
            });
        }
    },

    // Search suggestions functionality
    initSearchSuggestions: function() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            // Debounced search suggestions
            const debouncedSuggestions = window.FreshServiceUtils.core.debounce((value) => {
                this.showSearchSuggestions(value);
            }, 300);

            searchInput.addEventListener('input', function() {
                const value = this.value.trim();
                if (value.length >= 2) {
                    debouncedSuggestions(value);
                } else {
                    this.hideSearchSuggestions();
                }
            });
        }
    },

    // Show search suggestions
    showSearchSuggestions: function(searchValue) {
        // Implementation for showing search suggestions
        // This would typically involve API calls to get suggestions
        console.log('Showing suggestions for:', searchValue);
    },

    // Hide search suggestions
    hideSearchSuggestions: function() {
        // Implementation for hiding search suggestions
        console.log('Hiding search suggestions');
    },

    // Search filters functionality
    initSearchFilters: function() {
        // Sort functionality
        const sortBy = document.getElementById('sortBy');
        if (sortBy) {
            sortBy.addEventListener('change', function() {
                window.FreshServiceApp.loadTickets();
            });
        }

        // Advanced search filters
        const advancedSearchBtn = document.querySelector('.advanced-search-btn');
        if (advancedSearchBtn) {
            advancedSearchBtn.addEventListener('click', function() {
                this.toggleAdvancedSearch();
            });
        }
    },

    // Toggle advanced search
    toggleAdvancedSearch: function() {
        const advancedSearch = document.querySelector('.advanced-search');
        if (advancedSearch) {
            advancedSearch.classList.toggle('show');
        }
    },

    // Clear search
    clearSearch: function() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = '';
            window.FreshServiceApp.state.currentFilters.search = '';
            window.FreshServiceApp.loadTickets();
        }
    },

    // Search history
    addToSearchHistory: function(searchTerm) {
        if (!searchTerm || searchTerm.trim().length === 0) return;
        
        let searchHistory = JSON.parse(localStorage.getItem('freshservice_search_history') || '[]');
        searchHistory = searchHistory.filter(term => term !== searchTerm);
        searchHistory.unshift(searchTerm);
        searchHistory = searchHistory.slice(0, 10); // Keep only last 10 searches
        
        localStorage.setItem('freshservice_search_history', JSON.stringify(searchHistory));
    },

    // Get search history
    getSearchHistory: function() {
        return JSON.parse(localStorage.getItem('freshservice_search_history') || '[]');
    }
};
</script> 