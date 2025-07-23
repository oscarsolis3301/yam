"""
Content Highlighter Utility

This module provides utilities for highlighting search terms in content
when users navigate from search results.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ContentHighlighter:
    """Utility class for highlighting search terms in content."""
    
    def __init__(self):
        self.highlight_class = 'search-highlight'
        self.highlight_style = f"""
            .{self.highlight_class} {{
                background: linear-gradient(120deg, #ffd54f 0%, #ffb300 100%);
                color: #000;
                padding: 2px 4px;
                border-radius: 3px;
                font-weight: 600;
                box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                animation: highlight-pulse 2s ease-in-out;
            }}
            
            @keyframes highlight-pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.05); }}
                100% {{ transform: scale(1); }}
            }}
        """
    
    def highlight_text(self, text: str, query: str, max_highlights: int = 10) -> str:
        """
        Highlight search terms in text content.
        
        Args:
            text: The text content to highlight
            query: The search query
            max_highlights: Maximum number of highlights to apply
            
        Returns:
            Text with highlighted search terms
        """
        if not text or not query:
            return text
        
        try:
            # Split query into individual terms
            query_terms = self._extract_search_terms(query)
            
            if not query_terms:
                return text
            
            highlighted_text = text
            highlight_count = 0
            
            for term in query_terms:
                if highlight_count >= max_highlights:
                    break
                
                if len(term) > 2:  # Only highlight terms longer than 2 characters
                    # Create regex pattern for case-insensitive matching
                    pattern = re.compile(re.escape(term), re.IGNORECASE)
                    
                    # Find all matches
                    matches = list(pattern.finditer(highlighted_text))
                    
                    # Apply highlights (in reverse order to maintain positions)
                    for match in reversed(matches):
                        if highlight_count >= max_highlights:
                            break
                        
                        start, end = match.span()
                        original_text = highlighted_text[start:end]
                        
                        # Check if this text is already highlighted
                        if f'<span class="{self.highlight_class}">' not in highlighted_text[:start]:
                            highlighted_text = (
                                highlighted_text[:start] +
                                f'<span class="{self.highlight_class}">{original_text}</span>' +
                                highlighted_text[end:]
                            )
                            highlight_count += 1
            
            return highlighted_text
            
        except Exception as e:
            logger.error(f"Error highlighting text: {e}")
            return text
    
    def highlight_page_content(self, query: str, content_selectors: Optional[List[str]] = None) -> str:
        """
        Generate JavaScript to highlight search terms on the current page.
        
        Args:
            query: The search query
            content_selectors: CSS selectors for content to highlight
            
        Returns:
            JavaScript code to highlight content
        """
        if not query:
            return ""
        
        if content_selectors is None:
            content_selectors = [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'p', 'div.content', 'div.description', 'div.text',
                'span', 'td', 'li'
            ]
        
        query_terms = self._extract_search_terms(query)
        
        if not query_terms:
            return ""
        
        js_code = f"""
        (function() {{
            const highlightClass = '{self.highlight_class}';
            const queryTerms = {query_terms};
            const maxHighlights = 20;
            let highlightCount = 0;
            
            // Add highlight styles
            if (!document.getElementById('search-highlight-styles')) {{
                const style = document.createElement('style');
                style.id = 'search-highlight-styles';
                style.textContent = `{self.highlight_style}`;
                document.head.appendChild(style);
            }}
            
            function highlightText(text, terms) {{
                let highlightedText = text;
                
                for (const term of terms) {{
                    if (highlightCount >= maxHighlights) break;
                    if (term.length <= 2) continue;
                    
                    const regex = new RegExp('(' + term.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
                    const matches = highlightedText.match(regex);
                    
                    if (matches) {{
                        highlightedText = highlightedText.replace(regex, 
                            '<span class="' + highlightClass + '">$1</span>');
                        highlightCount += matches.length;
                    }}
                }}
                
                return highlightedText;
            }}
            
            function highlightElement(element) {{
                if (element.children.length === 0) {{
                    // Text node
                    const text = element.textContent;
                    if (text && text.trim().length > 0) {{
                        const highlightedText = highlightText(text, queryTerms);
                        if (highlightedText !== text) {{
                            element.innerHTML = highlightedText;
                        }}
                    }}
                }} else {{
                    // Element with children
                    for (const child of element.children) {{
                        highlightElement(child);
                    }}
                }}
            }}
            
            // Highlight content in specified selectors
            const selectors = {content_selectors};
            for (const selector of selectors) {{
                const elements = document.querySelectorAll(selector);
                for (const element of elements) {{
                    highlightElement(element);
                }}
            }}
            
            // Scroll to first highlight
            const firstHighlight = document.querySelector('.' + highlightClass);
            if (firstHighlight) {{
                firstHighlight.scrollIntoView({{
                    behavior: 'smooth',
                    block: 'center'
                }});
                
                // Add focus effect
                firstHighlight.style.animation = 'highlight-pulse 1s ease-in-out 3';
            }}
            
            console.log('Search highlighting applied for query:', queryTerms);
        }})();
        """
        
        return js_code
    
    def _extract_search_terms(self, query: str) -> List[str]:
        """
        Extract meaningful search terms from a query.
        
        Args:
            query: The search query
            
        Returns:
            List of search terms
        """
        if not query:
            return []
        
        # Clean and split the query
        cleaned_query = re.sub(r'[^\w\s]', ' ', query.lower())
        terms = cleaned_query.split()
        
        # Filter out common stop words and short terms
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have',
            'had', 'what', 'said', 'each', 'which', 'she', 'do', 'how', 'their',
            'if', 'up', 'out', 'many', 'then', 'them', 'these', 'so', 'some',
            'her', 'would', 'make', 'like', 'into', 'him', 'time', 'two',
            'more', 'go', 'no', 'way', 'could', 'my', 'than', 'first', 'been',
            'call', 'who', 'its', 'now', 'find', 'long', 'down', 'day', 'did',
            'get', 'come', 'made', 'may', 'part'
        }
        
        filtered_terms = []
        for term in terms:
            if len(term) > 2 and term not in stop_words:
                filtered_terms.append(term)
        
        return filtered_terms
    
    def generate_highlight_script(self, query: str) -> str:
        """
        Generate a complete script tag for highlighting search terms.
        
        Args:
            query: The search query
            
        Returns:
            Complete script tag with highlighting code
        """
        js_code = self.highlight_page_content(query)
        
        if not js_code:
            return ""
        
        return f"""
        <script>
        {js_code}
        </script>
        """
    
    def should_highlight(self, search_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if highlighting should be applied based on search context.
        
        Args:
            search_context: Search context from session storage
            
        Returns:
            True if highlighting should be applied
        """
        if not search_context:
            return False
        
        # Check if search context is recent (within last 5 minutes)
        timestamp = search_context.get('timestamp', 0)
        if timestamp:
            search_time = datetime.fromtimestamp(timestamp / 1000)
            if datetime.now() - search_time > timedelta(minutes=5):
                return False
        
        # Check if there's a valid query
        query = search_context.get('query', '').strip()
        return len(query) >= 2
    
    def get_search_context_from_storage(self) -> Optional[Dict[str, Any]]:
        """
        Get search context from browser session storage.
        
        Returns:
            Search context dictionary or None
        """
        try:
            # This will be called from JavaScript
            return None  # Placeholder for JavaScript implementation
        except Exception as e:
            logger.error(f"Error getting search context: {e}")
            return None

# Global instance
content_highlighter = ContentHighlighter() 