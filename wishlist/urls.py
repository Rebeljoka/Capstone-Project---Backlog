from django.urls import path
from . import views

urlpatterns = [
    # ...other patterns...
    path('item/<int:pk>/move/<str:direction>/', views.wishlist_item_move, name='wishlist_item_move'),
    path('create/', views.wishlist_create, name='wishlist_create'),
    path('<int:pk>/delete/', views.wishlist_delete, name='wishlist_delete'),
    path('item/<int:pk>/delete/', views.wishlist_item_delete, name='wishlist_item_delete'),
]
