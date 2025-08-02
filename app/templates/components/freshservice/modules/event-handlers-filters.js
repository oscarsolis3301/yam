<!-- FRESHSERVICE FILTER EVENT HANDLERS MODULE -->
<script>
// Filter functionality handlers for FreshService component
window.FreshServiceFilterHandlers = {
    
    // Initialize filter handlers
    init: function() {
        this.initFilterInputs();
        this.initResetFilters();
        this.initApplyFilters();
        this.initFilterPresets();
    },

    // Filter inputs functionality
    initFilterInputs: function() {
        // Status filter
        const statusFilter = document.querySelector('[data-filter="status"]');
        if (statusFilter) {
            statusFilter.addEventListener('change', function() {
                window.FreshServiceApp.state.currentFilters.status = this.value;
                window.FreshServiceApp.loadTickets();
            });
        }

        // Priority filter
        const priorityFilter = document.querySelector('[data-filter="priority"]');
        if (priorityFilter) {
            priorityFilter.addEventListener('change', function() {
                window.FreshServiceApp.state.currentFilters.priority = this.value;
                window.FreshServiceApp.loadTickets();
            });
        }

        // Agent filter
        const agentFilter = document.querySelector('[data-filter="agent"]');
        if (agentFilter) {
            agentFilter.addEventListener('input', function() {
                window.FreshServiceApp.state.currentFilters.agent = this.value;
                window.FreshServiceApp.loadTickets();
            });
        }

        // Created date filter
        const createdFilter = document.querySelector('[data-filter="created"]');
        if (createdFilter) {
            createdFilter.addEventListener('change', function() {
                window.FreshServiceApp.state.currentFilters.created = this.value;
                window.FreshServiceApp.loadTickets();
            });
        }

        // Requester filter
        const requesterFilter = document.getElementById('requesterFilter');
        if (requesterFilter) {
            requesterFilter.addEventListener('input', function() {
                window.FreshServiceApp.state.currentFilters.requester = this.value;
                this.loadRequesterSuggestions();
            });

            requesterFilter.addEventListener('change', function() {
                window.FreshServiceApp.loadTickets();
            });
        }

        // Department filter
        const departmentFilter = document.querySelector('[data-filter="department"]');
        if (departmentFilter) {
            departmentFilter.addEventListener('change', function() {
                window.FreshServiceApp.state.currentFilters.department = this.value;
                window.FreshServiceApp.loadTickets();
            });
        }

        // Group filter
        const groupFilter = document.querySelector('[data-filter="group"]');
        if (groupFilter) {
            groupFilter.addEventListener('change', function() {
                window.FreshServiceApp.state.currentFilters.group = this.value;
                window.FreshServiceApp.loadTickets();
            });
        }

        // Overdue filter
        const overdueFilter = document.getElementById('overdue');
        if (overdueFilter) {
            overdueFilter.addEventListener('change', function() {
                window.FreshServiceApp.state.currentFilters.overdue = this.checked;
                window.FreshServiceApp.loadTickets();
            });
        }

        // Category filters
        const categoryFilter = document.querySelector('[data-filter="category"]');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', function() {
                window.FreshServiceApp.state.currentFilters.category = this.value;
                window.FreshServiceApp.loadTickets();
            });
        }

        const subCategoryFilter = document.querySelector('[data-filter="subCategory"]');
        if (subCategoryFilter) {
            subCategoryFilter.addEventListener('change', function() {
                window.FreshServiceApp.state.currentFilters.subCategory = this.value;
                window.FreshServiceApp.loadTickets();
            });
        }

        const itemCategoryFilter = document.querySelector('[data-filter="itemCategory"]');
        if (itemCategoryFilter) {
            itemCategoryFilter.addEventListener('change', function() {
                window.FreshServiceApp.state.currentFilters.itemCategory = this.value;
                window.FreshServiceApp.loadTickets();
            });
        }
    },

    // Reset filters functionality
    initResetFilters: function() {
        const resetFilters = document.querySelector('.reset-filters');
        if (resetFilters) {
            resetFilters.addEventListener('click', function() {
                this.resetAllFilters();
            }.bind(this));
        }
    },

    // Reset all filters
    resetAllFilters: function() {
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
        window.FreshServiceApp.state.currentFilters = {
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
        
        window.FreshServiceApp.loadTickets();
    },

    // Apply filters functionality
    initApplyFilters: function() {
        const applyFiltersBtn = document.querySelector('.apply-filters-btn');
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', function() {
                window.FreshServiceApp.loadTickets();
            });
        }
    },

    // Filter presets functionality
    initFilterPresets: function() {
        // My tickets preset
        const myTicketsBtn = document.querySelector('.filter-preset-my-tickets');
        if (myTicketsBtn) {
            myTicketsBtn.addEventListener('click', function() {
                this.applyFilterPreset('my-tickets');
            }.bind(this));
        }

        // Unassigned tickets preset
        const unassignedBtn = document.querySelector('.filter-preset-unassigned');
        if (unassignedBtn) {
            unassignedBtn.addEventListener('click', function() {
                this.applyFilterPreset('unassigned');
            }.bind(this));
        }

        // Overdue tickets preset
        const overdueBtn = document.querySelector('.filter-preset-overdue');
        if (overdueBtn) {
            overdueBtn.addEventListener('click', function() {
                this.applyFilterPreset('overdue');
            }.bind(this));
        }
    },

    // Apply filter preset
    applyFilterPreset: function(preset) {
        const presets = {
            'my-tickets': {
                agent: window.FreshServiceApp.config.currentUser,
                status: 'all',
                priority: 'all'
            },
            'unassigned': {
                agent: 'unassigned',
                status: 'all',
                priority: 'all'
            },
            'overdue': {
                overdue: true,
                status: 'all',
                priority: 'all'
            }
        };

        const presetConfig = presets[preset];
        if (presetConfig) {
            // Apply preset filters
            Object.keys(presetConfig).forEach(key => {
                window.FreshServiceApp.state.currentFilters[key] = presetConfig[key];
            });

            // Update UI to reflect preset
            this.updateFilterUI(presetConfig);
            
            // Load tickets with new filters
            window.FreshServiceApp.loadTickets();
        }
    },

    // Update filter UI to reflect current state
    updateFilterUI: function(filters) {
        // Update status filter
        const statusFilter = document.querySelector('[data-filter="status"]');
        if (statusFilter && filters.status) {
            statusFilter.value = filters.status;
        }

        // Update priority filter
        const priorityFilter = document.querySelector('[data-filter="priority"]');
        if (priorityFilter && filters.priority) {
            priorityFilter.value = filters.priority;
        }

        // Update agent filter
        const agentFilter = document.querySelector('[data-filter="agent"]');
        if (agentFilter && filters.agent) {
            agentFilter.value = filters.agent;
        }

        // Update overdue filter
        const overdueFilter = document.getElementById('overdue');
        if (overdueFilter && filters.overdue !== undefined) {
            overdueFilter.checked = filters.overdue;
        }
    },

    // Save filter preset
    saveFilterPreset: function(name, filters) {
        let savedPresets = JSON.parse(localStorage.getItem('freshservice_filter_presets') || '{}');
        savedPresets[name] = filters;
        localStorage.setItem('freshservice_filter_presets', JSON.stringify(savedPresets));
    },

    // Load filter preset
    loadFilterPreset: function(name) {
        const savedPresets = JSON.parse(localStorage.getItem('freshservice_filter_presets') || '{}');
        return savedPresets[name] || null;
    },

    // Get all saved presets
    getSavedPresets: function() {
        return JSON.parse(localStorage.getItem('freshservice_filter_presets') || '{}');
    }
};
</script> 