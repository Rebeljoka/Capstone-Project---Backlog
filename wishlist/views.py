from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Wishlist, WishlistItem
from .forms import WishlistForm
from django.http import Http404


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
