// Infinite Scroll Functionality for Game List
class GameListManager {
	constructor() {
		this.currentPage = 1;
		this.loading = false;
		this.hasMore = true;
		this.searchQuery = "";
		this.selectedGenres = [];
		this.selectedTags = [];
		this.selectedPlatform = "";

		// Only initialize if we're on the game list page
		if (this.isGameListPage()) {
			this.init();
		}
	}

	isGameListPage() {
		return window.location.pathname === "/games/" || window.location.pathname.includes("/games/");
	}

	init() {
		this.gameContainer = document.getElementById("game-container");
		this.loadingSpinner = this.createLoadingSpinner();
		this.loadMoreContainer = document.getElementById("load-more-container");
		this.loadMoreBtn = document.getElementById("load-more-btn");

		if (this.gameContainer) {
			// Get current search parameters from URL
			const urlParams = new URLSearchParams(window.location.search);
			this.searchQuery = urlParams.get("search") || "";
			this.selectedGenres = urlParams.getAll("genres") || [];
			this.selectedTags = urlParams.getAll("tags") || [];
			this.selectedPlatform = urlParams.get("platform") || "";

			// Backward compatibility with single-select filters
			if (this.selectedGenres.length === 0 && urlParams.get("genre")) {
				this.selectedGenres = [urlParams.get("genre")];
			}
			if (this.selectedTags.length === 0 && urlParams.get("tag")) {
				this.selectedTags = [urlParams.get("tag")];
			}

			this.setupInfiniteScroll();
			this.setupSearch();
			this.setupLoadMoreButton();

			// Check if we need to show load more button after a short delay
			setTimeout(() => this.checkScrollability(), 500);
		}
	}

	createLoadingSpinner() {
		const spinner = document.createElement("div");
		spinner.className = "loading-spinner hidden";
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
		window.addEventListener("scroll", () => {
			clearTimeout(scrollTimeout);
			scrollTimeout = setTimeout(() => {
				this.handleScroll();
			}, 100); // Throttle scroll events
		});
	}

	setupSearch() {
		// Debounced search functionality
		const searchInput = document.getElementById("searchInput");
		if (searchInput) {
			let searchTimeout;
			searchInput.addEventListener("input", (e) => {
				clearTimeout(searchTimeout);
				searchTimeout = setTimeout(() => {
					this.handleSearch(e.target.value);
				}, 300);
			});
		}
	}

