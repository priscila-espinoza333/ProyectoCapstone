from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
     path('canchas/', views.canchas, name='canchas'),
     path('canchas/futbol/', views.canchas_futbol, name='canchas_futbol'),
     path('canchas/basquetbol/', views.canchas_basquetbol, name='canchas_basquetbol'),
     path('canchas/tenis/', views.canchas_tenis, name='canchas_tenis'),
     path('canchas/padel/', views.canchas_padel, name='canchas_padel'),


]

