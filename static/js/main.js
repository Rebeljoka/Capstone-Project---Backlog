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


    // Navigation search functionality - adapted from game_list search
    document.addEventListener('DOMContentLoaded', function() {
        // Update the search functions to work with navigation search
        const originalHandleSearchInput = window.handleSearchInput;
        const originalDisplaySuggestions = window.displaySuggestions;
        const originalHideSearchSuggestions = window.hideSearchSuggestions;
        const originalSelectSuggestion = window.selectSuggestion;
        
        // Override functions for navigation search
        window.handleSearchInput = function(input) {
            const isNavSearch = input.id === 'searchInputNav';
            
            if (isNavSearch) {
                clearTimeout(window.searchTimeout);
                const query = input.value.trim();
                
                if (query.length < 2) {
                    hideNavSearchSuggestions();
                    return;
                }
                
                window.searchTimeout = setTimeout(() => {
                    fetchNavSearchSuggestions(query);
                }, 300);
            } else if (originalHandleSearchInput) {
                originalHandleSearchInput(input);
            }
        };
        
        // Navigation-specific functions
        window.fetchNavSearchSuggestions = async function(query) {
            if (window.searchCache && window.searchCache.has(query)) {
                displayNavSuggestions(window.searchCache.get(query), query);
                return;
            }
            
            showNavSearchLoading();
            
            try {
                const response = await fetch(`/games/api/search-suggestions/?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                if (response.ok) {
                    if (!window.searchCache) {
                        window.searchCache = new Map();
                    }
                    window.searchCache.set(query, data.suggestions);
                    displayNavSuggestions(data.suggestions, query);
                } else {
                    hideNavSearchSuggestions();
                }
            } catch (error) {
                console.error('Nav search suggestions error:', error);
                hideNavSearchSuggestions();
            }
        };
        
        window.displayNavSuggestions = function(suggestions, query) {
            const suggestionsList = document.getElementById('suggestions-list-nav');
            const noSuggestions = document.getElementById('no-suggestions-nav');
            const dropdown = document.getElementById('search-suggestions-nav');
            
            hideNavSearchLoading();
            
            if (!suggestions || suggestions.length === 0) {
                suggestionsList.innerHTML = '';
                noSuggestions.classList.remove('hidden');
                dropdown.classList.remove('hidden');
                return;
            }
            
            noSuggestions.classList.add('hidden');
            
            suggestionsList.innerHTML = suggestions.map((game, index) => `
                <div class="suggestion-item cursor-pointer flex items-center gap-3 p-2 hover:bg-base-200 rounded" 
                     data-appid="${game.appid}" 
                     data-title="${game.name}"
                     onclick="selectNavSuggestion(this)">
                  <iconify-icon icon="tabler:device-gamepad-2" class="text-base-content/50 flex-shrink-0"></iconify-icon>
                  <span class="text-sm truncate">${highlightMatch(game.name, query)}</span>
                </div>
            `).join('');
            
            dropdown.classList.remove('hidden');
        };
        
        window.selectNavSuggestion = function(element) {
            const title = element.dataset.title;
            const input = document.getElementById('searchInputNav');
            
            input.value = title;
            hideNavSearchSuggestions();
            
            // Submit the form
            input.closest('form').submit();
        };
        
        window.showNavSearchLoading = function() {
            document.getElementById('search-loading-nav').classList.remove('hidden');
            document.getElementById('search-suggestions-nav').classList.remove('hidden');
        };
        
        window.hideNavSearchLoading = function() {
            document.getElementById('search-loading-nav').classList.add('hidden');
        };
        
        window.hideNavSearchSuggestions = function() {
            document.getElementById('search-suggestions-nav').classList.add('hidden');
        };
        
        // Close nav suggestions when clicking outside
        document.addEventListener('click', function(event) {
            const searchInput = document.getElementById('searchInputNav');
            const searchSuggestions = document.getElementById('search-suggestions-nav');
            
            if (searchInput && searchSuggestions && 
                !searchInput.contains(event.target) && 
                !searchSuggestions.contains(event.target)) {
                hideNavSearchSuggestions();
            }
        });
        
        // Focus handler for nav search
        const navSearchInput = document.getElementById('searchInputNav');
        if (navSearchInput) {
            navSearchInput.addEventListener('focus', function() {
                if (this.value.trim().length >= 2) {
                    const query = this.value.trim();
                    if (window.searchCache && window.searchCache.has(query)) {
                        displayNavSuggestions(window.searchCache.get(query), query);
                    }
                }
            });
        }
    });