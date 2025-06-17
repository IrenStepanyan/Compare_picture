from django.db import models

# Create your models here.
class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    user_name = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    coordinates = models.CharField(max_length=50, 
                                    help_text="Latitude, Longitude (e.g., 40.7128, -74.0060)", 
                                    default="0.0, 0.0")
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.telegram_id})"
