from django.urls import path
from . import views

urlpatterns = [
    path('', views.wishlist_list, name='wishlist_list'),
    path('<int:pk>/', views.wishlist_detail, name='wishlist_detail'),
    path('item/<int:pk>/move/<str:direction>/', views.wishlist_item_move, name='wishlist_item_move'),
    path('create/', views.wishlist_create, name='wishlist_create'),
    path('<int:pk>/delete/', views.wishlist_delete, name='wishlist_delete'),
    path('item/<int:pk>/delete/', views.wishlist_item_delete, name='wishlist_item_delete'),
    path('add-steam-game/<int:appid>/', views.add_steam_game_to_wishlist, name='add_steam_game_to_wishlist'),
    # API: return user's wishlists as JSON (used by AJAX modal picker)
    path('api/wishlists/', views.user_wishlists_json, name='api_wishlists'),
]
