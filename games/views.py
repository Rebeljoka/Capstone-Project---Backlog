import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Game, Genre, Tag, map_steam_to_game, set_game_genres_and_tags


# Create your views here.
def game_list(request):
    # Initialize error and results
    steam_error = None
    steam_games = []
    # 1. Fetch the full Steam app list (appid and name only)
    app_list_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    try:
        app_list_resp = requests.get(app_list_url, timeout=10)
        app_list_data = app_list_resp.json()
        all_apps = app_list_data.get('applist', {}).get('apps', [])
    except Exception as e:
        steam_error = f"Error fetching Steam app list: {e}"
        all_apps = []

    # 2. Search feature: filter app list by name if search query is provided
    search_query = request.GET.get('search', '').strip()
    if search_query:
        filtered_apps = [app for app in all_apps if search_query.lower() in app['name'].lower()]
    else:
        filtered_apps = all_apps

    # 3. Paginate the filtered app list (20 games per page)
    paginator = Paginator(filtered_apps, 20)  # 20 games per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 4. Get selected genre/tag from GET params for filtering
    selected_genre = request.GET.get('genre', '')
    selected_tag = request.GET.get('tag', '')
    genre_set = set()  # Collect unique genres for dropdown
    tag_set = set()    # Collect unique tags for dropdown

    # 5. For each game on the current page, fetch details from Steam API
    for app in page_obj:
        appid = app['appid']
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
                # 6. Collect all genres/tags for filter dropdowns
                for genre in genres:
                    genre_set.add((genre['id'], genre['description']))
                for tag in tags:
                    tag_set.add((tag['id'], tag['description']))
                # 7. Apply genre/tag filter if set (only show games matching selected genre/tag)
                if (selected_genre and not any(str(genre['id']) == selected_genre for genre in genres)) or \
                   (selected_tag and not any(str(tag['id']) == selected_tag for tag in tags)):
                    continue
                # 8. Add game details to steam_games list for display
                steam_games.append({
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

    # 9. Sort genres/tags for dropdowns
    genres_list = sorted(list(genre_set), key=lambda x: x[1])
    tags_list = sorted(list(tag_set), key=lambda x: x[1])

    # 10. Render the template with all context variables
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
    game = get_object_or_404(Game, pk=pk)
    return render(request, 'games/game_detail.html', {'game': game})


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
