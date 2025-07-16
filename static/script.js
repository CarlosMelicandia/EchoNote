// Common functionality across pages
document.addEventListener('DOMContentLoaded', function() {
    // Add active class to current nav item
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('nav a');
    
    navLinks.forEach(link => {
      if (link.getAttribute('href') === currentPath) {
        link.classList.add('active');
      }
    });
  
    // Initialize any other common UI elements
    
    // Handle keyboard shortcuts that should work across the app
    document.addEventListener('keydown', function(e) {
      // Add any global keyboard shortcuts here
      // For example: Ctrl+S to save, Esc to cancel, etc.
    });
  });