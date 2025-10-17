from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import HelpCategory, HelpProvider, InitialField, CustomField, HelpRequest


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = '/register/'
        self.login_url = '/login/'
        
    def test_user_registration(self):
        """Тест регистрации пользователя"""
        category = HelpCategory.objects.create(name="Test Category")
        
        response = self.client.post(self.register_url, {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'help_category': category.id,
        })
        
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_user_login(self):
        """Тест входа пользователя"""
        User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123',
        })
        
        self.assertRedirects(response, '/dashboard/')
    
    def test_user_logout(self):
        """Тест выхода пользователя"""
        User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/logout/')
        
        self.assertRedirects(response, '/')


class HelpRequestTests(TestCase):
    def setUp(self):
        self.category = HelpCategory.objects.create(name="Test Category")
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_create_help_request(self):
        """Тест создания запроса помощи"""
        InitialField.objects.create(
            name="First Name",
            field_key="first_name",
            field_type="text",
            required=True
        )
        
        response = self.client.post('/request/create/', {
            'help_category': self.category.id,
            'first_name': 'John',
            'last_name': 'Doe',
            'idnp': '12345678901',
            'email': 'john@example.com',
        })
        
        self.assertTrue(HelpRequest.objects.filter(help_category=self.category).exists())


class PermissionTests(TestCase):
    def setUp(self):
        self.category = HelpCategory.objects.create(name="Medical")
        
        self.provider_user = User.objects.create_user(
            username='provider',
            password='pass123'
        )
        self.provider = HelpProvider.objects.create(
            user=self.provider_user,
            help_category=self.category
        )
        
        self.request = HelpRequest.objects.create(
            help_category=self.category,
            initial_data={'name': 'John'},
            custom_data={}
        )
    
    def test_provider_can_edit_own_category(self):
        """Тест что поставщик может редактировать свою категорию"""
        self.client.login(username='provider', password='pass123')
        response = self.client.get(f'/request/{self.request.id}/edit/')
        
        self.assertEqual(response.status_code, 200)