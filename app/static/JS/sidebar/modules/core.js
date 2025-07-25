// Core Search Module
// Handles main search functionality and coordinates between modules

class CoreSearch {
    constructor() {
        console.log('Core Search Module: Initializing...');
        
        // DOM elements
        this.searchInput = document.getElementById('bannerSearchInput');
        this.clearBtn = document.getElementById('bannerSearchClearBtn');
        this.loading = document.getElementById('bannerSearchLoading');
        this.results = document.getElementById('bannerSearchResults');
        this.resultsContent = document.getElementById('bannerResultsContent');
        this.suggestions = document.getElementById('bannerSearchSuggestions');
        this.suggestionsContent = document.getElementById('bannerSuggestionsContent');
        
        // State management
        this.searchTimeout = null;
        this.suggestionsTimeout = null;
        this.isSearching = false;
        this.isGettingSuggestions = false;
        this.selectedSuggestionIndex = -1;
        this.currentSuggestions = [];
        this.currentQuery = '';
        this.currentSuggestionsController = null;
        this.currentSearchController = null;
        
        // Caching
        this.suggestionCache = new Map();
        this.cacheExpiry = 2 * 60 * 1000; // 2 minutes
        this.lastQuery = '';
        this.lastQueryTime = 0;
        
        // Module references (will be set by main module)
        this.suggestionsModule = null;
        this.resultsModule = null;
        this.userProfileModule = null;
        this.ticketModule = null;
        this.uiModule = null;
        this.apiModule = null;
        
        console.log('Core Search Module: Search input found:', !!this.searchInput);
        this.init();
    }
    
