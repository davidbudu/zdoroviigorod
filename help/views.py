import os
import json
from datetime import date, datetime
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.conf import settings

# Импорты для PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Импорты моделей и форм
from .models import (HelpCategory, HelpProvider, Person, PersonHelpService,
                     BaseField, CustomField)
from .forms import RegisterForm, PersonForm, PersonHelpServiceForm, PersonSearchForm


def serialize_data(data):
    """Конвертирует даты в строки для JSON"""
    cleaned_data = {}
    for key, value in data.items():
        if isinstance(value, (date, datetime)):
            cleaned_data[key] = value.isoformat()
        else:
            cleaned_data[key] = value
    return cleaned_data


def index(request):
    """Главная страница"""
    categories = HelpCategory.objects.all()
    total_people = Person.objects.count()
    total_providers = HelpProvider.objects.count()
    
    context = {
        'categories': categories,
        'total_people': total_people,
        'total_providers': total_providers,
    }
    return render(request, 'help/index.html', context)


def register(request):
    """Регистрация поставщика помощи"""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = RegisterForm()
    
    return render(request, 'help/register.html', {'form': form})


def login_view(request):
    """Вход в систему"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    
    return render(request, 'help/login.html')


@login_required
def logout_view(request):
    """Выход из системы"""
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('index')


@login_required
def dashboard(request):
    """Панель управления поставщика"""
    try:
        provider = HelpProvider.objects.get(user=request.user)
    except HelpProvider.DoesNotExist:
        messages.error(request, 'Вы не зарегистрированы как поставщик помощи')
        return redirect('index')
    
    my_people = Person.objects.filter(added_by=provider)
    my_categories = provider.help_categories.all()
    recent_people = my_people.order_by('-created_at')[:5]
    
    services_stats = []
    for category in my_categories:
        count = PersonHelpService.objects.filter(
            help_category=category,
            added_by=provider
        ).count()
        services_stats.append({
            'category': category,
            'count': count
        })
    
    context = {
        'provider': provider,
        'total_people': my_people.count(),
        'total_services': PersonHelpService.objects.filter(added_by=provider).count(),
        'recent_people': recent_people,
        'services_stats': services_stats,
        'my_categories': my_categories,
    }
    return render(request, 'help/dashboard.html', context)


@login_required
def people_list(request):
    """Список всех людей с продвинутой фильтрацией"""
    try:
        provider = HelpProvider.objects.get(user=request.user)
    except HelpProvider.DoesNotExist:
        messages.error(request, 'Nu sunteți înregistrat ca furnizor de ajutor')
        return redirect('index')
    
    people = Person.objects.all().prefetch_related('help_services__help_category')
    search_form = PersonSearchForm(request.GET)
    
    # Обработка экспорта в CSV
    if request.GET.get('export') == 'csv':
        return export_people_csv(people, request)
    
    if search_form.is_valid():
        # Общий поиск по всем полям
        search = search_form.cleaned_data.get('search')
        if search:
            q_objects = Q()
            # Поиск по базовым полям
            base_fields = BaseField.objects.all()
            for field in base_fields:
                q_objects |= Q(**{f'base_data__{field.field_key}__icontains': search})
            people = people.filter(q_objects)
        
        # Фильтр по категории помощи
        help_category = search_form.cleaned_data.get('help_category')
        if help_category:
            people = people.filter(help_services__help_category=help_category).distinct()
        
        # Фильтр по статусу
        status = search_form.cleaned_data.get('status')
        if status:
            people = people.filter(help_services__status=status).distinct()
        
        # Фильтры по базовым полям
        base_fields = BaseField.objects.all()
        for field in base_fields:
            filter_key = f'filter_{field.field_key}'
            filter_value = request.GET.get(filter_key)
            
            if filter_value:
                if field.field_type == 'select':
                    # Точное совпадение для select полей
                    people = people.filter(
                        **{f'base_data__{field.field_key}': filter_value}
                    )
                else:
                    # Частичное совпадение для текстовых полей
                    people = people.filter(
                        **{f'base_data__{field.field_key}__icontains': filter_value}
                    )
        
        # Фильтры по кастомным полям категории
        if help_category:
            custom_fields = CustomField.objects.filter(help_category=help_category)
            for field in custom_fields:
                custom_filter_key = f'custom_{field.field_key}'
                custom_filter_value = request.GET.get(custom_filter_key)
                
                if custom_filter_value:
                    # Фильтруем людей, у которых есть эта категория с нужным значением поля
                    people = people.filter(
                        help_services__help_category=help_category,
                        **{f'help_services__custom_data__{field.field_key}__icontains': custom_filter_value}
                    ).distinct()
    
    # Поля для отображения в таблице
    display_fields = BaseField.objects.filter(show_in_list=True).order_by('order')
    
    context = {
        'people': people,
        'search_form': search_form,
        'display_fields': display_fields,
        'provider': provider,
    }
    return render(request, 'help/people_list.html', context)


def export_people_csv(people, request):
    """Экспорт списка людей в CSV"""
    import csv
    from django.utils.encoding import smart_str
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="persoane_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # BOM для правильного отображения в Excel
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # Заголовки
    headers = ['ID', 'Nume complet']
    base_fields = BaseField.objects.filter(show_in_list=True).order_by('order')
    for field in base_fields:
        headers.append(field.name)
    headers.extend(['Număr servicii', 'Adăugat de', 'Data adăugării'])
    
    writer.writerow(headers)
    
    # Данные
    for person in people:
        row = [person.id, str(person)]
        
        for field in base_fields:
            value = person.base_data.get(field.field_key, '')
            row.append(smart_str(value))
        
        row.append(person.help_services.count())
        row.append(person.added_by.user.username if person.added_by else '-')
        row.append(person.created_at.strftime('%d.%m.%Y %H:%M'))
        
        writer.writerow(row)
    
    return response


@login_required
def person_detail(request, person_id):
    """Детальная информация о человеке"""
    try:
        provider = HelpProvider.objects.get(user=request.user)
    except HelpProvider.DoesNotExist:
        messages.error(request, 'Вы не зарегистрированы как поставщик помощи')
        return redirect('index')
    
    person = get_object_or_404(Person, id=person_id)
    services = person.help_services.all().select_related('help_category', 'added_by')
    
    editable_services = []
    readonly_services = []
    
    for service in services:
        if provider.can_edit_category(service.help_category):
            editable_services.append(service)
        else:
            readonly_services.append(service)
    
    base_fields = BaseField.objects.all().order_by('order')
    
    context = {
        'person': person,
        'provider': provider,
        'editable_services': editable_services,
        'readonly_services': readonly_services,
        'base_fields': base_fields,
    }
    return render(request, 'help/person_detail.html', context)


@login_required
def person_add(request):
    """Добавление нового человека"""
    try:
        provider = HelpProvider.objects.get(user=request.user)
    except HelpProvider.DoesNotExist:
        messages.error(request, 'Вы не зарегистрированы как поставщик помощи')
        return redirect('index')
    
    if request.method == 'POST':
        form = PersonForm(request.POST)
        if form.is_valid():
            # Конвертируем даты в строки для JSON
            cleaned_data = serialize_data(form.cleaned_data)
            
            person = Person.objects.create(
                base_data=cleaned_data,
                added_by=provider
            )
            messages.success(request, 'Человек успешно добавлен!')
            return redirect('person_detail', person_id=person.id)
    else:
        form = PersonForm()
    
    context = {
        'form': form,
        'provider': provider,
        'is_edit': False,
    }
    return render(request, 'help/person_form.html', context)


@login_required
def person_edit(request, person_id):
    """Редактирование базовых данных человека"""
    try:
        provider = HelpProvider.objects.get(user=request.user)
    except HelpProvider.DoesNotExist:
        messages.error(request, 'Вы не зарегистрированы как поставщик помощи')
        return redirect('index')
    
    person = get_object_or_404(Person, id=person_id)
    
    if request.method == 'POST':
        form = PersonForm(request.POST, instance=person)
        if form.is_valid():
            # Конвертируем даты в строки для JSON
            cleaned_data = serialize_data(form.cleaned_data)
            
            person.base_data = cleaned_data
            person.save()
            messages.success(request, 'Данные обновлены!')
            return redirect('person_detail', person_id=person.id)
    else:
        form = PersonForm(instance=person)
    
    context = {
        'form': form,
        'person': person,
        'provider': provider,
        'is_edit': True,
    }
    return render(request, 'help/person_form.html', context)


@login_required
def service_add(request, person_id):
    """Добавление услуги к человеку"""
    try:
        provider = HelpProvider.objects.get(user=request.user)
    except HelpProvider.DoesNotExist:
        messages.error(request, 'Вы не зарегистрированы как поставщик помощи')
        return redirect('index')
    
    person = get_object_or_404(Person, id=person_id)
    
    if request.method == 'POST':
        category_id = request.POST.get('help_category')
        if not category_id:
            messages.error(request, 'Выберите тип помощи')
            return redirect('service_add', person_id=person.id)
        
        category = get_object_or_404(HelpCategory, id=category_id)
        can_edit = provider.can_edit_category(category)
        
        if not can_edit:
            messages.error(request, 'Вы не предоставляете эту услугу')
            return redirect('person_detail', person_id=person.id)
        
        form = PersonHelpServiceForm(
            request.POST,
            category=category,
            can_edit=can_edit
        )
        
        if form.is_valid():
            existing = PersonHelpService.objects.filter(
                person=person,
                help_category=category
            ).first()
            
            if existing:
                messages.error(request, 'Эта услуга уже добавлена для данного человека')
                return redirect('person_detail', person_id=person.id)
            
            custom_data = {}
            for key, value in form.cleaned_data.items():
                if key not in ['help_category', 'status', 'notes']:
                    # Конвертируем даты в строки
                    if isinstance(value, (date, datetime)):
                        custom_data[key] = value.isoformat()
                    else:
                        custom_data[key] = value
            
            service = PersonHelpService.objects.create(
                person=person,
                help_category=category,
                custom_data=custom_data,
                status=form.cleaned_data['status'],
                notes=form.cleaned_data['notes'],
                added_by=provider
            )
            
            messages.success(request, f'Услуга "{category.name}" добавлена!')
            return redirect('person_detail', person_id=person.id)
    else:
        form = PersonHelpServiceForm()
    
    available_categories = provider.help_categories.all()
    
    context = {
        'form': form,
        'person': person,
        'provider': provider,
        'categories': available_categories,
        'is_edit': False,
        'can_edit': True,
    }
    return render(request, 'help/service_form.html', context)


@login_required
def service_edit(request, service_id):
    """Редактирование услуги"""
    try:
        provider = HelpProvider.objects.get(user=request.user)
    except HelpProvider.DoesNotExist:
        messages.error(request, 'Вы не зарегистрированы как поставщик помощи')
        return redirect('index')
    
    service = get_object_or_404(PersonHelpService, id=service_id)
    can_edit = provider.can_edit_category(service.help_category)
    
    if request.method == 'POST':
        if not can_edit:
            messages.error(request, 'У вас нет прав на редактирование этой услуги')
            return redirect('person_detail', person_id=service.person.id)
        
        form = PersonHelpServiceForm(
            request.POST,
            category=service.help_category,
            instance=service,
            can_edit=can_edit
        )
        
        if form.is_valid():
            custom_data = {}
            for key, value in form.cleaned_data.items():
                if key not in ['help_category', 'status', 'notes']:
                    # Конвертируем даты в строки
                    if isinstance(value, (date, datetime)):
                        custom_data[key] = value.isoformat()
                    else:
                        custom_data[key] = value
            
            service.custom_data = custom_data
            service.status = form.cleaned_data['status']
            service.notes = form.cleaned_data['notes']
            service.save()
            
            messages.success(request, 'Услуга обновлена!')
            return redirect('person_detail', person_id=service.person.id)
    else:
        form = PersonHelpServiceForm(
            category=service.help_category,
            instance=service,
            can_edit=can_edit
        )
    
    context = {
        'form': form,
        'service': service,
        'person': service.person,
        'provider': provider,
        'can_edit': can_edit,
        'is_edit': True,
    }
    return render(request, 'help/service_form.html', context)


@login_required
def get_category_fields(request, category_id):
    """API для получения полей категории (для AJAX)"""
    try:
        category = HelpCategory.objects.get(id=category_id)
        fields = []
        
        for field in category.custom_fields.all().order_by('order'):
            field_data = {
                'name': field.name,
                'field_key': field.field_key,
                'field_type': field.field_type,
                'required': field.required,
                'placeholder': field.placeholder,
            }
            
            if field.field_type == 'choice':
                field_data['choices'] = [c.strip() for c in field.choices.split(',')]
            
            fields.append(field_data)
        
        return JsonResponse({'fields': fields})
    except HelpCategory.DoesNotExist:
        return JsonResponse({'error': 'Категория не найдена'}, status=404)


def register_fonts():
    """Регистрация шрифтов с поддержкой кириллицы"""
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    
    # Путь к папке со шрифтами
    fonts_dir = os.path.join(settings.BASE_DIR, 'fonts')
    
    try:
        # Пробуем загрузить DejaVu из локальной папки
        dejavu_path = os.path.join(fonts_dir, 'DejaVuSans.ttf')
        dejavu_bold_path = os.path.join(fonts_dir, 'DejaVuSans-Bold.ttf')
        
        if os.path.exists(dejavu_path):
            pdfmetrics.registerFont(TTFont('DejaVuSans', dejavu_path))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', dejavu_bold_path))
            return 'DejaVuSans', 'DejaVuSans-Bold'
    except Exception as e:
        print(f"Ошибка загрузки DejaVu: {e}")
    
    try:
        # Альтернатива - попробуем найти системные шрифты
        import matplotlib.font_manager as fm
        fonts = fm.findSystemFonts(fontpaths=None, fontext='ttf')
        
        # Ищем подходящий шрифт с кириллицей
        for font_path in fonts:
            if 'DejaVu' in font_path or 'Arial' in font_path or 'Liberation' in font_path:
                try:
                    font_name = os.path.basename(font_path).replace('.ttf', '')
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    return font_name, font_name
                except:
                    continue
    except:
        pass
    
    # Последний вариант - используем Helvetica (без кириллицы)
    print("ВНИМАНИЕ: Шрифты с кириллицей не найдены. Используется Helvetica.")
    return 'Helvetica', 'Helvetica-Bold'


@login_required
def person_export_pdf(request, person_id):
    """Экспорт данных человека в PDF с поддержкой русского языка"""
    try:
        provider = HelpProvider.objects.get(user=request.user)
    except HelpProvider.DoesNotExist:
        messages.error(request, 'Вы не зарегистрированы как поставщик помощи')
        return redirect('index')
    
    person = get_object_or_404(Person, id=person_id)
    
    # Создаем PDF в памяти
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=2*cm, 
        leftMargin=2*cm, 
        topMargin=2*cm, 
        bottomMargin=2*cm
    )
    
    # Контейнер для элементов
    elements = []
    
    # Регистрируем шрифты
    font_name, font_bold = register_fonts()
    
    # Стили
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=font_bold,
        fontSize=18,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=20,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=font_bold,
        fontSize=14,
        textColor=colors.HexColor('#4b5563'),
        spaceAfter=12,
        spaceBefore=12,
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        textColor=colors.HexColor('#1f2937'),
    )
    
    # Заголовок
    elements.append(Paragraph(f'Информация о человеке #{person.id}', title_style))
    elements.append(Paragraph(str(person), heading_style))
    elements.append(Spacer(1, 0.5*cm))
    
    date_text = f'Дата создания отчёта: {datetime.now().strftime("%d.%m.%Y %H:%M")}'
    elements.append(Paragraph(date_text, normal_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Базовая информация
    elements.append(Paragraph('Базовая информация', heading_style))
    
    base_fields = BaseField.objects.all().order_by('order')
    base_data = [['Поле', 'Значение']]
    
    for field in base_fields:
        value = person.base_data.get(field.field_key, '—')
        base_data.append([str(field.name), str(value)])
    
    base_table = Table(base_data, colWidths=[7*cm, 10*cm])
    base_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), font_bold),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f9fafb')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('FONTNAME', (0, 1), (-1, -1), font_name),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(base_table)
    elements.append(Spacer(1, 1*cm))
    
    # Услуги
    services = person.help_services.all().select_related('help_category', 'added_by')
    
    if services:
        elements.append(Paragraph('Предоставляемые услуги', heading_style))
        elements.append(Spacer(1, 0.3*cm))
        
        for idx, service in enumerate(services, 1):
            service_title = f'{idx}. {service.help_category.name}'
            elements.append(Paragraph(service_title, heading_style))
            
            status_dict = {
                'active': 'Активно',
                'completed': 'Завершено',
                'pending': 'В ожидании',
                'cancelled': 'Отменено'
            }
            status_text = f'Статус: {status_dict.get(service.status, service.status)}'
            elements.append(Paragraph(status_text, normal_style))
            elements.append(Spacer(1, 0.2*cm))
            
            service_data = [['Поле', 'Значение']]
            
            custom_fields = CustomField.objects.filter(
                help_category=service.help_category
            ).order_by('order')
            
            for field in custom_fields:
                value = service.custom_data.get(field.field_key, '—')
                if len(str(value)) > 50:
                    value = Paragraph(str(value), normal_style)
                service_data.append([str(field.name), value])
            
            if service.notes:
                notes_para = Paragraph(service.notes, normal_style)
                service_data.append(['Заметки', notes_para])
            
            added_by = service.added_by.user.get_full_name() or service.added_by.user.username
            service_data.append(['Добавил', str(added_by)])
            service_data.append(['Дата добавления', service.created_at.strftime('%d.%m.%Y %H:%M')])
            
            service_table = Table(service_data, colWidths=[7*cm, 10*cm])
            service_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), font_bold),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fdf4')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
                ('FONTNAME', (0, 1), (-1, -1), font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            
            elements.append(service_table)
            elements.append(Spacer(1, 0.7*cm))
    else:
        elements.append(Paragraph('Услуги не добавлены', normal_style))
    
    # Футер
    elements.append(Spacer(1, 1*cm))
    from reportlab.platypus import HRFlowable
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
    elements.append(Spacer(1, 0.3*cm))
    
    footer_text = f'© {datetime.now().year} Система учёта помощи. Конфиденциально.'
    elements.append(Paragraph(footer_text, normal_style))
    
    # Генерируем PDF
    doc.build(elements)
    
    buffer.seek(0)
    person_name = str(person).replace(' ', '_')
    filename = f'person_{person.id}_{person_name}.pdf'
    
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response