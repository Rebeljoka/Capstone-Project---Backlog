"""
Views for Steam game browsing, details, and wishlist management.
Handles fetching Steam data, filtering, and rendering templates.
"""
import requests
import concurrent.futures
from django.core.cache import cache
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Genre, Tag, Game, map_steam_to_game, set_game_genres_and_tags


def get_cached_game_minimal(appid):
    """Get minimal game data for list view - much faster"""
    cache_key = f'steam_game_minimal_{appid}'
    game_data = cache.get(cache_key)

    if game_data is None:
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
        try:
            response = requests.get(url, timeout=2)  # Even shorter timeout
            if response.status_code == 200:
                data = response.json()
                app_data = data.get(str(appid), {})
                if app_data.get('success'):
                    info = app_data['data']
                    genres = info.get('genres', [])
                    categories = info.get('categories', [])

                    # Only get what we need for the list view
                    game_data = {
                        'appid': info.get('steam_appid'),
                        'title': info.get('name', 'Unknown'),
                        'image': info.get('header_image'),  # Add image back
                        'platforms': info.get('platforms', {}),  # Windows, Mac, Linux
                        'genres': genres[:2] if genres else [],  # Only first 2 genres
                        'tags': categories[:2] if categories else [],  # Only first 2 tags
                    }
                    # Cache for 24 hours
                    cache.set(cache_key, game_data, 86400)
        except Exception:
            pass

    return game_data


def get_cached_game_details(appid):
    """Get full game details for detail view"""
    cache_key = f'steam_game_full_{appid}'
    game_data = cache.get(cache_key)

    if game_data is None:
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                app_data = data.get(str(appid), {})
                if app_data.get('success'):
                    info = app_data['data']
                    game_data = {
                        'appid': info.get('steam_appid'),
                        'title': info.get('name', 'Unknown'),
                        'developer': ', '.join(info.get('developers', [])),
                        'publisher': ', '.join(info.get('publishers', [])),
                        'release_date': info.get('release_date', {}).get('date', ''),
                        'image': info.get('header_image'),
                        'short_description': info.get('short_description', ''),
                        'detailed_description': info.get('detailed_description', ''),
                        'platforms': info.get('platforms', {}),
                        'genres': info.get('genres', []),
                        'tags': info.get('categories', []),
                        'price_overview': info.get('price_overview', {}),
                        'metacritic': info.get('metacritic', {}),
                        'recommendations': info.get('recommendations', {}),
                    }
                    # Cache for 24 hours
                    cache.set(cache_key, game_data, 86400)
        except Exception:
            pass

    return game_data


def fetch_multiple_game_minimal(appids):
    """Fetch multiple minimal game details concurrently"""
    game_details = []

    # Use ThreadPoolExecutor for concurrent API calls
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:  # More workers for lighter requests
        # Submit all tasks
        future_to_appid = {executor.submit(get_cached_game_minimal, appid): appid for appid in appids}

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_appid):
            try:
                game_data = future.result()
                if game_data:
                    game_details.append(game_data)
            except Exception:
                continue

    return game_details


