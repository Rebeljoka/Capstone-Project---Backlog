from django.urls import path
from . import views

urlpatterns = [
    path('', views.game_list, name='game_list'),
    path('api/load-more/', views.game_list_api, name='game_list_api'),
    path('<int:pk>/', views.game_detail, name='game_detail'),
]
