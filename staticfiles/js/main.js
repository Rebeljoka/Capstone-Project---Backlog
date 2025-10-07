/* jshint esversion: 11, esnext: false */
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
        const updateLanguageOptions = function(selectedLang) {
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
        };
        
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


    // Navigation search functionality (same logic as infinite-scroll.js, adapted for nav bar)
    var navSearchTimeout;
    var navSearchCache = new Map();
    var navCurrentSuggestionIndex = -1;

    function handleNavSearchInput(input) {
        clearTimeout(navSearchTimeout);
        const query = input.value.trim();

        if (query.length < 2) {
            hideNavSearchSuggestions();
            return;
        }

        navSearchTimeout = setTimeout(() => {
            fetchNavSearchSuggestions(query);
        }, 300);
    }

    function fetchNavSearchSuggestions(query) {
        if (navSearchCache.has(query)) {
            displayNavSuggestions(navSearchCache.get(query), query);
            return;
        }
        showNavSearchLoading();
        fetch(`/games/api/search-suggestions/?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                navSearchCache.set(query, data.suggestions);
                displayNavSuggestions(data.suggestions, query);
            })
            .catch(() => {
                hideNavSearchSuggestions();
            });
    }

    function displayNavSuggestions(suggestions, query) {
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
        navCurrentSuggestionIndex = -1;
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
    }

    function selectNavSuggestion(element) {
        const title = element.dataset.title;
        const input = document.getElementById('searchInputNav');
        input.value = title;
        hideNavSearchSuggestions();
        input.closest('form').submit();
    }

    function showNavSearchLoading() {
        document.getElementById('search-loading-nav').classList.remove('hidden');
        document.getElementById('search-suggestions-nav').classList.remove('hidden');
    }

    function hideNavSearchLoading() {
        document.getElementById('search-loading-nav').classList.add('hidden');
    }

    function hideNavSearchSuggestions() {
        document.getElementById('search-suggestions-nav').classList.add('hidden');
    }

    document.addEventListener('click', function(event) {
        const searchInput = document.getElementById('searchInputNav');
        const searchSuggestions = document.getElementById('search-suggestions-nav');
        if (searchInput && searchSuggestions &&
            !searchInput.contains(event.target) &&
            !searchSuggestions.contains(event.target)) {
            hideNavSearchSuggestions();
        }
    });

    const navSearchInput = document.getElementById('searchInputNav');
    if (navSearchInput) {
        navSearchInput.addEventListener('input', function() {
            handleNavSearchInput(this);
        });
        navSearchInput.addEventListener('focus', function() {
            const query = this.value.trim();
            if (query.length >= 2 && navSearchCache.has(query)) {
                displayNavSuggestions(navSearchCache.get(query), query);
            }
        });
        navSearchInput.addEventListener('keydown', function(event) {
            const suggestions = document.querySelectorAll('#suggestions-list-nav .suggestion-item');
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                navCurrentSuggestionIndex = Math.min(navCurrentSuggestionIndex + 1, suggestions.length - 1);
                updateNavSuggestionHighlight(suggestions);
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                navCurrentSuggestionIndex = Math.max(navCurrentSuggestionIndex - 1, -1);
                updateNavSuggestionHighlight(suggestions);
            } else if (event.key === 'Enter') {
                if (navCurrentSuggestionIndex >= 0 && suggestions[navCurrentSuggestionIndex]) {
                    event.preventDefault();
                    selectNavSuggestion(suggestions[navCurrentSuggestionIndex]);
                }
            } else if (event.key === 'Escape') {
                hideNavSearchSuggestions();
                navSearchInput.blur();
            }
        });
    }

    function updateNavSuggestionHighlight(suggestions) {
        suggestions.forEach((item, index) => {
            if (index === navCurrentSuggestionIndex) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }