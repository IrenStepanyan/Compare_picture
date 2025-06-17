from django.contrib import admin
from django.contrib import messages
from django import forms
from django.http import JsonResponse
from django.shortcuts import render
from .models import TelegramUser
import telebot
import os
from django.urls import path
from .views import send_message_to_users_view
from unfold.admin import ModelAdmin
import requests

# Assuming you have your Telegram Bot Token stored in an environment variable
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Custom form for writing the message
class SendMessageForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea)

def get_username(user_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChat?chat_id={user_id}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data.get("ok"):
            return data["result"].get("username", "hidden")  # Return None if no username
        return "Not Active"
    return "Not Active" 




@admin.register(TelegramUser)
class TelegramUserAdmin(ModelAdmin):
    list_display = ('telegram_id','user_name', 'first_name', 'last_name', 'location', 'joined_at')
    actions = ['send_message_to_users','update_username']
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('hello/', self.admin_site.admin_view(send_message_to_users_view), name='analytics_data'),
        ]
        return custom_urls + urls
   
    # Custom admin action to send a message
    
    
    def update_username(modeladmin, request, queryset):
        users_to_update = []
        for user in queryset:
            if not user.user_name:  # Only update users with no username
                username = get_username(user.telegram_id)
                if username:
                    user.user_name = username
                    users_to_update.append(user)

        if users_to_update:
            TelegramUser.objects.bulk_update(users_to_update, ["user_name"])
            messages.success(request, f"Updated {len(users_to_update)} usernames successfully.")
        else:
            messages.info(request, "No usernames needed updating.")
            
        
    def send_message_to_users(self, request, queryset):
        print("send_message_to_users function called")
        print("Request Headers:", request.POST)

        # Handle AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            print("AJAX request detected")
            form = SendMessageForm(request.POST)

            if form.is_valid():
                print("Form is valid")
                message = form.cleaned_data['message']
                bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

                success_count = 0
                failure_count = 0

                for user in queryset:
                    try:
                        bot.send_message(chat_id=user.telegram_id, text=message)
                        print(f"Message sent to {user.telegram_id}")
                        success_count += 1
                    except Exception as e:
                        failure_count += 1
                        print(f"Failed to send message to {user.telegram_id}: {e}")

                return JsonResponse({
                    "success": True,
                    "message": f"Successfully sent message to {success_count} users. Failed: {failure_count}"
                })

            print("Form is invalid:", form.errors)
            return JsonResponse({"success": False, "message": "Invalid form data"}, status=400)

        # Handle normal (non-AJAX) request
        return render(
            request,
            'admin/send_message.html',
            context={'users': queryset, 'form': SendMessageForm()},
        )

    send_message_to_users.short_description = "Send a message to selected users"

# Register the model with the custom admin class
