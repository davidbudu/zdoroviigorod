from django.core.management.base import BaseCommand
from help.models import InitialField

class Command(BaseCommand):
    help = 'Populate initial fields for all help requests'

    def handle(self, *args, **options):
        fields_data = [
            {'name': 'First Name', 'field_key': 'first_name', 'field_type': 'text', 'required': True, 'order': 1},
            {'name': 'Last Name', 'field_key': 'last_name', 'field_type': 'text', 'required': True, 'order': 2},
            {'name': 'IDNP', 'field_key': 'idnp', 'field_type': 'number', 'required': True, 'order': 3},
            {'name': 'Email', 'field_key': 'email', 'field_type': 'email', 'required': True, 'order': 4},
            {'name': 'Phone', 'field_key': 'phone', 'field_type': 'phone', 'required': False, 'order': 5},
        ]
        
        for field_data in fields_data:
            InitialField.objects.get_or_create(
                field_key=field_data['field_key'],
                defaults=field_data
            )
        
        self.stdout.write(self.style.SUCCESS('Initial fields populated successfully'))
