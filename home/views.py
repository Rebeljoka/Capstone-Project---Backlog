from datetime import timedelta
from math import pi

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from bokeh.embed import components
import logging
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.resources import CDN
# cumsum transform no longer used; angles computed server-side

from .models import SiteTrafficSnapshot


PALETTE = [
    "oklch(78% 0.22 80)",  # Gold
    "oklch(45% 0.18 30)",  # Sad Red
    "oklch(80% 0.25 20)",  # green-500
    "#EC4899",  # pink-500
    "#14B8A6",  # teal-500
    "#FACC15",  # yellow-400
    "#8B5CF6",  # violet-500
    "#0EA5E9",  # sky-500
]


def custom_404_view(request, exception):
    return render(request, '404.html', status=404)


def custom_500_view(request):
    return render(request, '500.html', status=500)


def _build_donut_chart(data_map, title, *, center_text=None):
    """Create a reusable Bokeh donut chart."""

    filtered = {label: value for label, value in data_map.items() if value > 0}
    if not filtered:
        filtered = {"No Data": 1}

    total = sum(filtered.values())
    source_data = []
    cumulative = 0.0
    for idx, (label, value) in enumerate(filtered.items()):
        angle = (value / total * 2 * pi) if total else 0
        start_angle = cumulative
        end_angle = cumulative + angle
        cumulative = end_angle
        percentage = (value / total * 100) if total else 0
        source_data.append(
            {
                "category": label,
                "value": value,
                "start": start_angle,
                "end": end_angle,
                "color": PALETTE[idx % len(PALETTE)],
                "percentage": percentage,
            }
        )

    source = ColumnDataSource({
        key: [row.get(key) for row in source_data]
        for key in source_data[0].keys()
    })

    plot = figure(
        height=555,
        width=555,
        toolbar_location=None,
        tools="hover",
        tooltips="@category: @value (@percentage{0.0}%)",
        x_range=(-0.6, 0.6),
        y_range=(0.4, 1.6),
    )

    plot.annular_wedge(
        x=0,
        y=1,
        inner_radius=0.25,
        outer_radius=0.45,
        start_angle='start',
        end_angle='end',
        line_color="white",
        fill_color='color',
        source=source,
    )

    plot.axis.visible = False
    plot.grid.grid_line_color = None
    plot.outline_line_color = None
    plot.min_border = 0
    plot.background_fill_alpha = 0
    plot.border_fill_alpha = 0
    plot.sizing_mode = "fixed"

    if center_text:
        plot.text(
            x=0,
            y=1,
            text=[center_text],
            text_align="center",
            text_baseline="middle",
            text_font_size="13pt",
            text_color="#22C55E",
        )

    return plot


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

    now = timezone.now()
    today = now.date()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # Traffic donut: Registered users vs visitor metrics
    total_users = User.objects.count()
    new_users_last_week = User.objects.filter(date_joined__gte=seven_days_ago).count()

    visitors_last_week = (
        SiteTrafficSnapshot.objects
        .filter(date__gte=seven_days_ago.date())
        .aggregate(total=Sum('unique_visitors'))
        .get('total')
        or 0
    )
    visitors_all_time = (
        SiteTrafficSnapshot.objects
        .aggregate(total=Sum('unique_visitors'))
        .get('total')
        or 0
    )
    visitors_prior = max(visitors_all_time - visitors_last_week, 0)

    traffic_chart = _build_donut_chart(
        {
            "Registered Users": total_users,
            "Visitors (Last 7 Days)": visitors_last_week,
            "Visitors (Before Last 7 Days)": visitors_prior,
        },
        "Users & Visitors",
        center_text=f"+{new_users_last_week} new"
        if new_users_last_week > 0
        else None,
    )

    # Wishlist creation rate donut
    from wishlist.models import Wishlist

    total_wishlists = Wishlist.objects.count()
    wishlists_today = Wishlist.objects.filter(created_at__date=today).count()
    wishlists_last_week = Wishlist.objects.filter(created_at__gte=seven_days_ago).count()
    wishlists_last_month = Wishlist.objects.filter(created_at__gte=thirty_days_ago).count()

    wishlist_segments = {
        "Past 24 Hours": wishlists_today,
        "Past 7 Days": max(wishlists_last_week - wishlists_today, 0),
        "Past 30 Days": max(wishlists_last_month - wishlists_last_week, 0),
    }

    wishlist_chart = _build_donut_chart(
        wishlist_segments,
        "Wishlist Creation Pace",
    )

    # Provide a tiny minimal chart for debugging: visit ?onlychart=minimal
    from bokeh.plotting import figure as _figure
    minimal_chart = _figure(height=200, width=300, toolbar_location=None)
    minimal_chart.circle([1], [1], size=20, color="#14B8A6")

    # Engagement donut
    users_with_wishlist = (
        Wishlist.objects.values('user').distinct().count()
    )
    users_without_wishlist = max(total_users - users_with_wishlist, 0)
    additional_wishlists = max(total_wishlists - users_with_wishlist, 0)
    avg_wishlists_per_user = (
        total_wishlists / total_users if total_users else 0
    )
    adoption_percent = (
        (users_with_wishlist / total_users) * 100 if total_users else 0
    )

    engagement_chart = _build_donut_chart(
        {
            "Users with Wishlists": users_with_wishlist,
            "Users without Wishlists": users_without_wishlist,
            "Additional Wishlists": additional_wishlists,
        },
        "Wishlist Engagement",
        center_text=f"{avg_wishlists_per_user:.1f} avg",
    )

    charts = {
        'traffic': traffic_chart,
        'wishlist': wishlist_chart,
        'engagement': engagement_chart,
        'minimal': minimal_chart,
    }
    # Allow testing by embedding only a subset of charts using ?onlychart=traffic,wishlist
    onlychart_param = None
    try:
        onlychart_param = request.GET.get('onlychart')
    except Exception:
        onlychart_param = None

    selected_charts = None
    if onlychart_param:
        requested = [c.strip().lower() for c in onlychart_param.split(',') if c.strip()]
        selected_charts = {k: v for k, v in charts.items() if k in requested}
        # If no valid keys found, fall back to all
        if not selected_charts:
            selected_charts = charts
    else:
        selected_charts = charts

    # Embed each chart separately to avoid creating a single Bokeh document that
    # (in some environments) can trigger recursive initialization in the browser.
    chart_script_parts = []
    chart_divs = {}
    chart_error = False
    chart_error_msg = ""
    try:
        for key, fig in selected_charts.items():
            try:
                s, d = components(fig)
                # s is a script string, d is a div or mapping when components() is used
                # When components() is called with a single figure it returns (script, div)
                chart_script_parts.append(s)
                # d may be a string or a dict; ensure we store the correct div
                if isinstance(d, dict):
                    # components returned a dict mapping keys to divs
                    # grab the first available value
                    any_key = next(iter(d.keys())) if d else None
                    chart_divs[key] = d.get(any_key) if any_key else None
                else:
                    chart_divs[key] = d
            except Exception:
                # Log per-chart failures but continue attempting other charts
                logging.getLogger(__name__).exception("Failed to build components for chart %s", key)
                chart_divs[key] = None

        chart_script = "\n".join(part for part in chart_script_parts if part)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Failed to generate Bokeh components (batch): %s", e)
        chart_script = ""
        chart_divs = {}
        chart_error = True
        chart_error_msg = str(e)

    context = {
        'popular_games': popular_games,
        'bokeh_js': CDN.js_files,
        'bokeh_css': CDN.css_files,
        'chart_script': chart_script,
        'traffic_chart_div': chart_divs.get('traffic'),
        'wishlist_chart_div': chart_divs.get('wishlist'),
        'engagement_chart_div': chart_divs.get('engagement'),
        # expose full mapping so template can render any extra placeholders (e.g. 'minimal')
        'chart_divs_all': chart_divs,
        'traffic_summary': {
            'total_users': total_users,
            'new_users_last_week': new_users_last_week,
            'visitors_last_week': visitors_last_week,
            'visitors_all_time': visitors_all_time,
        },
        'wishlist_summary': {
            'total_wishlists': total_wishlists,
            'created_today': wishlists_today,
            'created_last_week': wishlists_last_week,
            'created_last_month': wishlists_last_month,
        },
        'engagement_summary': {
            'average_wishlists': avg_wishlists_per_user,
            'adoption_percent': adoption_percent,
            'total_users': total_users,
            'users_with_wishlist': users_with_wishlist,
            'additional_wishlists': additional_wishlists,
        },
        'chart_error': chart_error,
        'chart_error_msg': chart_error_msg,
    }

    return render(request, 'home/index.html', context)


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
