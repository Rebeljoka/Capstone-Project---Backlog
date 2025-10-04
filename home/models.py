from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField


class FavoriteGenre(models.Model):
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name


class Platform(models.Model):
    name = models.CharField(max_length=64, unique=True)
    icon = models.CharField(max_length=32, default='device-gamepad')
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Extended user profile with additional fields"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = CloudinaryField('image', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    favorite_genres = models.ManyToManyField(FavoriteGenre, blank=True, related_name='users')
    platforms = models.ManyToManyField(Platform, blank=True, related_name='users')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def profile_picture_url(self):
        """Return profile picture URL or default avatar with multiple fallbacks"""
        if self.profile_picture:
            try:
                return self.profile_picture.url
            except Exception:
                # If there's an error getting the Cloudinary URL, use fallback
                pass

        # Generate a unique avatar based on user's initials and ID
        return self.get_default_avatar()

    def get_default_avatar(self):
        """Generate a default avatar URL with user's initials"""
        # Get user initials
        initials = ""
        if self.user.first_name and self.user.last_name:
            initials = f"{self.user.first_name[0]}{self.user.last_name[0]}".upper()
        elif self.user.first_name:
            initials = self.user.first_name[0].upper()
        elif self.user.username:
            initials = self.user.username[0].upper()
        else:
            initials = "U"

        # Generate a color based on user ID for consistency
        colors = [
            "3B82F6",  # Blue
            "EF4444",  # Red
            "10B981",  # Green
            "F59E0B",  # Yellow
            "8B5CF6",  # Purple
            "06B6D4",  # Cyan
            "EC4899",  # Pink
            "84CC16",  # Lime
        ]
        color = colors[self.user.id % len(colors)]

        # Return a generated avatar URL using UI Avatars or similar service
        return f"https://ui-avatars.com/api/?name={initials}&background={color}&color=ffffff&size=200&bold=true"


class Activity(models.Model):
    """User activity log for profile page and notifications"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_set')
    icon = models.CharField(max_length=32, default='activity')
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.text[:30]}... ({self.timestamp})"
