// Utility: Debounce and Throttle
function debounce(fn, delay) {
	let timer;
	return function(...args) {
		clearTimeout(timer);
		timer = setTimeout(() => fn.apply(this, args), delay);
	};
}

function throttle(fn, limit) {
	let lastCall = 0;
	return function(...args) {
		const now = Date.now();
		if (now - lastCall >= limit) {
			lastCall = now;
			fn.apply(this, args);
		}
	};
}
// Infinite Scroll Functionality for Game List
var GameListManager = class GameListManager {
	constructor() {
		this.currentPage = 1;
		this.loading = false;
		this.hasMore = true;
		this.searchQuery = "";
		this.selectedGenres = [];
		this.selectedTags = [];
		this.selectedPlatform = "";

		// Cache elements once in the constructor
		this.gameContainer = document.getElementById("game-container");
		this.loadMoreContainer = document.getElementById("load-more-container");
		this.loadMoreBtn = document.getElementById("load-more-btn");

		// Only initialize if we're on the game list page
		if (this.isGameListPage()) {
			this.init();
		}
	}

	isGameListPage() {
		return window.location.pathname === "/games/" || window.location.pathname.includes("/games/");
	}

	init() {
		this.loadingSpinner = this.createLoadingSpinner();

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
		spinner.className = "spinner-wrapper hidden"; // renamed to avoid conflict
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
		// Remove any existing spinner before adding a new one
		if (this.gameContainer && this.gameContainer.parentNode) {
			const existingSpinner = this.gameContainer.parentNode.querySelector('.spinner-wrapper');
			if (existingSpinner) {
				existingSpinner.remove();
			}
			this.gameContainer.parentNode.appendChild(this.loadingSpinner);
		}

		// Set up scroll event listener using throttle utility
		window.addEventListener(
			"scroll",
			throttle(() => {
				this.handleScroll();
			}, 100),
			{ passive: true }
		);
	}

	setupSearch() {
		// Debounced search functionality using debounce utility
		const searchInput = document.getElementById("searchInput");
		if (searchInput) {
			searchInput.addEventListener(
				"input",
				debounce((e) => {
					this.handleSearch(e.target.value);
				}, 300)
			);
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

			const response = await fetch(`/games/api/load-more/?${params}`);
			const data = await response.json();

			if (response.ok) {
				this.appendGames(data.games);
				this.currentPage++;
				this.hasMore = data.has_more;

				// Update URL without page refresh
				this.updateURL();
			} else {
				this.showError("Failed to load more games. Please try again.");
			}
		} catch (error) {
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

		// Build platform icons
		let platformIconsHTML = "";
		if (platforms.windows) {
			platformIconsHTML += `
                <span class="badge badge-neutral badge-sm" title="Windows">
                    <iconify-icon icon="simple-icons:windows"></iconify-icon>
                </span>
            `;
		}
		if (platforms.mac) {
			platformIconsHTML += `
                <span class="badge badge-neutral badge-sm" title="Mac">
                    <iconify-icon icon="simple-icons:apple"></iconify-icon>
                </span>
            `;
		}
		if (platforms.linux) {
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
					// Apply gradient + hover/focus ring classes per request
					return `<span class="badge badge-sm bg-gradient-to-r from-purple-500 to-pink-500 text-white">${genreName}</span>`;
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
		// resolve a canonical appid preferring DB (game.game_id) first
		const appid = game.game_id || game.appid || game.id;

		// Add data attributes so modal can read title/short reliably
		const dataAttrs = `data-title="${escapeHtmlAttr(game.title || '')}" data-short="${escapeHtmlAttr((game.short_description || '').split(/\s+/).slice(0,20).join(' '))}"`;
		const wishlistButtonHTML = window.userAuthenticated
			? `<a href="/wishlist/add-steam-game/${appid}/?title=${encodeURIComponent(game.title || '')}" 
				class="btn btn-outline btn-secondary btn-sm"
				onclick="event.stopPropagation();" ${dataAttrs}>
				<iconify-icon icon="tabler:heart"></iconify-icon>
			</a>`
			: "";

		card.innerHTML = `
			<a href="/games/${appid}/" class="block" data-title="${escapeHtmlAttr(game.title || '')}" data-short="${escapeHtmlAttr((game.short_description || '').split(/\s+/).slice(0,20).join(' '))}">
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

	function escapeHtmlAttr(s) { return String(s).replace(/"/g, '&quot;').replace(/&/g, '&amp;'); }

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
		// Use centralized message UI
		try { showMessage('error', message); } catch (e) { console.error('showError fallback', e); }
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
};

// Initialize infinite scroll when DOM is ready
// Single DOMContentLoaded listener for all initialization
if (!window.__GameListManagerInitialized) {
    window.__GameListManagerInitialized = true;
    document.addEventListener("DOMContentLoaded", function () {
        new GameListManager();
        updateGenreSelection();
        updateTagSelection();
    });
}

//  Search function
// Enhanced Search JavaScript
// Search functionality with debouncing and suggestions
var searchTimeout;
var searchCache = new Map();
var currentSuggestionIndex = -1;

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
	}, true);
}

function displaySuggestions(suggestions, query) {
    // Find the active input and its related suggestion elements
    let activeInput = document.activeElement;
    let suggestionsList = null;
    let noSuggestions = null;
    let dropdown = null;

    if (activeInput && activeInput.classList.contains('searchInput')) {
        // Use data attributes or DOM traversal to find related elements
        const parent = activeInput.closest('.search-bar, .relative, form') || document;
        suggestionsList = parent.querySelector('.suggestions-list') || document.getElementById('suggestions-list');
        noSuggestions = parent.querySelector('.no-suggestions') || document.getElementById('no-suggestions');
        dropdown = parent.querySelector('.search-suggestions') || document.getElementById('search-suggestions');
    } else {
        // Fallback to global elements
        suggestionsList = document.getElementById('suggestions-list');
        noSuggestions = document.getElementById('no-suggestions');
        dropdown = document.getElementById('search-suggestions');
    }

    hideSearchLoading();

    if (!suggestions || suggestions.length === 0) {
        if (suggestionsList) suggestionsList.innerHTML = "";
        if (noSuggestions) noSuggestions.classList.remove("hidden");
        if (dropdown) dropdown.classList.remove("hidden");
        return;
    }

    if (noSuggestions) noSuggestions.classList.add("hidden");
    currentSuggestionIndex = -1;

    // Create clean suggestion items with highlighted text
	if (suggestionsList) {
		suggestionsList.innerHTML = suggestions
			.map(
				(game, index) => {
					const sugAppid = game.game_id || game.appid || game.id;
					return `
		<div class="suggestion-item cursor-pointer flex items-center gap-3" 
			 data-appid="${sugAppid}" 
			 data-title="${game.name}"
			 onclick="selectSuggestion(this)">
		  <iconify-icon icon="tabler:device-gamepad-2" class="text-base-content/50 flex-shrink-0"></iconify-icon>
		  <span class="text-sm truncate">${highlightMatch(game.name, query)}</span>
		</div>
	  `
				}
			)
			.join("");
	}
    if (dropdown) dropdown.classList.remove("hidden");
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
			formToSubmit = input.closest("form");
		}
		if (!formToSubmit) {
			formToSubmit = document.querySelector("form");
		}
		if (formToSubmit) {
			formToSubmit.submit();
		} else {
		}
	} catch (e) {
	}
}

function showSearchLoading() {
	const loader = document.getElementById("search-loading");
	const suggestions = document.getElementById("search-suggestions");
	if (loader) loader.classList.remove("hidden");
	if (suggestions) suggestions.classList.remove("hidden");
}

function hideSearchLoading() {
	const loader = document.getElementById("search-loading");
	if (loader) loader.classList.add("hidden");
}

// Close suggestions when clicking outside any search input or dropdown
document.addEventListener("click", function (event) {
	let clickedInside = false;
	document.querySelectorAll('.searchInput, .search-suggestions').forEach(function(el) {
		if (el.contains(event.target)) {
			clickedInside = true;
		}
	});
	if (!clickedInside) {
		hideSearchSuggestions();
	}
});


// Event delegation for .searchInput focus
document.body.addEventListener('focusin', function(e) {
	if (e.target.classList.contains('searchInput')) {
		const query = e.target.value.trim();
		if (query.length >= 2 && searchCache.has(query)) {
			displaySuggestions(searchCache.get(query), query);
		}
	}
});

// Optimized search cache clearing: only clear if cache is large
setInterval(() => {
	if (searchCache.size > 100) searchCache.clear();
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
	let checkedCount = 0;
	genreCheckboxes.forEach(cb => { if (cb.checked) checkedCount++; });
	const display = document.getElementById("genre-display");
	// Update "All" checkbox state
	if (allCheckbox) {
		allCheckbox.checked = checkedCount === genreCheckboxes.length;
		allCheckbox.indeterminate = checkedCount > 0 && checkedCount < genreCheckboxes.length;
	}
	// Update display text
	if (display) {
		display.textContent = (checkedCount === 0 || (allCheckbox && allCheckbox.checked))
			? "All Genres"
			: `${checkedCount} genre${checkedCount === 1 ? "" : "s"} selected`;
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
	let checkedCount = 0;
	tagCheckboxes.forEach(cb => { if (cb.checked) checkedCount++; });
	const display = document.getElementById("tag-display");
	// Update "All" checkbox state
	if (allCheckbox) {
		allCheckbox.checked = checkedCount === tagCheckboxes.length;
		allCheckbox.indeterminate = checkedCount > 0 && checkedCount < tagCheckboxes.length;
	}
	// Update display text
	if (display) {
		display.textContent = (checkedCount === 0 || (allCheckbox && allCheckbox.checked))
			? "All Categories"
			: `${checkedCount} categor${checkedCount === 1 ? "y" : "ies"} selected`;
	}
}

// Filter pill removal functions
function removeGenre(genreId) {
	// Get current query params
	const params = new URLSearchParams(window.location.search);
	// Get all current genres
	const genres = params.getAll("genres");
	// Remove only the clicked genre
	const updatedGenres = genres.filter((g) => g !== genreId);
	// Remove all genres from params
	params.delete("genres");
	// Add back the remaining genres
	updatedGenres.forEach((g) => params.append("genres", g));
	// Redirect to updated URL
	window.location.href = window.location.pathname + "?" + params.toString();
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

function clearAllFilters() {
	// Clear search
	const searchInput = document.querySelector('input[name="search"]');
	if (searchInput) searchInput.value = "";


	// Clear all genre checkboxes
	document.querySelectorAll('input[name="genres"]').forEach((cb) => (cb.checked = false));
	// If you have an "All Genres" checkbox, check it
	const allGenreCheckbox = document.getElementById("genre-all");
	if (allGenreCheckbox) allGenreCheckbox.checked = true;
	if (typeof updateGenreSelection === "function") updateGenreSelection();

	// Clear all tag checkboxes
	document.querySelectorAll('input[name="tags"]').forEach((cb) => (cb.checked = false));
	// If you have an "All Tags" checkbox, check it
	const allTagCheckbox = document.getElementById("tag-all");
	if (allTagCheckbox) allTagCheckbox.checked = true;
	if (typeof updateTagSelection === "function") updateTagSelection();

	// Submit the filter form
	const filterForm = document.querySelector("form");
	if (filterForm) filterForm.submit();
}

// Show loading spinner during filter operations
document.querySelector("form").addEventListener("submit", function () {
	const loadingSpinner = document.getElementById("filter-loading");
	if (loadingSpinner) {
		loadingSpinner.classList.remove("hidden");
	}
});

// Initialize filter states on page load
function showSearchSuggestions() {
	requestAnimationFrame(() => {
		const dropdowns = document.querySelectorAll('.search-suggestions');
		const containers = document.querySelectorAll('.game-container');
		dropdowns.forEach(dropdown => dropdown.classList.remove('hidden'));
		containers.forEach(container => container.style.visibility = 'hidden');
	});
}

function hideSearchSuggestions() {
	requestAnimationFrame(() => {
		const dropdowns = document.querySelectorAll('.search-suggestions');
		const containers = document.querySelectorAll('.game-container');
		dropdowns.forEach(dropdown => dropdown.classList.add('hidden'));
		containers.forEach(container => container.style.visibility = 'visible');
		currentSuggestionIndex = -1;
	});
}

// Update fetchSearchSuggestions to call showSearchSuggestions
// Centralized search suggestion logic
async function fetchSearchSuggestions(query) {
	// Check cache first
	if (searchCache.has(query)) {
		displaySuggestions(searchCache.get(query), query);
		showSearchSuggestions();
		return;
	}

	// Show loading state
	showSearchLoading();
	showSearchSuggestions();

	try {
		const response = await fetch(`/games/api/search-suggestions/?q=${encodeURIComponent(query)}`);
		const data = await response.json();

		if (response.ok) {
			// Cache the results
			searchCache.set(query, data.suggestions);
			displaySuggestions(data.suggestions, query);
			showSearchSuggestions();
		} else {
			hideSearchSuggestions();
		}
	} catch (error) {
		hideSearchSuggestions();
	}
}


// -----------------------------
// AJAX add-to-wishlist handler (appended)
// -----------------------------

// Helper to read Django csrftoken cookie
function getCookie(name) {
	const value = `; ${document.cookie}`;
	const parts = value.split(`; ${name}=`);
	if (parts.length === 2) return parts.pop().split(';').shift();
}

const csrftoken = getCookie('csrftoken');

// Helper: show a message using the Django messages container markup in base.html
function showMessage(type, text) {
	try {
		let container = document.querySelector('.messages-container');
		if (!container) {
			// create one under the nav if missing
			const nav = document.querySelector('nav');
			container = document.createElement('div');
			container.className = 'container mx-auto px-4 mt-4 messages-container';
			if (nav && nav.parentNode) nav.parentNode.insertBefore(container, nav.nextSibling);
			else document.body.insertBefore(container, document.body.firstChild);
		}

		const alert = document.createElement('div');
		const typeClass = (type === 'error') ? 'alert-error' : (type === 'warning') ? 'alert-warning' : (type === 'success') ? 'alert-success' : 'alert-info';
		alert.className = `alert mb-4 ${typeClass}`;
		alert.setAttribute('role', 'status');
		function _esc(s) { return String(s).replace(/[&<>"']/g, function(m) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]); }); }

		alert.innerHTML = `
			<div class="flex items-center text-center">
				${type === 'error' ? '<span class="nf nf-oct-x mr-2"></span>' : type === 'warning' ? '<span class="nf nf-oct-alert mr-2"></span>' : type === 'success' ? '<span class="nf nf-oct-check_circle mr-2"></span>' : '<span class="nf nf-oct-info mr-2"></span>'}
				<span>${_esc(text)}</span>
			</div>
			<button type="button" class="btn-xs ml-auto" onclick="this.closest('.alert').style.display='none'">
				<span class="nf nf-oct-x"></span>
			</button>
		`;

		container.appendChild(alert);

		// auto-remove non-error messages after a short delay
		if (type !== 'error') setTimeout(() => { if (alert.parentNode) alert.parentNode.removeChild(alert); }, 4000);
	} catch (e) {
		console.error('showMessage error', e);
	}
}

// Delegated click handler for anchors that point to add-steam-game
// Use capture phase so we observe clicks even if inner elements call stopPropagation()
document.body.addEventListener('click', async (e) => {
	const anchor = e.target.closest('a[href*="/wishlist/add-steam-game/"]');
	if (!anchor) return;

	// Allow middle-click / cmd/ctrl + click for new tab
	if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;

	// Progressive enhancement: prevent default and perform AJAX POST
	e.preventDefault();
	e.stopPropagation();

	// Extract appid from href and optional title param, then open the modal immediately
	try {
		const url = new URL(anchor.href, window.location.origin);
		const title = url.searchParams.get('title') || '';
		const parts = url.pathname.split('/').filter(Boolean);
		const appid = parts[parts.length - 1];

		// Gather title/short description from data attributes or DOM as fallbacks
		const card = anchor.closest('.game-card');
		let domTitle = '';
		if (card) domTitle = (card.querySelector('h3')?.textContent || '').trim();
		if (!domTitle) domTitle = anchor.dataset?.title || anchor.getAttribute('title') || '';
		let shortDesc = '';
		if (card) {
			const sel = card.querySelector('.short-description, .game-short, .description, p');
			if (sel && (sel.textContent || '').trim()) shortDesc = sel.textContent.trim();
		}

		const finalTitle = title || domTitle || '';
		await openWishlistPickerAndAdd(url.pathname, finalTitle, shortDesc, anchor, csrftoken, appid);
		return;
	} catch (err) {
		// If anything goes wrong (network error, CSP blocking fetch, etc.),
		// fall back to the server full-page flow by navigating to the anchor href.
		try {
			window.location.href = anchor.href;
		} catch (navErr) {
			    showMessage('error', 'Network error. Try again.');
		}
	}
}, true);


// --- Wishlist picker modal helpers ---
async function fetchUserWishlists(game_id) {
	try {
		let url = '/wishlist/api/wishlists/';
		if (game_id) url += `?game_id=${encodeURIComponent(game_id)}`;
		const resp = await fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } });
		if (!resp.ok) return [];
		const data = await resp.json();
		return { wishlists: data.wishlists || [], game: data.game || null };
	} catch (e) {
		return { wishlists: [], game: null };
	}
}

function buildWishlistModal(wishlists, game) {
	const modal = document.createElement('div');
	// unique id so ARIA attributes can reference the title
	const modalId = 'wishlist-modal-' + Date.now();
	modal.setAttribute('id', modalId);
	modal.className = 'wishlist-modal fixed inset-0 flex items-center justify-center z-50';
	modal.style.background = 'rgba(0,0,0,0.4)';
	// Accessibility
	modal.setAttribute('role', 'dialog');
	modal.setAttribute('aria-modal', 'true');
	modal.setAttribute('aria-labelledby', modalId + '-title');

 	const box = document.createElement('div');
 	box.className = 'max-w-2xl mx-auto mt-8 p-6 bg-base-content rounded-lg shadow-md dark:bg-base-200 w-full';
 	box.setAttribute('tabindex', '-1');
 	box.innerHTML = `
 		<h1 id="${modalId}-title" class="text-2xl font-bold mb-4">Add to Wishlist</h1>

		<div class="mb-6 p-4 bg-base-content dark:bg-base-200 rounded">
			<h2 class="font-semibold text-lg">${escapeHtml(game.title || '')}</h2>
			${game.short_description ? `<p class="text-gray-600 mt-1">${escapeHtml(truncateWords(game.short_description, 20))}</p>` : ''}
		</div>

		<div class="mb-6">
			<label class="block text-sm font-medium mb-3"> Select Wishlist: </label>
			<div class="space-y-3 wishlist-list"></div>
		</div>

		<div class="flex gap-4">
			<button type="button" class="flex-1 bg-green-500 hover:bg-green-600 font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline dark:bg-green-700 dark:hover:bg-green-800 modal-add-btn" disabled>Add to Wishlist</button>
			<button type="button" class="flex-1 text-center bg-red-500 hover:bg-red-600 font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline dark:bg-red-700 dark:hover:bg-red-800 modal-cancel">Cancel</button>
		</div>

		<div class="mt-6 text-center dark:text-blue-300">
			<a href="/wishlist/create/" class="text-blue-600 hover:text-blue-800 underline"> Create New Wishlist </a>
		</div>
	`;

	// Helper insertion of wishlist rows
	const list = box.querySelector('.wishlist-list');
	wishlists.forEach(w => {
		const wrapper = document.createElement('div');
		if (w.has_game) {
			wrapper.className = 'border border-orange-200 dark:border-orange-400 bg-orange-50 dark:bg-orange-900 rounded-lg p-3 wishlist-row disabled';
			wrapper.setAttribute('tabindex', '-1');
			wrapper.innerHTML = `
				<div class="flex items-center justify-between">
					<label class="flex items-center text-gray-500 dark:text-gray-300 cursor-not-allowed">
						<input type="radio" name="wishlist_id" value="${w.pk}" disabled class="mr-3 text-gray-400" />
						<div>
							<span class="font-medium dark:text-white">${escapeHtml(w.name)}</span>
							<div class="text-sm text-gray-400">${w.items_count} game${w.items_count === 1 ? '' : 's'}</div>
						</div>
					</label>
					<span class="text-orange-600 text-sm font-medium flex items-center">
						<span class="icon-[tabler--check] mr-1"></span>
						Already added
					</span>
				</div>
			`;
		} else {
			wrapper.className = 'border border-gray-200 dark:border-blue-400 bg-white dark:bg-base-300 rounded-lg p-3 hover:border-blue-300 dark:hover:border-blue-400 transition-colors wishlist-row';
			wrapper.setAttribute('tabindex', '0');
			wrapper.innerHTML = `
				<label class="flex items-center cursor-pointer">
					<input type="radio" name="wishlist_id" value="${w.pk}" required class="mr-3 text-blue-500" />
					<div>
						<span class="font-medium">${escapeHtml(w.name)}</span>
						<div class="text-sm text-gray-500">${w.items_count} game${w.items_count === 1 ? '' : 's'}</div>
					</div>
				</label>
			`;
		}
		list.appendChild(wrapper);
	});

	// Utilities for truncation and escaping
	function truncateWords(str, n) { return str.split(/\s+/).slice(0, n).join(' '); }
	function escapeHtml(unsafe) { return String(unsafe).replace(/[&<>\"']/g, function(m) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]); }); }

	// Expose for focus management
	modal.appendChild(box);
	return modal;
}

async function openWishlistPickerAndAdd(pathname, title, short_description, anchor, csrftoken, game_id) {
	const res = await fetchUserWishlists(game_id);
	const wishlists = res.wishlists || [];
	// Prefer server-provided game metadata when available
	const serverGame = res.game || null;
	const modalGame = serverGame || { title: title || '', short_description: short_description || '' };
	const modal = buildWishlistModal(wishlists, modalGame);
	// Accessibility: hide the rest of the app from screen readers while modal is open
	const appRoot = document.querySelector('body > div') || document.body;
	if (appRoot && appRoot !== modal) appRoot.setAttribute('aria-hidden', 'true');
	document.body.appendChild(modal);

	// Focus management: trap focus inside modal
	const previouslyFocused = document.activeElement;
	const dialog = modal.querySelector('[tabindex="-1"]') || modal;
	setTimeout(() => dialog.focus(), 0);

	const focusableSelector = 'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';
	function getFocusableElements(container) {
		return Array.from(container.querySelectorAll(focusableSelector)).filter(el => el.offsetParent !== null);
	}

	function trapTabKey(e) {
		if (e.key !== 'Tab') return;
		const focusable = getFocusableElements(modal);
		if (focusable.length === 0) {
			e.preventDefault();
			return;
		}
		const first = focusable[0];
		const last = focusable[focusable.length - 1];
		if (!e.shiftKey && document.activeElement === last) {
			e.preventDefault();
			first.focus();
		} else if (e.shiftKey && document.activeElement === first) {
			e.preventDefault();
			last.focus();
		}
	}
	modal.addEventListener('keydown', trapTabKey);

	const addBtn = modal.querySelector('.modal-add-btn');
	const cancelBtn = modal.querySelector('.modal-cancel');
	const list = modal.querySelector('.wishlist-list');

	function close() { modal.remove(); }

	function closeAndRestore() {
		modal.removeEventListener('keydown', trapTabKey);
		if (appRoot && appRoot !== modal) appRoot.removeAttribute('aria-hidden');
		modal.remove();
		try { if (previouslyFocused && previouslyFocused.focus) previouslyFocused.focus(); } catch (e) {}
	}

	// Selection management: enable Add when a non-disabled radio is selected
	list.addEventListener('click', (ev) => {
		const wrapper = ev.target.closest('.wishlist-row');
		if (!wrapper || wrapper.classList.contains('disabled')) return;
		// mark the radio inside
		const radio = wrapper.querySelector('input[type="radio"]');
		if (radio) radio.checked = true;
		// enable add button
		addBtn.disabled = false;
		// store selected wishlist id on addBtn dataset
		addBtn.dataset.wishlistId = radio ? radio.value : '';
	});

	// Cancel behavior
	cancelBtn.addEventListener('click', () => close());

	// Add button behavior: POST with chosen wishlist_id
	addBtn.addEventListener('click', async () => {
		const wishlistId = addBtn.dataset.wishlistId;
		if (!wishlistId) return;
		const originalInner = anchor.innerHTML;
		anchor.innerHTML = '<iconify-icon icon="tabler:loader" class="animate-spin"></iconify-icon>';
		try {
			const resp = await fetch(pathname, {
				method: 'POST',
				credentials: 'same-origin',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': csrftoken,
					'X-Requested-With': 'XMLHttpRequest',
					'Accept': 'application/json'
				},
				body: JSON.stringify({ title: title, wishlist_id: wishlistId })
			});
			const data = await resp.json().catch(() => ({}));
			if (resp.ok && data.success) {
				anchor.classList.add('added');
				anchor.innerHTML = '<iconify-icon icon="tabler:heart-filled"></iconify-icon>';
				if (data.message) {
					showMessage('success', data.message);
				}
			} else {
				const msg = data.error || data.message || 'Failed to add to wishlist.';
				showMessage('error', msg);
				anchor.innerHTML = originalInner;
			}
		} catch (e) {
			anchor.innerHTML = originalInner;
		} finally {
			close();
		}
	});

	// Close on backdrop click
	modal.addEventListener('click', (ev) => {
		if (ev.target === modal) close();
	});

	// Keyboard: Enter triggers Add if enabled; Escape closes
	modal.addEventListener('keydown', (ev) => {
		if (ev.key === 'Escape') close();
		if ((ev.key === 'Enter' || ev.key === ' ') && !addBtn.disabled) addBtn.click();
	});

	// Keyboard accessibility: allow Enter/Space to select a row
	modal.addEventListener('keydown', (ev) => {
		if (ev.key === 'Enter' || ev.key === ' ') {
			const active = document.activeElement.closest && document.activeElement.closest('.wishlist-row');
			if (active && !active.classList.contains('disabled')) {
				active.click();
				ev.preventDefault();
			}
		} else if (ev.key === 'Escape') {
			close();
		}
	});
}