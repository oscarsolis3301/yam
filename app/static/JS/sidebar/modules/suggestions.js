// Suggestions Module - Completely revamped to match Universal Search behavior
// Handles instant suggestions, pattern recognition, and suggestion display

class SuggestionsModule {
    constructor(coreModule) {
        this.coreModule = coreModule;
        this.suggestionsContent = document.getElementById('bannerSuggestionsContent');
        this.isGettingSuggestions = false;
        this.currentSuggestionsController = null;
        this.lastQuery = '';
        this.lastQueryTime = 0;
        this.suggestionCache = new Map(); // Cache for instant suggestions
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
        // Generate common smart suggestions
        this.generateCommonSuggestions();
    }
    
    generateCommonSuggestions() {
        this.commonSuggestions = [
            { text: '👥 Search Users', icon: 'bi bi-person', subtitle: 'Find people & profiles', type: 'text' },
            { text: '🏢 Search Offices', icon: 'bi bi-building', subtitle: 'Find office locations', type: 'text' },
            { text: '💻 Search Workstations', icon: 'bi bi-laptop', subtitle: 'Find devices & computers', type: 'text' },
            { text: '📚 Search Knowledge Base', icon: 'bi bi-journal-text', subtitle: 'Find guides & articles', type: 'text' },
            { text: '⚠️ Check Outages', icon: 'bi bi-exclamation-triangle', subtitle: 'System status & alerts', type: 'text' }
        ];
    }
    
