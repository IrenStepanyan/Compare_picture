from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('test/', admin.site.urls),
    # other URL patterns
]