from django import template

register = template.Library()


@register.filter
def profile_picture_url(user):
    """Template filter to safely get user's profile picture URL"""
    if not user or not user.is_authenticated:
        return "https://ui-avatars.com/api/?name=G&background=6B7280&color=ffffff&size=200&bold=true"

    try:
        if hasattr(user, 'profile'):
            return user.profile.profile_picture_url
        else:
            # Create profile if it doesn't exist
            from home.models import UserProfile
            profile = UserProfile.objects.create(user=user)
            return profile.profile_picture_url
    except Exception:
        # Fallback if anything goes wrong
        initials = ""
        if user.first_name and user.last_name:
            initials = f"{user.first_name[0]}{user.last_name[0]}".upper()
        elif user.first_name:
            initials = user.first_name[0].upper()
        elif user.username:
            initials = user.username[0].upper()
        else:
            initials = "U"

        # Generate color based on user ID
        colors = ["3B82F6", "EF4444", "10B981", "F59E0B", "8B5CF6", "06B6D4", "EC4899", "84CC16"]
        color = colors[user.id % len(colors)] if user.id else "6B7280"

        return f"https://ui-avatars.com/api/?name={initials}&background={color}&color=ffffff&size=200&bold=true"


@register.filter
def user_initials(user):
    """Get user initials for display"""
    if not user:
        return "G"

    if user.first_name and user.last_name:
        return f"{user.first_name[0]}{user.last_name[0]}".upper()
    elif user.first_name:
        return user.first_name[0].upper()
    elif user.username:
        return user.username[0].upper()
    else:
        return "U"
