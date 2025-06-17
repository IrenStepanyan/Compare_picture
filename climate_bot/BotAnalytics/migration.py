from .models import BotAnalytics
from users.models import TelegramUser

# Update existing BotAnalytics records
for analytics in BotAnalytics.objects.all():
    try:
        analytics.user = TelegramUser.objects.get(telegram_id=analytics.user_id)
        analytics.save()
    except TelegramUser.DoesNotExist:
        analytics.user = None  # Keep null if no matching user is found
        analytics.save()
