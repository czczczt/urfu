from django.urls import path
from . import views

urlpatterns = [
    path('all', views.all_characters, name='all_characters'),
    path('character/<int:pk>/', views.character_detail, name='character_detail'), # pk = id
    path('starship/<int:pk>/', views.starship_detail, name='starship_detail'),
]
