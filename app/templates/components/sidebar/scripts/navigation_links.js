// Navigation Links Module
// Handles basic navigation link click events and active states

document.addEventListener('DOMContentLoaded', function () {
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        link.addEventListener('click', function () {
            navLinks.forEach(nav => nav.classList.remove('active')); // Remove from all
            this.classList.add('active'); // Add to clicked one
        });
    });
}); 