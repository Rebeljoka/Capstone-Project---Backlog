from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Game, Tag, Genre


class GameModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.tag = Tag.objects.create(name='Action')
        self.genre = Genre.objects.create(genre='RPG')

    def test_create_game(self):
        game = Game.objects.create(
            submitted_by=self.user,
            title='Test Game',
            image='test.jpg',
            short_description='Short',
            long_description='Long',
            developer='Dev',
            age_rating='E',
            platform='PC',
        )
        game.tags.add(self.tag)
        game.genres.add(self.genre)
        self.assertEqual(str(game), 'Test Game')
        self.assertIn(self.tag, game.tags.all())
        self.assertIn(self.genre, game.genres.all())

    def test_tag_str(self):
        self.assertEqual(str(self.tag), 'Action')

    def test_genre_str(self):
        self.assertEqual(str(self.genre), 'RPG')


class GameViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.genre = Genre.objects.create(genre='RPG')
        self.tag = Tag.objects.create(name='Action')
        self.game = Game.objects.create(
            submitted_by=self.user,
            title='Test Game',
            image='test.jpg',
            short_description='Short',
            long_description='Long',
            developer='Dev',
            age_rating='E',
            platform='PC',
        )
        self.game.tags.add(self.tag)
        self.game.genres.add(self.genre)

    def test_game_list_filter_by_genre(self):
        response = self.client.get(reverse('game_list') + f'?genre={self.genre.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Game')

    def test_game_list_filter_by_tag(self):
        response = self.client.get(reverse('game_list') + f'?tag={self.tag.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Game')

    def test_game_detail_404(self):
        response = self.client.get(reverse('game_detail', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_genre_games_404(self):
        response = self.client.get(reverse('genre_games', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_game_list_no_games(self):
        Game.objects.all().delete()
        response = self.client.get(reverse('game_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test Game')


class GameModelEdgeCaseTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='edgeuser', password='edgepass')
        self.genre = Genre.objects.create(genre='Strategy')
        self.tag = Tag.objects.create(name='Adventure')
        self.game = Game.objects.create(submitted_by=self.user, title='Test Game')
        self.game.genres.add(self.genre)
        self.game.tags.add(self.tag)
        # Optionally keep extra genres/tags for other tests
        self.tag2 = Tag.objects.create(name='Puzzle')
        self.genre2 = Genre.objects.create(genre='Shooter')

    def test_create_game_multiple_tags_genres(self):
        game = Game.objects.create(
            submitted_by=self.user,
            title='Multi Game',
        )
        game.tags.set([self.tag, self.tag2])
        game.genres.set([self.genre, self.genre2])
        self.assertEqual(game.tags.count(), 2)
        self.assertEqual(game.genres.count(), 2)

    def test_delete_genre_removes_from_game(self):
        game = Game.objects.create(submitted_by=self.user, title='Genre Test')
        game.genres.add(self.genre)
        self.genre.delete()
        game.refresh_from_db()
        self.assertEqual(game.genres.count(), 0)

    def test_delete_tag_removes_from_game(self):
        game = Game.objects.create(submitted_by=self.user, title='Tag Test')
        game.tags.add(self.tag)
        self.tag.delete()
        game.refresh_from_db()
        self.assertEqual(game.tags.count(), 0)

    def test_game_fields(self):
        game = Game.objects.create(
            submitted_by=self.user,
            title='Field Test',
            image='img.png',
            short_description='Short desc',
            long_description='Long desc',
            release_date='2025-09-29',
            developer='DevName',
            age_rating='T',
            platform='Switch',
        )
        self.assertEqual(game.image, 'img.png')
        self.assertEqual(game.short_description, 'Short desc')
        self.assertEqual(game.long_description, 'Long desc')
        self.assertEqual(str(game.release_date), '2025-09-29')
        self.assertEqual(game.developer, 'DevName')
        self.assertEqual(game.age_rating, 'T')
        self.assertEqual(game.platform, 'Switch')

    def test_game_list_view(self):
        response = self.client.get(reverse('game_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Game')

    def test_game_detail_view(self):
        response = self.client.get(reverse('game_detail', args=[self.game.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Game')

    def test_genre_games_view(self):
        response = self.client.get(reverse('genre_games', args=[self.genre.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Game')
