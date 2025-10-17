from django.db import models
from django.contrib.auth.models import User


class HelpCategory(models.Model):
    """Tip de ajutor/serviciu"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Nume')
    description = models.TextField(blank=True, verbose_name='Descriere')
    icon = models.CharField(max_length=50, default='help', verbose_name='Pictogramă')
    order = models.IntegerField(default=0, verbose_name='Ordine')

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Tip de ajutor'
        verbose_name_plural = 'Tipuri de ajutor'

    def __str__(self):
        return self.name


class BaseField(models.Model):
    """Câmpuri de bază pentru toate persoanele (configurabile prin admin)"""
    FIELD_TYPES = [
        ('text', 'Text'),
        ('email', 'Email'),
        ('phone', 'Telefon'),
        ('number', 'Număr'),
        ('date', 'Dată'),
        ('textarea', 'Text pe mai multe rânduri'),
        ('select', 'Alegere din listă'),  # НОВОЕ
    ]

    name = models.CharField(max_length=100, verbose_name='Nume câmp')
    field_key = models.CharField(max_length=50, unique=True, verbose_name='Cheie câmp')
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, verbose_name='Tip câmp')
    required = models.BooleanField(default=True, verbose_name='Obligatoriu')
    order = models.IntegerField(default=0, verbose_name='Ordine')
    placeholder = models.CharField(max_length=200, blank=True, verbose_name='Sugestie')
    show_in_list = models.BooleanField(default=True, verbose_name='Afișare în listă')
    choices = models.TextField(
        blank=True, 
        help_text='Variante separate prin virgulă pentru câmpuri tip "Alegere din listă"',
        verbose_name='Variante de alegere'
    )  # НОВОЕ

    class Meta:
        ordering = ['order']
        verbose_name = 'Câmp de bază'
        verbose_name_plural = 'Câmpuri de bază'

    def __str__(self):
        return self.name
    
    def get_choices_list(self):
        """Возвращает список вариантов выбора"""
        if self.choices:
            return [c.strip() for c in self.choices.split(',') if c.strip()]
        return []


class CustomField(models.Model):
    """Câmpuri suplimentare pentru un anumit tip de ajutor"""
    FIELD_TYPES = [
        ('text', 'Text'),
        ('textarea', 'Text pe mai multe rânduri'),
        ('email', 'Email'),
        ('phone', 'Telefon'),
        ('number', 'Număr'),
        ('choice', 'Alegere din listă'),
        ('date', 'Dată'),
        ('checkbox', 'Bifa'),
    ]

    help_category = models.ForeignKey(
        HelpCategory, 
        on_delete=models.CASCADE, 
        related_name='custom_fields',
        verbose_name='Tip de ajutor'
    )
    name = models.CharField(max_length=100, verbose_name='Nume câmp')
    field_key = models.CharField(max_length=50, verbose_name='Cheie câmp')
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, verbose_name='Tip câmp')
    required = models.BooleanField(default=False, verbose_name='Obligatoriu')
    order = models.IntegerField(default=0, verbose_name='Ordine')
    placeholder = models.CharField(max_length=200, blank=True, verbose_name='Sugestie')
    choices = models.TextField(
        blank=True, 
        help_text='Variante separate prin virgulă pentru câmpuri cu alegere',
        verbose_name='Variante de alegere'
    )

    class Meta:
        ordering = ['order']
        unique_together = ['help_category', 'field_key']
        verbose_name = 'Câmp suplimentar'
        verbose_name_plural = 'Câmpuri suplimentare'

    def __str__(self):
        return f"{self.help_category.name} - {self.name}"
    
    def get_choices_list(self):
        """Возвращает список вариантов выбора"""
        if self.choices:
            return [c.strip() for c in self.choices.split(',') if c.strip()]
        return []


# Остальные модели без изменений...
class HelpProvider(models.Model):
    """Furnizor de ajutor (utilizator al sistemului)"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Utilizator')
    help_categories = models.ManyToManyField(
        HelpCategory, 
        related_name='providers',
        verbose_name='Tipuri de ajutor oferite'
    )
    bio = models.TextField(blank=True, verbose_name='Despre mine')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data înregistrării')

    class Meta:
        verbose_name = 'Furnizor de ajutor'
        verbose_name_plural = 'Furnizori de ajutor'

    def __str__(self):
        categories = ', '.join([c.name for c in self.help_categories.all()])
        return f"{self.user.username} ({categories})"

    def can_edit_category(self, category):
        """Verifică dacă poate edita acest tip de ajutor"""
        return self.help_categories.filter(id=category.id).exists()


class Person(models.Model):
    """Persoană în baza de date (client)"""
    base_data = models.JSONField(default=dict, verbose_name='Date de bază')
    added_by = models.ForeignKey(
        HelpProvider, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='added_people',
        verbose_name='Adăugat de'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data adăugării')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data actualizării')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Persoană'
        verbose_name_plural = 'Persoane'

    def __str__(self):
        name = self.base_data.get('first_name', '') + ' ' + self.base_data.get('last_name', '')
        return name.strip() or f'Persoană #{self.id}'

    def get_help_services(self):
        """Obține toate tipurile de ajutor pentru această persoană"""
        return self.help_services.all()


class PersonHelpService(models.Model):
    """Legătura persoanei cu tipul de ajutor și date suplimentare"""
    STATUS_CHOICES = [
        ('active', 'Activ'),
        ('completed', 'Finalizat'),
        ('pending', 'În așteptare'),
        ('cancelled', 'Anulat'),
    ]

    person = models.ForeignKey(
        Person, 
        on_delete=models.CASCADE, 
        related_name='help_services',
        verbose_name='Persoană'
    )
    help_category = models.ForeignKey(
        HelpCategory, 
        on_delete=models.PROTECT,
        verbose_name='Tip de ajutor'
    )
    custom_data = models.JSONField(default=dict, verbose_name='Date suplimentare')
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='active',
        verbose_name='Status'
    )
    added_by = models.ForeignKey(
        HelpProvider, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='added_services',
        verbose_name='Serviciu adăugat de'
    )
    notes = models.TextField(blank=True, verbose_name='Notițe')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data adăugării')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data actualizării')

    class Meta:
        ordering = ['-created_at']
        unique_together = ['person', 'help_category']
        verbose_name = 'Serviciu pentru persoană'
        verbose_name_plural = 'Servicii pentru persoane'

    def __str__(self):
        return f"{self.person} - {self.help_category.name}"

    def can_edit(self, provider):
        """Poate furnizorul să editeze acest serviciu"""
        return provider.can_edit_category(self.help_category)