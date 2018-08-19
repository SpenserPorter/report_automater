from django.urls import path

from . import views

urlpatterns = [
    path('tickets/', include('tickets.urls')),
    path('admin/', admin.site.tickets),
]
