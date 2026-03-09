from django.urls import path, include
from . import views

urlpatterns = [
    path('luke_skywalker/', views.get_luke_info),
    path('imperial-shuttle/', views.imperial_shuttle_info),
    path('snowspeeder/', views.snowspeeder_info),
    path('xwing/', views.xwing_info),
]