// Infinite Scroll Functionality for Game List
class GameListManager {
    constructor() {
        this.currentPage = 1;
        this.loading = false;
        this.hasMore = true;
        this.searchQuery = '';
        this.selectedGenre = '';
        this.selectedTag = '';
        
        // Only initialize if we're on the game list page
        if (this.isGameListPage()) {
            this.init();
        }
    }
    
    isGameListPage() {
        return window.location.pathname === '/games/' || window.location.pathname.includes('/games/');
    }
    
    init() {
        this.gameContainer = document.getElementById('game-container');
        this.loadingSpinner = this.createLoadingSpinner();
        this.loadMoreContainer = document.getElementById('load-more-container');
        this.loadMoreBtn = document.getElementById('load-more-btn');
        
        if (this.gameContainer) {
            // Get current search parameters from URL
            const urlParams = new URLSearchParams(window.location.search);
            this.searchQuery = urlParams.get('search') || '';
            this.selectedGenre = urlParams.get('genre') || '';
            this.selectedTag = urlParams.get('tag') || '';
            
            this.setupInfiniteScroll();
            this.setupSearch();
            this.setupLoadMoreButton();
            
            // Check if we need to show load more button after a short delay
            setTimeout(() => this.checkScrollability(), 500);
        }
    }
    
    createLoadingSpinner() {
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner hidden';
        spinner.innerHTML = `
            <div class="flex justify-center items-center py-8">
                <div class="flex flex-col items-center gap-4">
                    <div class="loading loading-spinner loading-lg"></div>
                    <p class="text-base-content/70">Loading more games...</p>
                </div>
            </div>
        `;
        return spinner;
    }
    
