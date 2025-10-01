"""
Views for Steam game browsing, details, and wishlist management.
Handles fetching Steam data, filtering, and rendering templates.
"""
import requests
from django.core.cache import cache
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Genre, Tag, Game, map_steam_to_game, set_game_genres_and_tags


def game_list(request):
    # Initialize error and results
    steam_error = None
    # 1. Fetch the full Steam app list (appid and name only) from cache or API
    all_apps = cache.get('steam_all_apps')
    if all_apps is None:
        app_list_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
        try:
            app_list_resp = requests.get(app_list_url, timeout=10)
            app_list_data = app_list_resp.json()
            all_apps = app_list_data.get('applist', {}).get('apps', [])
            # Cache for 1 hour to avoid repeated API calls
            cache.set('steam_all_apps', all_apps, 3600)
        except Exception as e:
            steam_error = f"Error fetching Steam app list: {e}"
            all_apps = []

    # 2. Get search, genre, and tag filter parameters from request
    search_query = request.GET.get('search', '').strip()
    selected_genre = request.GET.get('genre', '')
    selected_tag = request.GET.get('tag', '')

    # Get all genres and tags from database for filter dropdowns
    genres_list = [(str(g.genre_id), g.genre) for g in Genre.objects.all()]  # All genres for dropdown
    tags_list = [(str(t.tag_id), t.name) for t in Tag.objects.all()]  # All tags for dropdown

    # 3. Build a list of appids to fetch details for:
    #    - If search is set, search ALL apps (not limited to 1000) and limit results after filtering
    #    - If genre/tag filter is set, fetch details for all filtered apps to check genre/tag
    #    - If no search/filter, just show first 1000 games for performance
    filtered_apps = all_apps
    if search_query:
        # Search through ALL apps, not just first 1000
        filtered_apps = [app for app in all_apps if search_query.lower() in app['name'].lower()]
        # Limit search results to first 100 matches for performance
        filtered_apps = filtered_apps[:100]
    else:
        # No search query, limit to first 1000 for performance
        filtered_apps = all_apps[:1000]

    appids_to_fetch = []
    if selected_genre or selected_tag:
        # Need to check all filtered_apps for genre/tag match, so fetch details for all
        appids_to_fetch = [app['appid'] for app in filtered_apps]
    else:
        # No genre/tag filter, just paginate and fetch details for current page
        paginator = Paginator(filtered_apps, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        appids_to_fetch = [app['appid'] for app in page_obj]

    # 4. Fetch details for each appid, exclude DLCs, collect tags, and apply genre/tag filter if set
    filtered_steam_games = []
    for appid in appids_to_fetch:
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                continue
            data = response.json()
            app_data = data.get(str(appid), {})
            if app_data.get('success'):
                info = app_data['data']
                genres = info.get('genres', [])
                tags = info.get('categories', [])
                name = info.get('name', '')
                # Exclude games with 'DLC' in name, genres, or tags
                if 'dlc' in name.lower() or 'DLC' in name.upper():
                    continue
                if any('dlc' in genre['description'].lower() for genre in genres):
                    continue
                if any('dlc' in tag['description'].lower() for tag in tags):
                    continue
                # If genre/tag filter is set, only include games that match
                if selected_genre and not any(str(genre['id']) == selected_genre for genre in genres):
                    continue
                if selected_tag and not any(str(tag['id']) == selected_tag for tag in tags):
                    continue
                filtered_steam_games.append({
                    'appid': info.get('steam_appid'),
                    'title': info.get('name', 'Unknown'),
                    'developer': ', '.join(info.get('developers', [])),
                    'image': info.get('header_image'),
                    'short_description': info.get('short_description', ''),
                    'genres': genres,
                    'tags': tags,
                })
        except Exception:
            continue

    # 5. Paginate the filtered steam games (20 games per page)
    paginator = Paginator(filtered_steam_games, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    steam_games = list(page_obj)

    # 6. Sort tags alphabetically (already sorted from database query)
    tags_list = sorted(tags_list, key=lambda x: x[1])

    # 7. Render the template with all context variables
    return render(
        request,
        'games/game_list.html',
        {
            'steam_games': steam_games,
            'steam_error': steam_error,
            'page_obj': page_obj,
            'search_query': search_query,
            'genres': genres_list,
            'tags': tags_list,
            'selected_genre': selected_genre,
            'selected_tag': selected_tag,
        }
    )


def game_detail(request, pk):
    url = f"https://store.steampowered.com/api/appdetails?appids={pk}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        app_data = data.get(str(pk), {})
        if app_data.get('success'):
            info = app_data['data']
            game = {
                'appid': info.get('steam_appid'),
                'title': info.get('name', 'Unknown'),
                'developer': ', '.join(info.get('developers', [])),
                'release_date': info.get('release_date', {}).get('date', ''),
                'description': info.get('short_description', ''),
                'image': info.get('header_image'),
                'genres': info.get('genres', []),
                'tags': info.get('categories', []),
            }
            return render(request, 'games/game_detail.html', {'game': game})
        else:
            error = 'Could not fetch game info from Steam.'
    except Exception as e:
        error = f'Error fetching game info: {e}'
    return render(request, 'games/game_detail.html', {'error': error})


def genre_games(request, genre_id):
    genre = get_object_or_404(Genre, genre_id=genre_id)
    games = genre.games.all()
    return render(request, 'games/genre_games.html', {'genre': genre, 'games': games})


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
