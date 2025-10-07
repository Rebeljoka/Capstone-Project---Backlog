from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Count


def custom_404_view(request, exception):
    return render(request, '404.html', status=404)


def custom_500_view(request):
    return render(request, '500.html', status=500)


# Create your views here.
def index(request):
    # Show 5 random games that appear in user wishlists (popular wishlisted games)
    try:
        from wishlist.models import WishlistItem
        from games.models import Game

        # Get games that appear in wishlists
        wish_game_ids = WishlistItem.objects.values_list('game_id', flat=True)
        popular_qs = Game.objects.filter(pk__in=wish_game_ids).distinct()

        # Randomly sample up to 5 games (ok for small/dev DBs); make a list so we can attach counts
        selected = list(popular_qs.order_by('?')[:5])

        # Compute wishlist counts for the selected games and attach as attribute for template use
        counts_qs = (
            WishlistItem.objects
            .filter(game__in=selected)
            .values('game')
            .annotate(count=Count('pk'))
        )
        counts = {item['game']: item['count'] for item in counts_qs}
        for g in selected:
            setattr(g, 'wishlist_count', counts.get(g.pk, 0))

        popular_games = selected
    except Exception:
        popular_games = []

    return render(request, 'home/index.html', {'popular_games': popular_games})


@login_required
def profile(request):
    """User profile page showing user stats and recent activity"""
    user = request.user

    # Calculate days since joining
    days_joined = (timezone.now().date() - user.date_joined.date()).days

    # Get total games from all wishlists using WishlistItem (avoid duplicates)
    wishlist_qs = user.wishlists.all()
    game_ids = set()
    for wishlist in wishlist_qs:
        for item in wishlist.items.all():
            game_ids.add(item.game.pk)
    total_games = len(game_ids)

    # Example: favorite genres (replace with your actual logic)
    favorite_genres = []
    if hasattr(user, 'profile') and hasattr(user.profile, 'favorite_genres'):
        favorite_genres = [g.name for g in user.profile.favorite_genres.all()]

    # Example: platforms (replace with your actual logic)
    platforms = []
    if hasattr(user, 'profile') and hasattr(user.profile, 'platforms'):
        platforms = [
            {
                'name': p.name,
                'icon': p.icon if hasattr(p, 'icon') else 'device-gamepad',
                'active': p.active if hasattr(p, 'active') else True,
            }
            for p in user.profile.platforms.all()
        ]

    # Example: activity log (replace with your actual logic)
    activity_log = []
    if hasattr(user, 'activity_set'):
        for activity in user.activity_set.order_by('-timestamp')[:10]:
            activity_log.append({
                'icon': activity.icon if hasattr(activity, 'icon') else 'activity',
                'text': activity.text,
                'time': activity.timestamp.strftime('%b %d, %Y %H:%M'),
            })

    # Example: stats (replace with your actual logic)
    stats = {
        'wishlists': wishlist_qs.count(),
        'games_added': total_games,
        'hours_played': getattr(user.profile, 'hours_played', 0) if hasattr(user, 'profile') else 0,
    }

    # Get wishlists ordered by most recently updated
    recent_wishlists = user.wishlists.all().order_by('-updated_at')

    context = {
        'user': user,
        'days_joined': days_joined,
        'total_games': total_games,
        'favorite_genres': favorite_genres,
        'platforms': platforms,
        'activity_log': activity_log,
        'stats': stats,
        'recent_wishlists': recent_wishlists,
    }

    return render(request, 'profile.html', context)


@login_required
def edit_profile(request):
    """Edit profile page with multiple forms for different settings"""
    user = request.user

    # Ensure user has a profile
    if not hasattr(user, 'profile'):
        from .models import UserProfile
        UserProfile.objects.create(user=user)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'basic_info':
            return handle_basic_info_update(request, user)
        elif form_type == 'email_change':
            return handle_email_change(request, user)
        elif form_type == 'password_change':
            return handle_password_change(request, user)
        elif form_type == 'account_deletion':
            return handle_account_deletion(request, user)
        elif form_type == 'profile_picture':
            return handle_profile_picture_upload(request, user)
        elif form_type == 'remove_profile_picture':
            return handle_profile_picture_removal(request, user)

    return render(request, 'edit_profile.html', {'user': user})


def handle_basic_info_update(request, user):
    """Handle basic information updates (username, first_name, last_name, bio)"""
    try:
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        bio = request.POST.get('bio', '').strip()

        # Validate username
        if not username:
            messages.error(request, 'Username cannot be empty.')
            return redirect('edit_profile')

        # Check if username already exists (excluding current user)
        from django.contrib.auth.models import User
        if User.objects.filter(username=username).exclude(id=user.id).exists():
            messages.error(request, 'This username is already taken.')
            return redirect('edit_profile')

        # Update user information
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        # Update profile bio
        user.profile.bio = bio
        user.profile.save()

        messages.success(request, 'Your profile information has been updated successfully!')

    except Exception as e:
        messages.error(request, f'An error occurred while updating your profile: {str(e)}')

    return redirect('edit_profile')


