// Results Module
// Handles search results display and result interactions

class ResultsModule {
    constructor(coreModule) {
        this.coreModule = coreModule;
        this.resultsContent = document.getElementById('bannerResultsContent');
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
            this.coreModule.showResults();
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
                this.coreModule.handleResultClick(result);
            });
            
            this.resultsContent.appendChild(item);
        });
        
        this.coreModule.showResults();
    }
    
    displayError(message) {
        if (!this.resultsContent) return;
        
        this.resultsContent.innerHTML = `
            <div class="banner-search-error">
                <i class="bi bi-exclamation-triangle"></i>
                <p>${message}</p>
            </div>
        `;
        this.coreModule.showResults();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ResultsModule;
} else {
    window.ResultsModule = ResultsModule;
} 