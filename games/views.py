"""
Views for Steam game browsing, details, and wishlist management.
Handles fetching Steam data, filtering, and rendering templates.
"""
import requests
import concurrent.futures
import logging
from django.core.cache import cache
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from games.models import (
    Genre,
    Tag,
    Game,
    map_steam_to_game,
    set_game_genres_and_tags,
)

logger = logging.getLogger(__name__)


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
                    info = app_data.get('data', {})
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
                    info = app_data.get('data', {})
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
                        # Add system requirements for PC, Mac, Linux
                        'pc_requirements_minimum': info.get('pc_requirements', {}).get('minimum', ''),
                        'mac_requirements_minimum': info.get('mac_requirements', {}).get('minimum', ''),
                        'linux_requirements_minimum': info.get('linux_requirements', {}).get('minimum', ''),
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
    # Unified DB-first merged flow:
    steam_error = None

    # Request params
    search_query = request.GET.get('search', '').strip()
    selected_platform = request.GET.get('platform', '')
    selected_genres = request.GET.getlist('genres')
    selected_tags = request.GET.getlist('tags')
    # Backward compatibility single-select
    if not selected_genres and request.GET.get('genre'):
        selected_genres = [request.GET.get('genre')]
    if not selected_tags and request.GET.get('tag'):
        selected_tags = [request.GET.get('tag')]

    # Pagination params
    games_per_page = 25
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    start_index = (page - 1) * games_per_page
    end_index = start_index + games_per_page

    # Build DB queryset with filters applied
    db_qs = Game.objects.all()
    if search_query:
        db_qs = db_qs.filter(title__icontains=search_query)
    if selected_genres:
        # Require ALL selected genres (AND semantics)
        for gid in selected_genres:
            db_qs = db_qs.filter(genres__genre_id=gid)
        db_qs = db_qs.distinct()
    if selected_tags:
        # Require ALL selected tags (AND semantics)
        for tid in selected_tags:
            db_qs = db_qs.filter(tags__tag_id=tid)
        db_qs = db_qs.distinct()
    if selected_platform:
        db_qs = db_qs.filter(platform__icontains=selected_platform)

    db_count = db_qs.count()

    # Slice DB results for this page (DB-first)
    db_slice = list(db_qs[start_index:end_index]) if db_count > start_index else []

    # Convert DB objects to minimal dicts expected by template
    def db_game_to_dict(game):
        genres = [{'description': genre.genre} for genre in game.genres.all()]
        tags = [{'description': tag.name} for tag in game.tags.all()]
        return {
            'appid': getattr(game, 'game_id', None),
            'game_id': getattr(game, 'game_id', None),
            'title': game.title,
            'image': game.image,
            'platforms': {
                'windows': 'windows' in (game.platform or '').lower(),
                'mac': 'mac' in (game.platform or '').lower(),
                'linux': 'linux' in (game.platform or '').lower(),
            },
            'genres': genres,
            'tags': tags,
        }

    db_results = [db_game_to_dict(g) for g in db_slice]

    # Determine how many API results we need to fill the page
    needed = games_per_page - len(db_results)

    # Prepare genre/tag lists for filters (cached)
    genres_list = cache.get('steam_genres_list')
    if genres_list is None:
        genres_list = [(str(g.genre_id), g.genre) for g in Genre.objects.all()]
        cache.set('steam_genres_list', genres_list, 3600)
    tags_list = cache.get('steam_tags_list')
    if tags_list is None:
        tags_list = sorted([(str(t.tag_id), t.name) for t in Tag.objects.all()], key=lambda x: x[1])
        cache.set('steam_tags_list', tags_list, 3600)

    # Build set of DB appids to exclude from API results
    db_appids = set()
    for g in db_qs:
        aid = getattr(g, 'game_id', None)
        if aid is not None:
            try:
                db_appids.add(int(aid))
            except Exception:
                pass

    api_results = []
    total_api_candidates = 0

    if needed > 0:
        # Fetch Steam app list
        all_apps = cache.get('steam_all_apps')
        if all_apps is None:
            try:
                app_list_resp = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v2/", timeout=10)
                app_list_data = app_list_resp.json()
                all_apps = app_list_data.get('applist', {}).get('apps', [])
                cache.set('steam_all_apps', all_apps, 21600)
            except Exception as e:
                steam_error = f"Error fetching Steam app list: {e}"
                all_apps = []

        # Apply simple search filter on app name (case-insensitive)
        filtered_apps = all_apps
        if search_query:
            ql = search_query.lower()
            filtered_apps = [a for a in filtered_apps if ql in a.get('name', '').lower()]

        # Exclude apps already present in DB
        filtered_apps = [a for a in filtered_apps if int(a.get('appid', 0)) not in db_appids]

        total_api_candidates = len(filtered_apps)

        # Limit candidate pool for performance
        candidate_limit = 3000 if search_query else 1500
        filtered_apps = filtered_apps[:candidate_limit]

        # If genre/tag filtering is requested we need to inspect details; fetch in batches
        batch_size = 30
        collected = 0
        for i in range(0, len(filtered_apps), batch_size):
            if collected >= needed:
                break
            batch = filtered_apps[i:i + batch_size]
            appids = [a['appid'] for a in batch]
            try:
                details = fetch_multiple_game_minimal(appids)
            except Exception:
                details = []

            for d in details:
                if not d:
                    continue
                # Platform filter
                if selected_platform:
                    plats = d.get('platforms', {})
                    sel_lower = selected_platform.lower()
                    plats_windows = plats.get('windows')
                    plats_mac = plats.get('mac')
                    plats_linux = plats.get('linux')
                    ok = False
                    if 'windows' in sel_lower and plats_windows:
                        ok = True
                    elif 'mac' in sel_lower and plats_mac:
                        ok = True
                    elif 'linux' in sel_lower and plats_linux:
                        ok = True
                    if not ok:
                        continue
                # Genre filter (AND semantics)
                if selected_genres:
                    game_genre_ids = [str(g.get('id')) for g in d.get('genres', [])]
                    if not all(gid in game_genre_ids for gid in selected_genres):
                        continue
                # Tag filter (AND semantics)
                if selected_tags:
                    game_tag_ids = [str(t.get('id')) for t in d.get('tags', [])]
                    if not all(tid in game_tag_ids for tid in selected_tags):
                        continue

                api_results.append(d)
                collected += 1
                if collected >= needed:
                    break

    # Merge DB + API results for this page
    merged_games = db_results + api_results

    # Estimate total results for pagination (DB + filtered API candidates)
    estimated_total = db_count + total_api_candidates
    # Fallback if both empty
    if estimated_total == 0:
        estimated_total = len(merged_games)

    # Create a simple paginator so templates can render page links
    paginator = Paginator(range(estimated_total), games_per_page)
    try:
        page_obj = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    # Map the actual merged games for this page onto the page_obj so templates can iterate page_obj
    try:
        page_obj.object_list = merged_games
    except Exception:
        # If anything goes wrong, log and continue with merged_games separately
        logger.exception('Failed to set page_obj.object_list')

    # Build a current_query string (all GET params except page) to preserve filters in links
    params = {}
    for key, values in request.GET.lists():
        if key == 'page':
            continue
        params[key] = values
    # Removed unused variable 'current_query'

    # Selected names for display
    selected_genres_with_names = [
        (genre_id, genre_name)
        for genre_id, genre_name in genres_list
        if genre_id in selected_genres
    ]
    selected_tags_with_names = [
        (tag_id, tag_name)
        for tag_id, tag_name in tags_list
        if tag_id in selected_tags
    ]

    return render(
        request,
        'games/game_list.html',
        {
            'steam_games': merged_games,
            'steam_error': steam_error,
            'page_obj': page_obj,
            'query': search_query,
            'search_query': search_query,
            'genres': genres_list,
            'tags': tags_list,
            'selected_platform': selected_platform,
            'selected_genres': selected_genres,
            'selected_tags': selected_tags,
            'selected_genres_with_names': selected_genres_with_names,
            'selected_tags_with_names': selected_tags_with_names,
            'games': merged_games,
        }
    )