def game_list(request):
    # Initialize error and results
    steam_error = None
    filtered_steam_games = []  # Initialize to prevent undefined variable errors
    page_obj = None  # Initialize pagination object

    # 1. Fetch the full Steam app list (appid and name only) from cache or API
    all_apps = cache.get('steam_all_apps')
    if all_apps is None:
        app_list_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
        try:
            app_list_resp = requests.get(app_list_url, timeout=10)
            app_list_data = app_list_resp.json()
            all_apps = app_list_data.get('applist', {}).get('apps', [])
            # Cache for 6 hours to avoid repeated API calls
            cache.set('steam_all_apps', all_apps, 21600)
        except Exception as e:
            steam_error = f"Error fetching Steam app list: {e}"
            all_apps = []

    # If no apps available, return empty results with error
    if not all_apps:
        # Create a minimal page object for template compatibility
        paginator = Paginator([], 20)
        page_obj = paginator.page(1)

        return render(
            request,
            'games/game_list.html',
            {
                'steam_games': [],
                'steam_error': steam_error or "No games available",
                'page_obj': page_obj,
                'query': request.GET.get('search', ''),
                'search_query': request.GET.get('search', ''),
                'genres': [],
                'tags': [],
                'selected_platform': '',
                'selected_genres': [],
                'selected_tags': [],
                'selected_genres_with_names': [],
                'selected_tags_with_names': [],
                'games': [],
            }
        )

    # 2. Get search, genre, tag, and platform filter parameters from request
    search_query = request.GET.get('search', '').strip()
    selected_platform = request.GET.get('platform', '')

    # Multi-select filters (genres and tags)
    selected_genres = request.GET.getlist('genres')  # Get list of selected genre IDs
    selected_tags = request.GET.getlist('tags')      # Get list of selected tag IDs

    # For backward compatibility with old single-select filters
    if not selected_genres and request.GET.get('genre'):
        selected_genres = [request.GET.get('genre')]
    if not selected_tags and request.GET.get('tag'):
        selected_tags = [request.GET.get('tag')]

    # Get all genres and tags from database for filter dropdowns (cache these too)
    genres_list = cache.get('steam_genres_list')
    if genres_list is None:
        genres_list = [(str(g.genre_id), g.genre) for g in Genre.objects.all()]
        cache.set('steam_genres_list', genres_list, 3600)  # Cache for 1 hour

    tags_list = cache.get('steam_tags_list')
    if tags_list is None:
        tags_list = sorted([(str(t.tag_id), t.name) for t in Tag.objects.all()], key=lambda x: x[1])
        cache.set('steam_tags_list', tags_list, 3600)  # Cache for 1 hour

    # 3. Filter apps based on search query only
    filtered_apps = all_apps
    if search_query:
        # Search through ALL games (not limited to 1000) for better results
        print(f"Searching through {len(all_apps)} games for '{search_query}'...")
        query_lower = search_query.lower()

        # First pass: exact matches and starts-with matches
        exact_matches = []
        starts_with_matches = []
        contains_matches = []

        for app in all_apps:
            name_lower = app['name'].lower()
            if name_lower == query_lower:
                exact_matches.append(app)
            elif name_lower.startswith(query_lower):
                starts_with_matches.append(app)
            elif query_lower in name_lower:
                contains_matches.append(app)

        # Combine results with priority: exact -> starts with -> contains
        filtered_apps = exact_matches + starts_with_matches + contains_matches

        # Limit to reasonable number for performance
        filtered_apps = filtered_apps[:2000]  # Increased from 500
        print(f"Found {len(filtered_apps)} matching games")
    else:
        # No search query, use a curated list of popular games
        filtered_apps = all_apps[:1000]  # Use first 1000 games

    # 4. If genre/tag filtering is requested, we need to check all games in the pool
    if selected_genres or selected_tags:
        # Fetch details for ALL games in the pool to apply genre/tag filtering
        print(f"Filtering by genre/tag across {len(filtered_apps)} games...")

        # Process in batches to avoid overwhelming the API
        batch_size = 100
        genre_tag_filtered_games = []

        for i in range(0, min(len(filtered_apps), 300), batch_size):  # Limit to first 300 for performance
            batch = filtered_apps[i:i + batch_size]
            batch_appids = [app['appid'] for app in batch]
            batch_details = fetch_multiple_game_minimal(batch_appids)

            # Apply genre/tag filtering to this batch
            for game_data in batch_details:
                if not game_data:
                    continue

                # Apply genre filter if selected (multi-select AND logic)
                if selected_genres:
                    genres = game_data.get('genres', [])
                    game_genre_ids = [str(genre.get('id')) for genre in genres]
                    # Check if ANY of the selected genres match (OR logic for multi-select)
                    if not any(genre_id in game_genre_ids for genre_id in selected_genres):
                        continue

                # Apply tag filter if selected (multi-select AND logic)
                if selected_tags:
                    tags = game_data.get('tags', [])
                    game_tag_ids = [str(tag.get('id')) for tag in tags]
                    # Check if ANY of the selected tags match (OR logic for multi-select)
                    if not any(tag_id in game_tag_ids for tag_id in selected_tags):
                        continue

                # Add appid back to the game data for pagination reference
                game_data['app_list_index'] = next((j for j, app in enumerate(filtered_apps) if app['appid'] == game_data['appid']), -1)
                genre_tag_filtered_games.append(game_data)

        # Now paginate the filtered results
        games_per_page = 20
        page_number = int(request.GET.get('page', 1))

        # Use Django paginator on the filtered games
        paginator = Paginator(genre_tag_filtered_games, games_per_page)

        try:
            page_obj = paginator.page(page_number)
            filtered_steam_games = list(page_obj)
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.page(1)
            filtered_steam_games = list(page_obj)

    else:
        # No genre/tag filtering - use simple pagination
        games_per_page = 20
        # Request extra games to account for API failures
        games_to_request = 30  # Request 30 to get ~20 successful ones
        page_number = int(request.GET.get('page', 1))

        # Calculate start and end indices for this page
        start_index = (page_number - 1) * games_to_request
        end_index = start_index + games_to_request

        # Get games for current page
        games_for_page = filtered_apps[start_index:end_index]

        # 5. Fetch details for games on current page
        appids_for_page = [app['appid'] for app in games_for_page]
        all_game_details = fetch_multiple_game_minimal(appids_for_page)

        # 6. Filter successful games and limit to games_per_page
        filtered_steam_games = []
        for game_data in all_game_details:
            if game_data and len(filtered_steam_games) < games_per_page:  # Only add up to games_per_page
                filtered_steam_games.append(game_data)

        # If no games were successfully fetched, create some dummy data for testing
        if not filtered_steam_games:
            dummy_games = []
            for i in range(min(10, len(games_for_page))):  # Show up to 10 dummy games
                app = games_for_page[i]
                dummy_games.append({
                    'appid': app['appid'],
                    'title': app['name'],
                    'image': None,
                    'platforms': {'windows': True, 'mac': False, 'linux': False},
                    'genres': [{'description': 'Action'}, {'description': 'Adventure'}],
                    'tags': [],
                })
            filtered_steam_games = dummy_games
            steam_error = "Showing sample games - Steam API is temporarily unavailable. Game details and images will load when the service is restored."

        # 7. Create proper pagination for non-filtered results
        paginator = Paginator(filtered_apps, games_per_page)

        try:
            page_obj = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.page(1)

    # 8. Render the template with all context variables
    # Prepare selected filter names for template display
    selected_genres_with_names = []
    if selected_genres:
        selected_genres_with_names = [(genre_id, genre_name) for genre_id, genre_name in genres_list if genre_id in selected_genres]

    selected_tags_with_names = []
    if selected_tags:
        selected_tags_with_names = [(tag_id, tag_name) for tag_id, tag_name in tags_list if tag_id in selected_tags]

    return render(
        request,
        'games/game_list.html',
        {
            'steam_games': filtered_steam_games,
            'steam_error': steam_error,
            'page_obj': page_obj,
            'query': search_query,  # Updated to match template
            'search_query': search_query,  # Keep for compatibility
            'genres': genres_list,
            'tags': tags_list,
            'selected_platform': selected_platform,
            'selected_genres': selected_genres,
            'selected_tags': selected_tags,
            'selected_genres_with_names': selected_genres_with_names,
            'selected_tags_with_names': selected_tags_with_names,
            'games': filtered_steam_games,  # For results count
        }
    )


