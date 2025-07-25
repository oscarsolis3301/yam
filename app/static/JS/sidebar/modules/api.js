// API Module
// Handles all API calls and data fetching for search functionality

class APIModule {
    constructor() {
        this.baseURL = '';
        this.defaultHeaders = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        };
    }
    
    async performSearch(query, signal) {
        // Use the unified search endpoint for better performance
        const response = await fetch(`/unified_search?q=${encodeURIComponent(query)}&limit=8`, {
            signal: signal
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
        
        return results;
    }
    
    async getClockIdSuggestions(query, signal) {
        try {
            const response = await fetch(`/api/clock-id/suggestions?q=${encodeURIComponent(query.trim())}`, {
                signal: signal
            });
            
            if (response.ok) {
                const data = await response.json();
                return data.success ? data.suggestions : [];
            }
        } catch (error) {
            console.warn('Clock ID cache lookup failed:', error);
        }
        
        return [];
    }
    
    async getUnifiedSearchData(query, signal) {
        try {
            const response = await fetch(`/unified_search?q=${encodeURIComponent(query)}&limit=8`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Cache-Control': 'max-age=60'
                },
                signal: signal
            });
            
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.warn('Unified search failed:', error);
        }
        
        return { offices: [], workstations: [] };
    }
    
    async loadUserProfileData(clockId, userData = null) {
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
        
        return userInfo;
    }
    
    async unlockAccount(userId) {
        const response = await fetch('/api/admin/unlock-account', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        
        if (!response.ok) {
            throw new Error('Failed to unlock account');
        }
        
        return await response.json();
    }
    
    async resetPassword(userId) {
        const response = await fetch('/api/admin/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        
        if (!response.ok) {
            throw new Error('Failed to reset password');
        }
        
        return await response.json();
    }
    
    async enableAccount(userId) {
        const response = await fetch('/api/admin/enable-account', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        
        if (!response.ok) {
            throw new Error('Failed to enable account');
        }
        
        return await response.json();
    }
    
    async disableAccount(userId) {
        const response = await fetch('/api/admin/disable-account', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        
        if (!response.ok) {
            throw new Error('Failed to disable account');
        }
        
        return await response.json();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIModule;
} else {
    window.APIModule = APIModule;
} 