    init() {
        if (!this.searchInput) {
            console.error('Core Search Module: Search input not found!');
            return;
        }
        
        console.log('Core Search Module: Initializing event listeners...');
        
        // Input event handling with proper debouncing
        this.searchInput.addEventListener('input', (e) => {
            this.handleInput(e.target.value);
        });
        
        // Clear button
        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => {
                this.clearSearch();
            });
        }
        
        // Keyboard navigation
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeydown(e);
        });
        
        // Click outside to close results
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.banner-search-container')) {
                this.hideAll();
            }
        });
        
        // Focus to show suggestions if there's a query
        this.searchInput.addEventListener('focus', () => {
            if (this.searchInput.value.trim()) {
                this.showSuggestions();
            }
        });
        
        // Blur to hide suggestions after a delay
        this.searchInput.addEventListener('blur', () => {
            setTimeout(() => {
                if (!this.suggestions?.matches(':hover')) {
                    this.hideSuggestions();
                }
            }, 150);
        });
        
        console.log('Core Search Module: Initialization complete');
    }
    
    handleInput(value) {
        const query = value.trim();
        this.currentQuery = query;
        
        // Show/hide clear button immediately
        if (this.clearBtn) {
            this.clearBtn.style.display = query ? 'flex' : 'none';
        }
        
        // Cancel any pending requests immediately when input changes
        if (this.currentSuggestionsController) {
            this.currentSuggestionsController.abort();
        }
        if (this.currentSearchController) {
            this.currentSearchController.abort();
        }
        
        if (!query) {
            this.hideAll();
            return;
        }
        
        // Show instant pattern-based suggestions immediately (no delay)
        this.suggestionsModule.showInstantSuggestions(query);
        
        // Check if this is a duplicate query to avoid unnecessary API calls
        const now = Date.now();
        const isDuplicateQuery = this.lastQuery === query && (now - this.lastQueryTime) < 500; // Reduced to 500ms for faster response
        
        if (!isDuplicateQuery) {
            this.lastQuery = query;
            this.lastQueryTime = now;
            
            // Clear any existing timeouts
            if (this.searchTimeout) {
                clearTimeout(this.searchTimeout);
            }
            if (this.suggestionsTimeout) {
                clearTimeout(this.suggestionsTimeout);
            }
            
            // Start suggestions immediately without any delay
            this.suggestionsModule.getSuggestions(query);
            
            // Only perform full search for queries longer than 2 characters to reduce noise
            if (query.length > 2) {
                // Minimal delay for search to prioritize suggestions
                this.searchTimeout = setTimeout(() => {
                    this.performSearch(query);
                }, 10); // Reduced to 10ms for near-instant response
            }
        }
    }
    
    async performSearch(query) {
        if (this.isSearching) return;
        
        // Cancel any pending search request
        if (this.currentSearchController) {
            this.currentSearchController.abort();
        }
        
        // Create new abort controller for this search request
        this.currentSearchController = new AbortController();
        
        this.isSearching = true;
        this.showLoading(true);
        this.hideSuggestions();
        
        try {
            const results = await this.apiModule.performSearch(query, this.currentSearchController.signal);
            this.resultsModule.displayResults(results);
        } catch (error) {
            if (error.name === 'AbortError') {
                return;
            }
            console.error('Search error:', error);
            // Show helpful search options on error
            const helpfulResults = this.suggestionsModule.createHelpfulSearchResults(query);
            this.resultsModule.displayResults(helpfulResults);
        } finally {
            this.isSearching = false;
            this.showLoading(false);
        }
    }
    
    handleSuggestionClick(suggestion) {
        console.log('Core Search Module: Suggestion clicked:', suggestion);
        // Hide suggestions dropdown immediately when any suggestion is clicked
        this.hideSuggestions();
        
        if (suggestion.url) {
            console.log('Core Search Module: Navigating to URL:', suggestion.url);
            window.location.href = suggestion.url;
        } else if (suggestion.type === 'clock_id') {
            console.log('Core Search Module: Handling clock ID lookup for:', suggestion.data.clock_id);
            // Handle clock ID lookup with user data if available
            this.userProfileModule.handleClockIdLookup(suggestion.data.clock_id, suggestion.data.user_data);
        } else {
            console.log('Core Search Module: Defaulting to universal search');
            // Default to universal search
            window.location.href = `/unified_search?q=${encodeURIComponent(this.currentQuery)}`;
        }
    }
    
    handleResultClick(result) {
        // Hide results dropdown immediately when any result is clicked
        this.hideResults();
        
        if (result.url) {
            window.location.href = result.url;
        } else {
            window.location.href = `/unified_search?q=${encodeURIComponent(this.currentQuery)}`;
        }
    }
    
    updateSuggestionSelection() {
        const items = this.suggestionsContent?.querySelectorAll('.banner-search-suggestion-item');
        if (!items) return;
        
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === this.selectedSuggestionIndex);
        });
    }
    
    navigateSuggestions(direction) {
        const items = this.suggestionsContent?.querySelectorAll('.banner-search-suggestion-item');
        if (!items || items.length === 0) return;
        
        this.selectedSuggestionIndex += direction;
        
        if (this.selectedSuggestionIndex < 0) {
            this.selectedSuggestionIndex = items.length - 1;
        } else if (this.selectedSuggestionIndex >= items.length) {
            this.selectedSuggestionIndex = 0;
        }
        
        this.updateSuggestionSelection();
        
        // Scroll to selected item
        const selectedItem = items[this.selectedSuggestionIndex];
        if (selectedItem) {
            selectedItem.scrollIntoView({ block: 'nearest' });
        }
    }
    
    showSuggestions() {
        if (this.suggestions) {
            this.suggestions.classList.add('show');
        }
    }
    
    hideSuggestions() {
        if (this.suggestions) {
            this.suggestions.classList.remove('show');
        }
        this.selectedSuggestionIndex = -1;
    }
    
    showResults() {
        if (this.results) {
            this.results.classList.add('show');
        }
    }
    
    hideResults() {
        if (this.results) {
            this.results.classList.remove('show');
        }
    }
    
    hideAll() {
        this.hideResults();
        this.hideSuggestions();
    }
    
    showLoading(show) {
        if (this.loading) {
            this.loading.style.display = show ? 'block' : 'none';
        }
    }
    
    clearSearch() {
        this.searchInput.value = '';
        this.hideAll();
        if (this.clearBtn) {
            this.clearBtn.style.display = 'none';
        }
        this.searchInput.focus();
    }
    
    handleKeydown(e) {
        if (e.key === 'Escape') {
            this.hideAll();
            this.searchInput.blur();
        } else if (e.key === 'Enter') {
            if (this.suggestions?.classList.contains('show')) {
                const selectedItem = this.suggestionsContent?.querySelector('.banner-search-suggestion-item.selected');
                if (selectedItem) {
                    selectedItem.click();
                } else {
                    const firstItem = this.suggestionsContent?.querySelector('.banner-search-suggestion-item');
                    if (firstItem) {
                        firstItem.click();
                    }
                }
            } else if (this.results?.classList.contains('show')) {
                const firstResult = this.resultsContent?.querySelector('.banner-search-result-item');
                if (firstResult) {
                    firstResult.click();
                }
            } else {
                this.performSearch(this.searchInput.value);
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.navigateSuggestions(1);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.navigateSuggestions(-1);
        }
    }
    
    // Setter methods for module references
    setSuggestionsModule(module) {
        this.suggestionsModule = module;
    }
    
    setResultsModule(module) {
        this.resultsModule = module;
    }
    
    setUserProfileModule(module) {
        this.userProfileModule = module;
    }
    
    setTicketModule(module) {
        this.ticketModule = module;
    }
    
    setUIModule(module) {
        this.uiModule = module;
    }
    
    setAPIModule(module) {
        this.apiModule = module;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CoreSearch;
} else {
    window.CoreSearch = CoreSearch;
} 