def game_detail(request, pk):
    # Use the cached full details function for game detail page
    game = get_cached_game_details(pk)

    if game:
        return render(request, 'games/game_detail.html', {'game': game})
    else:
        error = 'Could not fetch game info from Steam.'
        return render(request, 'games/game_detail.html', {'error': error})


@login_required
# This view handles adding a Steam game to the database and the user's wishlist.
# It fetches game details from the Steam API using the appid, maps the fields,
# creates the Game object, sets genres/tags, and redirects to the game detail page.
def add_game_from_steam(request, appid):
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    response = requests.get(url)
    data = response.json()
    app_data = data.get(str(appid), {})
    if app_data.get('success'):
        info = app_data['data']
        fields = map_steam_to_game(info, user=request.user)
        game = Game.objects.create(**fields)
        set_game_genres_and_tags(game, info)
        # Redirect to game detail or list page
        return redirect('game_detail', pk=game.pk)
    else:
        return render(request, 'games/game_error.html', {'error': 'Could not fetch game info from Steam.'})


@require_http_methods(["GET"])
def search_suggestions_api(request):
    """API endpoint for real-time search suggestions"""
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'suggestions': []})

    # Get cached app list for fast searching
    all_apps = cache.get('steam_all_apps')
    if not all_apps:
        # Try to fetch if not cached
        try:
            app_list_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
            response = requests.get(app_list_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                all_apps = data.get('applist', {}).get('apps', [])
                cache.set('steam_all_apps', all_apps, 21600)  # 6 hours
            else:
                all_apps = []
        except Exception:
            all_apps = []

    if not all_apps:
        return JsonResponse({'suggestions': []})

    # Search through all games (not limited to 1000)
    query_lower = query.lower()
    matching_games = []

    for app in all_apps:
        if query_lower in app['name'].lower():
            matching_games.append({
                'appid': app['appid'],
                'name': app['name']
            })

            # Limit suggestions to prevent overwhelming UI
            if len(matching_games) >= 10:
                break

    # Prioritize exact matches and shorter names
    matching_games.sort(key=lambda x: (
        not x['name'].lower().startswith(query_lower),  # Exact matches first
        len(x['name']),  # Shorter names first
        x['name'].lower()  # Alphabetical
    ))

    return JsonResponse({'suggestions': matching_games[:8]})  # Return top 8 suggestions


@require_http_methods(["GET"])
def game_list_api(request):
    """API endpoint for infinite scroll - returns JSON game data"""
    page = int(request.GET.get('page', 1))
    search_query = request.GET.get('search', '').strip()

    # Multi-select filters
    selected_genres = request.GET.getlist('genres')
    selected_tags = request.GET.getlist('tags')

    # Backward compatibility
    if not selected_genres and request.GET.get('genre'):
        selected_genres = [request.GET.get('genre')]
    if not selected_tags and request.GET.get('tag'):
        selected_tags = [request.GET.get('tag')]

    # Determine games per page based on whether it's first load or subsequent
    games_per_page = 50 if page == 1 else 25

    try:
        if search_query:
            # Search functionality - same as original but optimized for API
            steam_data = cache.get('steam_app_list')
            if not steam_data:
                response = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v2/")
                if response.status_code == 200:
                    steam_data = response.json()
                    cache.set('steam_app_list', steam_data, 21600)  # 6 hours
                else:
                    return JsonResponse({'error': 'Failed to fetch Steam data'}, status=500)

            all_apps = steam_data['applist']['apps']
            filtered_apps = [
                app for app in all_apps
                if search_query.lower() in app['name'].lower()
            ][:500]  # Limit search results

            # Paginate search results
            start_index = (page - 1) * games_per_page
            end_index = start_index + games_per_page
            paginated_apps = filtered_apps[start_index:end_index]

            has_more = end_index < len(filtered_apps)

        elif selected_genres or selected_tags:
            # Genre/tag filtering - simplified for API
            steam_data = cache.get('steam_app_list')
            if not steam_data:
                response = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v2/")
                if response.status_code == 200:
                    steam_data = response.json()
                    cache.set('steam_app_list', steam_data, 21600)
                else:
                    return JsonResponse({'error': 'Failed to fetch Steam data'}, status=500)

            all_apps = steam_data['applist']['apps'][:1000]  # Limit for performance

            # Get first batch for filtering
            start_index = (page - 1) * games_per_page
            end_index = start_index + games_per_page
            paginated_apps = all_apps[start_index:end_index]

            has_more = end_index < len(all_apps)

        else:
            # Default listing - no filters
            steam_data = cache.get('steam_app_list')
            if not steam_data:
                response = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v2/")
                if response.status_code == 200:
                    steam_data = response.json()
                    cache.set('steam_app_list', steam_data, 21600)
                else:
                    return JsonResponse({'error': 'Failed to fetch Steam data'}, status=500)

            all_apps = steam_data['applist']['apps'][:1000]  # First 1000 games

            start_index = (page - 1) * games_per_page
            end_index = start_index + games_per_page
            paginated_apps = all_apps[start_index:end_index]

            has_more = end_index < len(all_apps)

        # Fetch game details for the paginated apps
        games = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_appid = {
                executor.submit(get_cached_game_minimal, app['appid']): app['appid']
                for app in paginated_apps
            }

            for future in concurrent.futures.as_completed(future_to_appid):
                game_data = future.result()
                if game_data and game_data.get('title'):
                    games.append({
                        'appid': game_data.get('appid'),
                        'title': game_data.get('title'),
                        'image': game_data.get('image'),
                        'platforms': game_data.get('platforms', {}),
                        'genres': game_data.get('genres', [])[:2],  # Limit to 2 genres
                    })

        return JsonResponse({
            'games': games,
            'has_more': has_more,
            'total_count': len(games),
            'page': page
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
