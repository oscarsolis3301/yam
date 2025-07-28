// Modular Banner Search
// Main entry point that coordinates all modules

(function() {
    'use strict';
    
    console.log('Modular Banner Search: Loading...');
    
    // Import all modules
    // Note: In a real environment, you would use ES6 imports or a module loader
    // For this implementation, we assume all modules are loaded before this file
    
    class ModularBannerSearch {
        constructor() {
            console.log('Modular Banner Search: Initializing...');
            
            // Initialize all modules
            this.initializeModules();
            
            // Set up module references
            this.setupModuleReferences();
            
            // Expose instance globally for suggestions to use
            window.bannerSearchInstance = this;
            
            // Ensure selectSuggestion is available globally as a fallback
            this.ensureGlobalMethods();
            
            console.log('Modular Banner Search: Initialization complete');
        }
        
        initializeModules() {
            // Initialize core search module
            this.coreModule = new CoreSearch();
            
            // Initialize API module
            this.apiModule = new APIModule();
            
            // Initialize suggestions module with core reference
            this.suggestionsModule = new SuggestionsModule(this.coreModule);
            
            // Initialize results module with core reference
            this.resultsModule = new ResultsModule(this.coreModule);
            
            // Initialize user profile module with core and API references
            this.userProfileModule = new UserProfileModule(this.coreModule, this.apiModule);
            
            // Initialize ticket module
            this.ticketModule = new TicketModule();
        }
        
        setupModuleReferences() {
            // Set up cross-module references
            this.coreModule.setSuggestionsModule(this.suggestionsModule);
            this.coreModule.setResultsModule(this.resultsModule);
            this.coreModule.setUserProfileModule(this.userProfileModule);
            this.coreModule.setTicketModule(this.ticketModule);
            this.coreModule.setAPIModule(this.apiModule);
        }
        
        ensureGlobalMethods() {
            // Ensure selectSuggestion is available globally as a fallback
            if (!window.selectSuggestion) {
                window.selectSuggestion = (suggestion, type = 'text', data = {}) => {
                    console.log('Global selectSuggestion called:', { suggestion, type, data });
                    this.selectSuggestion(suggestion, type, data);
                };
            }
        }
        
        // Delegate suggestion selection to suggestions module
        selectSuggestion(suggestion, type = 'text', data = {}) {
            console.log('ModularBannerSearch.selectSuggestion called:', { suggestion, type, data });
            
            try {
                if (this.suggestionsModule && typeof this.suggestionsModule.selectSuggestion === 'function') {
                    console.log('Delegating to suggestionsModule.selectSuggestion');
                    this.suggestionsModule.selectSuggestion(suggestion, type, data);
                } else {
                    console.error('suggestionsModule not available or selectSuggestion method missing');
                    // Fallback: handle clock_id directly
                    if (type === 'clock_id') {
                        this.handleClockIdFallback(suggestion, data);
                    }
                }
            } catch (error) {
                console.error('Error in selectSuggestion:', error);
                // Fallback: handle clock_id directly
                if (type === 'clock_id') {
                    this.handleClockIdFallback(suggestion, data);
                }
            }
        }
        
        handleClockIdFallback(suggestion, data) {
            console.log('Handling clock_id fallback:', { suggestion, data });
            const cid = (data.clock_id || suggestion).toString().replace(/\D/g, '').padStart(5, '0');
            if (cid) {
                if (typeof window.showSidebarUserModal === 'function') {
                    console.log('Calling window.showSidebarUserModal with clockId:', cid);
                    window.showSidebarUserModal(cid, data.user_data);
                } else {
                    console.error('showSidebarUserModal not available');
                    // Last resort: redirect to user lookup page
                    window.location.href = `/api/clock-id/lookup/${cid}`;
                }
            }
        }
    }
    
    // Initialize the modular banner search when DOM is ready
    console.log('Modular Banner Search: DOM ready state:', document.readyState);
    if (document.readyState === 'loading') {
        console.log('Modular Banner Search: DOM still loading, waiting for DOMContentLoaded...');
        document.addEventListener('DOMContentLoaded', () => {
            console.log('Modular Banner Search: DOMContentLoaded fired, creating ModularBannerSearch instance...');
            new ModularBannerSearch();
        });
    } else {
        console.log('Modular Banner Search: DOM already ready, creating ModularBannerSearch instance immediately...');
        new ModularBannerSearch();
    }
})(); 