from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

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
    age_rating = models.CharField(max_length=50, null=True, blank=True)
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

    Mapping according to Steam API structure:
    title > name
    image > header_image
    short_description > short_description
    release_date > release_date.date
    developer > developers (array, joined)
    age_rating > ratings.usk
    platform > platforms (object, extract true values)
    """
    # Handle release_date parsing - could be a string
    release_date = None
    if info.get('release_date') and info.get('release_date').get('date'):
        date_str = info.get('release_date').get('date')
        if date_str and date_str != 'Coming soon':
            try:
                # Try different date formats
                for fmt in ['%b %d, %Y', '%d %b, %Y', '%Y-%m-%d']:
                    try:
                        release_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue
            except (ValueError, TypeError):
                pass  # Keep as None if parsing fails

    # Handle platforms - extract platform names where value is True
    platforms = []
    if info.get('platforms'):
        for platform, available in info.get('platforms', {}).items():
            if available:
                platforms.append(platform.capitalize())

    # Handle age rating safely
    age_rating = None
    if info.get('ratings') and isinstance(info.get('ratings'), dict):
        raw_age_rating = info.get('ratings').get('usk')
        if raw_age_rating:
            # Truncate to 50 characters to fit the model field
            age_rating = str(raw_age_rating)[:50]

    return {
        'submitted_by': user,
        'title': info.get('name', ''),
        'image': info.get('header_image', ''),
        'short_description': info.get('short_description', ''),
        'long_description': info.get('detailed_description', ''),
        'release_date': release_date,
        'developer': ', '.join(info.get('developers', [])),
        'age_rating': age_rating,
        'platform': ', '.join(platforms),
    }


# Helper function to set genres and tags on a Game object from Steam API data.
def set_game_genres_and_tags(game, info):
    """
    Given a Game instance and Steam API info dict,
    map and set genres and tags using Steam API structure.

    Genres mapping:
    - genre_id > genres[0].id, genres[1].id, etc.
    - genre > genres[0].description, genres[1].description, etc.

    Tags mapping:
    - tag_id > categories[0].id, categories[1].id, etc.
    - name > categories[0].description, categories[1].description, etc.
    """

    # Genres - Steam API: genres array with id and description
    genre_objs = []
    for genre in info.get('genres', []):
        if 'id' in genre and 'description' in genre:
            try:
                genre_obj, _ = Genre.objects.get_or_create(
                    genre_id=genre['id'],
                    defaults={'genre': genre['description']}
                )
                genre_objs.append(genre_obj)
            except (ValueError, TypeError, KeyError):
                continue  # Skip malformed genre data
    game.genres.set(genre_objs)

    # Tags - Steam API: categories array with id and description
    tag_objs = []
    for tag in info.get('categories', []):
        if 'id' in tag and 'description' in tag:
            try:
                tag_obj, _ = Tag.objects.get_or_create(
                    tag_id=tag['id'],
                    defaults={'name': tag['description']}
                )
                tag_objs.append(tag_obj)
            except (ValueError, TypeError, KeyError):
                continue  # Skip malformed tag data
    game.tags.set(tag_objs)
