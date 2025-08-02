<!-- FRESHSERVICE DOM UTILITIES MODULE -->
<script>
// FreshService DOM Utilities
window.FreshServiceDOMUtils = {
    // Get element by ID with error handling
    getById: function(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Element with ID '${id}' not found`);
        }
        return element;
    },

    // Get elements by selector with error handling
    querySelector: function(selector, parent = document) {
        const element = parent.querySelector(selector);
        if (!element) {
            console.warn(`Element with selector '${selector}' not found`);
        }
        return element;
    },

    // Get all elements by selector
    querySelectorAll: function(selector, parent = document) {
        return parent.querySelectorAll(selector);
    },

    // Create element with attributes
    createElement: function(tag, attributes = {}, innerHTML = '') {
        const element = document.createElement(tag);
        
        // Set attributes
        Object.keys(attributes).forEach(key => {
            if (key === 'className') {
                element.className = attributes[key];
            } else if (key === 'innerHTML') {
                element.innerHTML = attributes[key];
            } else {
                element.setAttribute(key, attributes[key]);
            }
        });
        
        if (innerHTML) {
            element.innerHTML = innerHTML;
        }
        
        return element;
    },

    // Add event listener with error handling
    addEventListener: function(element, event, handler, options = {}) {
        if (!element) {
            console.warn('Cannot add event listener to null element');
            return;
        }
        
        try {
            element.addEventListener(event, handler, options);
        } catch (error) {
            console.error(`Error adding event listener for ${event}:`, error);
        }
    },

    // Remove event listener
    removeEventListener: function(element, event, handler, options = {}) {
        if (!element) return;
        
        try {
            element.removeEventListener(event, handler, options);
        } catch (error) {
            console.error(`Error removing event listener for ${event}:`, error);
        }
    },

    // Show/hide elements
    show: function(element) {
        if (element) element.style.display = '';
    },

    hide: function(element) {
        if (element) element.style.display = 'none';
    },

    // Toggle element visibility
    toggle: function(element) {
        if (element) {
            element.style.display = element.style.display === 'none' ? '' : 'none';
        }
    },

    // Add/remove CSS classes
    addClass: function(element, className) {
        if (element && !element.classList.contains(className)) {
            element.classList.add(className);
        }
    },

    removeClass: function(element, className) {
        if (element && element.classList.contains(className)) {
            element.classList.remove(className);
        }
    },

    toggleClass: function(element, className) {
        if (element) {
            element.classList.toggle(className);
        }
    }
};
</script> 