<!-- FRESHSERVICE MAIN EVENT HANDLERS MODULE -->
<script>
// Main event handlers coordinator for FreshService component
window.FreshServiceEventHandlers = {
    
    // Initialize all event handlers
    init: function() {
        // Initialize specialized event handler modules
        if (window.FreshServiceSearchHandlers) {
            window.FreshServiceSearchHandlers.init();
        }
        
        if (window.FreshServiceFilterHandlers) {
            window.FreshServiceFilterHandlers.init();
        }
        
        // Initialize pagination handlers
        this.initPaginationHandlers();
        
        // Initialize modal handlers
        this.initModalHandlers();
        
        // Initialize responsive handlers
        this.initResponsiveHandlers();
        
        // Initialize global handlers
        this.initGlobalHandlers();
    },

    // Pagination functionality handlers
    initPaginationHandlers: function() {
        // Previous page
        const prevPage = document.getElementById('prevPage');
        if (prevPage) {
            prevPage.addEventListener('click', function() {
                if (window.FreshServiceApp.state.currentPage > 1) {
                    window.FreshServiceApp.state.currentPage--;
                    window.FreshServiceApp.loadTickets();
                }
            });
        }

        // Next page
        const nextPage = document.getElementById('nextPage');
        if (nextPage) {
            nextPage.addEventListener('click', function() {
                window.FreshServiceApp.state.currentPage++;
                window.FreshServiceApp.loadTickets();
            });
        }

        // Page size selector
        const pageSize = document.getElementById('pageSize');
        if (pageSize) {
            pageSize.addEventListener('change', function() {
                window.FreshServiceApp.state.pageSize = parseInt(this.value);
                window.FreshServiceApp.state.currentPage = 1;
                window.FreshServiceApp.loadTickets();
            });
        }
    },

    // Modal functionality handlers
    initModalHandlers: function() {
        // Ticket detail modal
        const ticketModal = document.getElementById('ticketModal');
        if (ticketModal) {
            // Close modal on backdrop click
            ticketModal.addEventListener('click', function(e) {
                if (e.target === ticketModal) {
                    this.closeModal();
                }
            }.bind(this));

            // Close modal on escape key
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' && ticketModal.classList.contains('show')) {
                    this.closeModal();
                }
            }.bind(this));
        }

        // Close modal button
        const closeModalBtn = document.querySelector('.close-modal');
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', function() {
                this.closeModal();
            }.bind(this));
        }
    },

    // Close modal
    closeModal: function() {
        const ticketModal = document.getElementById('ticketModal');
        if (ticketModal) {
            ticketModal.classList.remove('show');
            document.body.classList.remove('modal-open');
        }
    },

    // Responsive functionality handlers
    initResponsiveHandlers: function() {
        // Sidebar toggle for mobile
        const sidebarToggle = document.querySelector('.sidebar-toggle');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', function() {
                this.toggleSidebar();
            }.bind(this));
        }

        // Handle window resize
        window.addEventListener('resize', window.FreshServiceUtils.core.debounce(function() {
            this.handleResize();
        }.bind(this), 250));
    },

    // Toggle sidebar
    toggleSidebar: function() {
        const sidebar = document.querySelector('.filters-sidebar');
        const mainContent = document.querySelector('.freshservice-main');
        
        if (sidebar && mainContent) {
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('expanded');
        }
    },

    // Handle window resize
    handleResize: function() {
        const width = window.innerWidth;
        
        // Auto-collapse sidebar on small screens
        if (width < 768) {
            const sidebar = document.querySelector('.filters-sidebar');
            if (sidebar && !sidebar.classList.contains('collapsed')) {
                this.toggleSidebar();
            }
        }
    },

    // Global functionality handlers
    initGlobalHandlers: function() {
        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + F for search
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                const searchInput = document.getElementById('searchInput');
                if (searchInput) {
                    searchInput.focus();
                }
            }
            
            // Ctrl/Cmd + R for refresh
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                window.FreshServiceApp.loadTickets();
            }
        });

        // Handle clicks outside of dropdowns
        document.addEventListener('click', function(e) {
            // Close any open dropdowns
            const dropdowns = document.querySelectorAll('.dropdown.show');
            dropdowns.forEach(dropdown => {
                if (!dropdown.contains(e.target)) {
                    dropdown.classList.remove('show');
                }
            });
        });

        // Handle form submissions
        document.addEventListener('submit', function(e) {
            // Prevent default form submission for filter forms
            if (e.target.classList.contains('filter-form')) {
                e.preventDefault();
                window.FreshServiceApp.loadTickets();
            }
        });
    },

    // Cleanup event handlers
    cleanup: function() {
        // Remove event listeners to prevent memory leaks
        // This would be called when the component is destroyed
        console.log('Cleaning up event handlers');
    }
};
</script> 