	setupLoadMoreButton() {
		if (this.loadMoreBtn) {
			this.loadMoreBtn.addEventListener("click", () => {
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
			this.loadMoreContainer.style.display = "flex";
		} else if (this.loadMoreContainer) {
			// Hide load more button if page is scrollable or no more content
			this.loadMoreContainer.style.display = "none";
		}

		// Update button text and state
		if (this.loadMoreBtn) {
			if (!this.hasMore) {
				this.loadMoreBtn.textContent = "No More Games";
				this.loadMoreBtn.disabled = true;
				this.loadMoreBtn.classList.add("btn-disabled");
			} else {
				this.loadMoreBtn.innerHTML = `
                    <iconify-icon icon="tabler:chevron-down"></iconify-icon>
                    Load More Games
                `;
				this.loadMoreBtn.disabled = false;
				this.loadMoreBtn.classList.remove("btn-disabled");
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
			this.gameContainer.innerHTML = "";
		}

		// Load new search results
		this.loadMoreGames();
	}

	async loadMoreGames() {
		if (this.loading || !this.hasMore) return;

		this.loading = true;
		this.showLoadingSpinner();

		try {
			const params = new URLSearchParams();
			params.append("page", this.currentPage + 1);
			params.append("search", this.searchQuery);
			params.append("platform", this.selectedPlatform);

			// Add multi-select genres
			this.selectedGenres.forEach((genre) => {
				params.append("genres", genre);
			});

			// Add multi-select tags
			this.selectedTags.forEach((tag) => {
				params.append("tags", tag);
			});

			console.log(`Loading page ${this.currentPage + 1} with params:`, params.toString());

			const response = await fetch(`/games/api/load-more/?${params}`);
			const data = await response.json();

			if (response.ok) {
				console.log(`Loaded ${data.games.length} games, has_more: ${data.has_more}`);
				console.log("Game data received:", data.games); // Debug: see all game data
				this.appendGames(data.games);
				this.currentPage++;
				this.hasMore = data.has_more;

				// Update URL without page refresh
				this.updateURL();
			} else {
				console.error("Error loading games:", data.error);
				this.showError("Failed to load more games. Please try again.");
			}
		} catch (error) {
			console.error("Network error:", error);
			this.showError("Network error. Please check your connection.");
		} finally {
			this.loading = false;
			this.hideLoadingSpinner();

			// Check scrollability after loading new content
			setTimeout(() => this.checkScrollability(), 100);
		}
	}

	appendGames(games) {
		if (!this.gameContainer || !games.length) return;

		games.forEach((game) => {
			const gameCard = this.createGameCard(game);
			this.gameContainer.appendChild(gameCard);
		});

		// Ensure the grid container maintains its classes
		if (!this.gameContainer.classList.contains("games-grid")) {
			this.gameContainer.classList.add("games-grid", "grid", "gap-6");
		}

		// Animate new cards
		const newCards = this.gameContainer.querySelectorAll(".game-card:not(.animated)");
		newCards.forEach((card, index) => {
			card.classList.add("animated");
			setTimeout(() => {
				card.style.opacity = "1";
				card.style.transform = "translateY(0)";
			}, index * 50); // Stagger animation
		});
	}

	createGameCard(game) {
		const card = document.createElement("div");
		card.className = "game-card bg-base-100 shadow-lg rounded-lg overflow-hidden hover:shadow-xl transition-all duration-300 group opacity-0 transform translate-y-4";
		card.style.transition = "opacity 0.3s ease, transform 0.3s ease";

		const platforms = game.platforms || {};
		console.log("Game platforms for", game.title, ":", platforms); // Debug log

		// Build platform icons
		let platformIconsHTML = "";
		if (platforms.windows) {
			console.log("Adding Windows platform for", game.title);
			platformIconsHTML += `
                <span class="badge badge-neutral badge-sm" title="Windows">
                    <iconify-icon icon="simple-icons:windows"></iconify-icon>
                </span>
            `;
		}
		if (platforms.mac) {
			console.log("Adding Mac platform for", game.title);
			platformIconsHTML += `
                <span class="badge badge-neutral badge-sm" title="Mac">
                    <iconify-icon icon="simple-icons:apple"></iconify-icon>
                </span>
            `;
		}
		if (platforms.linux) {
			console.log("Adding Linux platform for", game.title);
			platformIconsHTML += `
                <span class="badge badge-neutral badge-sm" title="Linux">
                    <iconify-icon icon="simple-icons:linux"></iconify-icon>
                </span>
            `;
		}

		// Build genres
		const genres = game.genres || [];
		let genresHTML = "";
		if (genres.length > 0) {
			genresHTML = genres
				.slice(0, 2)
				.map((genre) => {
					const genreName = genre.description || genre.name || genre;
					return `<span class="badge badge-outline badge-sm">${genreName}</span>`;
				})
				.join("\n              ");
		} else {
			genresHTML = '<span class="badge badge-ghost badge-sm">Unknown Genre</span>';
		}

		// Build image section
		const imageHTML = game.image
			? `<img src="${game.image}" 
                 alt="${game.title}" 
                 class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                 loading="lazy">`
			: `<div class="w-full h-full flex items-center justify-center text-base-content/50">
                <iconify-icon icon="tabler:device-gamepad-2" class="text-4xl"></iconify-icon>
            </div>`;

		// Build wishlist button if user is authenticated
		const wishlistButtonHTML = window.userAuthenticated
			? `<a href="/games/add-to-wishlist/${game.appid}/" 
			   class="btn btn-outline btn-secondary btn-sm"
			   onclick="event.stopPropagation();">
				<iconify-icon icon="tabler:heart"></iconify-icon>
			</a>`
			: "";

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
			this.loadingSpinner.classList.remove("hidden");
		}
	}

	hideLoadingSpinner() {
		if (this.loadingSpinner) {
			this.loadingSpinner.classList.add("hidden");
		}
	}

	showError(message) {
		// Create error toast
		const errorToast = document.createElement("div");
		errorToast.className = "toast toast-top toast-center";
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
			params.set("search", this.searchQuery);
		} else {
			params.delete("search");
		}

		const newURL = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`;
		window.history.replaceState({}, "", newURL);
	}
}

// Initialize infinite scroll when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
	new GameListManager();
});

//  Search function
// Enhanced Search JavaScript
// Search functionality with debouncing and suggestions
let searchTimeout;
let searchCache = new Map();
let currentSuggestionIndex = -1;

function handleSearchInput(input) {
	clearTimeout(searchTimeout);
	const query = input.value.trim();

	// Clear suggestions if query is too short
	if (query.length < 2) {
		hideSearchSuggestions();
		return;
	}

	// Debounced search - wait 300ms after user stops typing
	searchTimeout = setTimeout(() => {
		fetchSearchSuggestions(query);
	}, 300);
}

function handleSearchKeydown(event) {
	const suggestions = document.querySelectorAll("#suggestions-list .suggestion-item");

	if (event.key === "ArrowDown") {
		event.preventDefault();
		currentSuggestionIndex = Math.min(currentSuggestionIndex + 1, suggestions.length - 1);
		updateSuggestionHighlight(suggestions);
	} else if (event.key === "ArrowUp") {
		event.preventDefault();
		currentSuggestionIndex = Math.max(currentSuggestionIndex - 1, -1);
		updateSuggestionHighlight(suggestions);
	} else if (event.key === "Enter") {
		if (currentSuggestionIndex >= 0 && suggestions[currentSuggestionIndex]) {
			event.preventDefault();
			selectSuggestion(suggestions[currentSuggestionIndex]);
		}
		// Otherwise let form submit normally
	} else if (event.key === "Escape") {
		hideSearchSuggestions();
		document.getElementById("searchInput").blur();
	}
}

function updateSuggestionHighlight(suggestions) {
	suggestions.forEach((item, index) => {
		if (index === currentSuggestionIndex) {
			item.classList.add("active");
		} else {
			item.classList.remove("active");
		}
	});
}

async function fetchSearchSuggestions(query) {
	// Check cache first
	if (searchCache.has(query)) {
		displaySuggestions(searchCache.get(query), query);
		return;
	}

	// Show loading state
	showSearchLoading();

	try {
		const response = await fetch(`/games/api/search-suggestions/?q=${encodeURIComponent(query)}`);
		const data = await response.json();

		if (response.ok) {
			// Cache the results
			searchCache.set(query, data.suggestions);
			displaySuggestions(data.suggestions, query);
		} else {
			hideSearchSuggestions();
		}
	} catch (error) {
		console.error("Search suggestions error:", error);
		hideSearchSuggestions();
	}
}

function displaySuggestions(suggestions, query) {
	const suggestionsList = document.getElementById("suggestions-list");
	const noSuggestions = document.getElementById("no-suggestions");
	const dropdown = document.getElementById("search-suggestions");

	hideSearchLoading();

	if (!suggestions || suggestions.length === 0) {
		suggestionsList.innerHTML = "";
		noSuggestions.classList.remove("hidden");
		dropdown.classList.remove("hidden");
		return;
	}

	noSuggestions.classList.add("hidden");
	currentSuggestionIndex = -1;

	// Create clean suggestion items with highlighted text
	suggestionsList.innerHTML = suggestions
		.map(
			(game, index) => `
    <div class="suggestion-item cursor-pointer flex items-center gap-3" 
         data-appid="${game.appid}" 
         data-title="${game.name}"
         onclick="selectSuggestion(this)">
      <iconify-icon icon="tabler:device-gamepad-2" class="text-base-content/50 flex-shrink-0"></iconify-icon>
      <span class="text-sm truncate">${highlightMatch(game.name, query)}</span>
    </div>
  `
		)
		.join("");

	dropdown.classList.remove("hidden");
}

function highlightMatch(text, query) {
	const regex = new RegExp(`(${escapeRegex(query)})`, "gi");
	return text.replace(regex, '<mark class="bg-primary/20 text-primary font-medium">$1</mark>');
}

function escapeRegex(string) {
	return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function selectSuggestion(element) {
	const title = element.dataset.title;
	const input = document.getElementById("searchInput");

	input.value = title;
	hideSearchSuggestions();

	// Submit the form that contains the search input (robust against multiple forms on page)
	try {
		let formToSubmit = null;
		if (input) {
			formToSubmit = input.closest('form');
		}
		if (!formToSubmit) {
			formToSubmit = document.querySelector('form');
		}
		if (formToSubmit) {
			formToSubmit.submit();
		} else {
			console.warn('selectSuggestion: no form found to submit');
		}
	} catch (e) {
		console.error('selectSuggestion submit failed', e);
	}
}

function showSearchLoading() {
	try {
		const loader = document.getElementById("search-loading");
		const suggestions = document.getElementById("search-suggestions");
		if (loader) loader.classList.remove("hidden");
		if (suggestions) suggestions.classList.remove("hidden");
	} catch (e) {
		// Defensive: ignore if DOM not ready or elements missing
		console.debug('showSearchLoading: element missing', e);
	}
}

function hideSearchLoading() {
	try {
		const loader = document.getElementById("search-loading");
		if (loader) loader.classList.add("hidden");
	} catch (e) {
		console.debug('hideSearchLoading: element missing', e);
	}
}

function hideSearchSuggestions() {
	document.getElementById("search-suggestions").classList.add("hidden");
	currentSuggestionIndex = -1;
}

// Close suggestions when clicking outside
document.addEventListener("click", function (event) {
	const searchInput = document.getElementById("searchInput");
	const searchSuggestions = document.getElementById("search-suggestions");

	if (!searchInput.contains(event.target) && !searchSuggestions.contains(event.target)) {
		hideSearchSuggestions();
	}
});

// Show suggestions when input is focused and has content
document.getElementById("searchInput").addEventListener("focus", function () {
	if (this.value.trim().length >= 2) {
		const query = this.value.trim();
		if (searchCache.has(query)) {
			displaySuggestions(searchCache.get(query), query);
		}
	}
});

// Clear search cache periodically (every 5 minutes)
setInterval(() => {
	searchCache.clear();
}, 300000);

// Multi-Select Filter JavaScript
// Genre filter functions
function toggleAllGenres(checkbox) {
	const genreCheckboxes = document.querySelectorAll(".genre-checkbox");
	genreCheckboxes.forEach((cb) => (cb.checked = checkbox.checked));
	updateGenreSelection();
}

function updateGenreSelection() {
	const allCheckbox = document.getElementById("genre-all");
	const genreCheckboxes = document.querySelectorAll(".genre-checkbox");
	const checkedGenres = document.querySelectorAll(".genre-checkbox:checked");
	const display = document.getElementById("genre-display");

	// Update "All" checkbox state
	allCheckbox.checked = checkedGenres.length === genreCheckboxes.length;
	allCheckbox.indeterminate = checkedGenres.length > 0 && checkedGenres.length < genreCheckboxes.length;

	// Update display text
	if (checkedGenres.length === 0 || allCheckbox.checked) {
		display.textContent = "All Genres";
	} else {
		display.textContent = `${checkedGenres.length} genre${checkedGenres.length === 1 ? "" : "s"} selected`;
	}
}

// Tag filter functions
function toggleAllTags(checkbox) {
	const tagCheckboxes = document.querySelectorAll(".tag-checkbox");
	tagCheckboxes.forEach((cb) => (cb.checked = checkbox.checked));
	updateTagSelection();
}

function updateTagSelection() {
	const allCheckbox = document.getElementById("tag-all");
	const tagCheckboxes = document.querySelectorAll(".tag-checkbox");
	const checkedTags = document.querySelectorAll(".tag-checkbox:checked");
	const display = document.getElementById("tag-display");

	// Update "All" checkbox state
	allCheckbox.checked = checkedTags.length === tagCheckboxes.length;
	allCheckbox.indeterminate = checkedTags.length > 0 && checkedTags.length < tagCheckboxes.length;

	// Update display text
	if (checkedTags.length === 0 || allCheckbox.checked) {
		display.textContent = "All Categories";
	} else {
		display.textContent = `${checkedTags.length} categor${checkedTags.length === 1 ? "y" : "ies"} selected`;
	}
}

// Filter pill removal functions
function removeGenre(genreId) {
	const checkbox = document.querySelector(`input[name="genres"][value="${genreId}"]`);
	if (checkbox) {
		checkbox.checked = false;
		updateGenreSelection();
		document.querySelector("form").submit();
	}
}

function removeTag(tagId) {
	const checkbox = document.querySelector(`input[name="tags"][value="${tagId}"]`);
	if (checkbox) {
		checkbox.checked = false;
		updateTagSelection();
		document.querySelector("form").submit();
	}
}

function clearSearch() {
	document.querySelector('input[name="search"]').value = "";
	document.querySelector("form").submit();
}

function clearPlatform() {
	document.querySelector('select[name="platform"]').value = "";
	document.querySelector("form").submit();
}

function clearAllFilters() {
	// Clear search
	document.querySelector('input[name="search"]').value = "";

	// Clear platform
	document.querySelector('select[name="platform"]').value = "";

	// Clear all genre checkboxes
	document.querySelectorAll(".genre-checkbox").forEach((cb) => (cb.checked = false));
	document.getElementById("genre-all").checked = true;
	updateGenreSelection();

	// Clear all tag checkboxes
	document.querySelectorAll(".tag-checkbox").forEach((cb) => (cb.checked = false));
	document.getElementById("tag-all").checked = true;
	updateTagSelection();

	// Submit form
	document.querySelector("form").submit();
}

// Show loading spinner during filter operations
document.querySelector("form").addEventListener("submit", function () {
	const loadingSpinner = document.getElementById("filter-loading");
	if (loadingSpinner) {
		loadingSpinner.classList.remove("hidden");
	}
});

// Initialize filter states on page load
document.addEventListener("DOMContentLoaded", function () {
	updateGenreSelection();
	updateTagSelection();
});
