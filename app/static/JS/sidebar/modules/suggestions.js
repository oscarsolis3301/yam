// Suggestions Module
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
                text: `FIND USER ${padded}`,
                icon: 'bi bi-person-badge',
                subtitle: 'LOOKUP USER BY CLOCK ID',
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
        } else if (/^\d{1,2}$/.test(trimmedQuery)) {
            // Partial clock ID (1-2 digits) - show immediate suggestion
            const padded = trimmedQuery.padStart(5, '0');
            instantSuggestions.push({
                text: `FIND USER ${padded}`,
                icon: 'bi bi-person-badge',
                subtitle: 'LOOKUP USER BY CLOCK ID',
                type: 'clock_id',
                data: { clock_id: padded }
            });
        } else if (/^\d{3,4}$/.test(trimmedQuery)) {
            // Partial clock ID (3-4 digits) - show immediate suggestion
            const padded = trimmedQuery.padStart(5, '0');
            instantSuggestions.push({
                text: `FIND USER ${padded}`,
                icon: 'bi bi-person-badge',
                subtitle: 'LOOKUP USER BY CLOCK ID',
                type: 'clock_id',
                data: { clock_id: padded }
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
        
        // Removed generic 'Search for' fallback to keep only real or pattern-based suggestions
        
        // Show instant suggestions immediately
        this.displaySuggestions(instantSuggestions);
        
        // Store in cache for instant access
        this.suggestionCache.set(trimmedQuery, instantSuggestions);
    }
    
    async getSuggestions(query) {
        const trimmedQuery = query.trim();
        
        // Check if we already have cached suggestions for this exact query
        if (this.suggestionCache.has(trimmedQuery)) {
            const cachedSuggestions = this.suggestionCache.get(trimmedQuery);
            // Update with fresh data in background
            this.updateSuggestionsInBackground(trimmedQuery);
            return;
        }
        
        // Cancel any pending suggestions request
        if (this.currentSuggestionsController) {
            this.currentSuggestionsController.abort();
        }
        
        // Create new abort controller for this suggestions request
        this.currentSuggestionsController = new AbortController();
        
        this.isGettingSuggestions = true;
        
        try {
            // For clock IDs, make a separate fast lookup call
            let clockSuggestions = [];
            if (/^\d{1,5}$/.test(trimmedQuery)) {
                try {
                    const cacheRes = await fetch(`/api/clock-id/suggestions?q=${encodeURIComponent(trimmedQuery)}`, {
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
            
            // Added universal-search text suggestions endpoint to mirror Universal Search component
            const [suggestionsResponse, unifiedResponse, universalResponse, kbResponse, notesResponse] = await Promise.allSettled([
                // Universal Search text suggestions (titles, intelligent patterns, etc.)
                fetch(`/api/universal-search/suggestions?q=${encodeURIComponent(trimmedQuery)}&limit=8`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Cache-Control': 'max-age=60'
                    },
                    signal: this.currentSuggestionsController.signal
                }),
                
                // Unified search for offices and workstations
                fetch(`/unified_search?q=${encodeURIComponent(trimmedQuery)}&limit=8`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Cache-Control': 'max-age=60'
                    },
                    signal: this.currentSuggestionsController.signal
                }),
                
                // Universal search full results (same as universalSearch.html uses)
                fetch(`/api/universal-search?q=${encodeURIComponent(trimmedQuery)}&limit=8`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Cache-Control': 'max-age=60'
                    },
                    signal: this.currentSuggestionsController.signal
                }),
                
                // KB API for knowledge base articles
                fetch(`/api/kb?q=${encodeURIComponent(trimmedQuery)}&per_page=5`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Cache-Control': 'max-age=60'
                    },
                    signal: this.currentSuggestionsController.signal
                }),
                
                // Notes search for user notes
                // Corrected path for collaborative notes search (blueprint prefix is /notes)
                fetch(`/notes/api/notes/search?q=${encodeURIComponent(trimmedQuery)}`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Cache-Control': 'max-age=60'
                    },
                    signal: this.currentSuggestionsController.signal
                })
            ]);
            
            // Process unified search results (offices and workstations)
            let officeData = [];
            let workstationData = [];
            
            if (unifiedResponse.status === 'fulfilled' && unifiedResponse.value.ok) {
                const unifiedData = await unifiedResponse.value.json();
                officeData = unifiedData.offices || [];
                workstationData = unifiedData.workstations || [];
            }
            
            // Process universal-search text suggestions
            let textSuggestions = [];
            if (suggestionsResponse.status === 'fulfilled' && suggestionsResponse.value.ok) {
                const suggestionsData = await suggestionsResponse.value.json();
                textSuggestions = suggestionsData.suggestions || [];
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

            // Add text suggestions from universal search
            if (textSuggestions.length > 0) {
                textSuggestions.slice(0, 8).forEach(text => {
                    allSuggestions.push({
                        text: text,
                        icon: 'bi bi-search',
                        subtitle: 'Universal search suggestion',
                        type: 'text_suggestion',
                        data: { query: text },
                        url: `/universal-search?q=${encodeURIComponent(text)}`
                    });
                });
            }
            
            // Add office suggestions
            if (officeData.length > 0) {
                officeData.slice(0, 5).forEach(office => {
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
                workstationData.slice(0, 5).forEach(ws => {
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
                kbArticles.slice(0, 5).forEach(article => {
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
                notesData.slice(0, 5).forEach(note => {
                    allSuggestions.push({
                        text: note.title || 'Unknown Note',
                        icon: 'bi bi-sticky',
                        subtitle: note.content ? note.content.substring(0, 50) + '...' : 'User Note',
                        type: 'note',
                        data: note
                    });
                });
            }
            
            // Add user suggestions from unified search
            if (unifiedResponse.status === 'fulfilled' && unifiedResponse.value.ok) {
                 const unifiedData = await unifiedResponse.value.json();
                 const usersData = unifiedData.users || [];
                 if (usersData.length > 0) {
                     usersData.slice(0, 5).forEach(user => {
                         allSuggestions.push({
                             text: user.name || 'Unknown User',
                             icon: 'bi bi-person',
                             subtitle: 'User',
                             type: 'user',
                             data: user
                         });
                     });
                 }
            }

            // Add universal search results (any content type)
             if (universalResults.length > 0) {
                 universalResults.slice(0, 8).forEach(result => {
                         allSuggestions.push({
                             text: result.title || 'Unknown Result',
                             icon: this.getIconForContentType(result.content_type),
                             subtitle: result.description ? result.description.substring(0, 50) + '...' : result.content_type,
                             type: result.content_type,
                             data: result
                         });
                 });
             }

            // --- PRIORITIZATION: ensure clock ID suggestion is always first ---
            // Detect suggestions that represent a specific user looked up by clock ID.
            const isClockUser = (s) => {
                if (s.type === 'clock_id') return true;
                // Some APIs may label the result as a generic 'user' type while still including a clock_id.
                return s.type === 'user' && s.data && (s.data.clock_id || s.data.clockId);
            };

            const prioritized = allSuggestions.filter(isClockUser);
            const rest = allSuggestions.filter((s) => !isClockUser(s));
 
            // Always prepend a generic fallback "Find User" action so the user can hit ENTER to force a lookup,
            // no matter what was typed. If the query looks numeric we pad to 5-digits, otherwise keep as-is.
            const fallbackClockId = /^\d{1,5}$/.test(trimmedQuery)
                ? trimmedQuery.padStart(5, '0')
                : trimmedQuery;

            const fallbackExists = prioritized.some(
                (s) => s.type === 'clock_id' && (s.data?.clock_id || '').toString() === fallbackClockId.toString()
            );

            if (!fallbackExists) {
                prioritized.unshift({
                    text: `FIND USER ${fallbackClockId}`,
                    icon: 'bi bi-person-badge',
                    subtitle: 'LOOKUP USER',
                    type: 'clock_id',
                    data: { clock_id: fallbackClockId }
                });
            }

            allSuggestions.length = 0;
            allSuggestions.push(...prioritized, ...rest);
            
            // If no real suggestions, hide dropdown entirely instead of showing generic fallbacks
            if (allSuggestions.length === 0) {
                this.coreModule.hideSuggestions();
                return;
            }
            
            // Cache the results
            this.suggestionCache.set(trimmedQuery, allSuggestions);
            
            this.coreModule.currentSuggestions = allSuggestions;
            this.displaySuggestions(allSuggestions);
            
        } catch (error) {
            if (error.name === 'AbortError') {
                return;
            }
            console.error('Suggestions error:', error);
            // Show helpful suggestions even on error
            const helpfulSuggestions = this.createHelpfulSuggestions(trimmedQuery);
            this.suggestionCache.set(trimmedQuery, helpfulSuggestions);
            this.displaySuggestions(helpfulSuggestions);
        } finally {
            this.isGettingSuggestions = false;
        }
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
                    const currentSuggestions = this.suggestionCache.get(query) || [];
                    const updatedSuggestions = currentSuggestions.map(suggestion => {
                        if (suggestion.type === 'clock_id') {
                            const freshSuggestion = data.suggestions[0];
                            return {
                                ...suggestion,
                                text: freshSuggestion.display_text,
                                data: { 
                                    clock_id: freshSuggestion.clock_id,
                                    full_name: freshSuggestion.full_name,
                                    user_data: freshSuggestion
                                }
                            };
                        }
                        return suggestion;
                    });
                    
                    this.suggestionCache.set(query, updatedSuggestions);
                    this.displaySuggestions(updatedSuggestions);
                }
            }
        } catch (error) {
            // Silent fail for background updates
            console.debug('Background suggestion update failed:', error);
        }
    }
    
    createHelpfulSuggestions(query) {
        const searchTerm = query.trim();
        const suggestions = [];
        
        // Removed generic 'Search for' option
        
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
    
    displaySuggestions(suggestions) {
        if (!this.suggestionsContent) return;
        if (!Array.isArray(suggestions) || suggestions.length === 0) {
            this.coreModule.hideSuggestions();
            return;
        }

        // Clear previous contents
        this.suggestionsContent.innerHTML = '';

        // Helper for creating suggestion element
        const createItem = (suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'banner-search-suggestion-item';
            item.innerHTML = `
                <div class="banner-search-suggestion-icon"><i class="${suggestion.icon}"></i></div>
                <div class="banner-search-suggestion-content">
                    <div class="banner-search-suggestion-text">${suggestion.text}</div>
                    <div class="banner-search-suggestion-subtitle">${suggestion.subtitle || ''}</div>
                </div>`;

            item.addEventListener('click', () => {
                this.coreModule.handleSuggestionClick(suggestion);
            });

            item.addEventListener('mouseenter', () => {
                this.coreModule.selectedSuggestionIndex = index;
                this.coreModule.updateSuggestionSelection();
            });
            return item;
        };

        // --- 1) RENDER QUICK-ACTIONS FIRST --------------------------------------------------
        const quickActions = suggestions.filter((s) => s.type === 'clock_id');
        let visualIndex = 0;

        if (quickActions.length) {
            const qaHeader = document.createElement('div');
            qaHeader.className = 'banner-suggestion-category-header';
            qaHeader.textContent = 'Quick actions';
            this.suggestionsContent.appendChild(qaHeader);
            quickActions.forEach((sugg) => {
                this.suggestionsContent.appendChild(createItem(sugg, visualIndex++));
            });
        }

        // --- 2) RENDER REMAINING GROUPS ------------------------------------------------------

        const groupOrder = [
            'text_suggestion', 'pattern', 'user', 'office', 'workstation', 'kb_article', 'note', 'device', 'search'
        ];

        const grouped = {};
        suggestions.forEach((s) => {
            if (s.type === 'clock_id') return; // already rendered
            const key = s.type || 'other';
            if (!grouped[key]) grouped[key] = [];
            grouped[key].push(s);
        });

        groupOrder.forEach((type) => {
            const items = grouped[type];
            if (items && items.length) {
                const header = document.createElement('div');
                header.className = 'banner-suggestion-category-header';
                header.textContent = {
                    'text_suggestion': 'Suggestions',
                    'pattern': 'Smart suggestions',
                    'user': 'Users',
                    'office': 'Offices',
                    'workstation': 'Workstations',
                    'kb_article': 'Knowledge Base',
                    'note': 'Notes',
                    'device': 'Devices',
                    'search': 'Search'
                }[type] || type;
                this.suggestionsContent.appendChild(header);

                items.forEach((sugg) => {
                    this.suggestionsContent.appendChild(createItem(sugg, visualIndex++));
                });
            }
        });

        // Fallback if some types were not in predefined order
        Object.keys(grouped).forEach((type) => {
            if (groupOrder.includes(type)) return; // already handled
            const header = document.createElement('div');
            header.className = 'banner-suggestion-category-header';
            header.textContent = type.charAt(0).toUpperCase() + type.slice(1);
            this.suggestionsContent.appendChild(header);
            grouped[type].forEach((sugg) => {
                this.suggestionsContent.appendChild(createItem(sugg, visualIndex++));
            });
        });

        this.coreModule.showSuggestions();
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