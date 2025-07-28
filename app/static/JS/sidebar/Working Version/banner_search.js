// Banner Search Module
// Handles banner search functionality, suggestions, and user profile modals

(function() {
    'use strict';
    
    console.log('Banner Search Module: Loading...');
    
    class BannerSearch {
        constructor() {
            console.log('Banner Search Module: Initializing...');
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
            
            console.log('Banner Search Module: Search input found:', !!this.searchInput);
            this.init();
        }
        
        init() {
            if (!this.searchInput) {
                console.error('Banner Search Module: Search input not found!');
                return;
            }
            
            console.log('Banner Search Module: Initializing event listeners...');
            
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
            
            console.log('Banner Search Module: Initialization complete');
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
            
            // Pattern recognition for immediate feedback
            if (/^\d{1,5}$/.test(query.trim())) {
                // Clock ID pattern - show immediate suggestion
                const padded = query.trim().padStart(5, '0');
                instantSuggestions.push({
                    text: `Find user ${padded}`,
                    icon: 'bi bi-person-badge',
                    subtitle: 'View user profile',
                    type: 'clock_id',
                    data: { clock_id: padded }
                });
            } else if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(query.trim())) {
                // IP address pattern
                instantSuggestions.push({
                    text: `Search for IP ${query.trim()}`,
                    icon: 'bi bi-hdd-network',
                    subtitle: 'Find devices with this IP',
                    type: 'ip_search',
                    data: { ip: query.trim() }
                });
            } else if (/^[0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}$/.test(query.trim())) {
                // MAC address pattern
                instantSuggestions.push({
                    text: `Search for MAC ${query.trim()}`,
                    icon: 'bi bi-hdd-network',
                    subtitle: 'Find devices with this MAC address',
                    type: 'mac_search',
                    data: { mac: query.trim() }
                });
            } else if (/^[A-Z]{2,3}-\d{4,6}$/i.test(query.trim())) {
                // Ticket pattern
                instantSuggestions.push({
                    text: `Search for ticket ${query.trim().toUpperCase()}`,
                    icon: 'bi bi-ticket-detailed',
                    subtitle: 'Find ticket information',
                    type: 'ticket_search',
                    data: { ticket: query.trim().toUpperCase() }
                });
            } else if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(query.trim())) {
                // Email pattern
                instantSuggestions.push({
                    text: `Search for email ${query.trim()}`,
                    icon: 'bi bi-envelope',
                    subtitle: 'Find user by email address',
                    type: 'email_search',
                    data: { email: query.trim() }
                });
            } else if (/^\d{3}-\d{3}-\d{4}$/.test(query.trim())) {
                // Phone pattern
                instantSuggestions.push({
                    text: `Search for phone ${query.trim()}`,
                    icon: 'bi bi-telephone',
                    subtitle: 'Find user by phone number',
                    type: 'phone_search',
                    data: { phone: query.trim() }
                });
            }
            
            // Always add helpful search options for any query
            instantSuggestions.push({
                text: `Search for "${query}"`,
                subtitle: 'Universal search across all content',
                url: `/unified_search?q=${encodeURIComponent(query)}`,
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
                // Optimize API calls - use a single unified endpoint for better performance
                // and reduce the number of concurrent requests
                const unifiedResponse = await fetch(`/unified_search?q=${encodeURIComponent(query)}&limit=8`, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json',
                            'Cache-Control': 'max-age=60'
                        },
                        signal: this.currentSuggestionsController.signal
                }).catch(() => null);
                
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
                
                // Process unified search results
                let officeData = [];
                let workstationData = [];
                
                if (unifiedResponse && unifiedResponse.ok) {
                    const unifiedData = await unifiedResponse.json();
                    officeData = unifiedData.offices || [];
                    workstationData = unifiedData.workstations || [];
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
            console.log('Banner Search Module: Suggestion clicked:', suggestion);
            // Hide suggestions dropdown immediately when any suggestion is clicked
            this.hideSuggestions();
            
            if (suggestion.url) {
                console.log('Banner Search Module: Navigating to URL:', suggestion.url);
                window.location.href = suggestion.url;
            } else if (suggestion.type === 'clock_id') {
                console.log('Banner Search Module: Handling clock ID lookup for:', suggestion.data.clock_id);
                // Handle clock ID lookup with user data if available
                this.handleClockIdLookup(suggestion.data.clock_id, suggestion.data.user_data);
            } else {
                console.log('Banner Search Module: Defaulting to universal search');
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
            console.log('Banner Search Module: handleClockIdLookup called with:', { clockId, userData });
            // Hide suggestions dropdown when opening user profile modal
            this.hideSuggestions();
            this.hideResults();
            
            // Use the existing sidebar user modal
            if (window.showSidebarUserModal) {
                window.showSidebarUserModal(clockId, userData);
            } else {
                // Fallback to creating a new modal if sidebar modal is not available
                this.showUserProfileModal(clockId, userData);
            }
        }
        
        showUserProfileModal(clockId, userData = null) {
            console.log('Banner Search Module: showUserProfileModal called with:', { clockId, userData });
            
            // Add CSS styles if not already present
            if (!document.getElementById('userProfileModalStyles')) {
                const styles = `
                    <style id="userProfileModalStyles">
                        .user-profile-modal-overlay {
                            position: fixed;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            background: rgba(0, 0, 0, 0.8);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            z-index: 9999999;
                            animation: overlayFadeIn 0.2s ease-out;
                        }
                        
                        @keyframes overlayFadeIn {
                            from { opacity: 0; }
                            to { opacity: 1; }
                        }
                        
                        .user-profile-modal {
                            background: #1a1a1a;
                            border-radius: 16px;
                            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.1);
                            width: 95%;
                            max-width: 1400px;
                            height: 90vh;
                            overflow: hidden;
                            animation: modalBounceIn 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            display: flex;
                            flex-direction: column;
                        }
                        
                        @keyframes modalBounceIn {
                            0% {
                                opacity: 0;
                                transform: scale(0.3) translateY(-50px);
                            }
                            50% {
                                transform: scale(1.05) translateY(10px);
                            }
                            100% {
                                opacity: 1;
                                transform: scale(1) translateY(0);
                            }
                        }
                        
                        .user-profile-modal-header {
                            display: flex;
                            align-items: center;
                            justify-content: space-between;
                            padding: 20px 24px;
                            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                            background: #2a2a2a;
                            position: relative;
                            flex-shrink: 0;
                        }
                        
                        .user-profile-modal-header h3 {
                            margin: 0;
                            color: #ffffff;
                            font-size: 20px;
                            font-weight: 600;
                            display: flex;
                            align-items: center;
                            gap: 8px;
                        }
                        
                        .user-profile-modal-close {
                            background: rgba(255, 255, 255, 0.1);
                            border: none;
                            color: #ffffff;
                            font-size: 18px;
                            cursor: pointer;
                            padding: 8px;
                            border-radius: 50%;
                            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                            width: 36px;
                            height: 36px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            position: absolute;
                            top: 16px;
                            right: 20px;
                            z-index: 10;
                        }
                        
                        .user-profile-modal-close:hover {
                            background: rgba(255, 255, 255, 0.2);
                            transform: rotate(90deg) scale(1.1);
                            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                        }
                        
                        .user-profile-modal-content {
                            padding: 20px;
                            flex: 1;
                            overflow: hidden;
                            display: flex;
                            flex-direction: column;
                            gap: 16px;
                        }
                        
                        .user-profile-loading {
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            justify-content: center;
                            padding: 40px 20px;
                            color: #ffffff;
                        }
                        
                        .loading-spinner {
                            width: 40px;
                            height: 40px;
                            border: 3px solid rgba(255, 255, 255, 0.1);
                            border-top: 3px solid #ffffff;
                            border-radius: 50%;
                            animation: spin 1s linear infinite;
                            margin-bottom: 16px;
                        }
                        
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                        
                        .user-profile-header {
                            display: flex;
                            align-items: center;
                            justify-content: space-between;
                            margin-bottom: 16px;
                            flex-shrink: 0;
                            padding: 0 20px;
                        }
                        
                        .user-profile-avatar {
                            width: 60px;
                            height: 60px;
                            border-radius: 50%;
                            background: #4169e1;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 24px;
                            font-weight: bold;
                            color: #ffffff;
                            position: relative;
                            z-index: 10;
                            box-shadow: 0 8px 24px rgba(65, 105, 225, 0.3);
                            border: 2px solid rgba(255, 255, 255, 0.2);
                            flex-shrink: 0;
                        }
                        
                        .user-profile-avatar-text {
                            position: relative;
                            z-index: 15;
                            color: #ffffff;
                            font-weight: 700;
                        }
                        
                        .user-profile-info-header {
                            display: flex;
                            flex-direction: column;
                            gap: 4px;
                        }
                        
                        .user-profile-actions-header {
                            display: flex;
                            gap: 8px;
                            align-items: center;
                            flex-shrink: 0;
                            min-width: 200px;
                            justify-content: flex-end;
                        }
                        
                        .user-profile-name-row {
                            display: flex;
                            align-items: center;
                            gap: 8px;
                        }
                        
                        .user-profile-name {
                            font-size: 20px;
                            font-weight: 600;
                            color: #ffffff;
                            margin: 0;
                        }
                        
                        .user-profile-title {
                            font-size: 14px;
                            color: rgba(255, 255, 255, 0.7);
                            margin: 0;
                        }
                        
                        .user-profile-badges {
                            display: flex;
                            gap: 8px;
                            flex-wrap: wrap;
                        }
                        
                        .user-profile-badge {
                            padding: 4px 12px;
                            border-radius: 20px;
                            font-size: 12px;
                            font-weight: 500;
                            display: flex;
                            align-items: center;
                            gap: 4px;
                        }
                        
                        .badge-active {
                            background: rgba(76, 175, 80, 0.2);
                            color: #4caf50;
                            border: 1px solid rgba(76, 175, 80, 0.3);
                        }
                        
                        .badge-locked {
                            background: rgba(244, 67, 54, 0.2);
                            color: #f44336;
                            border: 1px solid rgba(244, 67, 54, 0.3);
                        }
                        
                        .badge-disabled {
                            background: rgba(158, 158, 158, 0.2);
                            color: #9e9e9e;
                            border: 1px solid rgba(158, 158, 158, 0.3);
                        }
                        
                        .badge-admin {
                            background: rgba(33, 150, 243, 0.2);
                            color: #2196f3;
                            border: 1px solid rgba(33, 150, 243, 0.3);
                        }
                        
                        .badge-vip {
                            background: rgba(255, 193, 7, 0.2);
                            color: #ffc107;
                            border: 1px solid rgba(255, 193, 7, 0.3);
                        }
                        
                        .user-profile-info {
                            display: grid;
                            grid-template-columns: 1fr 1fr;
                            gap: 16px;
                            flex: 1;
                            overflow: hidden;
                            margin-bottom: 16px;
                        }
                        
                        .user-profile-section {
                            background: rgba(255, 255, 255, 0.05);
                            border-radius: 12px;
                            padding: 16px;
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            display: flex;
                            flex-direction: column;
                            overflow: hidden;
                        }
                        
                        .user-profile-section h4 {
                            margin: 0 0 12px 0;
                            color: #ffffff;
                            font-size: 14px;
                            font-weight: 600;
                            display: flex;
                            align-items: center;
                            gap: 6px;
                            flex-shrink: 0;
                        }
                        
                        .user-profile-fields {
                            flex: 1;
                            overflow-y: auto;
                            scrollbar-width: thin;
                            scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
                        }
                        
                        .user-profile-fields::-webkit-scrollbar {
                            width: 4px;
                        }
                        
                        .user-profile-fields::-webkit-scrollbar-track {
                            background: transparent;
                        }
                        
                        .user-profile-fields::-webkit-scrollbar-thumb {
                            background: rgba(255, 255, 255, 0.2);
                            border-radius: 2px;
                        }
                        
                        .user-profile-field {
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            padding: 6px 0;
                            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                        }
                        
                        .user-profile-field:last-child {
                            border-bottom: none;
                        }
                        
                        .user-profile-field-label {
                            color: rgba(255, 255, 255, 0.7);
                            font-size: 12px;
                            font-weight: 500;
                        }
                        
                        .user-profile-field-value {
                            color: #ffffff;
                            font-size: 12px;
                            font-weight: 500;
                            text-align: right;
                            max-width: 60%;
                            word-break: break-word;
                        }
                        
                        .user-profile-status {
                            display: flex;
                            align-items: center;
                            gap: 4px;
                            padding: 4px 8px;
                            border-radius: 12px;
                            font-size: 12px;
                            font-weight: 500;
                        }
                        
                        .status-active {
                            background: rgba(76, 175, 80, 0.2);
                            color: #4caf50;
                        }
                        
                        .status-locked {
                            background: rgba(244, 67, 54, 0.2);
                            color: #f44336;
                        }
                        
                        .status-disabled {
                            background: rgba(158, 158, 158, 0.2);
                            color: #9e9e9e;
                        }
                        
                        .user-profile-actions-consolidated {
                            display: grid;
                            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                            gap: 8px;
                            justify-content: center;
                            align-items: center;
                            flex-shrink: 0;
                        }
                        
                        .action-icon-btn {
                            background: rgba(255, 255, 255, 0.1);
                            border: 1px solid rgba(255, 255, 255, 0.2);
                            color: #ffffff;
                            padding: 8px;
                            border-radius: 50%;
                            cursor: pointer;
                            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                            text-decoration: none;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            width: 36px;
                            height: 36px;
                            position: relative;
                            overflow: hidden;
                        }
                        
                        .action-icon-btn-header {
                            background: rgba(255, 255, 255, 0.1);
                            border: 1px solid rgba(255, 255, 255, 0.2);
                            color: #ffffff;
                            padding: 6px;
                            border-radius: 50%;
                            cursor: pointer;
                            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                            text-decoration: none;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            width: 32px;
                            height: 32px;
                            position: relative;
                            overflow: hidden;
                            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
                        }
                        
                        .action-icon-btn::before {
                            content: '';
                            position: absolute;
                            top: 0;
                            left: -100%;
                            width: 100%;
                            height: 100%;
                            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
                            transition: left 0.5s;
                        }
                        
                        .action-icon-btn:hover::before {
                            left: 100%;
                        }
                        
                        .action-icon-btn:hover {
                            background: rgba(255, 255, 255, 0.2);
                            transform: translateY(-3px) scale(1.05);
                            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
                            border-color: rgba(255, 255, 255, 0.3);
                        }
                        
                        .action-icon-btn:active {
                            transform: translateY(-1px) scale(1.02);
                        }
                        
                        .action-icon-btn i {
                            font-size: 14px;
                            transition: transform 0.3s ease;
                        }
                        
                        .action-icon-btn:hover i {
                            transform: scale(1.2);
                        }
                        
                        .action-icon-btn-header:hover {
                            background: rgba(255, 255, 255, 0.15);
                            transform: translateY(-2px) scale(1.1);
                            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                            border-color: rgba(255, 255, 255, 0.2);
                            color: #ffffff;
                        }
                        
                        .action-icon-btn-header:active {
                            transform: translateY(-1px) scale(1.05);
                        }
                        
                        .action-icon-btn-header i {
                            font-size: 12px;
                            transition: transform 0.3s ease;
                        }
                        
                        .action-icon-btn-header:hover i {
                            transform: scale(1.2);
                        }
                        
                        /* Tooltip styles */
                        .tooltip {
                            position: relative;
                        }
                        
                        .tooltip .tooltiptext {
                            visibility: hidden;
                            width: auto;
                            background-color: rgba(0, 0, 0, 0.9);
                            color: #fff;
                            text-align: center;
                            border-radius: 6px;
                            padding: 6px 10px;
                            position: absolute;
                            z-index: 10000000;
                            bottom: 125%;
                            left: 50%;
                            transform: translateX(-50%);
                            opacity: 0;
                            transition: opacity 0.3s;
                            font-size: 11px;
                            font-weight: 500;
                            white-space: nowrap;
                            pointer-events: none;
                        }
                        
                        .tooltip .tooltiptext::after {
                            content: "";
                            position: absolute;
                            top: 100%;
                            left: 50%;
                            margin-left: -5px;
                            border-width: 5px;
                            border-style: solid;
                            border-color: rgba(0, 0, 0, 0.9) transparent transparent transparent;
                        }
                        
                        .tooltip:hover .tooltiptext {
                            visibility: visible;
                            opacity: 1;
                        }
                        
                        .recent-tickets-section {
                            background: rgba(255, 255, 255, 0.05);
                            border-radius: 12px;
                            padding: 16px;
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            flex-shrink: 0;
                            margin-top: 16px;
                        }
                        
                        .recent-tickets-section h4 {
                            margin: 0 0 12px 0;
                            color: #ffffff;
                            font-size: 14px;
                            font-weight: 600;
                            display: flex;
                            align-items: center;
                            gap: 6px;
                        }
                        
                        .recent-tickets-list {
                            display: flex;
                            flex-direction: column;
                            gap: 6px;
                            max-height: 150px;
                            overflow-y: auto;
                            scrollbar-width: thin;
                            scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
                        }
                        
                        .recent-tickets-list::-webkit-scrollbar {
                            width: 4px;
                        }
                        
                        .recent-tickets-list::-webkit-scrollbar-track {
                            background: transparent;
                        }
                        
                        .recent-tickets-list::-webkit-scrollbar-thumb {
                            background: rgba(255, 255, 255, 0.2);
                            border-radius: 2px;
                        }
                        
                        .ticket-item {
                            display: flex;
                            align-items: center;
                            gap: 8px;
                            padding: 8px;
                            background: rgba(255, 255, 255, 0.05);
                            border-radius: 6px;
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            transition: all 0.2s ease;
                            cursor: pointer;
                        }
                        
                        .ticket-item:hover {
                            background: rgba(255, 255, 255, 0.08);
                            transform: translateX(4px);
                            border-color: rgba(255, 255, 255, 0.2);
                        }
                        
                        .ticket-icon {
                            width: 24px;
                            height: 24px;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 12px;
                            flex-shrink: 0;
                        }
                        
                        .ticket-priority-high {
                            background: linear-gradient(135deg, #ff6b6b, #ee5a52);
                            color: #ffffff;
                        }
                        
                        .ticket-priority-medium {
                            background: linear-gradient(135deg, #ffa726, #ff9800);
                            color: #ffffff;
                        }
                        
                        .ticket-priority-low {
                            background: linear-gradient(135deg, #66bb6a, #4caf50);
                            color: #ffffff;
                        }
                        
                        .ticket-content {
                            flex: 1;
                            min-width: 0;
                        }
                        
                        .ticket-title {
                            font-size: 12px;
                            font-weight: 600;
                            color: #ffffff;
                            margin-bottom: 2px;
                            white-space: nowrap;
                            overflow: hidden;
                            text-overflow: ellipsis;
                        }
                        
                        .ticket-meta {
                            font-size: 10px;
                            color: rgba(255, 255, 255, 0.7);
                        }
                        
                        .ticket-status {
                            font-size: 10px;
                            font-weight: 600;
                            padding: 3px 6px;
                            border-radius: 4px;
                            text-transform: uppercase;
                            letter-spacing: 0.5px;
                            flex-shrink: 0;
                        }
                        
                        .ticket-status-open {
                            background: rgba(255, 193, 7, 0.2);
                            color: #ffc107;
                            border: 1px solid rgba(255, 193, 7, 0.3);
                        }
                        
                        .ticket-status-resolved {
                            background: rgba(76, 175, 80, 0.2);
                            color: #4caf50;
                            border: 1px solid rgba(76, 175, 80, 0.3);
                        }
                        
                        .ticket-status-closed {
                            background: rgba(158, 158, 158, 0.2);
                            color: #9e9e9e;
                            border: 1px solid rgba(158, 158, 158, 0.3);
                        }
                        
                        .ticket-priority {
                            padding: 3px 8px;
                            border-radius: 12px;
                            font-size: 10px;
                            font-weight: 600;
                            text-transform: uppercase;
                            letter-spacing: 0.5px;
                        }
                        
                        .ticket-priority-high {
                            background: rgba(244, 67, 54, 0.2);
                            color: #f44336;
                            border: 1px solid rgba(244, 67, 54, 0.3);
                        }
                        
                        .ticket-priority-medium {
                            background: rgba(255, 152, 0, 0.2);
                            color: #ff9800;
                            border: 1px solid rgba(255, 152, 0, 0.3);
                        }
                        
                        .ticket-priority-low {
                            background: rgba(76, 175, 80, 0.2);
                            color: #4caf50;
                            border: 1px solid rgba(76, 175, 80, 0.3);
                        }
                        
                        @media (max-width: 1200px) {
                            .user-profile-modal {
                                width: 95%;
                                height: 90vh;
                            }
                            
                            .user-profile-info {
                                grid-template-columns: 1fr 1fr;
                            }
                            
                            .user-profile-actions-consolidated {
                                gap: 8px;
                            }
                            
                            .action-icon-btn {
                                min-width: 100px;
                                padding: 10px 12px;
                                font-size: 13px;
                            }
                        }
                        
                        @media (max-width: 768px) {
                            .user-profile-modal {
                                width: 98%;
                                height: 95vh;
                            }
                            
                            .user-profile-modal-content {
                                padding: 16px;
                            }
                            
                            .user-profile-info {
                                grid-template-columns: 1fr;
                            }
                            
                            .user-profile-header {
                                flex-direction: column;
                                gap: 12px;
                                align-items: flex-start;
                            }
                            
                            .user-profile-actions-header {
                                gap: 6px;
                                flex-wrap: wrap;
                            }
                            
                            .action-icon-btn-header {
                                width: 28px;
                                height: 28px;
                            }
                            
                            .action-icon-btn-header i {
                                font-size: 11px;
                            }
                        }
                        
                        /* Ticket Modal Styles */
                        .ticket-modal-overlay {
                            position: fixed;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            background: rgba(0, 0, 0, 0.8);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            z-index: 99999999;
                            animation: overlayFadeIn 0.2s ease-out;
                        }
                        
                        .ticket-modal {
                            background: #1a1a1a;
                            border-radius: 16px;
                            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.1);
                            width: 95%;
                            max-width: 800px;
                            max-height: 90vh;
                            overflow: hidden;
                            animation: modalBounceIn 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            display: flex;
                            flex-direction: column;
                        }
                        
                        .ticket-modal-header {
                            display: flex;
                            align-items: center;
                            justify-content: space-between;
                            padding: 20px 24px;
                            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                            background: #2a2a2a;
                            position: relative;
                            flex-shrink: 0;
                        }
                        
                        .ticket-modal-header h3 {
                            margin: 0;
                            color: #ffffff;
                            font-size: 18px;
                            font-weight: 600;
                            display: flex;
                            align-items: center;
                            gap: 8px;
                        }
                        
                        .ticket-modal-close {
                            background: rgba(255, 255, 255, 0.1);
                            border: none;
                            color: #ffffff;
                            font-size: 18px;
                            cursor: pointer;
                            padding: 8px;
                            border-radius: 50%;
                            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                            width: 36px;
                            height: 36px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            position: absolute;
                            top: 16px;
                            right: 20px;
                            z-index: 10;
                        }
                        
                        .ticket-modal-close:hover {
                            background: rgba(255, 255, 255, 0.2);
                            transform: rotate(90deg) scale(1.1);
                            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                        }
                        
                        .ticket-modal-content {
                            padding: 20px;
                            flex: 1;
                            overflow-y: auto;
                            scrollbar-width: thin;
                            scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
                        }
                        
                        .ticket-modal-content::-webkit-scrollbar {
                            width: 4px;
                        }
                        
                        .ticket-modal-content::-webkit-scrollbar-track {
                            background: transparent;
                        }
                        
                        .ticket-modal-content::-webkit-scrollbar-thumb {
                            background: rgba(255, 255, 255, 0.2);
                            border-radius: 2px;
                        }
                        
                        .ticket-details {
                            display: grid;
                            grid-template-columns: 1fr 1fr;
                            gap: 20px;
                            margin-bottom: 20px;
                        }
                        
                        .ticket-section {
                            background: rgba(255, 255, 255, 0.05);
                            border-radius: 12px;
                            padding: 16px;
                            border: 1px solid rgba(255, 255, 255, 0.1);
                        }
                        
                        .ticket-section h4 {
                            margin: 0 0 12px 0;
                            color: #ffffff;
                            font-size: 14px;
                            font-weight: 600;
                            display: flex;
                            align-items: center;
                            gap: 6px;
                        }
                        
                        .ticket-field {
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            padding: 6px 0;
                            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                        }
                        
                        .ticket-field:last-child {
                            border-bottom: none;
                        }
                        
                        .ticket-field-label {
                            color: rgba(255, 255, 255, 0.7);
                            font-size: 12px;
                            font-weight: 500;
                        }
                        
                        .ticket-field-value {
                            color: #ffffff;
                            font-size: 12px;
                            font-weight: 500;
                            text-align: right;
                            max-width: 60%;
                            word-break: break-word;
                        }
                        
                        .ticket-description {
                            background: rgba(255, 255, 255, 0.05);
                            border-radius: 12px;
                            padding: 16px;
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            margin-bottom: 20px;
                        }
                        
                        .ticket-description h4 {
                            margin: 0 0 12px 0;
                            color: #ffffff;
                            font-size: 14px;
                            font-weight: 600;
                            display: flex;
                            align-items: center;
                            gap: 6px;
                        }
                        
                        .ticket-description-text {
                            color: #ffffff;
                            font-size: 13px;
                            line-height: 1.5;
                            margin: 0;
                        }
                        
                        .ticket-timeline {
                            background: rgba(255, 255, 255, 0.05);
                            border-radius: 12px;
                            padding: 16px;
                            border: 1px solid rgba(255, 255, 255, 0.1);
                        }
                        
                        .ticket-timeline h4 {
                            margin: 0 0 12px 0;
                            color: #ffffff;
                            font-size: 14px;
                            font-weight: 600;
                            display: flex;
                            align-items: center;
                            gap: 6px;
                        }
                        
                        .timeline-item {
                            display: flex;
                            gap: 12px;
                            padding: 8px 0;
                            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                        }
                        
                        .timeline-item:last-child {
                            border-bottom: none;
                        }
                        
                        .timeline-icon {
                            width: 24px;
                            height: 24px;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 12px;
                            flex-shrink: 0;
                            margin-top: 2px;
                        }
                        
                        .timeline-content {
                            flex: 1;
                        }
                        
                        .timeline-action {
                            color: #ffffff;
                            font-size: 12px;
                            font-weight: 600;
                            margin-bottom: 2px;
                        }
                        
                        .timeline-meta {
                            color: rgba(255, 255, 255, 0.7);
                            font-size: 11px;
                        }
                        
                        .ticket-actions {
                            display: flex;
                            gap: 8px;
                            justify-content: flex-end;
                            margin-top: 16px;
                        }
                        
                        .ticket-action-btn {
                            background: rgba(255, 255, 255, 0.1);
                            border: 1px solid rgba(255, 255, 255, 0.2);
                            color: #ffffff;
                            padding: 8px 16px;
                            border-radius: 8px;
                            cursor: pointer;
                            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                            text-decoration: none;
                            display: flex;
                            align-items: center;
                            gap: 6px;
                            font-size: 12px;
                            font-weight: 500;
                        }
                        
                        .ticket-action-btn:hover {
                            background: rgba(255, 255, 255, 0.2);
                            transform: translateY(-2px);
                            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                        }
                        
                        @media (max-width: 768px) {
                            .ticket-modal {
                                width: 98%;
                                max-height: 95vh;
                            }
                            
                            .ticket-details {
                                grid-template-columns: 1fr;
                            }
                            
                            .ticket-actions {
                                flex-direction: column;
                            }
                        }
                    </style>
                `;
                document.head.insertAdjacentHTML('beforeend', styles);
            }
            
            // Create modal HTML with improved design
            const modalHTML = `
                <div id="userProfileModal" class="user-profile-modal-overlay">
                    <div class="user-profile-modal">
                        <div class="user-profile-modal-header">
                            <h3><i class="bi bi-person-circle"></i> User Profile</h3>
                            <button class="user-profile-modal-close" onclick="window.closeUserProfileModal()">
                                <i class="bi bi-x-lg"></i>
                            </button>
                        </div>
                        <div class="user-profile-modal-content">
                            <div class="user-profile-loading">
                                <div class="loading-spinner"></div>
                                <p>Loading user information...</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            console.log('Banner Search Module: Adding modal to page...');
            // Add modal to page
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            console.log('Banner Search Module: User profile modal added to page');
            
            // Debug: Check if action buttons are present
            setTimeout(() => {
                const actionButtons = document.querySelectorAll('.action-icon-btn-header');
                console.log('Banner Search Module: Found action buttons:', actionButtons.length);
                actionButtons.forEach((btn, index) => {
                    console.log(`Banner Search Module: Action button ${index}:`, btn);
                });
            }, 100);
            
            // Add click outside to close functionality
            const modalOverlay = document.getElementById('userProfileModal');
            modalOverlay.addEventListener('click', (e) => {
                if (e.target === modalOverlay) {
                    this.closeUserProfileModal();
                }
            });
            
            // Add escape key to close functionality
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    this.closeUserProfileModal();
                    document.removeEventListener('keydown', handleEscape);
                }
            };
            document.addEventListener('keydown', handleEscape);
            
            // Add global close function
            window.closeUserProfileModal = () => {
                const modal = document.getElementById('userProfileModal');
                if (modal) {
                    modal.remove();
                }
            };
            
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
                
                // Compact 2-column layout with all user data
                console.log('Banner Search Module: Rendering user profile with action buttons');
                modalContent.innerHTML = `
                    <div class="user-profile-header">
                        <div style="display: flex; align-items: center; gap: 16px;">
                            <div class="user-profile-avatar">
                                <span class="user-profile-avatar-text">${initials}</span>
                            </div>
                            <div class="user-profile-info-header">
                                <div class="user-profile-name-row">
                                    <div class="user-profile-name">${fullName}</div>
                                    ${badges.join('')}
                                </div>
                                <div class="user-profile-title">${userInfo.title || userInfo.job_title || 'Employee'}</div>
                            </div>
                        </div>
                        <div class="user-profile-actions-header" style="display: flex; gap: 8px; align-items: center; flex-shrink: 0; min-width: 200px; justify-content: flex-end;">
                            <div class="tooltip">
                                <button class="action-icon-btn-header" onclick="window.createTicket('${clockId}')" title="Create Ticket" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #ffffff; padding: 6px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; width: 32px; height: 32px;">
                                    <i class="bi bi-ticket"></i>
                                </button>
                                <span class="tooltiptext">Create Ticket</span>
                            </div>
                            <div class="tooltip">
                                <button class="action-icon-btn-header" onclick="window.resetPassword('${clockId}')" title="Reset Password" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #ffffff; padding: 6px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; width: 32px; height: 32px;">
                                    <i class="bi bi-key"></i>
                                </button>
                                <span class="tooltiptext">Reset Password</span>
                            </div>
                            <div class="tooltip">
                                <button class="action-icon-btn-header" onclick="window.viewHistory('${clockId}')" title="View History" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #ffffff; padding: 6px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; width: 32px; height: 32px;">
                                    <i class="bi bi-clock-history"></i>
                                </button>
                                <span class="tooltiptext">View History</span>
                            </div>
                            ${isLocked ? `<div class="tooltip">
                                <button class="action-icon-btn-header" onclick="window.unlockAccount('${clockId}')" title="Unlock Account">
                                    <i class="bi bi-unlock"></i>
                                </button>
                                <span class="tooltiptext">Unlock Account</span>
                            </div>` : ''}
                            ${isDisabled ? `<div class="tooltip">
                                <button class="action-icon-btn-header" onclick="window.enableAccount('${clockId}')" title="Enable Account">
                                    <i class="bi bi-check-circle"></i>
                                </button>
                                <span class="tooltiptext">Enable Account</span>
                            </div>` : ''}
                            ${!isDisabled ? `<div class="tooltip">
                                <button class="action-icon-btn-header" onclick="window.disableAccount('${clockId}')" title="Disable Account">
                                    <i class="bi bi-x-circle"></i>
                                </button>
                                <span class="tooltiptext">Disable Account</span>
                            </div>` : ''}
                            <div class="tooltip">
                                <a href="/tickets?user=${encodeURIComponent(clockId)}" class="action-icon-btn-header" title="View Tickets">
                                    <i class="bi bi-ticket-detailed"></i>
                                </a>
                                <span class="tooltiptext">View Tickets</span>
                            </div>
                            <div class="tooltip">
                                <a href="/admin/users/${clockId}" class="action-icon-btn-header" title="Admin View" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #ffffff; padding: 6px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; text-decoration: none;">
                                    <i class="bi bi-gear"></i>
                                </a>
                                <span class="tooltiptext">Admin View</span>
                            </div>
                            <!-- Test button to ensure layout is working -->
                            <div class="tooltip">
                                <button class="action-icon-btn-header" onclick="alert('Test button works!')" title="Test Button" style="background: rgba(255, 0, 0, 0.3); border: 1px solid rgba(255, 0, 0, 0.5); color: #ffffff; padding: 6px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; width: 32px; height: 32px;">
                                    <i class="bi bi-exclamation-triangle"></i>
                                </button>
                                <span class="tooltiptext">Test Button</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="user-profile-info">
                        <div class="user-profile-section">
                            <h4><i class="bi bi-person"></i> Basic Info</h4>
                            <div class="user-profile-fields">
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
                                <div class="user-profile-field">
                                    <span class="user-profile-field-label">Manager</span>
                                    <span class="user-profile-field-value">${userInfo.manager || userInfo.supervisor || 'N/A'}</span>
                                </div>
                                <div class="user-profile-field">
                                    <span class="user-profile-field-label">Start Date</span>
                                    <span class="user-profile-field-value">${userInfo.start_date || userInfo.hire_date || 'N/A'}</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="user-profile-section">
                            <h4><i class="bi bi-envelope"></i> Contact</h4>
                            <div class="user-profile-fields">
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
                                <div class="user-profile-field">
                                    <span class="user-profile-field-label">Mobile</span>
                                    <span class="user-profile-field-value">${userInfo.mobile || userInfo.cell_phone || 'N/A'}</span>
                                </div>
                                <div class="user-profile-field">
                                    <span class="user-profile-field-label">Emergency</span>
                                    <span class="user-profile-field-value">${userInfo.emergency_contact || 'N/A'}</span>
                                </div>
                                <div class="user-profile-field">
                                    <span class="user-profile-field-label">Address</span>
                                    <span class="user-profile-field-value">${userInfo.address || userInfo.street_address || 'N/A'}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="recent-tickets-section">
                        <h4><i class="bi bi-clock-history"></i> Recent Tickets</h4>
                        <div class="recent-tickets-list">
                            <div class="ticket-item" onclick="window.showTicketModal('TK-2024-001', 'Password Reset Request', 'high', 'open')">
                                <div class="ticket-icon ticket-priority-high">
                                    <i class="bi bi-exclamation-triangle"></i>
                                </div>
                                <div class="ticket-content">
                                    <div class="ticket-title">Password Reset Request</div>
                                    <div class="ticket-meta">#TK-2024-001 • 2 hours ago</div>
                                </div>
                                <div class="ticket-status ticket-status-open">Open</div>
                            </div>
                            <div class="ticket-item" onclick="window.showTicketModal('TK-2024-002', 'Software Installation', 'medium', 'resolved')">
                                <div class="ticket-icon ticket-priority-medium">
                                    <i class="bi bi-laptop"></i>
                                </div>
                                <div class="ticket-content">
                                    <div class="ticket-title">Software Installation</div>
                                    <div class="ticket-meta">#TK-2024-002 • 1 day ago</div>
                                </div>
                                <div class="ticket-status ticket-status-resolved">Resolved</div>
                            </div>
                            <div class="ticket-item" onclick="window.showTicketModal('TK-2024-003', 'General Inquiry', 'low', 'closed')">
                                <div class="ticket-icon ticket-priority-low">
                                    <i class="bi bi-question-circle"></i>
                                </div>
                                <div class="ticket-content">
                                    <div class="ticket-title">General Inquiry</div>
                                    <div class="ticket-meta">#TK-2024-003 • 3 days ago</div>
                                </div>
                                <div class="ticket-status ticket-status-closed">Closed</div>
                            </div>
                            <div class="ticket-item" onclick="window.showTicketModal('TK-2024-004', 'Printer Configuration', 'medium', 'resolved')">
                                <div class="ticket-icon ticket-priority-medium">
                                    <i class="bi bi-printer"></i>
                                </div>
                                <div class="ticket-content">
                                    <div class="ticket-title">Printer Configuration</div>
                                    <div class="ticket-meta">#TK-2024-004 • 4 days ago</div>
                                </div>
                                <div class="ticket-status ticket-status-resolved">Resolved</div>
                            </div>
                            <div class="ticket-item" onclick="window.showTicketModal('TK-2024-005', 'Network Connectivity', 'high', 'closed')">
                                <div class="ticket-icon ticket-priority-high">
                                    <i class="bi bi-wifi"></i>
                                </div>
                                <div class="ticket-content">
                                    <div class="ticket-title">Network Connectivity</div>
                                    <div class="ticket-meta">#TK-2024-005 • 5 days ago</div>
                                </div>
                                <div class="ticket-status ticket-status-closed">Closed</div>
                            </div>
                            <div class="ticket-item" onclick="window.showTicketModal('TK-2024-006', 'Hardware Replacement', 'low', 'resolved')">
                                <div class="ticket-icon ticket-priority-low">
                                    <i class="bi bi-keyboard"></i>
                                </div>
                                <div class="ticket-content">
                                    <div class="ticket-title">Hardware Replacement</div>
                                    <div class="ticket-meta">#TK-2024-006 • 1 week ago</div>
                                </div>
                                <div class="ticket-status ticket-status-resolved">Resolved</div>
                            </div>
                            <div class="ticket-item" onclick="window.showTicketModal('TK-2024-007', 'Security Update', 'medium', 'closed')">
                                <div class="ticket-icon ticket-priority-medium">
                                    <i class="bi bi-shield-check"></i>
                                </div>
                                <div class="ticket-content">
                                    <div class="ticket-title">Security Update</div>
                                    <div class="ticket-meta">#TK-2024-007 • 1 week ago</div>
                                </div>
                                <div class="ticket-status ticket-status-closed">Closed</div>
                            </div>
                            <div class="ticket-item" onclick="window.showTicketModal('TK-2024-008', 'Audio Equipment', 'low', 'resolved')">
                                <div class="ticket-icon ticket-priority-low">
                                    <i class="bi bi-headphones"></i>
                                </div>
                                <div class="ticket-content">
                                    <div class="ticket-title">Audio Equipment</div>
                                    <div class="ticket-meta">#TK-2024-008 • 2 weeks ago</div>
                                </div>
                                <div class="ticket-status ticket-status-resolved">Resolved</div>
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
                            <div class="user-profile-fields">
                                <div class="user-profile-field">
                                    <span class="user-profile-field-label">Clock ID</span>
                                    <span class="user-profile-field-value">${clockId}</span>
                                </div>
                                <div class="user-profile-field">
                                    <span class="user-profile-field-label">Status</span>
                                    <span class="user-profile-field-value">Unknown</span>
                                </div>
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
        
        closeUserProfileModal() {
            const modal = document.getElementById('userProfileModal');
            if (modal) {
                modal.remove();
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
            
            // Ticket modal functionality
            window.showTicketModal = (ticketId, title, priority, status) => {
                this.showTicketModal(ticketId, title, priority, status);
            };
        }
        
        showTicketModal(ticketId, title, priority, status) {
            console.log('Banner Search Module: showTicketModal called with:', { ticketId, title, priority, status });
            
            // Generate dummy ticket data based on the ticket ID
            const ticketData = this.generateDummyTicketData(ticketId, title, priority, status);
            
            // Create modal HTML
            const modalHTML = `
                <div id="ticketModal" class="ticket-modal-overlay">
                    <div class="ticket-modal">
                        <div class="ticket-modal-header">
                            <h3><i class="bi bi-ticket-detailed"></i> ${ticketData.title}</h3>
                            <button class="ticket-modal-close" onclick="window.closeTicketModal()">
                                <i class="bi bi-x-lg"></i>
                            </button>
                        </div>
                        <div class="ticket-modal-content">
                            <div class="ticket-details">
                                <div class="ticket-section">
                                    <h4><i class="bi bi-info-circle"></i> Ticket Information</h4>
                                    <div class="ticket-field">
                                        <span class="ticket-field-label">Ticket ID</span>
                                        <span class="ticket-field-value">${ticketData.id}</span>
                                    </div>
                                    <div class="ticket-field">
                                        <span class="ticket-field-label">Status</span>
                                        <span class="ticket-field-value">
                                            <span class="ticket-status ticket-status-${ticketData.status}">${ticketData.status}</span>
                                        </span>
                                    </div>
                                    <div class="ticket-field">
                                        <span class="ticket-field-label">Priority</span>
                                        <span class="ticket-field-value">
                                            <span class="ticket-priority ticket-priority-${ticketData.priority}">${ticketData.priority}</span>
                                        </span>
                                    </div>
                                    <div class="ticket-field">
                                        <span class="ticket-field-label">Category</span>
                                        <span class="ticket-field-value">${ticketData.category}</span>
                                    </div>
                                    <div class="ticket-field">
                                        <span class="ticket-field-label">Created</span>
                                        <span class="ticket-field-value">${ticketData.created}</span>
                                    </div>
                                    <div class="ticket-field">
                                        <span class="ticket-field-label">Updated</span>
                                        <span class="ticket-field-value">${ticketData.updated}</span>
                                    </div>
                                </div>
                                
                                <div class="ticket-section">
                                    <h4><i class="bi bi-person"></i> User Information</h4>
                                    <div class="ticket-field">
                                        <span class="ticket-field-label">Requester</span>
                                        <span class="ticket-field-value">${ticketData.requester}</span>
                                    </div>
                                    <div class="ticket-field">
                                        <span class="ticket-field-label">Department</span>
                                        <span class="ticket-field-value">${ticketData.department}</span>
                                    </div>
                                    <div class="ticket-field">
                                        <span class="ticket-field-label">Location</span>
                                        <span class="ticket-field-value">${ticketData.location}</span>
                                    </div>
                                    <div class="ticket-field">
                                        <span class="ticket-field-label">Contact</span>
                                        <span class="ticket-field-value">${ticketData.contact}</span>
                                    </div>
                                    <div class="ticket-field">
                                        <span class="ticket-field-label">Assigned To</span>
                                        <span class="ticket-field-value">${ticketData.assignedTo}</span>
                                    </div>
                                    <div class="ticket-field">
                                        <span class="ticket-field-label">Escalation</span>
                                        <span class="ticket-field-value">${ticketData.escalation}</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="ticket-description">
                                <h4><i class="bi bi-chat-text"></i> Description</h4>
                                <p class="ticket-description-text">${ticketData.description}</p>
                            </div>
                            
                            <div class="ticket-timeline">
                                <h4><i class="bi bi-clock-history"></i> Timeline</h4>
                                ${ticketData.timeline.map(item => `
                                    <div class="timeline-item">
                                        <div class="timeline-icon ticket-priority-${item.priority}">
                                            <i class="bi ${item.icon}"></i>
                                        </div>
                                        <div class="timeline-content">
                                            <div class="timeline-action">${item.action}</div>
                                            <div class="timeline-meta">${item.meta}</div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                            
                            <div class="ticket-actions">
                                <button class="ticket-action-btn" onclick="window.editTicket('${ticketId}')">
                                    <i class="bi bi-pencil"></i>
                                    Edit Ticket
                                </button>
                                <button class="ticket-action-btn" onclick="window.addComment('${ticketId}')">
                                    <i class="bi bi-chat"></i>
                                    Add Comment
                                </button>
                                <button class="ticket-action-btn" onclick="window.escalateTicket('${ticketId}')">
                                    <i class="bi bi-arrow-up"></i>
                                    Escalate
                                </button>
                                <button class="ticket-action-btn" onclick="window.closeTicket('${ticketId}')">
                                    <i class="bi bi-check-circle"></i>
                                    Close Ticket
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Add modal to page
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            // Add click outside to close functionality
            const modalOverlay = document.getElementById('ticketModal');
            modalOverlay.addEventListener('click', (e) => {
                if (e.target === modalOverlay) {
                    this.closeTicketModal();
                }
            });
            
            // Add escape key to close functionality
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    this.closeTicketModal();
                    document.removeEventListener('keydown', handleEscape);
                }
            };
            document.addEventListener('keydown', handleEscape);
            
            // Add global close function
            window.closeTicketModal = () => {
                const modal = document.getElementById('ticketModal');
                if (modal) {
                    modal.remove();
                }
            };
            
            // Add ticket action handlers
            window.editTicket = (ticketId) => {
                alert(`Edit ticket ${ticketId} - This would open the edit form`);
            };
            
            window.addComment = (ticketId) => {
                alert(`Add comment to ticket ${ticketId} - This would open the comment form`);
            };
            
            window.escalateTicket = (ticketId) => {
                alert(`Escalate ticket ${ticketId} - This would escalate the ticket`);
            };
            
            window.closeTicket = (ticketId) => {
                if (confirm('Are you sure you want to close this ticket?')) {
                    alert(`Ticket ${ticketId} closed successfully`);
                    this.closeTicketModal();
                }
            };
        }
        
        generateDummyTicketData(ticketId, title, priority, status) {
            const priorities = {
                high: { color: '#ff6b6b', icon: 'bi-exclamation-triangle' },
                medium: { color: '#ffa726', icon: 'bi-exclamation-circle' },
                low: { color: '#66bb6a', icon: 'bi-info-circle' }
            };
            
            const categories = [
                'Hardware', 'Software', 'Network', 'Access', 'Account', 'Email', 'Printing', 'Security'
            ];
            
            const departments = [
                'IT Support', 'HR', 'Finance', 'Operations', 'Sales', 'Marketing', 'Engineering'
            ];
            
            const locations = [
                'Main Office', 'Branch A', 'Branch B', 'Remote', 'HQ', 'Satellite Office'
            ];
            
            const assignees = [
                'John Smith', 'Sarah Johnson', 'Mike Davis', 'Lisa Wilson', 'David Brown', 'Emily Chen'
            ];
            
            const descriptions = {
                'TK-2024-001': 'User is unable to log into their account and has been locked out after multiple failed attempts. Need immediate password reset and account unlock.',
                'TK-2024-002': 'Request for installation of Adobe Creative Suite and Microsoft Office 365 on user workstation. User needs these applications for daily work tasks.',
                'TK-2024-003': 'General inquiry about VPN access and remote work setup. User wants to understand the process for working from home.',
                'TK-2024-004': 'Printer is not responding and showing offline status. Need to troubleshoot network connectivity and driver issues.',
                'TK-2024-005': 'User experiencing intermittent network connectivity issues. Connection drops frequently and affects work productivity.',
                'TK-2024-006': 'Keyboard keys are sticking and some are not responding. Need replacement keyboard for user workstation.',
                'TK-2024-007': 'Security update required for user workstation. System is showing outdated antivirus definitions.',
                'TK-2024-008': 'Audio equipment not working properly. Headphones and microphone need configuration or replacement.'
            };
            
            const timelines = {
                'TK-2024-001': [
                    { action: 'Ticket Created', meta: '2 hours ago by User', priority: 'high', icon: 'bi-plus-circle' },
                    { action: 'Assigned to IT Support', meta: '1 hour 45 minutes ago by System', priority: 'medium', icon: 'bi-person-check' },
                    { action: 'Password Reset Initiated', meta: '1 hour 30 minutes ago by John Smith', priority: 'high', icon: 'bi-key' },
                    { action: 'Account Unlocked', meta: '1 hour 15 minutes ago by John Smith', priority: 'high', icon: 'bi-unlock' }
                ],
                'TK-2024-002': [
                    { action: 'Ticket Created', meta: '1 day ago by User', priority: 'medium', icon: 'bi-plus-circle' },
                    { action: 'Assigned to IT Support', meta: '23 hours ago by System', priority: 'medium', icon: 'bi-person-check' },
                    { action: 'Software Installation Started', meta: '22 hours ago by Sarah Johnson', priority: 'medium', icon: 'bi-download' },
                    { action: 'Installation Completed', meta: '21 hours ago by Sarah Johnson', priority: 'medium', icon: 'bi-check-circle' },
                    { action: 'Ticket Resolved', meta: '20 hours ago by Sarah Johnson', priority: 'medium', icon: 'bi-check-double' }
                ],
                'TK-2024-003': [
                    { action: 'Ticket Created', meta: '3 days ago by User', priority: 'low', icon: 'bi-plus-circle' },
                    { action: 'Assigned to IT Support', meta: '2 days 23 hours ago by System', priority: 'low', icon: 'bi-person-check' },
                    { action: 'Information Provided', meta: '2 days 22 hours ago by Mike Davis', priority: 'low', icon: 'bi-chat-text' },
                    { action: 'Ticket Closed', meta: '2 days 21 hours ago by Mike Davis', priority: 'low', icon: 'bi-x-circle' }
                ]
            };
            
            // Generate random data for tickets not in the predefined lists
            const randomCategory = categories[Math.floor(Math.random() * categories.length)];
            const randomDepartment = departments[Math.floor(Math.random() * departments.length)];
            const randomLocation = locations[Math.floor(Math.random() * locations.length)];
            const randomAssignee = assignees[Math.floor(Math.random() * assignees.length)];
            
            const description = descriptions[ticketId] || `Standard ${randomCategory.toLowerCase()} issue requiring attention. User has reported problems with their system and needs assistance.`;
            
            const timeline = timelines[ticketId] || [
                { action: 'Ticket Created', meta: '1 week ago by User', priority: 'medium', icon: 'bi-plus-circle' },
                { action: 'Assigned to IT Support', meta: '6 days 23 hours ago by System', priority: 'medium', icon: 'bi-person-check' },
                { action: 'Work Started', meta: '6 days 22 hours ago by ' + randomAssignee, priority: 'medium', icon: 'bi-play-circle' },
                { action: 'Issue Resolved', meta: '6 days 21 hours ago by ' + randomAssignee, priority: 'medium', icon: 'bi-check-circle' },
                { action: 'Ticket Closed', meta: '6 days 20 hours ago by ' + randomAssignee, priority: 'medium', icon: 'bi-x-circle' }
            ];
            
            return {
                id: ticketId,
                title: title,
                status: status,
                priority: priority,
                category: randomCategory,
                created: '2024-01-15 09:30:00',
                updated: '2024-01-15 11:45:00',
                requester: 'John Doe',
                department: randomDepartment,
                location: randomLocation,
                contact: 'john.doe@company.com',
                assignedTo: randomAssignee,
                escalation: 'None',
                description: description,
                timeline: timeline
            };
        }
        
        closeTicketModal() {
            const modal = document.getElementById('ticketModal');
            if (modal) {
                modal.remove();
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
    }
    
    // Initialize the banner search when DOM is ready
    console.log('Banner Search Module: DOM ready state:', document.readyState);
    if (document.readyState === 'loading') {
        console.log('Banner Search Module: DOM still loading, waiting for DOMContentLoaded...');
        document.addEventListener('DOMContentLoaded', () => {
            console.log('Banner Search Module: DOMContentLoaded fired, creating BannerSearch instance...');
            new BannerSearch();
        });
    } else {
        console.log('Banner Search Module: DOM already ready, creating BannerSearch instance immediately...');
        new BannerSearch();
    }
})(); 