from django.urls import path
from . import views

urlpatterns = [
    path('', views.game_list, name='game_list'),
    path('api/load-more/', views.game_list_api, name='game_list_api'),
    path('api/search-suggestions/', views.search_suggestions_api, name='search_suggestions_api'),
    path('<int:pk>/', views.game_detail, name='game_detail'),
]