    setupInfiniteScroll() {
        // Add loading spinner to the page
        if (this.gameContainer) {
            this.gameContainer.parentNode.appendChild(this.loadingSpinner);
        }
        
        // Set up scroll event listener
        let scrollTimeout;
        window.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                this.handleScroll();
            }, 100); // Throttle scroll events
        });
    }
    
    setupSearch() {
        // Debounced search functionality
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.handleSearch(e.target.value);
                }, 300);
            });
        }
    }
    
    setupLoadMoreButton() {
        if (this.loadMoreBtn) {
            this.loadMoreBtn.addEventListener('click', () => {
                this.loadMoreGames();
            });
        }
    }
    
    checkScrollability() {
        // Check if the page is scrollable
        const documentHeight = document.body.offsetHeight;
        const viewportHeight = window.innerHeight;
        const isScrollable = documentHeight > viewportHeight + 50;
        
        if (!isScrollable && this.hasMore && this.loadMoreContainer) {
            // Show load more button if page isn't scrollable but has more content
            this.loadMoreContainer.style.display = 'flex';
        } else if (this.loadMoreContainer) {
            // Hide load more button if page is scrollable or no more content
            this.loadMoreContainer.style.display = 'none';
        }
        
        // Update button text and state
        if (this.loadMoreBtn) {
            if (!this.hasMore) {
                this.loadMoreBtn.textContent = 'No More Games';
                this.loadMoreBtn.disabled = true;
                this.loadMoreBtn.classList.add('btn-disabled');
            } else {
                this.loadMoreBtn.innerHTML = `
                    <iconify-icon icon="tabler:chevron-down"></iconify-icon>
                    Load More Games
                `;
                this.loadMoreBtn.disabled = false;
                this.loadMoreBtn.classList.remove('btn-disabled');
            }
        }
    }
    
    handleScroll() {
        if (this.loading || !this.hasMore) return;
        
        const scrollPosition = window.innerHeight + window.scrollY;
        const documentHeight = document.body.offsetHeight;
        
        // Use a smaller threshold for smaller screens or when document is short
        let threshold = Math.min(documentHeight - 500, documentHeight * 0.8);
        
        // If document is shorter than viewport, trigger immediately
        if (documentHeight <= window.innerHeight + 100) {
            threshold = documentHeight - 50;
        }
        
        if (scrollPosition >= threshold) {
            this.loadMoreGames();
        }
    }
    
    handleSearch(query) {
        // Reset pagination for new search
        this.currentPage = 1;
        this.hasMore = true;
        this.searchQuery = query;
        
        // Clear current games
        if (this.gameContainer) {
            this.gameContainer.innerHTML = '';
        }
        
        // Load new search results
        this.loadMoreGames();
    }
    
    async loadMoreGames() {
        if (this.loading || !this.hasMore) return;
        
        this.loading = true;
        this.showLoadingSpinner();
        
        try {
            const params = new URLSearchParams({
                page: this.currentPage + 1,
                search: this.searchQuery,
                genre: this.selectedGenre,
                tag: this.selectedTag
            });
            
            console.log(`Loading page ${this.currentPage + 1} with params:`, params.toString());
            
            const response = await fetch(`/games/api/load-more/?${params}`);
            const data = await response.json();
            
            if (response.ok) {
                console.log(`Loaded ${data.games.length} games, has_more: ${data.has_more}`);
                console.log('Game data received:', data.games); // Debug: see all game data
                this.appendGames(data.games);
                this.currentPage++;
                this.hasMore = data.has_more;
                
                // Update URL without page refresh
                this.updateURL();
            } else {
                console.error('Error loading games:', data.error);
                this.showError('Failed to load more games. Please try again.');
            }
        } catch (error) {
            console.error('Network error:', error);
            this.showError('Network error. Please check your connection.');
        } finally {
            this.loading = false;
            this.hideLoadingSpinner();
            
            // Check scrollability after loading new content
            setTimeout(() => this.checkScrollability(), 100);
        }
    }
    
    appendGames(games) {
        if (!this.gameContainer || !games.length) return;
        
        games.forEach(game => {
            const gameCard = this.createGameCard(game);
            this.gameContainer.appendChild(gameCard);
        });
        
        // Ensure the grid container maintains its classes
        if (!this.gameContainer.classList.contains('games-grid')) {
            this.gameContainer.classList.add('games-grid', 'grid', 'gap-6');
        }
        
        // Animate new cards
        const newCards = this.gameContainer.querySelectorAll('.game-card:not(.animated)');
        newCards.forEach((card, index) => {
            card.classList.add('animated');
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 50); // Stagger animation
        });
    }
    
    createGameCard(game) {
        const card = document.createElement('div');
        card.className = 'game-card bg-base-100 shadow-lg rounded-lg overflow-hidden hover:shadow-xl transition-all duration-300 group opacity-0 transform translate-y-4';
        card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        
        const platforms = game.platforms || {};
        console.log('Game platforms for', game.title, ':', platforms); // Debug log
        
        // Build platform icons
        let platformIconsHTML = '';
        if (platforms.windows) {
            console.log('Adding Windows platform for', game.title);
            platformIconsHTML += `
                <span class="badge badge-neutral badge-sm" title="Windows">
                    <iconify-icon icon="simple-icons:windows"></iconify-icon>
                </span>
            `;
        }
        if (platforms.mac) {
            console.log('Adding Mac platform for', game.title);
            platformIconsHTML += `
                <span class="badge badge-neutral badge-sm" title="Mac">
                    <iconify-icon icon="simple-icons:apple"></iconify-icon>
                </span>
            `;
        }
        if (platforms.linux) {
            console.log('Adding Linux platform for', game.title);
            platformIconsHTML += `
                <span class="badge badge-neutral badge-sm" title="Linux">
                    <iconify-icon icon="simple-icons:linux"></iconify-icon>
                </span>
            `;
        }
        
        // Build genres
        const genres = game.genres || [];
        let genresHTML = '';
        if (genres.length > 0) {
            genresHTML = genres.slice(0, 2).map(genre => {
                const genreName = genre.description || genre.name || genre;
                return `<span class="badge badge-outline badge-sm">${genreName}</span>`;
            }).join('\n              ');
        } else {
            genresHTML = '<span class="badge badge-ghost badge-sm">Unknown Genre</span>';
        }
        
        // Build image section
        const imageHTML = game.image ? 
            `<img src="${game.image}" 
                 alt="${game.title}" 
                 class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                 loading="lazy">` :
            `<div class="w-full h-full flex items-center justify-center text-base-content/50">
                <iconify-icon icon="tabler:device-gamepad-2" class="text-4xl"></iconify-icon>
            </div>`;
        
        // Build wishlist button if user is authenticated
        const wishlistButtonHTML = window.userAuthenticated ? 
            `<a href="/games/add-to-wishlist/${game.appid}/" 
               class="btn btn-outline btn-sm"
               onclick="event.stopPropagation();">
                <iconify-icon icon="tabler:heart"></iconify-icon>
            </a>` : '';
        
        card.innerHTML = `
            <a href="/games/${game.appid}/" class="block">
                <!-- Game Image -->
                <div class="aspect-video bg-base-200 relative overflow-hidden">
                    ${imageHTML}
                    
                    <!-- Platform Icons Overlay -->
                    <div class="absolute top-2 right-2 flex gap-1">
                        ${platformIconsHTML}
                    </div>
                </div>
                
                <!-- Game Info -->
                <div class="p-4">
                    <h3 class="font-semibold text-lg mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                        ${game.title}
                    </h3>
                    
                    <!-- Genres -->
                    <div class="flex gap-1 flex-wrap mb-3">
                        ${genresHTML}
                    </div>
                    
                    <!-- Action buttons -->
                    <div class="flex gap-2 mt-4">
                        <div class="btn btn-primary btn-sm flex-1">
                            <iconify-icon icon="tabler:eye"></iconify-icon>
                            View Details
                        </div>
                        ${wishlistButtonHTML}
                    </div>
                </div>
            </a>
        `;
        
        return card;
    }
    
    showLoadingSpinner() {
        if (this.loadingSpinner) {
            this.loadingSpinner.classList.remove('hidden');
        }
    }
    
    hideLoadingSpinner() {
        if (this.loadingSpinner) {
            this.loadingSpinner.classList.add('hidden');
        }
    }
    
    showError(message) {
        // Create error toast
        const errorToast = document.createElement('div');
        errorToast.className = 'toast toast-top toast-center';
        errorToast.innerHTML = `
            <div class="alert alert-error">
                <span class="icon-[tabler--exclamation-circle]"></span>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(errorToast);
        
        // Remove after 5 seconds
        setTimeout(() => {
            if (errorToast.parentNode) {
                errorToast.parentNode.removeChild(errorToast);
            }
        }, 5000);
    }
    
    updateURL() {
        const params = new URLSearchParams(window.location.search);
        if (this.searchQuery) {
            params.set('search', this.searchQuery);
        } else {
            params.delete('search');
        }
        
        const newURL = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
        window.history.replaceState({}, '', newURL);
    }
}

// Initialize infinite scroll when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    new GameListManager();
});