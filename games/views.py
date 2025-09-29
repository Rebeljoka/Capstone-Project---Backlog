from django.shortcuts import render, get_object_or_404
from .models import Game, Genre, Tag


# Create your views here.
def game_list(request):
    genre_id = request.GET.get('genre')
    tag_id = request.GET.get('tag')
    genres = Genre.objects.all()
    tags = Tag.objects.all()
    games = Game.objects.all()
    if genre_id:
        games = games.filter(genres__genre_id=genre_id)
    if tag_id:
        games = games.filter(tags__tag_id=tag_id)
    return render(
        request,
        'games/game_list.html',
        {
            'games': games,
            'genres': genres,
            'tags': tags,
            'selected_genre': genre_id,
            'selected_tag': tag_id,
        }
    )


def game_detail(request, pk):
    game = get_object_or_404(Game, pk=pk)
    return render(request, 'games/game_detail.html', {'game': game})


def genre_games(request, genre_id):
    genre = get_object_or_404(Genre, genre_id=genre_id)
    games = genre.games.all()
    return render(request, 'games/genre_games.html', {'genre': genre, 'games': games})