def game_detail(request, pk):

    # Try to get the game from the database first
    try:
        db_game = Game.objects.get(game_id=pk)
        # Convert genres and tags to list of dicts with 'description' key for template compatibility
        genres = [{'description': genre.genre} for genre in db_game.genres.all()]
        tags = [{'description': tag.name} for tag in db_game.tags.all()]
        # Convert stored platform string to the dict shape the template expects
        platform_str = (db_game.platform or '')
        platforms_dict = {
            'windows': 'windows' in platform_str.lower(),
            'mac': 'mac' in platform_str.lower(),
            'linux': 'linux' in platform_str.lower(),
        }

        game = {
            'appid': db_game.game_id,
            'title': db_game.title,
            'developer': db_game.developer,
            'release_date': db_game.release_date,
            'image': db_game.image,
            'description': db_game.short_description,
            'genres': genres,
            'tags': tags,
            'platforms': platforms_dict,
            'pc_requirements_minimum': db_game.pc_requirements_minimum,
            'mac_requirements_minimum': db_game.mac_requirements_minimum,
            'linux_requirements_minimum': db_game.linux_requirements_minimum,
            # Add other fields as needed
        }
        return render(request, 'games/game_detail.html', {'game': game})
    except Game.DoesNotExist:
        # If not in DB, use the cached full details function for game detail page
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
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return render(
                request,
                'games/game_error.html',
                {'error': 'Could not fetch game info from Steam (bad response).'}
            )
        data = response.json()
        if not data:
            return render(request, 'games/game_error.html', {'error': 'No data returned from Steam API.'})
        app_data = data.get(str(appid))
        if not app_data or not app_data.get('success'):
            return render(request, 'games/game_error.html', {'error': 'Could not fetch game info from Steam.'})
        info = app_data.get('data')
        if not info:
            return render(request, 'games/game_error.html', {'error': 'Game data missing from Steam API.'})
        fields = map_steam_to_game(info, user=request.user)
        game = Game.objects.create(**fields)
        set_game_genres_and_tags(game, info)
        # Redirect to game detail or list page
        return redirect('game_detail', pk=game.pk)
    except Exception as e:
        return render(request, 'games/game_error.html', {'error': f'Error fetching game info: {e}'})


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
        # Check database first
        db_games = Game.objects.all()
        if db_games.exists():
            # Apply filters
            if search_query:
                db_games = db_games.filter(title__icontains=search_query)
            if selected_genres:
                db_games = db_games.filter(genres__genre_id__in=selected_genres).distinct()
            if selected_tags:
                db_games = db_games.filter(tags__tag_id__in=selected_tags).distinct()
            if request.GET.get('platform'):
                db_games = db_games.filter(platform__icontains=request.GET.get('platform'))

            # Pagination
            paginator = Paginator(db_games, games_per_page)
            try:
                page_obj = paginator.page(page)
            except (PageNotAnInteger, EmptyPage):
                page_obj = paginator.page(1)
            has_more = page_obj.has_next()

            # Format games for frontend
            games = []
            for game in page_obj:
                genres = [{'description': genre.genre} for genre in game.genres.all()]
                game_dict = {
                    'appid': getattr(game, 'game_id', None),
                    'title': game.title,
                    'image': game.image,
                    'platforms': {'windows': 'windows' in (game.platform or '').lower(),
                                  'mac': 'mac' in (game.platform or '').lower(),
                                  'linux': 'linux' in (game.platform or '').lower()},
                    'genres': genres[:2],
                }
                games.append(game_dict)

            return JsonResponse({
                'games': games,
                'has_more': has_more,
                'total_count': len(games),
                'page': page
            })
        # If no games in DB, fallback to Steam API
        steam_data = cache.get('steam_app_list')
        if not steam_data:
            try:
                response = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v2/", timeout=10)
                if response.status_code == 200:
                    steam_data = response.json()
                    cache.set('steam_app_list', steam_data, 21600)
                else:
                    return JsonResponse({'error': 'Failed to fetch Steam data'}, status=500)
            except Exception as e:
                return JsonResponse({'error': f'Steam API error: {e}'}, status=500)

        all_apps = steam_data['applist']['apps']
        # Apply search filter
        filtered_apps = all_apps
        if search_query:
            filtered_apps = [app for app in filtered_apps if search_query.lower() in app['name'].lower()]
        # Limit for performance
        filtered_apps = filtered_apps[:1000]

        # Fetch minimal details for genre/tag filtering
        games_minimal = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_appid = {
                executor.submit(get_cached_game_minimal, app['appid']): app['appid']
                for app in filtered_apps
            }
            for future in concurrent.futures.as_completed(future_to_appid):
                game_data = future.result()
                if game_data and game_data.get('title'):
                    games_minimal.append(game_data)

        # Apply genre/tag filters if present
        if selected_genres:
            # Keep games that contain ALL of the selected genres (AND semantics)
            games_minimal = [
                g for g in games_minimal
                if all(
                    str(sel_gid) in [str(genre.get('id')) for genre in g.get('genres', [])]
                    for sel_gid in selected_genres
                )
            ]
        if selected_tags:
            # Keep games that contain ALL of the selected tags (AND semantics)
            games_minimal = [
                g for g in games_minimal
                if all(
                    str(sel_tid) in [str(tag.get('id')) for tag in g.get('tags', [])]
                    for sel_tid in selected_tags
                )
            ]

        # Pagination
        start_index = (page - 1) * games_per_page
        end_index = start_index + games_per_page
        paginated_games = games_minimal[start_index:end_index]
        has_more = end_index < len(games_minimal)

        # Format for frontend
        games = []
        for game_data in paginated_games:
            games.append({
                'appid': game_data.get('appid'),
                'title': game_data.get('title'),
                'image': game_data.get('image'),
                'platforms': game_data.get('platforms', {}),
                'genres': game_data.get('genres', [])[:2],
                'tags': game_data.get('tags', [])[:2],
            })

        return JsonResponse({
            'games': games,
            'has_more': has_more,
            'total_count': len(games_minimal),
            'page': page
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
