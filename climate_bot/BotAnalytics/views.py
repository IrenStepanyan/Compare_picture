import time
from django.db import models  # Import models for aggregation
from django.utils import timezone  # For accurate timestamping
from .models import BotAnalytics,LocationsAnalytics
from users.utils import save_telegram_user

def log_command_decorator(func):
    def wrapper(message):
        start_time = time.perf_counter()  # Start timing
        try:
            func(message)
            success = True
        except Exception as e:
            success = False
        end_time = time.perf_counter()  # End timing
        latency = end_time - start_time

        # Save analytics data
        # print(message.from_user)
        
        save_telegram_user(message.from_user)
        BotAnalytics.objects.create(
            user_id=message.from_user.id,
            user_name=message.from_user.username,
            command=message.text,
            success=success,
            response_time=latency,
        )

        # Update min/max response times
        analytics = BotAnalytics.objects.filter(user_id=message.from_user.id)
        min_latency = analytics.aggregate(models.Min('response_time'))['response_time__min']
        max_latency = analytics.aggregate(models.Max('response_time'))['response_time__max']

        BotAnalytics.objects.filter(id=analytics.latest('timestamp').id).update(
            min_response_time=min_latency,
            max_response_time=max_latency,
        )

    return wrapper



def save_selected_device_to_db(user_id=None, context=None,device_id = None):
    print(f"save_selected_device_to_db called with user_id={user_id} and context={context}")
    if user_id is not None and context is not None and device_id is not None:
        try:
            LocationsAnalytics.objects.create(
                user_id=user_id,
                device_id=context.get('device_id'),
                device_name=context.get('selected_device'),
                device_province=context.get('selected_country')
            )
            print("Device saved successfully!")
        except Exception as e:
            print(f"Failed to save device: {e}")
    else:
        print("Missing user_id or context in save_selected_device_to_db")