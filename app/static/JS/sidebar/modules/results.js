// Results Module
// Handles search results display and result interactions

class ResultsModule {
    constructor(coreModule) {
        this.coreModule = coreModule;
        this.resultsContent = document.getElementById('bannerResultsContent');
    }
    
    displayResults(results) {
        // Convert results into the new suggestions structure format
        const convertedResults = (results || []).map((r) => ({
            text: r.title,
            icon: r.icon || 'bi bi-file-text',
            subtitle: r.description || '',
            type: r.content_type || 'result',
            url: r.url,
            data: r
        }));

        // Get current suggestions structure
        const currentSuggestions = this.coreModule.suggestionsModule?.getCachedSuggestions(this.coreModule.currentQuery) || {
            clockSuggestions: [],
            offices: [],
            workstations: [],
            textSuggestions: [],
            commonSuggestions: []
        };

        // Create new suggestions structure with search results
        const newSuggestions = {
            clockSuggestions: currentSuggestions.clockSuggestions || [],
            offices: currentSuggestions.offices || [],
            workstations: currentSuggestions.workstations || [],
            textSuggestions: currentSuggestions.textSuggestions || [],
            commonSuggestions: currentSuggestions.commonSuggestions || [],
            searchResults: convertedResults
        };

        // Display the updated suggestions
        if (this.coreModule.suggestionsModule) {
            this.coreModule.suggestionsModule.displaySuggestions(newSuggestions);
        }

        // Ensure the suggestions dropdown is visible
        this.coreModule.showSuggestions();
    }
    
    displayError(message) {
        // Surface the error inside suggestions dropdown so the user still sees feedback
        const current = this.coreModule.currentSuggestions || [];
        const errorSuggestion = {
            text: 'Error',
            icon: 'bi bi-exclamation-triangle',
            subtitle: message,
            type: 'error'
        };
        const merged = [...current, errorSuggestion];
        this.coreModule.currentSuggestions = merged;
        if (this.coreModule.suggestionsModule) {
            this.coreModule.suggestionsModule.displaySuggestions(merged);
        }
        this.coreModule.showSuggestions();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ResultsModule;
} else {
    window.ResultsModule = ResultsModule;
} 