/**
 * Search Highlighting Utility
 * 
 * This utility provides functions for highlighting search terms in text
 * and applying search context when navigating from search results.
 */

class SearchHighlight {
    constructor() {
        this.highlightClass = 'search-highlight';
        this.init();
    }
    
    init() {
        // Check for search context on page load
        this.checkSearchContext();
    }
    
    /**
     * Check for search context and apply highlighting
     */
    checkSearchContext() {
        try {
            const searchContext = JSON.parse(sessionStorage.getItem('searchContext') || '{}');
            if (searchContext.query) {
                this.highlightSearchTerms(searchContext.query);
                
                // Clear the context after applying
                sessionStorage.removeItem('searchContext');
                
                // Scroll to highlighted elements if they exist
                setTimeout(() => {
                    this.scrollToHighlighted();
                }, 100);
            }
        } catch (error) {
            console.error('Error checking search context:', error);
        }
    }
    
    /**
     * Highlight search terms in the current page
     * @param {string} query - The search query
     */
    highlightSearchTerms(query) {
        if (!query || query.trim().length === 0) {
            return;
        }
        
        const searchTerms = this.extractSearchTerms(query);
        if (searchTerms.length === 0) {
            return;
        }
        
        // Highlight in main content areas
        const contentSelectors = [
            'main',
            '.content',
            '.main-content',
            'article',
            '.article-content',
            '.kb-content',
            '.outage-content'
        ];
        
        contentSelectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                this.highlightElement(element, searchTerms);
            });
        });
    }
    
    /**
     * Extract search terms from query
     * @param {string} query - The search query
     * @returns {Array} Array of search terms
     */
    extractSearchTerms(query) {
        return query.toLowerCase()
            .split(/\s+/)
            .filter(term => term.length >= 2)
            .map(term => term.replace(/[^\w]/g, ''));
    }
    
    /**
     * Highlight search terms in a specific element
     * @param {Element} element - The element to highlight
     * @param {Array} searchTerms - Array of search terms
     */
    highlightElement(element, searchTerms) {
        if (!element || searchTerms.length === 0) {
            return;
        }
        
        // Walk through text nodes
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: function(node) {
                    // Skip script and style tags
                    const parent = node.parentElement;
                    if (parent && (parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE')) {
                        return NodeFilter.FILTER_REJECT;
                    }
                    return NodeFilter.FILTER_ACCEPT;
                }
            }
        );
        
        const textNodes = [];
        let node;
        while (node = walker.nextNode()) {
            textNodes.push(node);
        }
        
        // Process each text node
        textNodes.forEach(textNode => {
            this.highlightTextNode(textNode, searchTerms);
        });
    }
    
    /**
     * Highlight search terms in a text node
     * @param {Text} textNode - The text node to highlight
     * @param {Array} searchTerms - Array of search terms
     */
    highlightTextNode(textNode, searchTerms) {
        const text = textNode.textContent;
        let highlightedText = text;
        
        searchTerms.forEach(term => {
            const regex = new RegExp(`(${this.escapeRegex(term)})`, 'gi');
            highlightedText = highlightedText.replace(regex, `<mark class="${this.highlightClass}">$1</mark>`);
        });
        
        if (highlightedText !== text) {
            const wrapper = document.createElement('span');
            wrapper.innerHTML = highlightedText;
            textNode.parentNode.replaceChild(wrapper, textNode);
        }
    }
    
    /**
     * Escape special regex characters
     * @param {string} string - String to escape
     * @returns {string} Escaped string
     */
    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    /**
     * Scroll to the first highlighted element
     */
    scrollToHighlighted() {
        const highlighted = document.querySelector(`.${this.highlightClass}`);
        if (highlighted) {
            highlighted.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
            
            // Add a brief flash effect
            highlighted.style.transition = 'background-color 0.3s ease';
            highlighted.style.backgroundColor = '#fff3cd';
            setTimeout(() => {
                highlighted.style.backgroundColor = '';
            }, 1000);
        }
    }
    
    /**
     * Remove all highlights from the page
     */
    removeHighlights() {
        const highlights = document.querySelectorAll(`.${this.highlightClass}`);
        highlights.forEach(highlight => {
            const parent = highlight.parentNode;
            if (parent) {
                parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
                parent.normalize(); // Merge adjacent text nodes
            }
        });
    }
    
    /**
     * Store search context for highlighting on next page
     * @param {string} query - The search query
     * @param {string} resultId - Optional result ID
     */
    storeSearchContext(query, resultId = null) {
        const context = {
            query: query,
            resultId: resultId,
            timestamp: Date.now()
        };
        sessionStorage.setItem('searchContext', JSON.stringify(context));
    }
}

// Initialize search highlighting when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.searchHighlight = new SearchHighlight();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SearchHighlight;
} 