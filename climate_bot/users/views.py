# views.py
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib import messages
from .models import TelegramUser
# from .forms import SendMessageForm
from django import forms

import telebot
import os
import json
import requests

class SendMessageForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea)
# Assuming you have your Telegram Bot Token stored in an environment variable
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

def send_message_to_users_view(request):
    # Check if it's an AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        print("AJAX request detected")
        form = SendMessageForm(request.POST)

        # Retrieve selected user IDs from the request
        user_ids = request.POST.get("user_ids")
        if not user_ids:
            return JsonResponse({"success": False, "message": "No users selected"}, status=400)

        try:
            user_ids = json.loads(user_ids)  # Convert from JSON string to Python list
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Invalid user data"}, status=400)

        users = TelegramUser.objects.filter(id__in=user_ids)  # Fetch users by IDs

        if form.is_valid():
            message = form.cleaned_data['message']
            bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

            success_count = 0
            failure_count = 0

            for user in users:
                try:
                    bot.send_message(chat_id=user.telegram_id, text=message)
                    success_count += 1
                except Exception as e:
                    failure_count += 1
                    print(f"Failed to send message to {user.telegram_id}: {e}")

            return JsonResponse({
                "success": True,
                "message": f"Successfully sent message to {success_count} users. Failed: {failure_count}"
            })

        return JsonResponse({"success": False, "message": "Invalid form data"}, status=400)

    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)


# def get_username(id):
#     url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN }/getChat?chat_id={id}"
#     response = requests.get(url)

#     if response.status_code == 200:
#         data = response.json()
#         if data["ok"]:
#             user_info = data["result"]
#             username = user_info.get("username", "No username")
#             first_name = user_info.get("first_name", "Unknown")
#             print(f"Username: @{username}, First Name: {first_name}")
#             return username
#         else:
#             print("Error:", data["description"])
#             return data["description"]
#     else:
#         print("Failed to reach Telegram API")
#         return "Not Active"
