from django.contrib.admin import SimpleListFilter
from django.db.models import Max
from datetime import timedelta
from django.utils.timezone import now
from .models import BotAnalytics




class UserStatusFilter(SimpleListFilter):
    title = 'User Status'  # The title of the filter
    parameter_name = 'status'  # The query parameter used in the URL

    def lookups(self, request, model_admin):
        # These are the options you want in the filter dropdown
        return (
            ('active', 'Active'),
            ('inactive', 'Inactive'),
        )

    def queryset(self, request, queryset):
        # Get the latest activity for each user (latest timestamp)
        latest_activities = BotAnalytics.objects.values('user_id').annotate(last_activity=Max('timestamp'))
        print(f"==============:{latest_activities}")
        # Get the most recent activity logs for active users (last activity more than 3 days ago)
        if self.value() == 'inactive':
            active_user_ids = latest_activities.filter(last_activity__lt=now() - timedelta(days=3)).values_list('user_id', flat=True)
            # Now filter the queryset to get only the last activity for these active users
            return queryset.filter(user_id__in=active_user_ids, timestamp__in=latest_activities.filter(user_id__in=active_user_ids).values('last_activity'))

        # Get the most recent activity logs for inactive users (last activity within the last 3 days)
        if self.value() == 'active':
            inactive_user_ids = latest_activities.filter(last_activity__gte=now() - timedelta(days=3)).values_list('user_id', flat=True)
            # Now filter the queryset to get only the last activity for these inactive users
            return queryset.filter(user_id__in=inactive_user_ids, timestamp__in=latest_activities.filter(user_id__in=inactive_user_ids).values('last_activity'))

        return queryset.filter(timestamp__in=latest_activities.values('last_activity'))