    // Pre-load common data for instant suggestions
    async preloadCommonData() {
        try {
            // Load recent searches from localStorage
            const recentSearches = JSON.parse(localStorage.getItem('bannerSearchRecent') || '[]');
            this.preloadedData.recentSearches = recentSearches.slice(0, 10);

            // Pre-load some common office data (async, non-blocking)
            this.preloadOfficesAndWorkstations();
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
        
        let recent = JSON.parse(localStorage.getItem('bannerSearchRecent') || '[]');
        recent = recent.filter(item => item.toLowerCase() !== query.toLowerCase());
        recent.unshift(query);
        recent = recent.slice(0, 10); // Keep only 10 recent searches
        
        localStorage.setItem('bannerSearchRecent', JSON.stringify(recent));
        this.preloadedData.recentSearches = recent;
    }
    
    showInstantSuggestions(query) {
        // Show instant pattern-based suggestions immediately (no API calls)
        const instantSuggestions = [];
        const trimmedQuery = query.trim();
        
        // Enhanced pattern recognition for immediate feedback
        if (/^\d{1,5}$/.test(trimmedQuery)) {
            // Clock ID pattern - show immediate suggestion with better formatting
            const padded = trimmedQuery.padStart(5, '0');
            instantSuggestions.push({
                text: `👤 Find User ${padded}`,
                icon: 'bi bi-person-badge',
                subtitle: 'Lookup user by Clock ID',
                type: 'clock_id',
                data: { clock_id: padded }
            });
        } else if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(trimmedQuery)) {
            // IP address pattern
            instantSuggestions.push({
                text: `🌐 Search for IP ${trimmedQuery}`,
                icon: 'bi bi-hdd-network',
                subtitle: 'Find devices with this IP address',
                type: 'ip_search',
                data: { ip: trimmedQuery }
            });
        } else if (/^[0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}$/.test(trimmedQuery)) {
            // MAC address pattern
            instantSuggestions.push({
                text: `🔗 Search for MAC ${trimmedQuery}`,
                icon: 'bi bi-hdd-network',
                subtitle: 'Find devices with this MAC address',
                type: 'mac_search',
                data: { mac: trimmedQuery }
            });
        } else if (/^[A-Z]{2,3}-\d{4,6}$/i.test(trimmedQuery)) {
            // Ticket pattern
            instantSuggestions.push({
                text: `🎫 Search for ticket ${trimmedQuery.toUpperCase()}`,
                icon: 'bi bi-ticket-detailed',
                subtitle: 'Find ticket information & details',
                type: 'ticket_search',
                data: { ticket: trimmedQuery.toUpperCase() }
            });
        } else if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedQuery)) {
            // Email pattern
            instantSuggestions.push({
                text: `📧 Search for email ${trimmedQuery}`,
                icon: 'bi bi-envelope',
                subtitle: 'Find user by email address',
                type: 'email_search',
                data: { email: trimmedQuery }
            });
        } else if (/^\d{3}-\d{3}-\d{4}$/.test(trimmedQuery)) {
            // Phone pattern
            instantSuggestions.push({
                text: `📞 Search for phone ${trimmedQuery}`,
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
                    text: `💻 Find workstation "${trimmedQuery}"`,
                    icon: 'bi bi-laptop',
                    subtitle: 'Search workstations database',
                    type: 'workstation_search',
                    data: { query: trimmedQuery }
                });
            }
            
            // Office pattern (office names often contain letters and may have numbers)
            if (/^[A-Za-z]/.test(trimmedQuery)) {
                instantSuggestions.push({
                    text: `🏢 Find office "${trimmedQuery}"`,
                    icon: 'bi bi-building',
                    subtitle: 'Search offices database',
                    type: 'office_search',
                    data: { query: trimmedQuery }
                });
            }
            
            // Knowledge base pattern (any text query)
            instantSuggestions.push({
                text: `📚 Search KB for "${trimmedQuery}"`,
                icon: 'bi bi-journal-text',
                subtitle: 'Search knowledge base articles',
                type: 'kb_search',
                data: { query: trimmedQuery }
            });
            
            // Notes pattern (any text query)
            instantSuggestions.push({
                text: `📝 Search notes for "${trimmedQuery}"`,
                icon: 'bi bi-sticky',
                subtitle: 'Search user notes & documentation',
                type: 'note_search',
                data: { query: trimmedQuery }
            });
        }
        
        // Show instant suggestions immediately
        this.displaySuggestions({
            clockSuggestions: [],
            offices: [],
            workstations: [],
            textSuggestions: instantSuggestions,
            commonSuggestions: []
        });
        
        // Store in cache for instant access
        this.suggestionCache.set(trimmedQuery, {
            clockSuggestions: [],
            offices: [],
            workstations: [],
            textSuggestions: instantSuggestions,
            commonSuggestions: []
        });
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
                        text: `👤 Find User ${padded}`,
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
                                text: `🏢 ${office['Internal Name'] || office.name || 'Unknown Office'}`,
                                icon: 'bi bi-building',
                                subtitle: office.Number ? `Office ${office.Number}` : 'Office Location',
                                type: 'office',
                                data: office
                            }));
                        }

                        // Add workstations
                        if (universalData.workstations && universalData.workstations.length > 0) {
                            suggestions.workstations = universalData.workstations.slice(0, 3).map(ws => ({
                                text: `💻 ${ws.name || 'Unknown Workstation'}`,
                                icon: 'bi bi-laptop',
                                subtitle: ws.user ? `User: ${ws.user}` : 'Workstation Device',
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
                            text: suggestion.display_text.includes('👤') ? suggestion.display_text : `👤 ${suggestion.display_text}`,
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
    
    // Display partial suggestions immediately from cached/preloaded data
    displayPartialSuggestions(query) {
        const lowerQuery = query.toLowerCase();
        const suggestions = {
            clockSuggestions: [],
            offices: [],
            workstations: [],
            textSuggestions: [],
            commonSuggestions: []
        };

        // Add recent searches that match
        suggestions.textSuggestions = this.preloadedData.recentSearches
            .filter(search => search.toLowerCase().includes(lowerQuery))
            .slice(0, 3)
            .map(search => {
                let displayText = search;
                if (search.includes('Search for')) {
                    displayText = search.replace('Search for', '🔍 Search for');
                } else if (search.includes('Find')) {
                    displayText = search.replace('Find', '🔍 Find');
                }
                return displayText;
            });

        // Add matching preloaded offices
        suggestions.offices = this.preloadedData.offices
            .filter(office => 
                (office['Internal Name'] || '').toLowerCase().includes(lowerQuery) ||
                (office.Number || '').toString().includes(query)
            )
            .slice(0, 3)
            .map(office => ({
                text: `🏢 ${office['Internal Name'] || office.name || 'Unknown Office'}`,
                icon: 'bi bi-building',
                subtitle: office.Number ? `Office ${office.Number}` : 'Office Location',
                type: 'office',
                data: office
            }));

        // Add matching preloaded workstations
        suggestions.workstations = this.preloadedData.workstations
            .filter(ws => 
                (ws.name || '').toLowerCase().includes(lowerQuery) ||
                (ws.user || '').toLowerCase().includes(lowerQuery)
            )
            .slice(0, 3)
            .map(ws => ({
                text: `💻 ${ws.name || 'Unknown Workstation'}`,
                icon: 'bi bi-laptop',
                subtitle: ws.user ? `User: ${ws.user}` : 'Workstation Device',
                type: 'workstation',
                data: ws
            }));

        // Generate clock ID suggestions instantly for numeric queries
        if (/^\d+$/.test(query.trim())) {
            const padded = query.trim().padStart(5, '0');
            const originalQuery = query.trim();
            
            suggestions.clockSuggestions = [
                {
                    text: `👤 Find User ${padded}`,
                    icon: 'bi bi-person',
                    subtitle: 'Lookup user by Clock ID',
                    type: 'clock_id',
                    data: { clock_id: padded }
                },
                {
                    text: `💻 Search for workstation matching ${originalQuery}`,
                    icon: 'bi bi-laptop',
                    subtitle: 'Device search',
                    type: 'text'
                },
                {
                    text: `🏢 Search for office number ${originalQuery}`,
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
    
    // Update suggestions in background without blocking UI
    async updateSuggestionsInBackground(query) {
        // Only perform background clock-ID refresh for numeric queries (1-5 digits)
        if (!/^\d{1,5}$/.test(query.trim())) return;
        try {
            const response = await fetch(`/api/clock-id/suggestions?q=${encodeURIComponent(query)}`);
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.suggestions.length > 0) {
                    // Update the cached suggestions with fresh data
                    const currentSuggestions = this.getCachedSuggestions(query) || {
                        clockSuggestions: [],
                        offices: [],
                        workstations: [],
                        textSuggestions: [],
                        commonSuggestions: []
                    };
                    
                    const freshSuggestion = data.suggestions[0];
                    if (freshSuggestion.type === 'clock_id') {
                        currentSuggestions.clockSuggestions = [{
                            text: freshSuggestion.display_text.includes('👤') ? freshSuggestion.display_text : `👤 ${freshSuggestion.display_text}`,
                            icon: 'bi bi-person-circle',
                            subtitle: freshSuggestion.subtitle,
                            type: 'clock_id',
                            data: { clock_id: freshSuggestion.clock_id }
                        }];
                    }
                    
                    this.setCachedSuggestions(query, currentSuggestions);
                    this.displaySuggestions(currentSuggestions);
                }
            }
        } catch (error) {
            // Silent fail for background updates
            console.debug('Background suggestion update failed:', error);
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
            html += '<div class="category-title">🔍 User Lookups</div>';
            
            allSuggestions.clockSuggestions.forEach(suggestion => {
                // Clean and format the text for better readability
                let displayText = suggestion.text;
                let displaySubtitle = suggestion.subtitle;
                
                // Enhance text formatting
                if (displayText.includes('FIND USER')) {
                    displayText = displayText.replace('FIND USER', '👤 Find User');
                } else if (displayText.includes('View') && displayText.includes('full profile')) {
                    displayText = displayText.replace('View ', '📋 View ');
                    displaySubtitle = 'Complete user profile & details';
                } else if (displayText.includes('Find user')) {
                    displayText = displayText.replace('Find user', '🔍 Find User');
                    displaySubtitle = 'Lookup user by Clock ID';
                }
                
                html += `
                    <div class="suggestion-item" onclick="window.bannerSearchInstance.selectSuggestion('${suggestion.text}', '${suggestion.type}', ${JSON.stringify(suggestion.data)})">
                        <div class="suggestion-icon">
                            <i class="${suggestion.icon}"></i>
                        </div>
                        <div class="suggestion-content">
                            <div class="suggestion-text">${displayText}</div>
                            <div class="suggestion-subtitle">${displaySubtitle}</div>
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
            html += '<div class="category-title">🏢 Office Locations</div>';
            
            allSuggestions.offices.forEach(office => {
                let displayText = office.text;
                let displaySubtitle = office.subtitle;
                
                // Enhance office text formatting
                if (displayText.includes('Office')) {
                    displayText = displayText.replace('Office', '🏢 Office');
                }
                
                html += `
                    <div class="suggestion-item" onclick="window.bannerSearchInstance.selectSuggestion('${office.text}', '${office.type}', ${JSON.stringify(office.data)})">
                        <div class="suggestion-icon">
                            <i class="${office.icon}"></i>
                        </div>
                        <div class="suggestion-content">
                            <div class="suggestion-text">${displayText}</div>
                            <div class="suggestion-subtitle">${displaySubtitle}</div>
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
            html += '<div class="category-title">💻 Workstations</div>';
            
            allSuggestions.workstations.forEach(ws => {
                let displayText = ws.text;
                let displaySubtitle = ws.subtitle;
                
                // Enhance workstation text formatting
                if (displayText.includes('Workstation')) {
                    displayText = displayText.replace('Workstation', '💻 Workstation');
                }
                
                html += `
                    <div class="suggestion-item" onclick="window.bannerSearchInstance.selectSuggestion('${ws.text}', '${ws.type}', ${JSON.stringify(ws.data)})">
                        <div class="suggestion-icon">
                            <i class="${ws.icon}"></i>
                        </div>
                        <div class="suggestion-content">
                            <div class="suggestion-text">${displayText}</div>
                            <div class="suggestion-subtitle">${displaySubtitle}</div>
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
            html += '<div class="category-title">⏰ Recent Searches</div>';
            
            allSuggestions.textSuggestions.forEach(suggestion => {
                let displayText = suggestion;
                
                // Enhance recent search text formatting
                if (typeof suggestion === 'string') {
                    // For string suggestions, add appropriate icons
                    if (suggestion.includes('Search for')) {
                        displayText = suggestion.replace('Search for', '🔍 Search for');
                    } else if (suggestion.includes('Find')) {
                        displayText = suggestion.replace('Find', '🔍 Find');
                    }
                }
                
                html += `
                    <div class="suggestion-item" onclick="window.bannerSearchInstance.selectSuggestion('${suggestion}', 'text')">
                        <div class="suggestion-icon">
                            <i class="bi bi-clock-history"></i>
                        </div>
                        <div class="suggestion-content">
                            <div class="suggestion-text">${displayText}</div>
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
            html += '<div class="category-title">⚡ Quick Actions</div>';
            
            allSuggestions.commonSuggestions.forEach(suggestion => {
                let displayText = suggestion.text;
                let displaySubtitle = suggestion.subtitle;
                
                // Enhance quick action text formatting
                if (displayText.includes('Search users')) {
                    displayText = displayText.replace('Search users', '👥 Search Users');
                } else if (displayText.includes('Search offices')) {
                    displayText = displayText.replace('Search offices', '🏢 Search Offices');
                } else if (displayText.includes('Search workstations')) {
                    displayText = displayText.replace('Search workstations', '💻 Search Workstations');
                } else if (displayText.includes('Search knowledge base')) {
                    displayText = displayText.replace('Search knowledge base', '📚 Search Knowledge Base');
                } else if (displayText.includes('Check outages')) {
                    displayText = displayText.replace('Check outages', '⚠️ Check Outages');
                }
                
                html += `
                    <div class="suggestion-item" onclick="window.bannerSearchInstance.selectSuggestion('${suggestion.text}', '${suggestion.type}')">
                        <div class="suggestion-icon">
                            <i class="${suggestion.icon}"></i>
                        </div>
                        <div class="suggestion-content">
                            <div class="suggestion-text">${displayText}</div>
                            <div class="suggestion-subtitle">${displaySubtitle}</div>
                        </div>
                        <div class="suggestion-action">
                            <i class="bi bi-arrow-right"></i>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }

        // Search results
        if (allSuggestions.searchResults && allSuggestions.searchResults.length > 0) {
            hasSuggestions = true;
            html += '<div class="suggestion-category">';
            html += '<div class="category-title">🔍 Search Results</div>';
            
            allSuggestions.searchResults.forEach(result => {
                let displayText = result.text;
                let displaySubtitle = result.subtitle;
                
                // Enhance search result text formatting
                if (displayText.includes('Search for')) {
                    displayText = displayText.replace('Search for', '🔍 Search for');
                }
                
                html += `
                    <div class="suggestion-item" onclick="window.bannerSearchInstance.selectSuggestion('${result.text}', '${result.type}', ${JSON.stringify(result.data)})">
                        <div class="suggestion-icon">
                            <i class="${result.icon}"></i>
                        </div>
                        <div class="suggestion-content">
                            <div class="suggestion-text">${displayText}</div>
                            <div class="suggestion-subtitle">${displaySubtitle}</div>
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
        if (hasSuggestions && this.coreModule.currentQuery && this.coreModule.currentQuery.trim()) {
            html += `
                <div class="suggestion-category">
                    <div class="suggestion-item suggestion-viewall" onclick="window.bannerSearchInstance.selectSuggestion('view_all', 'view_all')">
                        <div class="suggestion-icon">
                            <i class="bi bi-search"></i>
                        </div>
                        <div class="suggestion-content">
                            <div class="suggestion-text">🔍 View All Results for "${this.coreModule.currentQuery}"</div>
                            <div class="suggestion-subtitle">Complete search results & more options</div>
                        </div>
                        <div class="suggestion-action">
                            <i class="bi bi-arrow-right"></i>
                        </div>
                    </div>
                </div>
            `;
        }

        this.suggestionsContent.innerHTML = html;
        
        if (hasSuggestions) {
            this.coreModule.showSuggestions();
        } else {
            this.coreModule.hideSuggestions();
        }
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
            if (window.showBannerSearchDetail) {
                window.showBannerSearchDetail('office', data['Internal Name'] || data.name || suggestion);
            }
            return;
        } else if (type === 'workstation' && data) {
            // Show workstation detail modal
            console.log('Workstation detail:', data);
            if (window.showBannerSearchDetail) {
                window.showBannerSearchDetail('workstation', data.name || suggestion);
            }
            return;
        } else if (type === 'result' && data && data.url) {
            // Handle search results with URLs
            console.log('Search result:', data);
            window.location.href = data.url;
            return;
        } else {
            // Handle text-based suggestions
            console.log('Text-based suggestion:', suggestion);
            this.coreModule.searchInput.value = suggestion;
            this.coreModule.currentQuery = suggestion;
            this.coreModule.performSearch(suggestion);
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
        }
    }

    // Display error message
    displayError(message) {
        if (this.suggestionsContent) {
            this.suggestionsContent.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: #dc3545;">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                    <h4>Error</h4>
                    <p>${message}</p>
                </div>
            `;
            this.coreModule.showSuggestions();
        }
    }
    
    viewAllResults() {
        if (this.coreModule.currentQuery) {
            // Save to recent searches
            this.saveRecentSearch(this.coreModule.currentQuery);
            
            const params = new URLSearchParams({ q: this.coreModule.currentQuery });
            window.location.href = `/universal-search?${params}`;
        }
    }
    
    // Clear cache when needed
    clearCache() {
        this.suggestionCache.clear();
    }
    
    // Get cached suggestions for instant access
    getCachedSuggestions(query) {
        return this.suggestionCache.get(query.trim()) || [];
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

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SuggestionsModule;
} else {
    window.SuggestionsModule = SuggestionsModule;
} 