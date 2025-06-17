from django.urls import path
from . import views
from django.conf import settings
from django.templatetags.static import static


urlpatterns = [
    #path('', views.run_bot_view, name='run-bot'),
    #path('webhook/', views.telegram_webhook, name='telegram_webhook'),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)