// Banner Search Module
// Handles banner search functionality, suggestions, and user profile modals

(function() {
    'use strict';
    
    class BannerSearch {
        constructor() {
            this.searchInput = document.getElementById('bannerSearchInput');
            this.clearBtn = document.getElementById('bannerSearchClearBtn');
            this.loading = document.getElementById('bannerSearchLoading');
            this.results = document.getElementById('bannerSearchResults');
            this.resultsContent = document.getElementById('bannerResultsContent');
            this.suggestions = document.getElementById('bannerSearchSuggestions');
            this.suggestionsContent = document.getElementById('bannerSuggestionsContent');
            
            this.searchTimeout = null;
            this.suggestionsTimeout = null;
            this.isSearching = false;
            this.isGettingSuggestions = false;
            this.selectedSuggestionIndex = -1;
            this.currentSuggestions = [];
            this.currentQuery = '';
            this.currentSuggestionsController = null;
            this.currentSearchController = null;
            
            // Caching for suggestions
            this.suggestionCache = new Map();
            this.cacheExpiry = 2 * 60 * 1000; // 2 minutes for faster cache refresh
            this.lastQuery = '';
            this.lastQueryTime = 0;
            
            this.init();
        }
        
        init() {
            if (!this.searchInput) return;
            
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
            this.showInstantSuggestions(query);
            
            // Check if this is a duplicate query to avoid unnecessary API calls
            const now = Date.now();
            const isDuplicateQuery = this.lastQuery === query && (now - this.lastQueryTime) < 1000; // 1 second threshold
            
            if (!isDuplicateQuery) {
                this.lastQuery = query;
                this.lastQueryTime = now;
                
                // For all query lengths, start API calls immediately with minimal debouncing
                // Use a very short delay (30ms) to prevent excessive API calls during rapid typing
                // but still provide near-instant feedback
                const minimalDelay = 30;
                
                // Clear any existing timeouts
                if (this.searchTimeout) {
                    clearTimeout(this.searchTimeout);
                }
                if (this.suggestionsTimeout) {
                    clearTimeout(this.suggestionsTimeout);
                }
                
                // Start both suggestions and search with minimal delay
                this.suggestionsTimeout = setTimeout(() => {
                    this.getSuggestions(query);
                }, minimalDelay);
                
                // Only perform full search for queries longer than 2 characters to reduce noise
                if (query.length > 2) {
                this.searchTimeout = setTimeout(() => {
                    this.performSearch(query);
                    }, minimalDelay + 15); // Slight stagger to prioritize suggestions
                }
            }
        }
        
        showInstantSuggestions(query) {
            // Show instant pattern-based suggestions immediately (no API calls)
            const instantSuggestions = [];
            const trimmedQuery = query.trim();
            
            // Pattern recognition for immediate feedback
            if (/^\d{1,5}$/.test(trimmedQuery)) {
                // Clock ID pattern - show immediate suggestion
                const padded = trimmedQuery.padStart(5, '0');
                instantSuggestions.push({
                    text: `Find user ${padded}`,
                    icon: 'bi bi-person-badge',
                    subtitle: 'View user profile',
                    type: 'clock_id',
                    data: { clock_id: padded }
                });
            } else if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(trimmedQuery)) {
                // IP address pattern
                instantSuggestions.push({
                    text: `Search for IP ${trimmedQuery}`,
                    icon: 'bi bi-hdd-network',
                    subtitle: 'Find devices with this IP',
                    type: 'ip_search',
                    data: { ip: trimmedQuery }
                });
            } else if (/^[0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}$/.test(trimmedQuery)) {
                // MAC address pattern
                instantSuggestions.push({
                    text: `Search for MAC ${trimmedQuery}`,
                    icon: 'bi bi-hdd-network',
                    subtitle: 'Find devices with this MAC address',
                    type: 'mac_search',
                    data: { mac: trimmedQuery }
                });
            } else if (/^[A-Z]{2,3}-\d{4,6}$/i.test(trimmedQuery)) {
                // Ticket pattern
                instantSuggestions.push({
                    text: `Search for ticket ${trimmedQuery.toUpperCase()}`,
                    icon: 'bi bi-ticket-detailed',
                    subtitle: 'Find ticket information',
                    type: 'ticket_search',
                    data: { ticket: trimmedQuery.toUpperCase() }
                });
            } else if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedQuery)) {
                // Email pattern
                instantSuggestions.push({
                    text: `Search for email ${trimmedQuery}`,
                    icon: 'bi bi-envelope',
                    subtitle: 'Find user by email address',
                    type: 'email_search',
                    data: { email: trimmedQuery }
                });
            } else if (/^\d{3}-\d{3}-\d{4}$/.test(trimmedQuery)) {
                // Phone pattern
                instantSuggestions.push({
                    text: `Search for phone ${trimmedQuery}`,
                    icon: 'bi bi-telephone',
                    subtitle: 'Find user by phone number',
                    type: 'phone_search',
                    data: { phone: trimmedQuery }
                });
            }
            
            // Enhanced instant suggestions for different content types
            if (trimmedQuery.length >= 2) {
                // Workstation pattern (computer names often start with letters and contain numbers)
                if (/^[A-Za-z]/.test(trimmedQuery) && /[A-Za-z0-9]/.test(trimmedQuery)) {
                    instantSuggestions.push({
                        text: `Find workstation "${trimmedQuery}"`,
                        icon: 'bi bi-laptop',
                        subtitle: 'Search workstations database',
                        type: 'workstation_search',
                        data: { query: trimmedQuery }
                    });
                }
                
                // Office pattern (office names often contain letters and may have numbers)
                if (/^[A-Za-z]/.test(trimmedQuery)) {
                    instantSuggestions.push({
                        text: `Find office "${trimmedQuery}"`,
                        icon: 'bi bi-building',
                        subtitle: 'Search offices database',
                        type: 'office_search',
                        data: { query: trimmedQuery }
                    });
                }
                
                // Knowledge base pattern (any text query)
                instantSuggestions.push({
                    text: `Search KB for "${trimmedQuery}"`,
                    icon: 'bi bi-journal-text',
                    subtitle: 'Search knowledge base articles',
                    type: 'kb_search',
                    data: { query: trimmedQuery }
                });
                
                // Notes pattern (any text query)
                instantSuggestions.push({
                    text: `Search notes for "${trimmedQuery}"`,
                    icon: 'bi bi-sticky',
                    subtitle: 'Search user notes',
                    type: 'note_search',
                    data: { query: trimmedQuery }
                });
            }
            
            // Always add helpful search options for any query
            instantSuggestions.push({
                text: `Search for "${trimmedQuery}"`,
                subtitle: 'Universal search across all content',
                url: `/unified_search?q=${encodeURIComponent(trimmedQuery)}`,
                icon: 'bi-search',
                type: 'search'
            });
            
            // Show instant suggestions immediately
            this.displaySuggestions(instantSuggestions);
        }
        
        async getSuggestions(query) {
            if (this.isGettingSuggestions) return;
            
            // Cancel any pending suggestions request
            if (this.currentSuggestionsController) {
                this.currentSuggestionsController.abort();
            }
            
            // Create new abort controller for this suggestions request
            this.currentSuggestionsController = new AbortController();
            
            this.isGettingSuggestions = true;
            
            try {
                // Fetch from multiple endpoints simultaneously for comprehensive results
                const [unifiedResponse, universalResponse, kbResponse, notesResponse] = await Promise.allSettled([
                    // Unified search for offices and workstations
                    fetch(`/unified_search?q=${encodeURIComponent(query)}&limit=8`, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json',
                            'Cache-Control': 'max-age=60'
                        },
                        signal: this.currentSuggestionsController.signal
                    }),
                    
                    // Universal search for KB articles, notes, and other content
                    fetch(`/universal-search?q=${encodeURIComponent(query)}&limit=5`, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json',
                            'Cache-Control': 'max-age=60'
                        },
                        signal: this.currentSuggestionsController.signal
                    }),
                    
                    // KB API for knowledge base articles
                    fetch(`/api/kb?q=${encodeURIComponent(query)}&per_page=5`, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json',
                            'Cache-Control': 'max-age=60'
                        },
                        signal: this.currentSuggestionsController.signal
                    }),
                    
                    // Notes search for user notes
                    fetch(`/collab-notes/api/notes/search?q=${encodeURIComponent(query)}`, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json',
                            'Cache-Control': 'max-age=60'
                        },
                        signal: this.currentSuggestionsController.signal
                    })
                ]);
                
                // For clock IDs, make a separate fast lookup call
                let clockSuggestions = [];
                if (/^\d{1,5}$/.test(query.trim())) {
                    try {
                        const cacheRes = await fetch(`/api/clock-id/suggestions?q=${encodeURIComponent(query.trim())}`, {
                            signal: this.currentSuggestionsController.signal
                        });
                        if (cacheRes.ok) {
                            const response = await cacheRes.json();
                            if (response.success && response.suggestions.length > 0) {
                                const suggestion = response.suggestions[0];
                                if (suggestion.type === 'clock_id') {
                                    // Show single clean suggestion for found user
                                    clockSuggestions.push({
                                        text: suggestion.display_text,
                                        icon: 'bi bi-person-circle',
                                        subtitle: 'View user profile',
                                        type: 'clock_id',
                                        data: { 
                                            clock_id: suggestion.clock_id,
                                            full_name: suggestion.full_name,
                                            user_data: suggestion
                                        }
                                    });
                                } else if (suggestion.type === 'clock_id_not_found') {
                                    clockSuggestions.push({
                                        text: suggestion.display_text,
                                        icon: 'bi bi-person-badge',
                                        subtitle: suggestion.subtitle,
                                        type: 'clock_id',
                                        data: { clock_id: suggestion.clock_id }
                                    });
                                }
                            }
                        }
                    } catch (error) {
                        // Clock ID lookup failed, continue with other suggestions
                        console.warn('Clock ID cache lookup failed:', error);
                    }
                }
                
                // Process unified search results (offices and workstations)
                let officeData = [];
                let workstationData = [];
                
                if (unifiedResponse.status === 'fulfilled' && unifiedResponse.value.ok) {
                    const unifiedData = await unifiedResponse.value.json();
                    officeData = unifiedData.offices || [];
                    workstationData = unifiedData.workstations || [];
                }
                
                // Process universal search results (KB articles, notes, etc.)
                let universalResults = [];
                if (universalResponse.status === 'fulfilled' && universalResponse.value.ok) {
                    const universalData = await universalResponse.value.json();
                    universalResults = universalData.results || [];
                }
                
                // Process KB API results
                let kbArticles = [];
                if (kbResponse.status === 'fulfilled' && kbResponse.value.ok) {
                    const kbData = await kbResponse.value.json();
                    kbArticles = kbData.articles || [];
                }
                
                // Process notes search results
                let notesData = [];
                if (notesResponse.status === 'fulfilled' && notesResponse.value.ok) {
                    const notesResponseData = await notesResponse.value.json();
                    notesData = Array.isArray(notesResponseData) ? notesResponseData : [];
                }
                
                // Combine all suggestions
                const allSuggestions = [
                    ...clockSuggestions
                ];
                
                // Add office suggestions
                if (officeData.length > 0) {
                    officeData.slice(0, 3).forEach(office => {
                        allSuggestions.push({
                            text: office['Internal Name'] || office.name || 'Unknown Office',
                            icon: 'bi bi-building',
                            subtitle: office.Number ? `Office ${office.Number}` : 'Office',
                            type: 'office',
                            data: office
                        });
                    });
                }
                
                // Add workstation suggestions
                if (workstationData.length > 0) {
                    workstationData.slice(0, 3).forEach(ws => {
                        allSuggestions.push({
                            text: ws.name || 'Unknown Workstation',
                            icon: 'bi bi-laptop',
                            subtitle: ws.user ? `User: ${ws.user}` : 'Workstation',
                            type: 'workstation',
                            data: ws
                        });
                    });
                }
                
                // Add knowledge base article suggestions
                if (kbArticles.length > 0) {
                    kbArticles.slice(0, 3).forEach(article => {
                        allSuggestions.push({
                            text: article.title || 'Unknown Article',
                            icon: 'bi bi-journal-text',
                            subtitle: article.description ? article.description.substring(0, 50) + '...' : 'Knowledge Base Article',
                            type: 'kb_article',
                            data: article
                        });
                    });
                }
                
                // Add notes suggestions
                if (notesData.length > 0) {
                    notesData.slice(0, 3).forEach(note => {
                        allSuggestions.push({
                            text: note.title || 'Unknown Note',
                            icon: 'bi bi-sticky',
                            subtitle: note.content ? note.content.substring(0, 50) + '...' : 'User Note',
                            type: 'note',
                            data: note
                        });
                    });
                }
                
                // Add universal search results (KB articles, notes, etc.)
                if (universalResults.length > 0) {
                    universalResults.slice(0, 3).forEach(result => {
                        // Skip if we already have this type of result
                        const existingType = allSuggestions.find(s => s.type === result.content_type);
                        if (!existingType) {
                            allSuggestions.push({
                                text: result.title || 'Unknown Result',
                                icon: this.getIconForContentType(result.content_type),
                                subtitle: result.description ? result.description.substring(0, 50) + '...' : result.content_type,
                                type: result.content_type,
                                data: result
                            });
                        }
                    });
                }
                
                // Always add helpful search options if we have few suggestions
                if (allSuggestions.length < 3) {
                    allSuggestions.push(...this.createHelpfulSuggestions(query));
                }
                
                this.currentSuggestions = allSuggestions;
                this.displaySuggestions(allSuggestions);
                
            } catch (error) {
                if (error.name === 'AbortError') {
                    return;
                }
                console.error('Suggestions error:', error);
                // Show helpful suggestions even on error
                this.displaySuggestions(this.createHelpfulSuggestions(query));
            } finally {
                this.isGettingSuggestions = false;
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
                // Use the unified search endpoint for better performance
                const response = await fetch(`/unified_search?q=${encodeURIComponent(query)}&limit=8`, {
                    signal: this.currentSearchController.signal
                });
                
                if (!response.ok) throw new Error('Search failed');
                
                const data = await response.json();
                let results = [];
                    
                    // Process office results
                    if (data.offices && data.offices.length > 0) {
                        data.offices.forEach(office => {
                            results.push({
                                title: office['Internal Name'] || office.name || 'Unknown Office',
                                description: `Office • ${office.Location || 'Unknown location'}`,
                            url: `/offices?search=${encodeURIComponent(query)}`,
                                content_type: 'office',
                                icon: 'bi-building-fill'
                            });
                        });
                    }
                    
                    // Process workstation results
                    if (data.workstations && data.workstations.length > 0) {
                        data.workstations.forEach(ws => {
                            results.push({
                                title: ws.name || 'Unknown Workstation',
                                description: `Workstation • ${ws.user || 'Unknown user'}`,
                            url: `/workstations?search=${encodeURIComponent(query)}`,
                                content_type: 'workstation',
                                icon: 'bi-laptop-fill'
                            });
                        });
                    }
                
                // If no results, provide helpful search options
                if (results.length === 0) {
                    results = this.createHelpfulSearchResults(query);
                }
                
                this.displayResults(results);
                
            } catch (error) {
                if (error.name === 'AbortError') {
                    return;
                }
                console.error('Search error:', error);
                // Show helpful search options on error
                this.displayResults(this.createHelpfulSearchResults(query));
            } finally {
                this.isSearching = false;
                this.showLoading(false);
            }
        }
        
        createHelpfulSearchResults(query) {
            const searchTerm = query.trim();
            const results = [];
                
                // Always provide helpful search options
                    results.push({
                        title: `Search for "${searchTerm}"`,
                        description: 'Universal search across all content',
                        url: `/unified_search?q=${encodeURIComponent(searchTerm)}`,
                        content_type: 'search',
                        icon: 'bi-search'
                    });
            
            results.push({
                title: `Find users like "${searchTerm}"`,
                description: 'Search user database',
                url: `/users?search=${encodeURIComponent(searchTerm)}`,
                content_type: 'user',
                icon: 'bi-person-fill'
            });
                    
                    results.push({
                        title: `Find workstations containing "${searchTerm}"`,
                        description: 'Search workstations database',
                        url: `/workstations?search=${encodeURIComponent(searchTerm)}`,
                        content_type: 'workstation',
                        icon: 'bi-laptop'
                    });
                    
                    results.push({
                        title: `Find offices containing "${searchTerm}"`,
                        description: 'Search offices database',
                        url: `/offices?search=${encodeURIComponent(searchTerm)}`,
                        content_type: 'office',
                        icon: 'bi-building'
                    });
                    
                    results.push({
                        title: `Find notes containing "${searchTerm}"`,
                        description: 'Search notes database',
                        url: `/notes?search=${encodeURIComponent(searchTerm)}`,
                        content_type: 'note',
                        icon: 'bi-journal-text'
                    });
            
            results.push({
                title: `Find devices containing "${searchTerm}"`,
                description: 'Search devices database',
                url: `/devices?search=${encodeURIComponent(searchTerm)}`,
                content_type: 'device',
                icon: 'bi-hdd-network'
            });
            
            return results;
        }
        
        createHelpfulSuggestions(query) {
            const searchTerm = query.trim();
            const suggestions = [];
            
            // Always provide helpful search options
            suggestions.push({
                text: `Search for "${searchTerm}"`,
                subtitle: 'Universal search across all content',
                url: `/unified_search?q=${encodeURIComponent(searchTerm)}`,
                icon: 'bi-search',
                type: 'search'
            });
            
            suggestions.push({
                text: `Find users like "${searchTerm}"`,
                subtitle: 'Search user database',
                url: `/users?search=${encodeURIComponent(searchTerm)}`,
                icon: 'bi-person-fill',
                type: 'user_search'
            });
            
            suggestions.push({
                text: `Find workstations containing "${searchTerm}"`,
                subtitle: 'Search workstations database',
                url: `/workstations?search=${encodeURIComponent(searchTerm)}`,
                icon: 'bi-laptop',
                type: 'workstation_search'
            });
            
            suggestions.push({
                text: `Find offices containing "${searchTerm}"`,
                subtitle: 'Search offices database',
                url: `/offices?search=${encodeURIComponent(searchTerm)}`,
                icon: 'bi-building',
                type: 'office_search'
            });
            
            suggestions.push({
                text: `Find notes containing "${searchTerm}"`,
                subtitle: 'Search notes database',
                url: `/notes?search=${encodeURIComponent(searchTerm)}`,
                icon: 'bi-journal-text',
                type: 'note_search'
            });
            
            suggestions.push({
                text: `Find devices containing "${searchTerm}"`,
                subtitle: 'Search devices database',
                url: `/devices?search=${encodeURIComponent(searchTerm)}`,
                icon: 'bi-hdd-network',
                type: 'device_search'
            });
            
            return suggestions;
        }
        
        displaySuggestions(suggestions) {
            if (!this.suggestionsContent) return;
            
            if (suggestions.length === 0) {
                this.hideSuggestions();
                return;
            }
            
            this.suggestionsContent.innerHTML = '';
            
            suggestions.forEach((suggestion, index) => {
                const item = document.createElement('div');
                item.className = 'banner-search-suggestion-item';
                item.innerHTML = `
                    <div class="banner-search-suggestion-icon">
                        <i class="${suggestion.icon}"></i>
                    </div>
                    <div class="banner-search-suggestion-content">
                        <div class="banner-search-suggestion-text">${suggestion.text}</div>
                        <div class="banner-search-suggestion-subtitle">${suggestion.subtitle || ''}</div>
                    </div>
                `;
                
                item.addEventListener('click', () => {
                    this.handleSuggestionClick(suggestion);
                });
                
                item.addEventListener('mouseenter', () => {
                    this.selectedSuggestionIndex = index;
                    this.updateSuggestionSelection();
                });
                
                this.suggestionsContent.appendChild(item);
            });
            
            this.showSuggestions();
        }
        
        displayResults(results) {
            if (!this.resultsContent) return;
            
            if (results.length === 0) {
                this.resultsContent.innerHTML = `
                    <div class="banner-search-no-results">
                        <i class="bi bi-search"></i>
                        <p>No results found</p>
                        <small>Try a different search term</small>
                    </div>
                `;
                this.showResults();
                return;
            }
            
            this.resultsContent.innerHTML = '';
            
            results.forEach(result => {
                const item = document.createElement('div');
                item.className = 'banner-search-result-item';
                item.innerHTML = `
                    <div class="banner-search-result-icon">
                        <i class="${result.icon || 'bi bi-file-text'}"></i>
                    </div>
                    <div class="banner-search-result-content">
                        <div class="banner-search-result-title">${result.title}</div>
                        <div class="banner-search-result-description">${result.description}</div>
                    </div>
                `;
                
                item.addEventListener('click', () => {
                    this.handleResultClick(result);
                });
                
                this.resultsContent.appendChild(item);
            });
            
            this.showResults();
        }
        
        displayError(message) {
            if (!this.resultsContent) return;
            
            this.resultsContent.innerHTML = `
                <div class="banner-search-error">
                    <i class="bi bi-exclamation-triangle"></i>
                    <p>${message}</p>
                </div>
            `;
            this.showResults();
        }
        
        handleSuggestionClick(suggestion) {
            // Hide suggestions dropdown immediately when any suggestion is clicked
            this.hideSuggestions();
            
            if (suggestion.url) {
                window.location.href = suggestion.url;
            } else if (suggestion.type === 'clock_id') {
                // Handle clock ID lookup with user data if available
                this.handleClockIdLookup(suggestion.data.clock_id, suggestion.data.user_data);
            } else {
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
        
        handleClockIdLookup(clockId, userData = null) {
            // Hide suggestions dropdown when opening user profile modal
            this.hideSuggestions();
            this.hideResults();
            
            // Show beautiful user profile modal
            this.showUserProfileModal(clockId, userData);
        }
        
        showUserProfileModal(clockId, userData = null) {
            // Create modal HTML with improved design
            const modalHTML = `
                <div id="userProfileModal" class="user-profile-modal-overlay">
                    <div class="user-profile-modal">
                        <div class="user-profile-modal-header">
                            <h3><i class="bi bi-person-circle"></i> User Profile</h3>
                        </div>
                        <button class="user-profile-modal-close" onclick="this.closest('.user-profile-modal-overlay').remove()">
                            <i class="bi bi-x-lg"></i>
                        </button>
                        <div class="user-profile-modal-content">
                            <div class="user-profile-loading">
                                <div class="loading-spinner"></div>
                                <p>Loading user information...</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Add modal to page
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            // Add click outside to close functionality
            const modalOverlay = document.getElementById('userProfileModal');
            modalOverlay.addEventListener('click', (e) => {
                if (e.target === modalOverlay) {
                    modalOverlay.remove();
                }
            });
            
            // Add escape key to close functionality
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    modalOverlay.remove();
                    document.removeEventListener('keydown', handleEscape);
                }
            };
            document.addEventListener('keydown', handleEscape);
            
            // Load user data immediately
            this.loadUserProfileData(clockId, userData);
        }
        
        async loadUserProfileData(clockId, userData = null) {
            const modalContent = document.querySelector('.user-profile-modal-content');
            
            try {
                let userInfo = userData;
                
                // Enhanced user lookup - try multiple sources to ensure any user can be found
                if (!userInfo) {
                    // First try the clock ID suggestions API
                    try {
                        const response = await fetch(`/api/clock-id/suggestions?q=${encodeURIComponent(clockId)}`);
                        if (response.ok) {
                            const data = await response.json();
                            if (data.success && data.suggestions.length > 0) {
                                userInfo = data.suggestions[0];
                            }
                        }
                    } catch (e) {
                        console.warn('Clock ID API failed, trying fallback:', e);
                    }
                    
                    // Fallback: try unified search if clock ID lookup fails
                    if (!userInfo || userInfo.type !== 'clock_id') {
                        try {
                            const searchResponse = await fetch(`/unified_search?q=${encodeURIComponent(clockId)}&limit=1`);
                            if (searchResponse.ok) {
                                const searchData = await searchResponse.json();
                                if (searchData.users && searchData.users.length > 0) {
                                    userInfo = searchData.users[0];
                                    userInfo.type = 'clock_id';
                                }
                            }
                        } catch (e) {
                            console.warn('Unified search fallback failed:', e);
                        }
                    }
                    
                    // Final fallback: create a basic user profile if no data found
                    if (!userInfo) {
                        userInfo = {
                            type: 'clock_id',
                            clock_id: clockId,
                            full_name: `User ${clockId}`,
                            status: 'Unknown',
                            title: 'Employee',
                            email: `${clockId}@company.com`,
                            department: 'Unknown'
                        };
                    }
                }
                
                // Generate initials for avatar with fallback
                const fullName = userInfo.full_name || `User ${clockId}`;
                const initials = fullName.split(' ').map(name => name.charAt(0)).join('').toUpperCase().slice(0, 2) || 'U';
                
                // Determine user status and badges
                const status = userInfo.status || 'Active';
                const isLocked = status.toLowerCase().includes('locked') || status.toLowerCase().includes('lockout');
                const isDisabled = status.toLowerCase().includes('disabled') || status.toLowerCase().includes('inactive');
                const isAdmin = userInfo.role === 'admin' || userInfo.department === 'IT' || userInfo.is_admin;
                const isVip = userInfo.is_vip || userInfo.priority === 'high';
                
                // Generate badges
                const badges = [];
                if (status.toLowerCase().includes('active') && !isLocked && !isDisabled) {
                    badges.push('<span class="user-profile-badge badge-active"><i class="bi bi-check-circle"></i> Active</span>');
                }
                if (isLocked) {
                    badges.push('<span class="user-profile-badge badge-locked"><i class="bi bi-lock"></i> Locked</span>');
                }
                if (isDisabled) {
                    badges.push('<span class="user-profile-badge badge-disabled"><i class="bi bi-x-circle"></i> Disabled</span>');
                }
                if (isAdmin) {
                    badges.push('<span class="user-profile-badge badge-admin"><i class="bi bi-shield-check"></i> Admin</span>');
                }
                if (isVip) {
                    badges.push('<span class="user-profile-badge badge-vip"><i class="bi bi-star"></i> VIP</span>');
                }
                
                // Streamlined layout with consolidated actions and recent tickets
                modalContent.innerHTML = `
                    <div class="user-profile-header">
                        <div class="user-profile-avatar">
                            <span class="user-profile-avatar-text">${initials}</span>
                        </div>
                        <div class="user-profile-name">${fullName}</div>
                        <div class="user-profile-title">${userInfo.title || userInfo.job_title || 'Employee'}</div>
                        <div class="user-profile-badges">${badges.join('')}</div>
                    </div>
                    
                    <div class="user-profile-info">
                        <div class="user-profile-section">
                            <h4><i class="bi bi-person"></i> Basic Info</h4>
                            <div class="user-profile-field">
                                <span class="user-profile-field-label">Clock ID</span>
                                <span class="user-profile-field-value">${userInfo.clock_id || clockId}</span>
                            </div>
                            <div class="user-profile-field">
                                <span class="user-profile-field-label">Status</span>
                                <span class="user-profile-field-value">
                                    <span class="user-profile-status ${isLocked ? 'status-locked' : isDisabled ? 'status-disabled' : 'status-active'}">
                                        <i class="bi bi-${isLocked ? 'lock' : isDisabled ? 'x-circle' : 'check-circle'}"></i>
                                        ${status}
                                    </span>
                                </span>
                            </div>
                            <div class="user-profile-field">
                                <span class="user-profile-field-label">Department</span>
                                <span class="user-profile-field-value">${userInfo.department || 'N/A'}</span>
                            </div>
                            <div class="user-profile-field">
                                <span class="user-profile-field-label">Location</span>
                                <span class="user-profile-field-value">${userInfo.location || userInfo.office || 'N/A'}</span>
                            </div>
                        </div>
                        
                        <div class="user-profile-section">
                            <h4><i class="bi bi-envelope"></i> Contact</h4>
                            <div class="user-profile-field">
                                <span class="user-profile-field-label">Email</span>
                                <span class="user-profile-field-value">${userInfo.email || 'N/A'}</span>
                            </div>
                            <div class="user-profile-field">
                                <span class="user-profile-field-label">Phone</span>
                                <span class="user-profile-field-value">${userInfo.phone || userInfo.phone_number || 'N/A'}</span>
                            </div>
                            <div class="user-profile-field">
                                <span class="user-profile-field-label">Extension</span>
                                <span class="user-profile-field-value">${userInfo.extension || 'N/A'}</span>
                            </div>
                        </div>
                        
                        <div class="user-profile-section">
                            <h4><i class="bi bi-tools"></i> Actions</h4>
                            <div class="user-profile-actions-consolidated">
                                <button class="action-icon-btn" onclick="window.createTicket('${clockId}')" title="Create Ticket">
                                    <i class="bi bi-ticket"></i>
                                </button>
                                <button class="action-icon-btn" onclick="window.resetPassword('${clockId}')" title="Reset Password">
                                    <i class="bi bi-key"></i>
                                </button>
                                <button class="action-icon-btn" onclick="window.viewHistory('${clockId}')" title="View History">
                                    <i class="bi bi-clock-history"></i>
                                </button>
                                ${isLocked ? `<button class="action-icon-btn" onclick="window.unlockAccount('${clockId}')" title="Unlock Account">
                                    <i class="bi bi-unlock"></i>
                                </button>` : ''}
                                ${isDisabled ? `<button class="action-icon-btn" onclick="window.enableAccount('${clockId}')" title="Enable Account">
                                    <i class="bi bi-check-circle"></i>
                                </button>` : ''}
                                ${!isDisabled ? `<button class="action-icon-btn" onclick="window.disableAccount('${clockId}')" title="Disable Account">
                                    <i class="bi bi-x-circle"></i>
                                </button>` : ''}
                                <a href="/tickets?user=${encodeURIComponent(clockId)}" class="action-icon-btn" title="View Tickets">
                                    <i class="bi bi-ticket-detailed"></i>
                                </a>
                            </div>
                        </div>
                    </div>
                `;
                
                // Add service desk action handlers
                this.addServiceDeskHandlers(clockId, userInfo);
                
            } catch (error) {
                console.error('Error loading user profile:', error);
                // Show a user-friendly error with the ability to still view basic info
                modalContent.innerHTML = `
                    <div class="user-profile-header">
                        <div class="user-profile-avatar">
                            <span class="user-profile-avatar-text">${clockId.slice(0, 2).toUpperCase()}</span>
                        </div>
                        <div class="user-profile-name">User ${clockId}</div>
                        <div class="user-profile-title">Clock ID Lookup</div>
                    </div>
                    
                    <div class="user-profile-info">
                        <div class="user-profile-section">
                            <h4><i class="bi bi-exclamation-triangle"></i> Information</h4>
                            <div class="user-profile-field">
                                <span class="user-profile-field-label">Clock ID</span>
                                <span class="user-profile-field-value">${clockId}</span>
                            </div>
                            <div class="user-profile-field">
                                <span class="user-profile-field-label">Status</span>
                                <span class="user-profile-field-value">Unknown</span>
                            </div>
                        </div>
                        
                        <div class="user-profile-section">
                            <h4><i class="bi bi-tools"></i> Actions</h4>
                            <div class="user-profile-actions-consolidated">
                                <a href="/users?search=${encodeURIComponent(clockId)}" class="action-icon-btn" title="Search User">
                                    <i class="bi bi-search"></i>
                                </a>
                                <a href="/tickets/new?user=${encodeURIComponent(clockId)}" class="action-icon-btn" title="Create Ticket">
                                    <i class="bi bi-ticket"></i>
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            }
        }
        
        addServiceDeskHandlers(clockId, userInfo) {
            // Add service desk action handlers to the global scope
            window.createTicket = (userId) => {
                window.open(`/tickets/new?user=${encodeURIComponent(userId)}`, '_blank');
            };
            
            window.unlockAccount = async (userId) => {
                if (confirm('Are you sure you want to unlock this account?')) {
                    try {
                        const response = await fetch('/api/admin/unlock-account', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ user_id: userId })
                        });
                        
                        if (response.ok) {
                            alert('Account unlocked successfully!');
                            // Refresh the modal to show updated status
                            this.loadUserProfileData(clockId, userInfo);
                        } else {
                            alert('Failed to unlock account. Please try again.');
                        }
                    } catch (error) {
                        console.error('Error unlocking account:', error);
                        alert('Error unlocking account. Please try again.');
                    }
                }
            };
            
            window.resetPassword = async (userId) => {
                if (confirm('Are you sure you want to reset the password for this user?')) {
                    try {
                        const response = await fetch('/api/admin/reset-password', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ user_id: userId })
                        });
                        
                        if (response.ok) {
                            const data = await response.json();
                            alert(`Password reset successfully! New password: ${data.new_password}`);
                        } else {
                            alert('Failed to reset password. Please try again.');
                        }
                    } catch (error) {
                        console.error('Error resetting password:', error);
                        alert('Error resetting password. Please try again.');
                    }
                }
            };
            
            window.enableAccount = async (userId) => {
                if (confirm('Are you sure you want to enable this account?')) {
                    try {
                        const response = await fetch('/api/admin/enable-account', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ user_id: userId })
                        });
                        
                        if (response.ok) {
                            alert('Account enabled successfully!');
                            // Refresh the modal to show updated status
                            this.loadUserProfileData(clockId, userInfo);
                        } else {
                            alert('Failed to enable account. Please try again.');
                        }
                    } catch (error) {
                        console.error('Error enabling account:', error);
                        alert('Error enabling account. Please try again.');
                    }
                }
            };
            
            window.disableAccount = async (userId) => {
                if (confirm('Are you sure you want to disable this account? This will prevent the user from logging in.')) {
                    try {
                        const response = await fetch('/api/admin/disable-account', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ user_id: userId })
                        });
                        
                        if (response.ok) {
                            alert('Account disabled successfully!');
                            // Refresh the modal to show updated status
                            this.loadUserProfileData(clockId, userInfo);
                        } else {
                            alert('Failed to disable account. Please try again.');
                        }
                    } catch (error) {
                        console.error('Error disabling account:', error);
                        alert('Error disabling account. Please try again.');
                    }
                }
            };
            
            window.viewHistory = (userId) => {
                window.open(`/admin/users/${userId}/history`, '_blank');
            };
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
        
        getIconForContentType(contentType) {
            const iconMap = {
                'kb_article': 'bi bi-journal-text',
                'note': 'bi bi-sticky',
                'office': 'bi bi-building',
                'workstation': 'bi bi-laptop',
                'user': 'bi bi-person',
                'outage': 'bi bi-exclamation-triangle',
                'document': 'bi bi-file-earmark-text',
                'ticket': 'bi bi-ticket-detailed',
                'device': 'bi bi-hdd-network',
                'search': 'bi bi-search'
            };
            return iconMap[contentType] || 'bi bi-file-text';
        }
    }
    
    // Initialize the banner search when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            new BannerSearch();
        });
    } else {
        new BannerSearch();
    }
})(); 