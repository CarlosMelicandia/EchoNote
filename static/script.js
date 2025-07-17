// Common functionality across pages
document.addEventListener('DOMContentLoaded', function() {
    // Load theme from localStorage with robust error handling
    try {
        const savedThemeJSON = localStorage.getItem('echoNoteTheme');
        console.log('Raw theme data from localStorage:', savedThemeJSON);
        
        if (savedThemeJSON && savedThemeJSON !== 'undefined') {
            const savedTheme = JSON.parse(savedThemeJSON);
            console.log('Parsed theme data:', savedTheme);
            
            // Apply theme only if we have valid data
            if (savedTheme && typeof savedTheme === 'object') {
                // Apply each property with fallbacks
                document.documentElement.style.setProperty('--bg-primary', savedTheme.bgPrimary || '#212121');
                document.documentElement.style.setProperty('--bg-secondary', savedTheme.bgSecondary || '#303030');
                document.documentElement.style.setProperty('--text-primary', savedTheme.textPrimary || '#ececf1');
                document.documentElement.style.setProperty('--text-secondary', savedTheme.textSecondary || '#ffffff');
                document.documentElement.style.setProperty('--accent', savedTheme.accent || '#FCFCFD');
                document.documentElement.style.setProperty('--button-text', savedTheme.buttonText || '#36395A');
                document.documentElement.style.setProperty('--border-color', savedTheme.borderColor || '#444');
                
                console.log('Theme applied successfully');
            }
        } else {
            console.log('No saved theme found in localStorage');
        }
    } catch (error) {
        console.error('Error loading theme:', error);
    }

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