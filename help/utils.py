from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import HelpProvider

def provider_required(view_func):
    """Декоратор для проверки что пользователь является поставщиком помощи"""
    def wrapper(request, *args, **kwargs):
        try:
            HelpProvider.objects.get(user=request.user)
            return view_func(request, *args, **kwargs)
        except HelpProvider.DoesNotExist:
            return JsonResponse({'error': 'You must be a help provider'}, status=403)
    return wrapper