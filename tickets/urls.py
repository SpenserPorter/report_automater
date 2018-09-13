from django.urls import include, path
from django.conf.urls.static import static
from . import views
import re

urlpatterns = [
    path('', views.index, name='index'),
    path('upload', views.upload, name='upload'),
    path('view/<uuid:file_uuid>/', views.view, name='process_view'),
    path('view/<int:pk>/', views.agent_detail, name='agent_details'),
    path('view', views.view, name='view'),
    path('about', views.about, name='about'),
    path('emailer', views.emailer, name='emailer')
]
