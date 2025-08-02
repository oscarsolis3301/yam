<!-- FRESHSERVICE DATA SERVICE MODULE -->
<script>
// Extend FreshServiceApp with data service functionality
Object.assign(window.FreshServiceApp, {
    // Load tickets from API
    loadTickets: function() {
        this.showLoadingState();
        
        // Build query parameters
        const params = new URLSearchParams({
            page: this.state.currentPage,
            ...this.state.currentFilters
        });
        
        // Make API call
        fetch(`/api/freshservice/tickets?${params}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.state.allTickets = data.tickets || [];
                this.renderTickets();
                this.updatePagination(data.pagination);
                this.hideLoadingState();
            })
            .catch(error => {
                console.error('Error loading tickets:', error);
                this.showErrorState('Failed to load tickets. Please try again.');
                this.hideLoadingState();
            });
    },

    // Load requester suggestions
    loadRequesterSuggestions: function() {
        fetch('/api/freshservice/requesters')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.state.requesterSuggestions = data.requesters || [];
                this.displayRequesterSuggestions(this.state.requesterSuggestions.slice(0, 5));
            })
            .catch(error => {
                console.error('Error loading requester suggestions:', error);
            });
    },

    // Load ticket details
    loadTicketDetails: function(ticketId) {
        fetch(`/api/freshservice/tickets/${ticketId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.renderTicketDetails(data.ticket);
            })
            .catch(error => {
                console.error('Error loading ticket details:', error);
                this.showErrorState('Failed to load ticket details.');
            });
    },

    // Start database monitoring
    startDatabaseMonitoring: function() {
        this.state.databaseCheckInterval = setInterval(() => {
            this.checkDatabaseUpdates();
        }, 30000); // Check every 30 seconds
    },

    // Check for database updates
    checkDatabaseUpdates: function() {
        const lastCheck = this.state.lastDatabaseCheck;
        
        fetch(`/api/freshservice/check-updates?since=${lastCheck}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.hasUpdates) {
                    this.showDatabaseUpdateIndicator();
                    setTimeout(() => {
                        this.state.lastDatabaseCheck = Date.now();
                        this.loadTickets();
                        this.hideDatabaseUpdateIndicator();
                    }, 2000);
                }
            })
            .catch(error => {
                console.error('Error checking database updates:', error);
            });
    },

    // Display requester suggestions
    displayRequesterSuggestions: function(suggestions) {
        const suggestionList = document.getElementById('suggestionList');
        if (!suggestionList) return;

        suggestionList.innerHTML = '';
        
        suggestions.forEach(suggestion => {
            const suggestionItem = document.createElement('div');
            suggestionItem.className = 'suggestion-item';
            suggestionItem.innerHTML = `
                <div class="suggestion-name">${suggestion.name}</div>
                <div class="suggestion-email">${suggestion.email}</div>
            `;
            
            suggestionItem.addEventListener('click', () => {
                const requesterFilter = document.getElementById('requesterFilter');
                if (requesterFilter) {
                    requesterFilter.value = suggestion.name;
                    this.state.currentFilters.requester = suggestion.name;
                    this.state.currentPage = 1;
                    this.loadTickets();
                }
                
                const suggestionsContainer = document.getElementById('requesterSuggestions');
                if (suggestionsContainer) {
                    suggestionsContainer.style.display = 'none';
                }
            });
            
            suggestionList.appendChild(suggestionItem);
        });
    },

    // Show loading state
    showLoadingState: function() {
        const loadingState = document.getElementById('loadingState');
        const ticketsTable = document.querySelector('.tickets-table-container');
        const emptyState = document.getElementById('emptyState');
        
        if (loadingState) loadingState.style.display = 'flex';
        if (ticketsTable) ticketsTable.style.display = 'none';
        if (emptyState) emptyState.style.display = 'none';
    },

    // Hide loading state
    hideLoadingState: function() {
        const loadingState = document.getElementById('loadingState');
        if (loadingState) loadingState.style.display = 'none';
    },

    // Show error state
    showErrorState: function(message) {
        const ticketsTable = document.querySelector('.tickets-table-container');
        const emptyState = document.getElementById('emptyState');
        
        if (ticketsTable) ticketsTable.style.display = 'none';
        if (emptyState) {
            emptyState.innerHTML = `
                <i class="bi bi-exclamation-triangle"></i>
                <h3>Error</h3>
                <p>${message}</p>
            `;
            emptyState.style.display = 'flex';
        }
    },

    // Show database update indicator
    showDatabaseUpdateIndicator: function() {
        const indicator = document.getElementById('dbUpdateIndicator');
        if (indicator) {
            indicator.style.display = 'flex';
        }
    },

    // Hide database update indicator
    hideDatabaseUpdateIndicator: function() {
        const indicator = document.getElementById('dbUpdateIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    },

    // Update pagination info
    updatePagination: function(pagination) {
        const paginationInfo = document.getElementById('paginationInfo');
        if (paginationInfo && pagination) {
            const start = (pagination.current_page - 1) * pagination.per_page + 1;
            const end = Math.min(start + pagination.per_page - 1, pagination.total);
            paginationInfo.textContent = `${start} - ${end} of ${pagination.total}`;
        }
    },

    // Utility function to format date
    formatDate: function(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) {
            return 'Today';
        } else if (diffDays === 2) {
            return 'Yesterday';
        } else if (diffDays <= 7) {
            return `${diffDays - 1} days ago`;
        } else {
            return date.toLocaleDateString();
        }
    },

    // Utility function to get initials from name
    getInitials: function(name) {
        return name
            .split(' ')
            .map(word => word.charAt(0))
            .join('')
            .toUpperCase()
            .slice(0, 2);
    }
});
</script> 