from django.contrib import admin
from .models import Game, Tag, Genre

# Register your models here.
admin.site.register(Game)
admin.site.register(Tag)
admin.site.register(Genre)
