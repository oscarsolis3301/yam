// Sidebar Collapse Module
// Handles sidebar collapse/toggle functionality and positioning

document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.querySelector('.sidebar-fixed');
    const collapseBtn = document.getElementById('sidebarCollapseBtn');
    const testToggleBtn = document.getElementById('testToggleBtn');

    // Function to ensure sidebar is always positioned correctly
    function ensureSidebarPosition() {
        if (sidebar) {
            sidebar.style.position = 'fixed';
            sidebar.style.top = '0';
            sidebar.style.left = '0';
            sidebar.style.zIndex = '9999999';
            sidebar.style.margin = '0';
            sidebar.style.padding = '0';
        }
    }

    function toggleSidebar() {
        const wasCollapsed = sidebar.classList.contains('collapsed');
        sidebar.classList.toggle('collapsed');
        
        // Dispatch custom event with collapsed state
        document.dispatchEvent(new CustomEvent('sidebarCollapsed', {
            detail: {
                collapsed: !wasCollapsed
            }
        }));

        // Store the state in localStorage
        localStorage.setItem('sidebarCollapsed', !wasCollapsed);
    }

    // Initialize sidebar state from localStorage
    const savedState = localStorage.getItem('sidebarCollapsed');
    if (savedState === 'true') {
        sidebar.classList.add('collapsed');
        document.dispatchEvent(new CustomEvent('sidebarCollapsed', {
            detail: {
                collapsed: true
            }
        }));
    }

    // Ensure sidebar position on load and periodically
    ensureSidebarPosition();
    setInterval(ensureSidebarPosition, 1000);

    collapseBtn.addEventListener('click', toggleSidebar);
    if (testToggleBtn) {
        testToggleBtn.addEventListener('click', toggleSidebar);
    }
}); 