from django.urls import include, path
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload', views.upload, name='upload'),
    path('process/<uuid:file_uuid>/', views.process, name='process'),
    path('about', views.about, name='about')
]