def handle_email_change(request, user):
    """Handle email address changes with password verification"""
    try:
        new_email = request.POST.get('email', '').strip().lower()
        current_password = request.POST.get('current_password', '')

        # Validate inputs
        if not new_email:
            messages.error(request, 'Email address cannot be empty.')
            return redirect('edit_profile')

        if not current_password:
            messages.error(request, 'Current password is required to change email.')
            return redirect('edit_profile')

        # Verify current password
        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('edit_profile')

        # Check if email already exists
        from django.contrib.auth.models import User
        if User.objects.filter(email=new_email).exclude(id=user.id).exists():
            messages.error(request, 'This email address is already in use.')
            return redirect('edit_profile')

        # Update email
        user.email = new_email
        user.save()

        messages.success(request, 'Your email address has been updated successfully!')

    except Exception as e:
        messages.error(request, f'An error occurred while updating your email: {str(e)}')

    return redirect('edit_profile')


def handle_password_change(request, user):
    """Handle password changes using Django's built-in form"""
    try:
        old_password = request.POST.get('old_password', '')
        new_password1 = request.POST.get('new_password1', '')
        new_password2 = request.POST.get('new_password2', '')

        # Validate inputs
        if not all([old_password, new_password1, new_password2]):
            messages.error(request, 'All password fields are required.')
            return redirect('edit_profile')

        if new_password1 != new_password2:
            messages.error(request, 'New passwords do not match.')
            return redirect('edit_profile')

        # Verify old password
        if not user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('edit_profile')

        # Validate new password strength
        if len(new_password1) < 8:
            messages.error(request, 'New password must be at least 8 characters long.')
            return redirect('edit_profile')

        # Update password
        user.set_password(new_password1)
        user.save()

        # Update session to prevent logout
        update_session_auth_hash(request, user)

        messages.success(request, 'Your password has been changed successfully!')

    except Exception as e:
        messages.error(request, f'An error occurred while changing your password: {str(e)}')

    return redirect('edit_profile')


@transaction.atomic
def handle_account_deletion(request, user):
    """Handle secure account deletion with multiple verifications"""
    try:
        password_confirm = request.POST.get('password_confirm', '')
        deletion_confirm = request.POST.get('deletion_confirm', '')

        # Validate password confirmation
        if not password_confirm:
            messages.error(request, 'Password is required to delete your account.')
            return redirect('edit_profile')

        if not user.check_password(password_confirm):
            messages.error(request, 'Password is incorrect.')
            return redirect('edit_profile')

        # Validate deletion confirmation text
        if deletion_confirm != 'DELETE MY ACCOUNT':
            messages.error(request, 'Please type "DELETE MY ACCOUNT" exactly as shown.')
            return redirect('edit_profile')

        # Security check: ensure user can only delete their own account
        if request.user.id != user.id:
            messages.error(request, 'You can only delete your own account.')
            return redirect('edit_profile')

        # Log the user out before deletion
        from django.contrib.auth import logout

        # Store username for the goodbye message
        username = user.username

        # Delete the user account (this will cascade and delete related data)
        user.delete()

        # Log out the user
        logout(request)

        # Add a success message for the next page
        messages.success(request, f'Account "{username}" has been permanently deleted. We\'re sorry to see you go!')

        # Redirect to home page
        return redirect('home')

    except Exception as e:
        messages.error(request, f'An error occurred while deleting your account: {str(e)}')
        return redirect('edit_profile')


def handle_profile_picture_upload(request, user):
    """Handle profile picture upload to Cloudinary"""
    try:
        profile_picture = request.FILES.get('profile_picture')

        if not profile_picture:
            messages.error(request, 'No file selected.')
            return redirect('edit_profile')

        # Validate file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        file_name = profile_picture.name.lower()
        if not any(file_name.endswith(ext) for ext in valid_extensions):
            messages.error(request, 'Please upload a valid image file (JPG, PNG, or GIF).')
            return redirect('edit_profile')

        # Validate file size (5MB limit)
        if profile_picture.size > 5 * 1024 * 1024:
            messages.error(request, 'File size must be less than 5MB.')
            return redirect('edit_profile')

        # Upload to Cloudinary and update user profile
        user.profile.profile_picture = profile_picture
        user.profile.save()

        messages.success(request, 'Profile picture updated successfully!')

    except Exception as e:
        messages.error(request, f'An error occurred while uploading your profile picture: {str(e)}')

    return redirect('edit_profile')


def handle_profile_picture_removal(request, user):
    """Handle profile picture removal from Cloudinary and profile"""
    try:
        profile_picture = user.profile.profile_picture
        if profile_picture:
            public_id = getattr(profile_picture, 'public_id', None)
            if public_id:
                from cloudinary import api
                try:
                    api.delete_resources([public_id])
                except Exception as cloudinary_error:
                    messages.warning(request, f'Cloudinary deletion warning: {cloudinary_error}')
            profile_picture.delete()
            user.profile.profile_picture = None
            user.profile.save()
            messages.success(request, 'Profile picture removed successfully!')
        else:
            messages.info(request, 'No profile picture to remove.')

    except Exception as e:
        messages.error(request, f'An error occurred while removing your profile picture: {str(e)}')

    return redirect('edit_profile')
