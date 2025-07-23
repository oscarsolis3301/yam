// --- State Machine for Search Bar Visibility ---
(function() {
    let searchState = 'hidden';
    const container = document.getElementById('universalSearchContainer');
    const input = document.getElementById('universalSearchInput');
    const blurOverlay = document.getElementById('searchBlurOverlay');
    
    function flyOutSearchBar() {
        if (container && searchState === 'visible') {
            container.style.transition = 'transform 0.6s cubic-bezier(0.4, 0.8, 0.2, 1), opacity 0.5s';
            container.style.transform = 'translate(-50%, -60%) scale(0.95)';
            container.style.opacity = '0';
            setTimeout(() => {
                container.style.display = 'none';
                container.style.transform = 'translate(-50%, -50%) scale(1)';
                container.style.opacity = '1';
                searchState = 'hidden';
                // Remove blur effect
                if (blurOverlay) {
                    blurOverlay.classList.remove('active');
                }
                // Notify listeners (e.g., sidebar icon) of close action
                window.dispatchEvent(new CustomEvent('universalSearchToggled', { detail: 'close' }));
            }, 600);
        }
    }
    
    function flyInSearchBar() {
        if (container && searchState === 'hidden') {
            container.style.display = 'block';
            container.style.opacity = '0';
            container.style.transition = 'transform 0.6s cubic-bezier(0.4, 0.8, 0.2, 1), opacity 0.5s';
            container.offsetHeight;
            container.style.transform = 'translate(-50%, -50%) scale(1)';
            container.style.opacity = '1';
            setTimeout(() => {
                searchState = 'visible';
                if (input) input.focus();
                // Add blur effect
                if (blurOverlay) {
                    blurOverlay.classList.add('active');
                }
                // Notify listeners of open action
                window.dispatchEvent(new CustomEvent('universalSearchToggled', { detail: 'open' }));
            }, 600);
        }
    }
    
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            if (searchState === 'visible') {
                flyOutSearchBar();
            } else if (searchState === 'hidden') {
                flyInSearchBar();
            }
        }
    });

    // Expose global helpers so other components (e.g., sidebar) can toggle the panel
    window.openUniversalSearchBar = flyInSearchBar;
    window.closeUniversalSearchBar = flyOutSearchBar;
    window.isUniversalSearchOpen = () => searchState === 'visible';

    // Close the search bar when the blurred overlay itself is clicked
    if (blurOverlay) {
        blurOverlay.addEventListener('click', function () {
            if (searchState === 'visible') {
                flyOutSearchBar();
            }
        });
    }
})(); 