# from django.test import TestCase
# from .models import TelegramUser

# class TelegramUserModelTest(TestCase):
#     def setUp(self):
#         self.user = TelegramUser.objects.create(
#             telegram_id=123456789,
#             first_name="John",
#             last_name="Doe",
#             user_name="johndoe",
#             location="New York",
#             coordinates="40.7128, -74.0060"
#         )

#     def test_telegram_user_creation(self):
#         self.assertEqual(self.user.telegram_id, 123456789)
#         self.assertEqual(self.user.first_name, "John")
#         self.assertEqual(self.user.last_name, "Doe")
#         self.assertEqual(self.user.user_name, "johndoe")
#         self.assertEqual(self.user.location, "New York")
#         self.assertEqual(self.user.coordinates, "40.7128, -74.0060")

#     def test_telegram_id_unique(self):
#         with self.assertRaises(Exception):
#             TelegramUser.objects.create(telegram_id=123456789)

#     def test_default_coordinates(self):
#         user = TelegramUser.objects.create(telegram_id=987654321)
#         self.assertEqual(user.coordinates, "0.0, 0.0")

#     def test_str_representation(self):
#         self.assertEqual(str(self.user), "John Doe (123456789)")



from django.http import JsonResponse
import telebot
from telebot import types

import os
from dotenv import load_dotenv
import requests


#import logging

load_dotenv()


TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def get_profile_photo(user_id):
    # Get user's profile photos
    photos = bot.get_user_profile_photos(user_id)

    if photos.total_count > 0:
        # Get the largest version of the first profile photo
        file_id = photos.photos[1][-1].file_id  
        
        # Get file object
        file = bot.get_file(file_id)
        
        # Download as byte array
        file_path = file.file_path  # Extracted from bot.get_file(file_id) response

        # Construct the download URL
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

        # Download the image as bytes
        response = requests.get(file_url)

        if response.status_code == 200:
            # Save the image locally
            with open("profile.jpg", "wb") as f:
                f.write(response.content)
            print("Profile photo saved as profile.jpg")
        else:
            print("Failed to download profile photo")

# Example usage
user_id = 1005467897  # Replace with the actual user ID (chat_id)
# get_profile_photo(user_id)

def get_username(id):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN }/getChat?chat_id={id}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data["ok"]:
            user_info = data["result"]
            username = user_info.get("username", "No username")
            first_name = user_info.get("first_name", "Unknown")
            print(f"Username: @{username}, First Name: {first_name}")
        else:
            print("Error:", data["description"])
    else:
        print("Failed to reach Telegram API")
        
        
# get_username(user_id)