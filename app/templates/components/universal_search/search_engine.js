// Universal Search Component - Enhanced version with instant suggestions
(function() {
    'use strict';
    
    // Check if already initialized to prevent duplicate initialization
    if (window.universalSearchInitialized) {
        return;
    }
    
    class UniversalSearch {
        constructor() {
            // Get all required DOM elements
            this.searchInput = document.getElementById('universalSearchInput');
            this.clearBtn = document.getElementById('searchClearBtn');
            this.loading = document.getElementById('searchLoading');
            this.results = document.getElementById('searchResults');
            this.resultsContent = document.getElementById('resultsContent');
            this.resultsCount = document.getElementById('resultsCount');
            this.suggestions = document.getElementById('searchSuggestions');
            this.suggestionsContent = document.getElementById('suggestionsContent');
            this.filters = document.getElementById('searchFilters');
            this.viewAllBtn = document.getElementById('viewAllResults');
            this.blurOverlay = document.getElementById('searchBlurOverlay');
            
            // Check if all required elements exist
            if (!this.searchInput || !this.clearBtn || !this.loading || !this.results || 
                !this.resultsContent || !this.resultsCount || !this.suggestions || 
                !this.suggestionsContent || !this.filters || !this.viewAllBtn) {
                console.warn('Universal search elements not found. Search functionality disabled.');
                return;
            }
            
            this.currentQuery = '';
            this.searchTimeout = null;
            this.suggestionsTimeout = null;
            this.isSearching = false;
            this.currentResults = []; // Store current search results
            this.isInteractingWithSuggestions = false; // Track if user is interacting with suggestions
            
            // Buffer for suggestion HTML so we can merge with results later
            this._suggestionsMarkup = '';
            
            // Caching for instant suggestions
            this.suggestionCache = new Map();
            this.userCache = new Map();
            this.officeCache = new Map();
            this.workstationCache = new Map();
            this.cacheExpiry = 5 * 60 * 1000; // 5 minutes
            
            // Pre-loaded common suggestions
            this.commonSuggestions = [];
            this.preloadedData = {
                offices: [],
                workstations: [],
                recentSearches: []
            };
            
            this.init();
            this.preloadCommonData();
        }
        
        init() {
            // Event listeners
            this.searchInput.addEventListener('input', this.handleInput.bind(this));
            this.searchInput.addEventListener('focus', this.handleFocus.bind(this));
            this.searchInput.addEventListener('blur', this.handleBlur.bind(this));
            this.searchInput.addEventListener('keydown', this.handleKeydown.bind(this));
            
            this.clearBtn.addEventListener('click', this.clearSearch.bind(this));
            this.viewAllBtn.addEventListener('click', this.viewAllResults.bind(this));
            
            // Filter buttons
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.addEventListener('click', this.handleFilterClick.bind(this));
            });
            
            // Global keyboard shortcut
            document.addEventListener('keydown', this.handleGlobalKeydown.bind(this));
            
            // Enhanced click outside handling
            document.addEventListener('click', this.handleClickOutside.bind(this));
            
            // Mouse events for suggestions to prevent premature hiding
            this.suggestions.addEventListener('mouseenter', () => {
                this.isInteractingWithSuggestions = true;
            });
            
            this.suggestions.addEventListener('mouseleave', () => {
                this.isInteractingWithSuggestions = false;
                // Only hide if not focused on input
                if (!this.searchInput.matches(':focus')) {
                    setTimeout(() => {
                        if (!this.isInteractingWithSuggestions && !this.searchInput.matches(':focus')) {
                            this.hideSuggestions();
                        }
                    }, 200); // Increased timeout to prevent premature hiding
                }
            });
            
            // Prevent suggestion hiding when clicking inside suggestions
            this.suggestions.addEventListener('click', (e) => {
                e.stopPropagation();
            });
            
            // Prevent result hiding when clicking inside results
            this.results.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }

        // Pre-load common data for instant suggestions
        async preloadCommonData() {
            try {
                // Load recent searches from localStorage
                const recentSearches = JSON.parse(localStorage.getItem('universalSearchRecent') || '[]');
                this.preloadedData.recentSearches = recentSearches.slice(0, 10);

                // Pre-load some common office data (async, non-blocking)
                this.preloadOfficesAndWorkstations();

                // Generate common smart suggestions
                this.generateCommonSuggestions();
            } catch (error) {
                console.warn('Error preloading data:', error);
            }
        }

        async preloadOfficesAndWorkstations() {
            try {
                // Pre-load a small set of common offices/workstations for instant suggestions
                const response = await fetch('/unified_search?q=&limit=20', {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Cache-Control': 'max-age=300' // 5 minute cache
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    this.preloadedData.offices = data.offices || [];
                    this.preloadedData.workstations = data.workstations || [];
                }
            } catch (error) {
                console.warn('Error preloading offices/workstations:', error);
            }
        }

        generateCommonSuggestions() {
            this.commonSuggestions = [
                { text: 'Search users', icon: 'bi bi-person', subtitle: 'Find people', type: 'text' },
                { text: 'Search offices', icon: 'bi bi-building', subtitle: 'Find locations', type: 'text' },
                { text: 'Search workstations', icon: 'bi bi-laptop', subtitle: 'Find devices', type: 'text' },
                { text: 'Search knowledge base', icon: 'bi bi-journal-text', subtitle: 'Find guides', type: 'text' },
                { text: 'Check outages', icon: 'bi bi-exclamation-triangle', subtitle: 'System status', type: 'text' }
            ];
        }

        // Cache management
        getCachedSuggestions(query) {
            const cached = this.suggestionCache.get(query.toLowerCase());
            if (cached && (Date.now() - cached.timestamp) < this.cacheExpiry) {
                return cached.data;
            }
            return null;
        }

        setCachedSuggestions(query, data) {
            this.suggestionCache.set(query.toLowerCase(), {
                data: data,
                timestamp: Date.now()
            });
        }

        // Save recent searches
        saveRecentSearch(query) {
            if (!query || query.length < 2) return;
            
            let recent = JSON.parse(localStorage.getItem('universalSearchRecent') || '[]');
            recent = recent.filter(item => item.toLowerCase() !== query.toLowerCase());
            recent.unshift(query);
            recent = recent.slice(0, 10); // Keep only 10 recent searches
            
            localStorage.setItem('universalSearchRecent', JSON.stringify(recent));
            this.preloadedData.recentSearches = recent;
        }
        
        handleInput(e) {
            // Clear previous timeouts first
            if (this.searchTimeout) {
                clearTimeout(this.searchTimeout);
            }
            if (this.suggestionsTimeout) {
                clearTimeout(this.suggestionsTimeout);
            }
            
            // Process input immediately without any timeout delays
            const query = this.searchInput.value.trim();
            this.currentQuery = query;
            
            // Show/hide clear button
            this.clearBtn.style.display = query ? 'block' : 'none';
            
            if (query.length >= 1) {
                // Show filters immediately for better UX
                this.filters.style.display = 'block';
                
                // INSTANT suggestions with the correct query
                this.getSuggestionsInstant(query);
                
                // Perform search immediately without debouncing
                this.performSearch(query);
            } else {
                this.hideResults();
                this.hideSuggestions();
                this.filters.style.display = 'none';
            }
        }

        // Instant suggestions without any delay
        getSuggestionsInstant(query) {
            // First, show cached suggestions immediately if available
            const cached = this.getCachedSuggestions(query);
            if (cached) {
                this.displaySuggestions(cached);
            } else {
                // Show partial suggestions immediately based on pre-loaded data
                this.displayPartialSuggestions(query);
            }

            // Then fetch fresh suggestions asynchronously immediately
            this.getSuggestions(query);
        }

        // Display partial suggestions immediately from cached/preloaded data
        displayPartialSuggestions(query) {
            // Ensure we're working with the absolute latest query
            const actualQuery = query || this.searchInput.value.trim() || this.currentQuery;
            const lowerQuery = actualQuery.toLowerCase();
            const suggestions = {
                textSuggestions: [],
                offices: [],
                workstations: [],
                clockSuggestions: []
            };

            // Add recent searches that match
            suggestions.textSuggestions = this.preloadedData.recentSearches
                .filter(search => search.toLowerCase().includes(lowerQuery))
                .slice(0, 3);

            // Add matching preloaded offices
            suggestions.offices = this.preloadedData.offices
                .filter(office => 
                    (office['Internal Name'] || '').toLowerCase().includes(lowerQuery) ||
                    (office.Number || '').toString().includes(actualQuery)
                )
                .slice(0, 3);

            // Add matching preloaded workstations
            suggestions.workstations = this.preloadedData.workstations
                .filter(ws => 
                    (ws.name || '').toLowerCase().includes(lowerQuery) ||
                    (ws.user || '').toLowerCase().includes(lowerQuery)
                )
                .slice(0, 3);

            // Generate clock ID suggestions instantly for numeric queries
            if (/^\d+$/.test(actualQuery.trim())) {
                const padded = actualQuery.trim().padStart(5, '0');
                const originalQuery = actualQuery.trim();
                
                suggestions.clockSuggestions = [
                    {
                        text: `Find user ${padded}`,
                        icon: 'bi bi-person',
                        subtitle: 'Lookup user by Clock ID',
                        type: 'clock_id',
                        data: { clock_id: padded }
                    },
                    {
                        text: `Search for workstation matching ${originalQuery}`,
                        icon: 'bi bi-laptop',
                        subtitle: 'Device search',
                        type: 'text'
                    },
                    {
                        text: `Search for office number ${originalQuery}`,
                        icon: 'bi bi-building',
                        subtitle: 'Office search',
                        type: 'text'
                    }
                ];
            }

            // Add common suggestions if query is short
            if (query.length <= 2) {
                suggestions.commonSuggestions = this.commonSuggestions
                    .filter(s => s.text.toLowerCase().includes(lowerQuery))
                    .slice(0, 3);
            }

            this.displaySuggestions(suggestions);
        }
        
        clearSearch() {
            this.searchInput.value = '';
            this.currentQuery = '';
            this.clearBtn.style.display = 'none';
            this.hideResults();
            this.hideSuggestions();
            this.filters.style.display = 'none';
            this.searchInput.focus();
        }
        
        showLoading(show, message = '') {
            // Toggle loader visibility
            this.loading.style.display = show ? 'flex' : 'none';
            // Disable / enable input & clear button to prevent concurrent searches only for clock-ID lookups (when a message is provided)
            const shouldDisable = show && message;
            this.searchInput.disabled = shouldDisable;
            this.clearBtn.disabled = shouldDisable;

            // Handle dynamic status text inside loader
            let statusEl = this.loading.querySelector('.loading-status-text');
            if (show && message) {
                if (!statusEl) {
                    statusEl = document.createElement('span');
                    statusEl.className = 'loading-status-text';
                    this.loading.appendChild(statusEl);
                }
                statusEl.textContent = message;

                // Hide input elements entirely so only loader + text remain
                if (!this._origPlaceholder) {
                    this._origPlaceholder = this.searchInput.placeholder;
                }
                this.searchInput.value = '';
                this.searchInput.placeholder = '';
                this.searchInput.style.display = 'none';
                if (this.searchIcon) this.searchIcon.style.display = 'none';
                this.clearBtn.style.display = 'none';

            } else if (statusEl) {
                statusEl.textContent = '';

                // Restore input elements once loading finishes
                this.searchInput.style.display = 'block';
                if (this.searchIcon) this.searchIcon.style.display = '';
                this.searchInput.placeholder = this._origPlaceholder || 'Search everything...';
                // Show clear button only if there is text
                this.clearBtn.style.display = this.currentQuery ? 'block' : 'none';
            }
        }
        
        hideSuggestions() {
            this.suggestions.style.display = 'none';
        }
        
        hideResults() {
            this.results.style.display = 'none';
        }
        
        viewAllResults() {
            if (this.currentQuery) {
                // Save to recent searches
                this.saveRecentSearch(this.currentQuery);
                
                const params = new URLSearchParams({ q: this.currentQuery });
                window.location.href = `/universal-search?${params}`;
            }
        }
        
        getContentTypeIcon(contentType) {
            const icons = {
                'kb_article': 'bi-journal-text',
                'outage': 'bi-exclamation-triangle',
                'user': 'bi-person',
                'office': 'bi-building',
                'workstation': 'bi-laptop',
                'document': 'bi-file-earmark-text',
                'note': 'bi-sticky'
            };
            return icons[contentType] || 'bi-file-earmark';
        }
        
        getContentTypeTitle(contentType) {
            const titles = {
                'kb_article': 'Knowledge Base',
                'outage': 'Outages',
                'user': 'Users',
                'office': 'Offices',
                'workstation': 'Workstations',
                'document': 'Documents',
                'note': 'Notes'
            };
            return titles[contentType] || 'Other';
        }
        
        formatDate(dateString) {
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
        }
        
        // Placeholder methods for remaining functionality
        handleFocus() {
            if (this.currentQuery.length >= 1) {
                this.filters.style.display = 'block';
                if (this.suggestions.style.display === 'block') {
                    this.suggestions.style.display = 'block';
                }
            }
            // Ensure blur overlay is active when focused
            if (this.blurOverlay) {
                this.blurOverlay.classList.add('active');
            }
        }
        
        handleBlur() {
            // Don't immediately hide - let the click outside handler manage this
            setTimeout(() => {
                if (!this.isInteractingWithSuggestions && !this.searchInput.matches(':focus')) {
                    this.hideSuggestions();
                }
            }, 50);
        }
        
        handleKeydown(e) {
            if (e.key === 'Escape') {
                this.clearSearch();
            } else if (e.key === 'Enter') {
                e.preventDefault();
                const q = this.currentQuery.trim();
                if (!q) return;
                this.viewAllResults();
                return;
            }
        }
        
        handleGlobalKeydown(e) {
            // Ctrl+K or Cmd+K to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.searchInput.focus();
            }
        }
        
        handleClickOutside(e) {
            // Check if click is outside the search interface
            const searchContainer = document.getElementById('universalSearchContainer');
            if (!searchContainer.contains(e.target)) {
                this.hideResults();
                this.hideSuggestions();
                this.filters.style.display = 'none';

                // Also close the universal search overlay completely
                if (window.closeUniversalSearchBar) {
                    window.closeUniversalSearchBar();
                }
                // Remove blur effect when clicking outside
                if (this.blurOverlay) {
                    this.blurOverlay.classList.remove('active');
                }
            }
        }
        
        handleFilterClick(e) {
            // Remove active class from all buttons
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Add active class to clicked button
            e.target.closest('.filter-btn').classList.add('active');
            
            // Re-run search with new filter if there's a current query
            if (this.currentQuery) {
                this.performSearch(this.currentQuery);
            }
        }
        
        async performSearch(query) {
            // Simplified version - full implementation would be included
            if (this.isSearching) return;
            this.isSearching = true;
            this.showLoading(true);
            
            try {
                // Implementation would be here
                // For now, just hide loading
                this.showLoading(false);
            } catch (error) {
                console.error('Search error:', error);
            } finally {
                this.isSearching = false;
                this.showLoading(false);
            }
        }
        
        async getSuggestions(query) {
            if (!query || query.length < 1) {
                this.displaySuggestions({
                    textSuggestions: [],
                    offices: [],
                    workstations: [],
                    clockSuggestions: []
                });
                return;
            }

            const suggestions = {
                textSuggestions: [],
                offices: [],
                workstations: [],
                clockSuggestions: []
            };

            try {
                // Check if query is a numeric Clock ID (1-5 digits)
                if (/^\d{1,5}$/.test(query.trim())) {
                    const padded = query.trim().padStart(5, '0');
                    
                    // Use the new Clock ID cache API for fast lookups
                    let cachedUser = null;
                    try {
                        const cacheRes = await fetch(`/api/clock-id/suggestions?q=${encodeURIComponent(query.trim())}`);
                        if (cacheRes.ok) {
                            const response = await cacheRes.json();
                            if (response.success && response.suggestions.length > 0) {
                                // Use the first suggestion (most relevant)
                                const suggestion = response.suggestions[0];
                                if (suggestion.type === 'clock_id') {
                                    suggestions.clockSuggestions.push({
                                        text: suggestion.display_text,
                                        icon: 'bi bi-person-circle',
                                        subtitle: suggestion.subtitle,
                                        type: 'clock_id',
                                        data: { clock_id: suggestion.clock_id }
                                    });
                                    
                                    // Add secondary option for full profile
                                    suggestions.clockSuggestions.push({
                                        text: `View ${suggestion.full_name}'s full profile`,
                                        icon: 'bi bi-person-badge',
                                        subtitle: 'Complete user information',
                                        type: 'clock_id',
                                        data: { clock_id: suggestion.clock_id }
                                    });
                                } else if (suggestion.type === 'clock_id_not_found') {
                                    suggestions.clockSuggestions.push({
                                        text: suggestion.display_text,
                                        icon: 'bi bi-person-badge',
                                        subtitle: suggestion.subtitle,
                                        type: 'clock_id',
                                        data: { clock_id: padded }
                                    });
                                }
                            }
                        }
                    } catch (error) {
                        console.warn('Clock ID cache lookup failed:', error);
                    }

                    // If no cache results, show generic clock ID suggestion
                    if (suggestions.clockSuggestions.length === 0) {
                        suggestions.clockSuggestions.push({
                            text: `Find user ${padded}`,
                            icon: 'bi bi-person-badge',
                            subtitle: 'Lookup user by Clock ID',
                            type: 'clock_id',
                            data: { clock_id: padded }
                        });
                    }
                } else {
                    // For non-numeric queries, get regular suggestions
                    const [universalRes, clockRes] = await Promise.allSettled([
                        fetch(`/api/universal-search/suggestions?q=${encodeURIComponent(query)}&limit=5`),
                        fetch(`/api/clock-id/suggestions?q=${encodeURIComponent(query)}`)
                    ]);

                    // Process universal search suggestions
                    if (universalRes.status === 'fulfilled' && universalRes.value.ok) {
                        const universalData = await universalRes.value.json();
                        if (universalData.success) {
                            // Add offices
                            if (universalData.offices && universalData.offices.length > 0) {
                                suggestions.offices = universalData.offices.slice(0, 3).map(office => ({
                                    text: office['Internal Name'] || office.name || 'Unknown Office',
                                    icon: 'bi bi-building',
                                    subtitle: office.Number ? `Office ${office.Number}` : 'Office',
                                    type: 'office',
                                    data: office
                                }));
                            }

                            // Add workstations
                            if (universalData.workstations && universalData.workstations.length > 0) {
                                suggestions.workstations = universalData.workstations.slice(0, 3).map(ws => ({
                                    text: ws.name || 'Unknown Workstation',
                                    icon: 'bi bi-laptop',
                                    subtitle: ws.user ? `User: ${ws.user}` : 'Workstation',
                                    type: 'workstation',
                                    data: ws
                                }));
                            }
                        }
                    }

                    // Process clock ID suggestions
                    if (clockRes.status === 'fulfilled' && clockRes.value.ok) {
                        const clockData = await clockRes.value.json();
                        if (clockData.success && clockData.suggestions.length > 0) {
                            suggestions.clockSuggestions = clockData.suggestions.slice(0, 3).map(suggestion => ({
                                text: suggestion.display_text,
                                icon: 'bi bi-person-circle',
                                subtitle: suggestion.subtitle,
                                type: 'clock_id',
                                data: { clock_id: suggestion.clock_id }
                            }));
                        }
                    }
                }

                // Cache the suggestions
                this.setCachedSuggestions(query, suggestions);
                
                // Display the suggestions
                this.displaySuggestions(suggestions);

            } catch (error) {
                console.error('Error getting suggestions:', error);
                // Show partial suggestions on error
                this.displayPartialSuggestions(query);
            }
        }
        
        displaySuggestions(allSuggestions) {
            if (!this.suggestionsContent) return;

            let html = '';
            let hasSuggestions = false;

            // Clock ID suggestions (highest priority)
            if (allSuggestions.clockSuggestions && allSuggestions.clockSuggestions.length > 0) {
                hasSuggestions = true;
                html += '<div class="suggestion-category">';
                html += '<div class="category-title">Clock ID Lookups</div>';
                
                allSuggestions.clockSuggestions.forEach(suggestion => {
                    html += `
                        <div class="suggestion-item" onclick="window.universalSearchInstance.selectSuggestion('${suggestion.text}', '${suggestion.type}', ${JSON.stringify(suggestion.data)})">
                            <div class="suggestion-icon">
                                <i class="${suggestion.icon}"></i>
                            </div>
                            <div class="suggestion-content">
                                <div class="suggestion-text">${suggestion.text}</div>
                                <div class="suggestion-subtitle">${suggestion.subtitle}</div>
                            </div>
                            <div class="suggestion-action">
                                <i class="bi bi-arrow-right"></i>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            // Office suggestions
            if (allSuggestions.offices && allSuggestions.offices.length > 0) {
                hasSuggestions = true;
                html += '<div class="suggestion-category">';
                html += '<div class="category-title">Offices</div>';
                
                allSuggestions.offices.forEach(office => {
                    html += `
                        <div class="suggestion-item" onclick="window.universalSearchInstance.selectSuggestion('${office.text}', '${office.type}', ${JSON.stringify(office.data)})">
                            <div class="suggestion-icon">
                                <i class="${office.icon}"></i>
                            </div>
                            <div class="suggestion-content">
                                <div class="suggestion-text">${office.text}</div>
                                <div class="suggestion-subtitle">${office.subtitle}</div>
                            </div>
                            <div class="suggestion-action">
                                <i class="bi bi-arrow-right"></i>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            // Workstation suggestions
            if (allSuggestions.workstations && allSuggestions.workstations.length > 0) {
                hasSuggestions = true;
                html += '<div class="suggestion-category">';
                html += '<div class="category-title">Workstations</div>';
                
                allSuggestions.workstations.forEach(ws => {
                    html += `
                        <div class="suggestion-item" onclick="window.universalSearchInstance.selectSuggestion('${ws.text}', '${ws.type}', ${JSON.stringify(ws.data)})">
                            <div class="suggestion-icon">
                                <i class="${ws.icon}"></i>
                            </div>
                            <div class="suggestion-content">
                                <div class="suggestion-text">${ws.text}</div>
                                <div class="suggestion-subtitle">${ws.subtitle}</div>
                            </div>
                            <div class="suggestion-action">
                                <i class="bi bi-arrow-right"></i>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            // Text suggestions (recent searches, etc.)
            if (allSuggestions.textSuggestions && allSuggestions.textSuggestions.length > 0) {
                hasSuggestions = true;
                html += '<div class="suggestion-category">';
                html += '<div class="category-title">Recent Searches</div>';
                
                allSuggestions.textSuggestions.forEach(suggestion => {
                    html += `
                        <div class="suggestion-item" onclick="window.universalSearchInstance.selectSuggestion('${suggestion}', 'text')">
                            <div class="suggestion-icon">
                                <i class="bi bi-clock-history"></i>
                            </div>
                            <div class="suggestion-content">
                                <div class="suggestion-text">${suggestion}</div>
                                <div class="suggestion-subtitle">Recent search</div>
                            </div>
                            <div class="suggestion-action">
                                <i class="bi bi-arrow-right"></i>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            // Common suggestions for short queries
            if (allSuggestions.commonSuggestions && allSuggestions.commonSuggestions.length > 0) {
                hasSuggestions = true;
                html += '<div class="suggestion-category">';
                html += '<div class="category-title">Quick Actions</div>';
                
                allSuggestions.commonSuggestions.forEach(suggestion => {
                    html += `
                        <div class="suggestion-item" onclick="window.universalSearchInstance.selectSuggestion('${suggestion.text}', '${suggestion.type}')">
                            <div class="suggestion-icon">
                                <i class="${suggestion.icon}"></i>
                            </div>
                            <div class="suggestion-content">
                                <div class="suggestion-text">${suggestion.text}</div>
                                <div class="suggestion-subtitle">${suggestion.subtitle}</div>
                            </div>
                            <div class="suggestion-action">
                                <i class="bi bi-arrow-right"></i>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            // View all results option
            if (hasSuggestions && this.currentQuery.trim()) {
                html += `
                    <div class="suggestion-category">
                        <div class="suggestion-item suggestion-viewall" onclick="window.universalSearchInstance.selectSuggestion('view_all', 'view_all')">
                            <div class="suggestion-icon">
                                <i class="bi bi-search"></i>
                            </div>
                            <div class="suggestion-content">
                                <div class="suggestion-text">View all results for "${this.currentQuery}"</div>
                                <div class="suggestion-subtitle">Complete search results</div>
                            </div>
                            <div class="suggestion-action">
                                <i class="bi bi-arrow-right"></i>
                            </div>
                        </div>
                    </div>
                `;
            }

            this.suggestionsContent.innerHTML = html;
            this.suggestions.style.display = hasSuggestions ? 'block' : 'none';
        }

        // Handle suggestion selection
        selectSuggestion(suggestion, type = 'text', data = {}) {
            console.log('selectSuggestion called:', { suggestion, type, data });
            
            if (type === 'view_all') {
                this.viewAllResults();
                return;
            }
            
            if (type === 'clock_id') {
                const cid = (data.clock_id || suggestion).toString().replace(/\D/g, '').padStart(5, '0');
                console.log('Clock ID lookup:', cid);
                if (cid) {
                    this.lookupClockId(cid);
                }
                return;
            } else if (type === 'office' && data) {
                // Show office detail modal
                console.log('Office detail:', data);
                if (window.showUniversalSearchDetail) {
                    window.showUniversalSearchDetail('office', data['Internal Name'] || data.name || suggestion);
                }
                return;
            } else if (type === 'workstation' && data) {
                // Show workstation detail modal
                console.log('Workstation detail:', data);
                if (window.showUniversalSearchDetail) {
                    window.showUniversalSearchDetail('workstation', data.name || suggestion);
                }
                return;
            } else {
                // Handle text-based suggestions
                console.log('Text-based suggestion:', suggestion);
                this.searchInput.value = suggestion;
                this.currentQuery = suggestion;
                this.clearBtn.style.display = 'block';
                this.performSearch(suggestion);
            }
        }

        // Clock ID lookup functionality
        async lookupClockId(clockId) {
            try {
                // Normalize clock ID (remove leading zeros)
                const normalizedId = clockId.replace(/^0+/, '');
                
                // Show loading with personalized message
                const genericPhrases = [
                    'Obtaining user profile…',
                    'Searching for user account…',
                    'Fetching account information…'
                ];
                let personalisedMessage = genericPhrases[Math.floor(Math.random() * genericPhrases.length)];
                
                // Try to get personalized message from cache first
                try {
                    const cacheRes = await fetch(`/api/clock-id/lookup/${normalizedId}`);
                    if (cacheRes.ok) {
                        const cached = await cacheRes.json();
                        if (cached.success && cached.user && cached.user.first_name) {
                            const personalized = [
                                `Fetching ${cached.user.first_name}'s account information…`,
                                `Grabbing ${cached.user.first_name}'s credentials…`,
                                `Preparing ${cached.user.first_name}'s profile…`
                            ];
                            personalisedMessage = personalized[Math.floor(Math.random() * personalized.length)];
                            
                            // Show the cached user data immediately
                            this.showLoading(true, personalisedMessage);
                            if (window.showClockIdUserModal) {
                                window.showClockIdUserModal(cached.user);
                            }
                            return;
                        }
                    }
                } catch (error) {
                    console.warn('Cache lookup failed, trying fallback:', error);
                }
                
                // If cache lookup failed or user not found, try fallback to PowerShell
                this.showLoading(true, personalisedMessage);
                
                try {
                    // Try fallback to PowerShell lookup
                    const fallbackRes = await fetch(`/api/clock-id/fallback/${normalizedId}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    
                    if (fallbackRes.ok) {
                        const data = await fallbackRes.json();
                        if (data.success && data.user) {
                            if (window.showClockIdUserModal) {
                                window.showClockIdUserModal(data.user);
                            } else {
                                // Fallback if modal function doesn't exist
                                this.displayError(`User found: ${data.user.full_name} (${data.user.username})`);
                            }
                            return;
                        } else {
                            this.displayError(data.error || `No user found for Clock ID ${clockId}`);
                            return;
                        }
                    }
                } catch (fallbackError) {
                    console.warn('Fallback lookup failed:', fallbackError);
                }
                
                // If both cache and fallback failed, show error
                this.displayError(`No user found for Clock ID ${clockId}`);
                
            } catch (err) {
                console.error('Clock ID lookup error:', err);
                this.displayError('Clock ID lookup failed.');
            } finally {
                this.showLoading(false);
            }
        }

        // Display error message
        displayError(message) {
            if (this.resultsContent) {
                this.resultsContent.innerHTML = `
                    <div style="text-align: center; padding: 2rem; color: #dc3545;">
                        <i class="bi bi-exclamation-triangle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                        <h4>Error</h4>
                        <p>${message}</p>
                    </div>
                `;
                this.results.style.display = 'block';
            }
        }
    }
    
    // Initialize universal search when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        // Only initialize if the search container exists and hasn't been initialized
        if (document.getElementById('universalSearchContainer') && !window.universalSearchInitialized) {
            window.universalSearchInstance = new UniversalSearch();
            window.universalSearchInitialized = true;
        }
    });
})(); 