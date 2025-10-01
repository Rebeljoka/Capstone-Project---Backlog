// Dark Mode Toggle Functionality
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;
    
    if (themeToggle) {
        // Check for saved theme preference or default to light mode
        const currentTheme = localStorage.getItem('theme') || 'light';
        
        // Apply the current theme
        if (currentTheme === 'dark') {
            htmlElement.setAttribute('data-theme', 'dark');
            themeToggle.checked = true;
        } else {
            htmlElement.setAttribute('data-theme', 'light');
            themeToggle.checked = false;
        }
        
        // Toggle theme when switch is clicked
        themeToggle.addEventListener('change', function() {
            if (this.checked) {
                htmlElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            } else {
                htmlElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
            }
        });
    }
    
    // Language Selector Functionality
    const languageSelect = document.getElementById('language-select');
    
    if (languageSelect) {
        // Check for saved language preference, default to English
        const currentLanguage = localStorage.getItem('language') || 'en';
        
        // Function to update language options with checkmarks
        function updateLanguageOptions(selectedLang) {
            const options = languageSelect.querySelectorAll('option');
            options.forEach(option => {
                const value = option.value;
                const text = option.textContent.replace(' ✓', ''); // Remove existing checkmark
                
                if (value === selectedLang) {
                    option.textContent = text + ' ✓'; // Add checkmark to selected
                } else {
                    option.textContent = text; // Remove checkmark from others
                }
            });
        }
        
        // Set initial language and update display
        languageSelect.value = currentLanguage;
        updateLanguageOptions(currentLanguage);
        
        // Change language when selector changes
        languageSelect.addEventListener('change', function() {
            const selectedLanguage = this.value;
            localStorage.setItem('language', selectedLanguage);
            
            // Update the checkmarks
            updateLanguageOptions(selectedLanguage);
            
            // Here you can add actual language switching logic
            // For now, we'll just show a message
            console.log('Language changed to:', selectedLanguage);
            
            // You could redirect to a language-specific URL or
            // trigger a translation system here
            // Example: window.location.href = `/${selectedLanguage}/`;
        });
    }
});