
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Wishlist, WishlistItem
from games.models import Game
from django.urls import reverse


class WishlistModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.game = Game.objects.create(title='Test Game', submitted_by=self.user)

    def test_create_wishlist(self):
        wishlist = Wishlist.objects.create(user=self.user, name='Test Wishlist')
        self.assertEqual(str(wishlist), 'Test Wishlist (testuser)')

    def test_add_game_to_wishlist(self):
        wishlist = Wishlist.objects.create(user=self.user, name='Test Wishlist')
        item = WishlistItem.objects.create(wishlist=wishlist, game=self.game, order=0)
        self.assertEqual(str(item), 'Test Game in Test Wishlist (testuser)')
        self.assertEqual(wishlist.items.count(), 1)

    def test_wishlist_unique_per_user(self):
        Wishlist.objects.create(user=self.user, name='Unique Wishlist')
        with self.assertRaises(Exception):
            Wishlist.objects.create(user=self.user, name='Unique Wishlist')


class WishlistViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.game = Game.objects.create(title='Test Game', submitted_by=self.user)
        self.wishlist = Wishlist.objects.create(user=self.user, name='Test Wishlist')
        self.item = WishlistItem.objects.create(wishlist=self.wishlist, game=self.game, order=0)

    def test_wishlist_list_view_requires_login(self):
        response = self.client.get(reverse('wishlist_list'))
        self.assertNotEqual(response.status_code, 200)
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('wishlist_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Wishlist')

    def test_wishlist_detail_view(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('wishlist_detail', args=[self.wishlist.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Game')

    def test_wishlist_create_view(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('wishlist_create'), {'name': 'New Wishlist'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Wishlist.objects.filter(name='New Wishlist').exists())

    def test_wishlist_delete_view(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('wishlist_delete', args=[self.wishlist.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Wishlist.objects.filter(pk=self.wishlist.pk).exists())

    def test_wishlist_item_delete_view(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('wishlist_item_delete', args=[self.item.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(WishlistItem.objects.filter(pk=self.item.pk).exists())

    def test_wishlist_item_move_up_down(self):
        self.client.login(username='testuser', password='testpass')
        game2 = Game.objects.create(title='Second Game', submitted_by=self.user)
        item2 = WishlistItem.objects.create(wishlist=self.wishlist, game=game2, order=1)
        response = self.client.post(reverse('wishlist_item_move', args=[self.item.pk, 'down']))
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        item2.refresh_from_db()
        self.assertEqual(self.item.order, 1)
        self.assertEqual(item2.order, 0)
        response = self.client.post(reverse('wishlist_item_move', args=[self.item.pk, 'up']))
        self.item.refresh_from_db()
        item2.refresh_from_db()
        self.assertEqual(self.item.order, 0)
        self.assertEqual(item2.order, 1)

    def test_cannot_access_other_users_wishlist(self):
        other_user = User.objects.create_user(username='otheruser', password='otherpass')
        other_wishlist = Wishlist.objects.create(user=other_user, name='Other Wishlist')
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('wishlist_detail', args=[other_wishlist.pk]))
        self.assertEqual(response.status_code, 302)

    def test_cannot_delete_other_users_wishlist(self):
        other_user = User.objects.create_user(username='otheruser', password='otherpass')
        other_wishlist = Wishlist.objects.create(user=other_user, name='Other Wishlist')
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('wishlist_delete', args=[other_wishlist.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Wishlist.objects.filter(pk=other_wishlist.pk).exists())

    def test_cannot_delete_other_users_wishlist_item(self):
        other_user = User.objects.create_user(username='otheruser', password='otherpass')
        other_wishlist = Wishlist.objects.create(user=other_user, name='Other Wishlist')
        other_game = Game.objects.create(title='Other Game', submitted_by=other_user)
        other_item = WishlistItem.objects.create(wishlist=other_wishlist, game=other_game, order=0)
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('wishlist_item_delete', args=[other_item.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(WishlistItem.objects.filter(pk=other_item.pk).exists())

    def test_404_for_nonexistent_wishlist(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('wishlist_detail', args=[9999]))
        self.assertEqual(response.status_code, 302)

    def test_404_for_nonexistent_wishlist_item(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('wishlist_item_delete', args=[9999]))
        self.assertEqual(response.status_code, 302)
