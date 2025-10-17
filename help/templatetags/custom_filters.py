from django import template

register = template.Library()


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Получить значение из словаря по ключу
    Использование: {{ dict|get_item:key }}
    """
    if not dictionary:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter(name='dict_item')
def dict_item(dictionary, key):
    """
    Альтернативный способ получения значения из словаря
    Использование: {{ dict|dict_item:key }}
    """
    if not dictionary:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter(name='get_custom_fields')
def get_custom_fields(services):
    """
    Получить уникальные категории со всеми кастомными полями из списка услуг
    Использование: {% for category in services|get_custom_fields %}
    """
    if not services:
        return []
    
    # Получаем уникальные категории
    categories_dict = {}
    for service in services:
        if service.help_category.id not in categories_dict:
            categories_dict[service.help_category.id] = service.help_category
    
    return list(categories_dict.values())


@register.filter(name='add')
def add_filter(value, arg):
    """
    Сложение двух значений
    Использование: {{ value|add:"10" }}
    """
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return value


@register.filter(name='stringformat')
def stringformat(value, arg):
    """
    Форматирование строки
    Использование: {{ value|stringformat:"s" }}
    """
    try:
        if arg == 's':
            return str(value)
        return value
    except:
        return value