// Navigation Active States Module
// Handles navigation active states, path normalization, and submenu functionality

document.addEventListener('DOMContentLoaded', function () {
    const navLinks = document.querySelectorAll('.nav-link');
    const submenuLinks = document.querySelectorAll('.submenu .nav-link');
    const submenuContainers = document.querySelectorAll('.submenu-container');

    // Function to update active states
    function updateActiveStates() {
        // Normalize paths by removing trailing slash (except for root) so \
        // that links like "/unified" match currentPath "/unified/" after Flask redirect.
        const normalizePath = (p) => {
            if (!p) return '';
            return p.length > 1 && p.endsWith('/') ? p.slice(0, -1) : p;
        };
        const currentPath = normalizePath(window.location.pathname);
        
        // Update main nav links
        navLinks.forEach(link => {
            link.classList.remove('active');
            const linkPath = normalizePath(link.getAttribute('href'));
            if (linkPath === currentPath) {
                link.classList.add('active');
            }
        });

        // Update submenu links and containers
        submenuLinks.forEach(link => {
            link.classList.remove('active');
            const linkPathSub = normalizePath(link.getAttribute('href'));
            if (linkPathSub === currentPath) {
                link.classList.add('active');
                // Keep parent submenu open when a submenu item is active
                const submenuContainer = link.closest('.submenu-container');
                if (submenuContainer) {
                    submenuContainer.classList.add('open');
                }
            }
        });
    }

    // Handle submenu clicks
    submenuLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const submenuContainer = this.closest('.submenu-container');
            if (submenuContainer) {
                // Add open class to keep submenu visible
                submenuContainer.classList.add('open');
            }
        });
    });

    // Handle main nav clicks
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Only handle clicks on main nav items (not submenu items)
            if (!this.closest('.submenu')) {
                navLinks.forEach(nav => nav.classList.remove('active'));
                this.classList.add('active');
            }
        });
    });

    // Initial update
    updateActiveStates();

    // Update on navigation
    window.addEventListener('popstate', updateActiveStates);
}); 