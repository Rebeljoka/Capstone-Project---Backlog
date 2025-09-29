from django.db import models

# Create your models here.


class Game(models.Model):
    game_id = models.AutoField(primary_key=True)
    submitted_by = models.IntegerField()  # Will be a ForeignKey to User later
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


class Tag(models.Model):
    tag_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Genre(models.Model):
    genre_id = models.AutoField(primary_key=True)
    genre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.genre
