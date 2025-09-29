from django.test import TestCase
from django.contrib.auth.models import User
from .models import Wishlist, WishlistItem
from games.models import Game
from django.urls import reverse


class WishlistModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.game = Game.objects.create(title='Test Game')

    # Test that Wishlist string representation includes name and username
    def test_create_wishlist(self):
        wishlist = Wishlist.objects.create(user=self.user, name='Test Wishlist')
        self.assertEqual(str(wishlist), 'Test Wishlist (testuser)')

    # Test that adding a game to a wishlist works and string representation is correct
    def test_add_game_to_wishlist(self):
        wishlist = Wishlist.objects.create(user=self.user, name='Test Wishlist')
        item = WishlistItem.objects.create(wishlist=wishlist, game=self.game, order=0)
        self.assertEqual(str(item), 'Test Game in Test Wishlist (testuser)')
        self.assertEqual(wishlist.items.count(), 1)


class WishlistViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.game = Game.objects.create(title='Test Game')
        self.wishlist = Wishlist.objects.create(user=self.user, name='Test Wishlist')
        self.item = WishlistItem.objects.create(wishlist=self.wishlist, game=self.game, order=0)

    # Test that the wishlist list view requires login and displays wishlists for the user
    def test_wishlist_list_view_requires_login(self):
        response = self.client.get(reverse('wishlist_list'))
        self.assertNotEqual(response.status_code, 200)
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('wishlist_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Wishlist')

    # Test that the wishlist detail view displays the correct games
    def test_wishlist_detail_view(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('wishlist_detail', args=[self.wishlist.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Game')

    # Test that a user can create a wishlist via the view
    def test_wishlist_create_view(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('wishlist_create'), {'name': 'New Wishlist'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Wishlist.objects.filter(name='New Wishlist').exists())

    # Test that a user can delete their own wishlist
    def test_wishlist_delete_view(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('wishlist_delete', args=[self.wishlist.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Wishlist.objects.filter(pk=self.wishlist.pk).exists())

    # Test that a user can delete a game from their wishlist
    def test_wishlist_item_delete_view(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('wishlist_item_delete', args=[self.item.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(WishlistItem.objects.filter(pk=self.item.pk).exists())

    # Test that a user can move games up and down in their wishlist
    def test_wishlist_item_move_up_down(self):
        self.client.login(username='testuser', password='testpass')
        # Add a second item
        game2 = Game.objects.create(title='Second Game')
        item2 = WishlistItem.objects.create(wishlist=self.wishlist, game=game2, order=1)
        # Move down
        response = self.client.post(reverse('wishlist_item_move', args=[self.item.pk, 'down']))
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        item2.refresh_from_db()
        self.assertEqual(self.item.order, 1)
        self.assertEqual(item2.order, 0)
        # Move up
        response = self.client.post(reverse('wishlist_item_move', args=[self.item.pk, 'up']))
        self.item.refresh_from_db()
        item2.refresh_from_db()
        self.assertEqual(self.item.order, 0)
        self.assertEqual(item2.order, 1)

    # Test that a user cannot access another user's wishlist
    def test_cannot_access_other_users_wishlist(self):
        other_user = User.objects.create_user(username='otheruser', password='otherpass')
        other_wishlist = Wishlist.objects.create(user=other_user, name='Other Wishlist')
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('wishlist_detail', args=[other_wishlist.pk]))
        self.assertEqual(response.status_code, 302)  # Should redirect with error message

    # Test that a user cannot delete another user's wishlist
    def test_cannot_delete_other_users_wishlist(self):
        other_user = User.objects.create_user(username='otheruser', password='otherpass')
        other_wishlist = Wishlist.objects.create(user=other_user, name='Other Wishlist')
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('wishlist_delete', args=[other_wishlist.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Wishlist.objects.filter(pk=other_wishlist.pk).exists())

    # Test that a user cannot delete another user's wishlist item
    def test_cannot_delete_other_users_wishlist_item(self):
        other_user = User.objects.create_user(username='otheruser', password='otherpass')
        other_wishlist = Wishlist.objects.create(user=other_user, name='Other Wishlist')
        other_game = Game.objects.create(title='Other Game')
        other_item = WishlistItem.objects.create(wishlist=other_wishlist, game=other_game, order=0)
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('wishlist_item_delete', args=[other_item.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(WishlistItem.objects.filter(pk=other_item.pk).exists())

    # Test that accessing a non-existent wishlist redirects with an error
    def test_404_for_nonexistent_wishlist(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('wishlist_detail', args=[9999]))
        self.assertEqual(response.status_code, 302)  # Should redirect with error message

    # Test that deleting a non-existent wishlist item redirects with an error
    def test_404_for_nonexistent_wishlist_item(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('wishlist_item_delete', args=[9999]))
        self.assertEqual(response.status_code, 302)  # Should redirect with error message
