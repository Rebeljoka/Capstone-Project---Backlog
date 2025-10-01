from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Wishlist, WishlistItem
from .forms import WishlistForm
from django.http import Http404
from games.models import Game, map_steam_to_game, set_game_genres_and_tags
import requests


# Create your views here.
@login_required
def wishlist_list(request):
    wishlists = Wishlist.objects.filter(user=request.user)
    return render(request, 'wishlist/wishlist_list.html', {'wishlists': wishlists})


@login_required
def wishlist_detail(request, pk):
    try:
        wishlist = Wishlist.objects.get(pk=pk, user=request.user)
    except Wishlist.DoesNotExist:
        messages.error(request, "That wishlist could not be found or you do not have permission to view it.")
        return redirect('wishlist_list')
    return render(request, 'wishlist/wishlist_detail.html', {'wishlist': wishlist})


@login_required
def wishlist_item_move(request, pk, direction):
    item = get_object_or_404(WishlistItem, pk=pk, wishlist__user=request.user)
    wishlist = item.wishlist
    items = list(wishlist.items.order_by('order', 'added_on'))
    idx = items.index(item)
    moved = False
    if direction == 'up' and idx > 0:
        items[idx], items[idx - 1] = items[idx - 1], items[idx]
        moved = True
    elif direction == 'down' and idx < len(items) - 1:
        items[idx], items[idx + 1] = items[idx + 1], items[idx]
        moved = True
    # Reassign order values
    for i, obj in enumerate(items):
        obj.order = i
        obj.save()
    if moved:
        messages.success(request, "Game reordered successfully.")
    else:
        messages.info(request, "Game is already at the edge of the list.")
    return redirect('wishlist_detail', pk=wishlist.pk)


@login_required
def wishlist_create(request):
    if request.method == 'POST':
        form = WishlistForm(request.POST)
        if form.is_valid():
            wishlist = form.save(commit=False)
            wishlist.user = request.user
            wishlist.save()
            messages.success(request, "Wishlist created successfully.")
            return redirect('wishlist_list')
    else:
        form = WishlistForm()
    return render(request, 'wishlist/wishlist_form.html', {'form': form})


@login_required
def wishlist_delete(request, pk):
    try:
        wishlist = Wishlist.objects.get(pk=pk, user=request.user)
    except Wishlist.DoesNotExist:
        messages.error(request, "That wishlist could not be found or you do not have permission to delete it.")
        return redirect('wishlist_list')
    if request.method == 'POST':
        wishlist.delete()
        messages.success(request, "Wishlist deleted successfully.")
        return redirect('wishlist_list')
    return render(request, 'wishlist/wishlist_confirm_delete.html', {'wishlist': wishlist})


@login_required
def wishlist_item_delete(request, pk):
    try:
        item = WishlistItem.objects.get(pk=pk, wishlist__user=request.user)
    except WishlistItem.DoesNotExist:
        messages.error(request, "That game could not be found or you do not have permission to remove it.")
        return redirect('wishlist_list')
    wishlist_pk = item.wishlist.pk
    if request.method == 'POST':
        item.delete()
        messages.success(request, "Game removed from wishlist.")
        return redirect('wishlist_detail', pk=wishlist_pk)
    return render(request, 'wishlist/wishlist_item_confirm_delete.html', {'item': item})


@login_required
def add_steam_game_to_wishlist(request, appid):
    """
    Add a Steam game to a user's wishlist.
    If the game doesn't exist in our database, fetch it from Steam API first.
    """
    # Get user's wishlists for selection
    user_wishlists = Wishlist.objects.filter(user=request.user)

    if not user_wishlists.exists():
        messages.error(request, "You need to create a wishlist first.")
        return redirect('wishlist_create')

    # Try to find the game in our database first by title (since we don't store Steam appid)
    # Fetch game info from Steam API to get the title
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        app_data = data.get(str(appid), {})

        if not app_data.get('success'):
            messages.error(request, "Could not fetch game info from Steam.")
            return redirect('game_list')

        info = app_data['data']
        game_title = info.get('name', 'Unknown')

        # Try to find existing game by title
        try:
            game = Game.objects.get(title=game_title)
        except Game.DoesNotExist:
            # Game not in database, create it
            fields = map_steam_to_game(info, user=request.user)
            game = Game.objects.create(**fields)
            set_game_genres_and_tags(game, info)

    except Exception as e:
        messages.error(request, f"Error fetching game info: {e}")
        return redirect('game_list')

    if request.method == 'POST':
        wishlist_id = request.POST.get('wishlist_id')
        try:
            wishlist = Wishlist.objects.get(pk=wishlist_id, user=request.user)

            # Check if game is already in this wishlist
            if WishlistItem.objects.filter(wishlist=wishlist, game=game).exists():
                messages.info(request, f"'{game.title}' is already in your '{wishlist.name}' wishlist.")
            else:
                # Add to wishlist
                WishlistItem.objects.create(
                    wishlist=wishlist,
                    game=game,
                    order=wishlist.items.count()  # Add at the end
                )
                messages.success(request, f"'{game.title}' added to '{wishlist.name}' wishlist.")

            return redirect('game_list')

        except Wishlist.DoesNotExist:
            messages.error(request, "Invalid wishlist selection.")
            return redirect('game_list')

    # Show wishlist selection form
    return render(request, 'wishlist/add_to_wishlist.html', {
        'game': game,
        'wishlists': user_wishlists
    })
