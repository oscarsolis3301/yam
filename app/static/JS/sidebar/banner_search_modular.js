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
        
        // Delegate suggestion selection to suggestions module
        selectSuggestion(suggestion, type = 'text', data = {}) {
            if (this.suggestionsModule) {
                this.suggestionsModule.selectSuggestion(suggestion, type, data);
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