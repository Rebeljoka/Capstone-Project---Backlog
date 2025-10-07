from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Wishlist, WishlistItem
from .forms import WishlistForm
from django.http import Http404, JsonResponse
import json
from games.models import Game, map_steam_to_game, set_game_genres_and_tags
import requests


@login_required
def user_wishlists_json(request):
    """Return the current user's wishlists as JSON for the AJAX modal picker."""
    # Optionally accept a game_id (Steam appid) to indicate which wishlists already contain the game
    game = None
    game_id = request.GET.get('game_id') or request.GET.get('appid')
    if game_id:
        try:
            game = Game.objects.get(game_id=int(game_id))
        except Exception:
            game = None

    wishlists = []
    for wl in Wishlist.objects.filter(user=request.user):
        items_count = wl.items.count()
        has_game = False
        if game is not None:
            has_game = WishlistItem.objects.filter(wishlist=wl, game=game).exists()
        wishlists.append({'pk': wl.pk, 'name': wl.name, 'has_game': has_game, 'items_count': items_count})
    # Provide the client with game metadata so the modal can display title/description
    # If we didn't find the game in DB, allow a provided title query param as a fallback
    game_title = None
    game_short = ''
    if game is not None:
        game_title = getattr(game, 'title', None)
        game_short = getattr(game, 'short_description', '') or ''
    else:
        # prefer explicit `title` query param if supplied by the client
        game_title = request.GET.get('title') or request.GET.get('q') or None

    result = {'wishlists': wishlists}
    if game_title:
        result['game'] = {'title': game_title, 'short_description': game_short}

    return JsonResponse(result)


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
            # Log activity for profile page
            try:
                from home.models import Activity
                from django.utils import timezone
                Activity.objects.create(
                    user=request.user,
                    icon='heart',
                    text=f'Created a new wishlist <span class="text-primary">"{wishlist.name}"</span>',
                    timestamp=timezone.now()
                )
            except Exception:
                pass  # Don't break wishlist creation if activity logging fails
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
    NOTE: This project stores the Steam appid in the Game model's primary key `game_id`,
    so we try to look up/create using `game_id` (Steam appid) first and fall back to title.
    """
    # Get user's wishlists for selection
    user_wishlists = Wishlist.objects.filter(user=request.user)

    if not user_wishlists.exists():
        # If this is an AJAX request, return JSON instead of redirecting
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json' or 'application/json' in request.headers.get('accept', '')
        if is_ajax and request.method == 'POST':
            return JsonResponse({'success': False, 'error': 'You need to create a wishlist first.'}, status=400)
        messages.error(request, "You need to create a wishlist first.")
        return redirect('wishlist_create')

    # Prefer to find the game locally by Steam appid first to avoid unnecessary Steam API calls.
    game = None
    try:
        appid_int = int(appid)
    except Exception:
        appid_int = None

    if appid_int is not None:
        try:
            game = Game.objects.get(game_id=appid_int)
        except Game.DoesNotExist:
            game = None

    # Only call Steam API if we don't already have the game locally
    if game is None:
        # Try to use a provided title query param (sent from JS) to find a title match first
        provided_title = request.GET.get('title') or request.GET.get('q')
        if provided_title:
            try:
                # Case-insensitive title lookup
                game = Game.objects.get(title__iexact=provided_title)
            except Game.DoesNotExist:
                game = None

    # If still not found, call Steam API and create/find by appid or title
    if game is None:
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

            # Try to create/find the game using Steam appid if available
            if appid_int is not None:
                try:
                    fields = map_steam_to_game(info, user=request.user)
                    game, created = Game.objects.get_or_create(game_id=appid_int, defaults=fields)
                    if created:
                        set_game_genres_and_tags(game, info)
                except Exception:
                    game = None

            # If still not present, fall back to title-based lookup/create
            if game is None:
                try:
                    # Prefer case-insensitive match to avoid duplicates
                    game = Game.objects.get(title__iexact=game_title)
                except Game.DoesNotExist:
                    fields = map_steam_to_game(info, user=request.user)
                    game = Game.objects.create(**fields)
                    set_game_genres_and_tags(game, info)

        except Exception as e:
            messages.error(request, f"Error fetching game info: {e}")
            return redirect('game_list')

    # Detect AJAX/JSON POSTs so we can return structured JSON for client-side handlers
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json' or 'application/json' in request.headers.get('accept', '')

    if request.method == 'POST' and is_ajax:
        # Accept either JSON body or form-encoded data
        payload = {}
        if request.content_type == 'application/json':
            try:
                payload = json.loads(request.body.decode('utf-8') or '{}')
            except Exception:
                payload = {}
        else:
            payload = request.POST

        wishlist_id = payload.get('wishlist_id') or payload.get('wishlistId')
        if not wishlist_id:
            return JsonResponse({'success': False, 'error': 'Missing wishlist_id.'}, status=400)

        try:
            wishlist = Wishlist.objects.get(pk=wishlist_id, user=request.user)
        except Wishlist.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid wishlist selection.'}, status=400)

        try:
            # Check if game is already in this wishlist
            existed = WishlistItem.objects.filter(wishlist=wishlist, game=game).exists()
            if existed:
                return JsonResponse({'success': True, 'message': f"'{game.title}' is already in your '{wishlist.name}' wishlist.", 'already_in_wishlist': True, 'game_id': game.game_id, 'wishlist_id': wishlist.pk})

            # Add to wishlist
            WishlistItem.objects.create(
                wishlist=wishlist,
                game=game,
                order=wishlist.items.count()  # Add at the end
            )

            # Log activity for profile page (best-effort)
            try:
                from home.models import Activity
                from django.utils import timezone
                Activity.objects.create(
                    user=request.user,
                    icon='plus',
                    text=f'Added <span class="text-primary">{game.title}</span> to wishlist <span class="text-primary">"{wishlist.name}"</span>',
                    timestamp=timezone.now()
                )
            except Exception:
                pass

            return JsonResponse({'success': True, 'message': f"'{game.title}' added to '{wishlist.name}' wishlist.", 'already_in_wishlist': False, 'game_id': game.game_id, 'wishlist_id': wishlist.pk})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    # Non-AJAX POST (regular form submission) continues to use existing redirect flow
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
            # Log activity for profile page
            try:
                from home.models import Activity
                from django.utils import timezone
                Activity.objects.create(
                    user=request.user,
                    icon='plus',
                    text=f'Added <span class="text-primary">{game.title}</span> to wishlist <span class="text-primary">"{wishlist.name}"</span>',
                    timestamp=timezone.now()
                )
            except Exception:
                pass  # Don't break if activity logging fails

            return redirect('game_list')

        except Wishlist.DoesNotExist:
            messages.error(request, "Invalid wishlist selection.")
            return redirect('game_list')

    # Show wishlist selection form
    # Check which wishlists already contain this game
    wishlists_with_status = []
    for wishlist in user_wishlists:
        has_game = WishlistItem.objects.filter(wishlist=wishlist, game=game).exists()
        wishlists_with_status.append({
            'wishlist': wishlist,
            'has_game': has_game
        })

    return render(request, 'wishlist/add_to_wishlist.html', {
        'game': game,
        'wishlists_with_status': wishlists_with_status
    })
