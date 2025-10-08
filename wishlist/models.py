from django.db import models
from django.contrib.auth.models import User
from games.models import Game


class Wishlist(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wishlists',
    )
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        username = self.user.username
        return f"{self.name} ({username})"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name='items',
    )
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0, null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'game')
        ordering = ['order', 'added_on']

    def __str__(self):
        wishlist_name = self.wishlist.name
        username = self.wishlist.user.username
        game_title = self.game.title
        return f"{game_title} in {wishlist_name} ({username})"
