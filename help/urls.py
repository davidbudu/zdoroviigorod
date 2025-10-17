from django.urls import path
from . import views

urlpatterns = [
    # Основные страницы
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Управление людьми
    path('people/', views.people_list, name='people_list'),
    path('people/add/', views.person_add, name='person_add'),
    path('people/<int:person_id>/', views.person_detail, name='person_detail'),
    path('people/<int:person_id>/edit/', views.person_edit, name='person_edit'),
    path('people/<int:person_id>/export-pdf/', views.person_export_pdf, name='person_export_pdf'),
    
    # Управление услугами
    path('people/<int:person_id>/service/add/', views.service_add, name='service_add'),
    path('service/<int:service_id>/edit/', views.service_edit, name='service_edit'),
    
    # API
    path('api/category/<int:category_id>/fields/', views.get_category_fields, name='get_category_fields'),
]