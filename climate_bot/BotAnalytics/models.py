from django.db import models
from django.contrib.auth.models import User  # If you track specific users
from django.utils import timezone
import pytz

class BotAnalytics(models.Model):
    user_id = models.CharField(max_length=50)  # Telegram user ID
    user_name = models.CharField(max_length=40,blank=True)
    command = models.CharField(max_length=100)  # Command or action
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)  # Track errors if needed
    device_location = models.CharField(max_length=255, blank=True, null=True)  # For ClimateNet-specific devices
    response_time = models.FloatField(null=True, blank=True)  # New field for response latency
    min_response_time = models.FloatField(null=True, blank=True)  # Minimum latency
    max_response_time = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.user_id} - {self.user_name} - {self.command} - {self.timestamp}"
    
    """ 
    from django.db import models
from django.utils.timezone import now

class BotAnalytics(models.Model):
    user_id = models.CharField(max_length=50)
    command = models.CharField(max_length=50, blank=True, null=True)
    timestamp = models.DateTimeField(default=now)
    device_location = models.CharField(max_length=255, blank=True, null=True)  # For ClimateNet-specific devices

    class Meta:
        verbose_name_plural = "Bot Analytics"

    def __str__(self):
        return f"User {self.user_id} - Command: {self.command}"

    
    """


class LocationsAnalytics(models.Model):
    user_id = models.CharField(max_length=50)  # Telegram user ID
    timestamp = models.DateTimeField(auto_now_add=True)
    device_id = models.BigIntegerField(blank=True)
    device_name = models.CharField(blank=True,max_length=50)
    device_province = models.CharField(blank=True,max_length=50)


    def __str__(self):
        return f"{self.user_id}  - {self.timestamp} - {self.device_id}"