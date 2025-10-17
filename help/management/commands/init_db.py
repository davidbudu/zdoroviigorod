from django.core.management.base import BaseCommand
from help.models import BaseField


class Command(BaseCommand):
    help = 'Import câmpuri de bază din Google Form'

    def handle(self, *args, **options):
        # Câmpurile din Google Form
        fields_data = [
            {
                'name': 'Nume',
                'field_key': 'first_name',
                'field_type': 'text',
                'required': True,
                'show_in_list': True,
                'placeholder': 'Introduceți numele',
                'order': 1
            },
            {
                'name': 'Prenume',
                'field_key': 'last_name',
                'field_type': 'text',
                'required': True,
                'show_in_list': True,
                'placeholder': 'Introduceți prenumele',
                'order': 2
            },
            {
                'name': 'Email',
                'field_key': 'email',
                'field_type': 'email',
                'required': False,
                'show_in_list': True,
                'placeholder': 'exemplu@email.com',
                'order': 3
            },
            {
                'name': 'Telefon',
                'field_key': 'phone',
                'field_type': 'text',
                'required': True,
                'show_in_list': True,
                'placeholder': '+373 XX XXX XXX',
                'order': 4
            },
            {
                'name': 'Sex',
                'field_key': 'gender',
                'field_type': 'select',
                'required': True,
                'show_in_list': True,
                'placeholder': 'Selectați sexul',
                'order': 5,
                'choices': 'Masculin,Feminin'
            },
            {
                'name': 'Locul de trai (oraș, sat, raion)',
                'field_key': 'location',
                'field_type': 'select',
                'required': True,
                'show_in_list': True,
                'placeholder': 'Selectați locul de trai',
                'order': 6,
                'choices': 'Râșcani,Florești,Fălești,Sângerei,Glodeni,Edineț,Ocnița,Telenești,Soroca,Drochia,Bălți,Briceni,Dondușeni,Mun. Bălți/Elizavetovca/Sadovoe,Otaci,Brătușeni'
            },
            {
                'name': 'Numărul de persoane în familie',
                'field_key': 'family_members_count',
                'field_type': 'number',
                'required': True,
                'show_in_list': True,
                'placeholder': 'Introduceți numărul',
                'order': 7
            },
            {
                'name': 'Câți copii (indicați vârsta)',
                'field_key': 'children_ages',
                'field_type': 'textarea',
                'required': True,
                'show_in_list': False,
                'placeholder': 'De exemplu: 5 ani, 10 ani, 15 ani',
                'order': 8
            },
            {
                'name': 'Cetățenie',
                'field_key': 'citizenship',
                'field_type': 'select',
                'required': True,
                'show_in_list': True,
                'placeholder': 'Selectați cetățenia',
                'order': 9,
                'choices': 'Moldova,Ucraina'
            },
            {
                'name': 'Are acte de identitate?',
                'field_key': 'has_identity_documents',
                'field_type': 'select',
                'required': True,
                'show_in_list': True,
                'placeholder': 'Selectați răspunsul',
                'order': 10,
                'choices': 'Da,Nu'
            }
        ]

        created_count = 0
        updated_count = 0

        for field_data in fields_data:
            field, created = BaseField.objects.update_or_create(
                field_key=field_data['field_key'],
                defaults={
                    'name': field_data['name'],
                    'field_type': field_data['field_type'],
                    'required': field_data['required'],
                    'show_in_list': field_data['show_in_list'],
                    'placeholder': field_data.get('placeholder', ''),
                    'choices': field_data.get('choices', ''),
                    'order': field_data['order']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Câmp creat: {field.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Câmp actualizat: {field.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nGata! Creat: {created_count}, Actualizat: {updated_count}'
            )
        )