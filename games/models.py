from django.db import models
from django.contrib.auth.models import User

# Game model represents a Steam game in the database.
# It includes all relevant fields, and links to User, Tag, and Genre.


class Game(models.Model):
    game_id = models.AutoField(primary_key=True)
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    image = models.CharField(max_length=255, blank=True)
    short_description = models.TextField(blank=True)
    long_description = models.TextField(blank=True)
    release_date = models.DateField(null=True, blank=True)
    developer = models.CharField(max_length=255, blank=True)
    age_rating = models.CharField(max_length=20, null=True, blank=True)
    platform = models.CharField(max_length=255, blank=True)
    # ManyToManyField allows each game to have multiple tags and each tag to be linked to multiple games.
    # related_name='games' lets you access all games for a tag using tag.games.all()
    tags = models.ManyToManyField('Tag', related_name='games', blank=True)
    # ManyToManyField allows each game to have multiple genres and each genre to be linked to multiple games.
    # related_name='games' lets you access all games for a genre using genre.games.all()
    genres = models.ManyToManyField('Genre', related_name='games', blank=True)

    def __str__(self):
        # This method controls how the object is displayed in the admin and shell.
        return self.title


# Tag model represents a tag/category for games.
class Tag(models.Model):
    tag_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# Genre model represents a genre for games.
class Genre(models.Model):
    genre_id = models.AutoField(primary_key=True)
    genre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.genre


# Helper function to map Steam API data to Game model fields.
def map_steam_to_game(info, user=None):
    """
    Map Steam API data to Game model fields.
    info: dict from Steam appdetails API
    user: User instance for submitted_by
    Returns: dict suitable for Game.objects.create(**fields)
    """
    return {
        'submitted_by': user,
        'title': info.get('name'),
        'image': info.get('header_image'),
        'short_description': info.get('short_description'),
        'long_description': info.get('detailed_description', ''),
        'release_date': info.get('release_date', {}).get('date'),
        'developer': ', '.join(info.get('developers', [])),
        'age_rating': info.get('ratings', {}).get('usk'),
        'platform': ', '.join([k for k, v in info.get('platforms', {}).items() if v]),
    }


# Helper function to set genres and tags on a Game object from Steam API data.
def set_game_genres_and_tags(game, info):
    """
    Given a Game instance and Steam API info dict,
    map and set genres and tags using composite keys.
    """
    from .models import Genre, Tag
    # Genres
    genre_objs = []
    for genre in info.get('genres', []):
        genre_obj, _ = Genre.objects.get_or_create(
            genre_id=genre['id'],
            defaults={'genre': genre['description']}
        )
        genre_objs.append(genre_obj)
    game.genres.set(genre_objs)
    # Tags
    tag_objs = []
    for tag in info.get('categories', []):
        tag_obj, _ = Tag.objects.get_or_create(
            tag_id=tag['id'],
            defaults={'name': tag['description']}
        )
        tag_objs.append(tag_obj)
    game.tags.set(tag_objs)
