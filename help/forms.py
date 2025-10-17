from django import forms
from django.contrib.auth.models import User
from .models import HelpProvider, HelpCategory, Person, PersonHelpService, BaseField, CustomField


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Parolă'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label='Confirmați parola'
    )
    help_categories = forms.ModelMultipleChoiceField(
        queryset=HelpCategory.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label='Tipurile de ajutor pe care le oferiți',
        required=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
        labels = {
            'username': 'Nume utilizator',
            'email': 'Email',
            'first_name': 'Prenume',
            'last_name': 'Nume de familie',
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('password_confirm'):
            raise forms.ValidationError("Parolele nu coincid")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            provider = HelpProvider.objects.create(user=user)
            provider.help_categories.set(self.cleaned_data['help_categories'])
        return user


class PersonForm(forms.Form):
    """Formular pentru adăugarea/editarea unei persoane (câmpuri de bază)"""
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
        
        # Adăugăm dinamic câmpurile de bază
        base_fields = BaseField.objects.all().order_by('order')
        for field in base_fields:
            field_class = self._get_field_class(field)
            self.fields[field.field_key] = field_class
            
            # Dacă există instance, completăm valorile inițiale
            if instance:
                self.fields[field.field_key].initial = instance.base_data.get(field.field_key, '')
    
    def _get_field_class(self, field_obj):
        """Creează Django field din BaseField"""
        kwargs = {
            'label': field_obj.name,
            'required': field_obj.required,
        }
        
        if field_obj.placeholder:
            kwargs['widget'] = forms.TextInput(attrs={'placeholder': field_obj.placeholder})
        
        # ОБНОВЛЕНО: добавлена поддержка select
        if field_obj.field_type == 'select':
            choices = [('', '-- Selectați --')]
            choices.extend([(c, c) for c in field_obj.get_choices_list()])
            return forms.ChoiceField(choices=choices, **kwargs)
        elif field_obj.field_type == 'email':
            return forms.EmailField(**kwargs)
        elif field_obj.field_type == 'phone':
            kwargs['widget'] = forms.TextInput(attrs={'placeholder': field_obj.placeholder or '+373...'})
            return forms.CharField(**kwargs)
        elif field_obj.field_type == 'number':
            return forms.IntegerField(**kwargs)
        elif field_obj.field_type == 'date':
            kwargs['widget'] = forms.DateInput(attrs={'type': 'date'})
            return forms.DateField(**kwargs)
        elif field_obj.field_type == 'textarea':
            kwargs['widget'] = forms.Textarea(attrs={'rows': 3})
            return forms.CharField(**kwargs)
        else:  # text
            return forms.CharField(**kwargs)


class PersonHelpServiceForm(forms.Form):
    """Formular pentru adăugarea/editarea unui serviciu pentru o persoană"""
    
    help_category = forms.ModelChoiceField(
        queryset=HelpCategory.objects.all(),
        label='Tipul de ajutor',
        required=True,
        empty_label='-- Selectați tipul de ajutor --'
    )
    
    status = forms.ChoiceField(
        choices=PersonHelpService.STATUS_CHOICES,
        label='Status',
        initial='active'
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Notițe',
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        category = kwargs.pop('category', None)
        instance = kwargs.pop('instance', None)
        can_edit = kwargs.pop('can_edit', True)
        super().__init__(*args, **kwargs)
        
        # Dacă categoria este deja selectată, facem câmpul readonly
        if instance:
            self.fields['help_category'].initial = instance.help_category
            self.fields['help_category'].disabled = True
            self.fields['status'].initial = instance.status
            self.fields['notes'].initial = instance.notes
            category = instance.help_category
        
        # Dacă nu poate edita - facem toate câmpurile readonly
        if not can_edit:
            for field_name in self.fields:
                self.fields[field_name].disabled = True
        
        # Adăugăm dinamic câmpurile personalizate pentru categoria selectată
        if category:
            custom_fields = CustomField.objects.filter(help_category=category).order_by('order')
            for field in custom_fields:
                field_class = self._get_custom_field_class(field)
                self.fields[field.field_key] = field_class
                
                # Completăm valorile dacă există instance
                if instance:
                    self.fields[field.field_key].initial = instance.custom_data.get(field.field_key, '')
                
                # Facem readonly dacă nu poate edita
                if not can_edit:
                    self.fields[field.field_key].disabled = True
    
    def _get_custom_field_class(self, field_obj):
        """Creează Django field din CustomField"""
        kwargs = {
            'label': field_obj.name,
            'required': field_obj.required,
        }
        
        if field_obj.placeholder:
            kwargs['widget'] = forms.TextInput(attrs={'placeholder': field_obj.placeholder})
        
        if field_obj.field_type == 'email':
            return forms.EmailField(**kwargs)
        elif field_obj.field_type == 'phone':
            kwargs['widget'] = forms.TextInput(attrs={'placeholder': field_obj.placeholder or '+373...'})
            return forms.CharField(**kwargs)
        elif field_obj.field_type == 'number':
            return forms.IntegerField(**kwargs)
        elif field_obj.field_type == 'date':
            kwargs['widget'] = forms.DateInput(attrs={'type': 'date'})
            return forms.DateField(**kwargs)
        elif field_obj.field_type == 'textarea':
            kwargs['widget'] = forms.Textarea(attrs={'rows': 3})
            return forms.CharField(**kwargs)
        elif field_obj.field_type == 'checkbox':
            return forms.BooleanField(**kwargs)
        elif field_obj.field_type == 'choice':
            choices = [('', '-- Selectați --')]
            choices.extend([(c, c) for c in field_obj.get_choices_list()])
            return forms.ChoiceField(choices=choices, **kwargs)
        else:  # text
            return forms.CharField(**kwargs)


class PersonSearchForm(forms.Form):
    """Formular pentru căutarea și filtrarea persoanelor"""
    
    search = forms.CharField(
        required=False,
        label='Căutare',
        widget=forms.TextInput(attrs={'placeholder': 'Căutare după nume, email, telefon...'})
    )
    
    help_category = forms.ModelChoiceField(
        queryset=HelpCategory.objects.all(),
        required=False,
        label='Tipul de ajutor',
        empty_label='-- Toate tipurile --'
    )
    
    status = forms.ChoiceField(
        choices=[('', '-- Toate statusurile --')] + PersonHelpService.STATUS_CHOICES,
        required=False,
        label='Status'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Adăugăm dinamic filtre pentru câmpurile de bază
        base_fields = BaseField.objects.filter(show_in_list=True).order_by('order')
        for field in base_fields:
            if field.field_type in ['text', 'email', 'phone']:
                self.fields[f'filter_{field.field_key}'] = forms.CharField(
                    required=False,
                    label=field.name,
                    widget=forms.TextInput(attrs={'placeholder': f'Filtru după {field.name.lower()}'})
                )