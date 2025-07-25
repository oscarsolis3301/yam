// Universal Search Toggle Module
// Handles universal search toggle via sidebar icon

// --- Universal Search toggle via sidebar icon ---
const searchToggle = document.getElementById('sidebarUniversalSearchToggle');
if (searchToggle) {
    const updateActiveVisual = (isActive) => {
        if (isActive) {
            searchToggle.classList.add('search-active');
        } else {
            searchToggle.classList.remove('search-active');
        }
    };

    searchToggle.addEventListener('click', function (e) {
        e.preventDefault();
        if (window.isUniversalSearchOpen && window.isUniversalSearchOpen()) {
            window.closeUniversalSearchBar();
            updateActiveVisual(false);
        } else {
            window.openUniversalSearchBar();
            updateActiveVisual(true);
        }
    });

    // Sync with other toggles (keyboard shortcut etc.)
    window.addEventListener('universalSearchToggled', function (evt) {
        updateActiveVisual(evt.detail === 'open');
    });
} 