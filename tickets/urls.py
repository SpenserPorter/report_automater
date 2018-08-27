from django.urls import include, path
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.index, name='index'),
]
