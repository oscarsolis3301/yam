// Results Module
// Handles search results display and result interactions

class ResultsModule {
    constructor(coreModule) {
        this.coreModule = coreModule;
        this.resultsContent = document.getElementById('bannerResultsContent');
    }
    
    displayResults(results) {
        // Convert results into the same shape used by SuggestionsModule
        const convertedResults = (results || []).map((r) => ({
            text: r.title,
            icon: r.icon || 'bi bi-file-text',
            subtitle: r.description || '',
            type: r.content_type || 'result',
            url: r.url,
            data: r
        }));

        // Merge with any existing suggestions the SuggestionsModule is already holding
        const current = this.coreModule.currentSuggestions || [];
        const merged = [
            // keep existing suggestions first so smart / quick-actions stay on top
            ...current,
            // add a divider category header only once if we have new results
            ...(
                convertedResults.length ? [{
                    text: 'Search results',
                    icon: 'bi bi-search',
                    subtitle: 'Matches from all content',
                    type: 'header'
                }] : []
            ),
            ...convertedResults
        ];

        // De-duplicate by text to avoid showing identical entries twice
        const seen = new Set();
        const unique = merged.filter((s) => {
            const key = (s.text || '').toLowerCase();
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });

        this.coreModule.currentSuggestions = unique;

        if (this.coreModule.suggestionsModule) {
            this.coreModule.suggestionsModule.displaySuggestions(unique);
        }

        // Ensure the suggestions dropdown is visible again (it may have been hidden before search ran)
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