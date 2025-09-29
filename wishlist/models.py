from django.db import models
from django.contrib.auth.models import User
from games.models import Game


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'game')
        ordering = ['order', 'added_on']

    def __str__(self):
        return f"{self.game.title} in {self.wishlist.name} ({self.wishlist.user.username})"
        return f"{self.user.username} - {self.game.title}"
