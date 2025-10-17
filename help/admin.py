from django.contrib import admin
from .models import HelpCategory, BaseField, CustomField, HelpProvider, Person, PersonHelpService

@admin.register(HelpCategory)
class HelpCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'description', 'icon']
    list_editable = ['order']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('Informații de bază', {
            'fields': ('name', 'description', 'icon')
        }),
        ('Setări', {
            'fields': ('order',)
        }),
    )


@admin.register(BaseField)
class BaseFieldAdmin(admin.ModelAdmin):
    list_display = ['name', 'field_key', 'field_type', 'required', 'show_in_list', 'order', 'has_choices']
    list_editable = ['required', 'show_in_list', 'order']
    list_filter = ['field_type', 'required', 'show_in_list']
    search_fields = ['name', 'field_key']
    ordering = ['order']
    
    fieldsets = (
        ('Informații de bază', {
            'fields': ('name', 'field_key', 'field_type')
        }),
        ('Setări câmp', {
            'fields': ('required', 'show_in_list', 'placeholder', 'order')
        }),
        ('Variante de alegere', {
            'fields': ('choices',),
            'description': 'Pentru câmpuri tip "Alegere din listă" - introduceți variantele separate prin virgulă'
        }),
    )
    
    def has_choices(self, obj):
        """Показывает есть ли варианты выбора"""
        return bool(obj.choices)
    has_choices.short_description = 'Are variante'
    has_choices.boolean = True
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'choices':
            formfield.help_text = 'Variante separate prin virgulă pentru câmpuri tip "Alegere din listă". Exemplu: Opțiune1,Opțiune2,Opțiune3'
            formfield.widget.attrs['rows'] = 4
        return formfield


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    list_display = ['name', 'help_category', 'field_type', 'required', 'order', 'has_choices']
    list_filter = ['help_category', 'field_type', 'required']
    list_editable = ['required', 'order']
    search_fields = ['name', 'field_key']
    ordering = ['help_category', 'order']
    
    fieldsets = (
        ('Informații de bază', {
            'fields': ('help_category', 'name', 'field_key', 'field_type')
        }),
        ('Setări câmp', {
            'fields': ('required', 'placeholder', 'order')
        }),
        ('Variante de alegere', {
            'fields': ('choices',),
            'description': 'Pentru câmpuri cu alegere - introduceți variantele separate prin virgulă'
        }),
    )
    
    def has_choices(self, obj):
        """Показывает есть ли варианты выбора"""
        return bool(obj.choices)
    has_choices.short_description = 'Are variante'
    has_choices.boolean = True
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'choices':
            formfield.help_text = 'Variante separate prin virgulă pentru câmpuri cu alegere. Exemplu: Da,Nu sau Variantă1,Variantă2,Variantă3'
            formfield.widget.attrs['rows'] = 4
        return formfield


@admin.register(HelpProvider)
class HelpProviderAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_categories', 'created_at']
    list_filter = ['help_categories', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    filter_horizontal = ['help_categories']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Utilizator', {
            'fields': ('user',)
        }),
        ('Servicii oferite', {
            'fields': ('help_categories', 'bio')
        }),
        ('Informații sistem', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_categories(self, obj):
        return ', '.join([c.name for c in obj.help_categories.all()])
    get_categories.short_description = 'Tipuri de ajutor'


class PersonHelpServiceInline(admin.TabularInline):
    model = PersonHelpService
    extra = 1
    fields = ['help_category', 'status', 'notes', 'added_by', 'created_at']
    readonly_fields = ['added_by', 'created_at']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "added_by":
            kwargs["queryset"] = HelpProvider.objects.select_related('user')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_name', 'get_email', 'get_phone', 'get_services_count', 'added_by', 'created_at']
    list_filter = ['created_at', 'added_by', 'help_services__help_category']
    search_fields = ['base_data']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PersonHelpServiceInline]
    
    fieldsets = (
        ('Informații de bază', {
            'fields': ('base_data', 'added_by')
        }),
        ('Informații sistem', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_name(self, obj):
        first_name = obj.base_data.get('first_name', '')
        last_name = obj.base_data.get('last_name', '')
        return f"{first_name} {last_name}".strip() or f'Persoană #{obj.id}'
    get_name.short_description = 'Nume'
    
    def get_email(self, obj):
        return obj.base_data.get('email', '-')
    get_email.short_description = 'Email'
    
    def get_phone(self, obj):
        return obj.base_data.get('phone', '-')
    get_phone.short_description = 'Telefon'
    
    def get_services_count(self, obj):
        return obj.help_services.count()
    get_services_count.short_description = 'Număr servicii'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('help_services__help_category')


@admin.register(PersonHelpService)
class PersonHelpServiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_person_name', 'help_category', 'status', 'added_by', 'created_at', 'updated_at']
    list_filter = ['help_category', 'status', 'created_at', 'added_by']
    search_fields = ['person__base_data', 'notes', 'custom_data']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['status']
    
    fieldsets = (
        ('Informații de bază', {
            'fields': ('person', 'help_category', 'status')
        }),
        ('Date suplimentare', {
            'fields': ('custom_data', 'notes')
        }),
        ('Informații despre adăugare', {
            'fields': ('added_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_person_name(self, obj):
        return str(obj.person)
    get_person_name.short_description = 'Persoană'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('person', 'help_category', 'added_by__user')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "person":
            kwargs["queryset"] = Person.objects.all().order_by('-created_at')
        if db_field.name == "added_by":
            kwargs["queryset"] = HelpProvider.objects.select_related('user')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# Configurare titluri panou admin
admin.site.site_header = 'Sistem de evidență al ajutorului'
admin.site.site_title = 'Panou de administrare'
admin.site.index_title = 'Gestionare sistem'