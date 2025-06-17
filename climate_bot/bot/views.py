from django.http import JsonResponse
from django.views import View
import requests
import telebot
from telebot import types
import threading
import time
import os
from dotenv import load_dotenv
from bot.models import Device
from collections import defaultdict
import django
from django.conf import settings
from users.utils import save_telegram_user, save_users_locations
from BotAnalytics.views import log_command_decorator, save_selected_device_to_db
import imgkit
import uuid
from string import Template
import math


load_dotenv()


TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


def get_device_data():
    url = "https://climatenet.am/device_inner/list/"
    try:
        response = requests.get(url)
        response.raise_for_status()  
        devices = response.json()
        locations = defaultdict(list)
        device_ids = {}
        for device in devices:
            device_ids[device["name"]] = device["generated_id"]
            locations[device.get("parent_name", "Unknown")].append(device["name"])
        return locations, device_ids
    except requests.RequestException as e:
        print(f"Error fetching device data: {e}")
        return {}, {}


locations, device_ids = get_device_data()
user_context = {}


devices_with_issues = ["Berd", "Ashotsk", "Gavar", "Artsvaberd", "Chambarak", "Areni", "Amasia"]


def fetch_latest_measurement(device_id):
    url = f"https://climatenet.am/device_inner/{device_id}/latest/"
    print(device_id)
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            latest_measurement = data[0]  
            timestamp = latest_measurement["time"].replace("T", " ")
            return {
                "timestamp": timestamp,
                "uv": latest_measurement.get("uv"),
                "lux": latest_measurement.get("lux"),
                "temperature": latest_measurement.get("temperature"),
                "pressure": latest_measurement.get("pressure"),
                "humidity": latest_measurement.get("humidity"),
                "pm1": latest_measurement.get("pm1"),
                "pm2_5": latest_measurement.get("pm2_5"),
                "pm10": latest_measurement.get("pm10"),
                "wind_speed": latest_measurement.get("speed"),
                "rain": latest_measurement.get("rain"),
                "wind_direction": latest_measurement.get("direction")
            }
        else:
            return None
    else:
        print(f"Failed to fetch data: {response.status_code}")
        return None


def start_bot():
    bot.polling(none_stop=True)


def run_bot():
    while True:
        try:
            start_bot()
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(15)


def start_bot_thread():
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()


def send_location_selection(chat_id):
    location_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for country in locations.keys():
        location_markup.add(types.KeyboardButton(country))
    bot.send_message(chat_id, 'Please choose a location: 📍', reply_markup=location_markup)


@bot.message_handler(commands=['start'])
@log_command_decorator
def start(message):
    bot.send_message(
        message.chat.id,
        '🌤️ Welcome to ClimateNet! 🌧️'
    )
    save_telegram_user(message.from_user)
    bot.send_message(
        message.chat.id,
        f'''Hello {message.from_user.first_name}! 👋 I am your personal climate assistant.
With me, you can:
    🔹 Access current measurements of temperature, humidity, wind speed, and more, which are refreshed every 15 minutes for reliable updates.
'''
    )
    send_location_selection(message.chat.id)


@bot.message_handler(commands=['Compare'])
@log_command_decorator
def start_compare(message):
    chat_id = message.chat.id
    try:
        print("/compare triggered:", chat_id)
        if chat_id not in user_context:
            user_context[chat_id] = {}
        user_context[chat_id]['compare_mode'] = True
        user_context[chat_id]['compare_devices'] = []
        send_location_selection_for_compare(chat_id, device_number=1)
    except Exception as e:
        bot.send_message(chat_id, f"{e}")


@bot.message_handler(func=lambda message: message.text in locations.keys())
@log_command_decorator
def handle_country_selection(message):
    selected_country = message.text
    chat_id = message.chat.id
    if chat_id in user_context and user_context[chat_id].get('compare_mode'):
        compare_devices = user_context[chat_id].get('compare_devices', [])
        device_number = len(compare_devices) + 1
        user_context[chat_id][f'compare_country_{device_number}'] = selected_country
        send_device_selection_for_compare(chat_id, selected_country, device_number)
        return
    user_context[chat_id] = {'selected_country': selected_country}
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for device in locations[selected_country]:
        markup.add(types.KeyboardButton(device))
    markup.add(types.KeyboardButton('/Change_location'))
    bot.send_message(chat_id, 'Please choose a device: ✅', reply_markup=markup)


def uv_index(uv):
    if uv is None:
        return " "
    if uv < 3:
        return "Low 🟢"
    elif 3 <= uv <= 5:
        return "Moderate 🟡"
    elif 6 <= uv <= 7:
        return "High 🟠"
    elif 8 <= uv <= 10:
        return "Very High 🔴"
    else:
        return "Extreme 🟣"


def pm_level(pm, pollutant):
    if pm is None:
        return "N/A"
    thresholds = {
        "PM1.0": [50, 100, 150, 200, 300],
        "PM2.5": [12, 36, 56, 151, 251],
        "PM10": [54, 154, 254, 354, 504]
    }
    levels = [
        "Good 🟢",
        "Moderate 🟡",
        "Unhealthy for Sensitive Groups 🟠",
        "Unhealthy 🟠",
        "Very Unhealthy 🔴",
        "Hazardous 🔴"
    ]
    thresholds = thresholds.get(pollutant, [])
    for i, limit in enumerate(thresholds):
        if pm <= limit:
            return levels[i]
    return levels[-1]


def get_comparison_formatted_data(measurement1, device1, measurement2, device2):
    def safe_value(value, is_round=False):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "N/A"
        return f"{round(value)}" if is_round else f"{value}"


    def get_uv_desc(uv):
        return uv_index(uv) if uv is not None else "N/A"
   
    def get_pm_desc(pm, pollutant):
        return pm_level(pm, pollutant) if pm is not None else "N/A"


    def get_status_class(description):
        if "Good" in description:
            return "status-good"
        elif "Moderate" in description:
            return "status-moderate"
        elif "Unhealthy" in description or "High" in description:
            return "status-unhealthy"
        elif "Very High" in description or "Extreme" in description or "Hazardous" in description:
            return "status-dangerous"
        return ""


    issues1 = '<div class="warning">⚠️ Device has technical issues</div>' if device1 in devices_with_issues else ""
    issues2 = '<div class="warning">⚠️ Device has technical issues</div>' if device2 in devices_with_issues else ""


    # Load HTML template
    template_path = "comparison.html"
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = Template(f.read())
    except FileNotFoundError:
        print(f"Error: {template_path} not found")
        return None


    # Prepare data for template substitution
    template_data = {
        'device1': device1,
        'device2': device2,
        'timestamp1': safe_value(measurement1.get('timestamp')),
        'timestamp2': safe_value(measurement2.get('timestamp')),
        'uv1': safe_value(measurement1.get('uv')),
        'uv2': safe_value(measurement2.get('uv')),
        'uv_desc1': get_uv_desc(measurement1.get('uv')),
        'uv_desc2': get_uv_desc(measurement2.get('uv')),
        'uv_status1': get_status_class(get_uv_desc(measurement1.get('uv'))),
        'uv_status2': get_status_class(get_uv_desc(measurement2.get('uv'))),
        'lux1': safe_value(measurement1.get('lux')),
        'lux2': safe_value(measurement2.get('lux')),
        'temperature1': safe_value(measurement1.get('temperature'), is_round=True),
        'temperature2': safe_value(measurement2.get('temperature'), is_round=True),
        'humidity1': safe_value(measurement1.get('humidity')),
        'humidity2': safe_value(measurement2.get('humidity')),
        'pressure1': safe_value(measurement1.get('pressure')),
        'pressure2': safe_value(measurement2.get('pressure')),
        'pm1_1': safe_value(measurement1.get('pm1')),
        'pm1_2': safe_value(measurement2.get('pm1')),
        'pm1_desc1': get_pm_desc(measurement1.get('pm1'), 'PM1.0'),
        'pm1_desc2': get_pm_desc(measurement2.get('pm1'), 'PM1.0'),
        'pm1_status1': get_status_class(get_pm_desc(measurement1.get('pm1'), 'PM1.0')),
        'pm1_status2': get_status_class(get_pm_desc(measurement2.get('pm1'), 'PM1.0')),
        'pm2_5_1': safe_value(measurement1.get('pm2_5')),
        'pm2_5_2': safe_value(measurement2.get('pm2_5')),
        'pm2_5_desc1': get_pm_desc(measurement1.get('pm2_5'), 'PM2.5'),
        'pm2_5_desc2': get_pm_desc(measurement2.get('pm2_5'), 'PM2.5'),
        'pm2_5_status1': get_status_class(get_pm_desc(measurement1.get('pm2_5'), 'PM2.5')),
        'pm2_5_status2': get_status_class(get_pm_desc(measurement2.get('pm2_5'), 'PM2.5')),
        'pm10_1': safe_value(measurement1.get('pm10')),
        'pm10_2': safe_value(measurement2.get('pm10')),
        'pm10_desc1': get_pm_desc(measurement1.get('pm10'), 'PM10'),
        'pm10_desc2': get_pm_desc(measurement2.get('pm10'), 'PM10'),
        'pm10_status1': get_status_class(get_pm_desc(measurement1.get('pm10'), 'PM10')),
        'pm10_status2': get_status_class(get_pm_desc(measurement2.get('pm10'), 'PM10')),
        'wind_speed1': safe_value(measurement1.get('wind_speed')),
        'wind_speed2': safe_value(measurement2.get('wind_speed')),
        'rain1': safe_value(measurement1.get('rain')),
        'rain2': safe_value(measurement2.get('rain')),
        'wind_direction1': safe_value(measurement1.get('wind_direction')),
        'wind_direction2': safe_value(measurement2.get('wind_direction')),
        'weather_condition1': detect_weather_condition(measurement1),
        'weather_condition2': detect_weather_condition(measurement2),
        'issues1': issues1,
        'issues2': issues2
    }


    # Render HTML with substituted values
    try:
        html_content = template.substitute(template_data)
        return html_content
    except KeyError as e:
        print(f"Template substitution error: Missing key {e}")
        return None


def send_comparison_image(chat_id, html_content):
    if html_content is None:
        bot.send_message(chat_id, "⚠️ Error generating comparison table. Please try again.")
        return
    try:
        # Save HTML to a temporary file
        temp_html_path = f"temp_comparison_{uuid.uuid4()}.html"
        with open(temp_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
       
        # Ensure CSS file exists
        css_path = "comparison.css"
        if not os.path.exists(css_path):
            with open(css_path, 'w', encoding='utf-8') as f:
                f.write(CSS_CONTENT)
       
        # Convert HTML to image
        temp_image_path = f"temp_comparison_{uuid.uuid4()}.png"
        imgkit.from_file(temp_html_path, temp_image_path, options={'format': 'png', 'width': 800})
       
        # Send image to Telegram
        with open(temp_image_path, 'rb') as photo:
            bot.send_photo(chat_id, photo)
       
        # Clean up temporary files
        os.remove(temp_html_path)
        os.remove(temp_image_path)
       
    except Exception as e:
        print(f"Error generating/sending image: {e}")
        bot.send_message(chat_id, "⚠️ Error generating comparison image. Please try again.")


@bot.message_handler(func=lambda message: message.text in [device for devices in locations.values() for device in devices])
@log_command_decorator
def handle_device_selection(message):
    selected_device = message.text
    chat_id = message.chat.id
   
    if chat_id not in user_context:
        user_context[chat_id] = {}
   
    device_id = device_ids.get(selected_device)
    if not device_id:
        bot.send_message(chat_id, "⚠️ Device not found. ❌")
        return
   
    if user_context[chat_id].get('compare_mode'):
        compare_devices = user_context[chat_id].get('compare_devices', [])
        device_number = len(compare_devices) + 1
        compare_devices.append({
            'name': selected_device,
            'id': device_id
        })
        user_context[chat_id]['compare_devices'] = compare_devices
       
        if len(compare_devices) == 1:
            send_location_selection_for_compare(chat_id, device_number=2)
        elif len(compare_devices) == 2:
            try:
                device1 = compare_devices[0]
                device2 = compare_devices[1]
               
                measurement1 = fetch_latest_measurement(device1['id'])
                measurement2 = fetch_latest_measurement(device2['id'])
               
                if measurement1 and measurement2:
                    html_content = get_comparison_formatted_data(
                        measurement1, device1['name'],
                        measurement2, device2['name']
                    )
                    send_comparison_image(chat_id, html_content)
                    command_markup = get_command_menu()
                    bot.send_message(
                        chat_id,
                        "Comparison table sent as image above.",
                        reply_markup=command_markup
                    )
                else:
                    error_msg = "⚠️ Error retrieving data from one or both devices. Please try again."
                    command_markup = get_command_menu()
                    bot.send_message(chat_id, error_msg, reply_markup=command_markup)
               
            except Exception as e:
                print(f"Comparison error: {e}")
                error_msg = "⚠️ Error during comparison. Please try again."
                command_markup = get_command_menu()
                bot.send_message(chat_id, error_msg, reply_markup=command_markup)
           
            finally:
                user_context[chat_id].pop('compare_mode', None)
                user_context[chat_id].pop('compare_devices', None)
                for key in list(user_context[chat_id].keys()):
                    if key.startswith('compare_'):
                        user_context[chat_id].pop(key, None)
       
        return
   
    user_context[chat_id]['selected_device'] = selected_device
    user_context[chat_id]['device_id'] = device_id
   
    save_selected_device_to_db(user_id=message.from_user.id, context=user_context[chat_id], device_id=device_id)


    command_markup = get_command_menu(cur=selected_device)
    measurement = fetch_latest_measurement(device_id)
   
    if measurement:
        formatted_data = get_formatted_data(measurement=measurement, selected_device=selected_device)
        bot.send_message(chat_id, formatted_data, reply_markup=command_markup, parse_mode='HTML')
        bot.send_message(chat_id, '''For the next measurement, select\t
/Current 📍 every quarter of the hour. 🕒''')
    else:
        bot.send_message(chat_id, "⚠️ Error retrieving data. Please try again later.", reply_markup=command_markup)


def get_command_menu(cur=None):
    if cur is None:
        cur = ""
    command_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    command_markup.add(
        types.KeyboardButton(f'/Current 📍{cur}'),
        types.KeyboardButton('/Change_device 🔄'),
        types.KeyboardButton('/Help ❓'),
        types.KeyboardButton('/Website 🌐'),
        types.KeyboardButton('/Map 🗺️'),
        types.KeyboardButton('/Share_location 🌍'),
        types.KeyboardButton('/Compare 🆚')
    )
    return command_markup


@bot.message_handler(commands=['Current'])
@log_command_decorator
def get_current_data(message):
    chat_id = message.chat.id
    command_markup = get_command_menu()
    save_telegram_user(message.from_user)
    if chat_id in user_context and 'device_id' in user_context[chat_id]:
        device_id = user_context[chat_id]['device_id']
        selected_device = user_context[chat_id].get('selected_device')
        command_markup = get_command_menu(cur=selected_device)
        measurement = fetch_latest_measurement(device_id)
        if measurement:
            formatted_data = get_formatted_data(measurement=measurement, selected_device=selected_device)
            bot.send_message(chat_id, formatted_data, reply_markup=command_markup, parse_mode='HTML')
            bot.send_message(chat_id, '''For the next measurement, select\t
/Current 📍 every quarter of the hour. 🕒''')
        else:
            bot.send_message(chat_id, "⚠️ Error retrieving data. Please try again later.", reply_markup=command_markup)
    else:
        bot.send_message(chat_id, "⚠️ Please select a device first using /Change_device 🔄.", reply_markup=command_markup)


@bot.message_handler(commands=['Help'])
@log_command_decorator
def help(message):
    bot.send_message(message.chat.id, '''
<b>/Current 📍:</b> Get the latest climate data in selected location.\n
<b>/Change_device 🔄:</b> Change to another climate monitoring device.\n
<b>/Help ❓:</b> Show available commands.\n
<b>/Website 🌐:</b> Visit our website for more information.\n
<b>/Map 🗺️:</b> View the locations of all devices on a map.\n
<b>/Share_location 🌍:</b> Share your location.\n
<b>/Compare🆚:</b> Compare data from 2 different devices side by side.\n
''', parse_mode='HTML')


@bot.message_handler(commands=['Change_device'])
@log_command_decorator
def change_device(message):
    chat_id = message.chat.id
    if chat_id in user_context:
        user_context[chat_id].pop('selected_device', None)
        user_context[chat_id].pop('device_id', None)
    send_location_selection(chat_id)


@bot.message_handler(commands=['Change_location'])
@log_command_decorator
def change_location(message):
    chat_id = message.chat.id
    send_location_selection(chat_id)


@bot.message_handler(commands=['Website'])
@log_command_decorator
def website(message):
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton('Visit Website', url='https://climatenet.am/en/')
    markup.add(button)
    bot.send_message(
        message.chat.id,
        'For more information, click the button below to visit our official website: 🖥️',
        reply_markup=markup
    )


@bot.message_handler(commands=['Map'])
@log_command_decorator
def map(message):
    chat_id = message.chat.id
    image = 'https://images-in-website.s3.us-east-1.amazonaws.com/Bot/map.png'
    bot.send_photo(chat_id, photo=image)
    bot.send_message(chat_id,
'''📌 The highlighted locations indicate the current active climate devices. 🗺️ ''')


def send_location_selection_for_compare(chat_id, device_number):
    location_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if not locations:
        print("Error")
    for country in locations.keys():
        location_markup.add(types.KeyboardButton(country))
    location_markup.add(types.KeyboardButton('/Cancel_compare ❌'))
    bot.send_message(
        chat_id,
        f"Please choose a location for Device {device_number} 📍:",
        reply_markup=location_markup
    )


def send_device_selection_for_compare(chat_id, selected_country, device_number):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for device in locations[selected_country]:
        markup.add(types.KeyboardButton(device))
    markup.add(types.KeyboardButton('/Cancel_compare ❌'))
    bot.send_message(
        chat_id,
        f'Please choose Device {device_number}: ✅',
        reply_markup=markup
    )


@bot.message_handler(commands=['Cancel_compare'])
@log_command_decorator
def cancel_compare(message):
    chat_id = message.chat.id
    if chat_id in user_context:
        user_context[chat_id].pop('compare_mode', None)
        user_context[chat_id].pop('compare_devices', None)
        for key in list(user_context[chat_id].keys()):
            if key.startswith('compare_'):
                user_context[chat_id].pop(key, None)
    command_markup = get_command_menu()
    bot.send_message(
        chat_id,
        "Back to the main menu.",
        reply_markup=command_markup
    )


@bot.message_handler(content_types=['audio', 'document', 'photo', 'sticker', 'video', 'video_note', 'voice', 'contact', 'venue', 'animation'])
@log_command_decorator
def handle_media(message):
    bot.send_message(
        message.chat.id,
        '''❗ Please use a valid command.
You can see all available commands by typing /Help❓
'''
    )


@bot.message_handler(func=lambda message: not message.text.startswith('/'))
@log_command_decorator
def handle_text(message):
    bot.send_message(
        message.chat.id,
        '''❗ Please use a valid command.
You can see all available commands by typing /Help❓
'''
    )


@bot.message_handler(commands=['Share_location'])
@log_command_decorator
def request_location(message):
    location_button = types.KeyboardButton("📍 Share Location", request_location=True)
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    back_button = types.KeyboardButton("/back 🔴")
    markup.add(location_button, back_button)
    bot.send_message(
        message.chat.id,
        "Click the button below to share your location 🔽",
        reply_markup=markup
    )


@bot.message_handler(commands=['back'])
def go_back_to_menu(message):
    bot.send_message(
        message.chat.id,
        "You are back to the main menu. How can I assist you?",
        reply_markup=get_command_menu()
    )


@bot.message_handler(content_types=['location'])
@log_command_decorator
def handle_location(message):
    user_location = message.location
    if user_location:
        latitude = user_location.latitude
        longitude = user_location.longitude
        res = f"{longitude},{latitude}"
        save_users_locations(from_user=message.from_user.id, location=res)
        command_markup = get_command_menu()
        bot.send_message(
            message.chat.id,
            "Select other commands to continue ▶️",
            reply_markup=command_markup
        )
    else:
        bot.send_message(
            message.chat.id,
            "Failed to get your location. Please try again."
        )


def detect_weather_condition(measurement):
    temperature = measurement.get("temperature")
    humidity = measurement.get("humidity")
    lux = measurement.get("lux")
    pm2_5 = measurement.get("pm2_5")
    uv = measurement.get("uv")
    wind_speed = measurement.get("wind_speed")
    if temperature is not None and temperature < 1 and humidity and humidity > 85:
        return "Possibly Snowing ❄️❄️"
    elif lux is not None and lux < 100 and humidity and humidity > 90 and pm2_5 and pm2_5 > 40:
        return "Foggy 🌫️🌫️"
    elif lux and lux < 250 and uv and uv < 2:
        return "Cloudy ☁️"
    elif lux and lux > 5 and uv and uv > 3:
        return "Sunny ☀️"
    else:
        return "Unknown ❌"


# Store CSS content for writing to file if needed
CSS_CONTENT = """
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
}
.container {
    background: white;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    overflow: hidden;
    max-width: 800px;
    margin: 0 auto;
}
.header {
    background: linear-gradient(45deg, #4facfe persp0%, #00f2fe 100%);
    color: white;
    text-align: center;
    padding: 20px;
    font-size: 24px;
    font-weight: bold;
}
.comparison-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}
.comparison-table th {
    background: #f8f9fa;
    color: #333;
    font-weight: 600;
    padding: 15px 12px;
    text-align: left;
    border-bottom: 2px solid #e9ecef;
}
.comparison-table td {
    padding: 12px;
    border-bottom: 1px solid #e9ecef;
    vertical-align: top;
}
.comparison-table tbody tr:hover {
    background-color: #f8f9fa;
}
.metric-cell {
    font-weight: 600;
    color: #495057;
    background-color: #f8f9fa;
    width: 25%;
}
.device-cell {
    width: 37.5%;
}
.value {
    font-weight: 600;
    color: #007bff;
}
.description {
    font-size: 12px;
    color: #6c757d;
    font-style: italic;
}
.status-good { color: #28a745; }
.status-moderate { color: #ffc107; }
.status-unhealthy-high { color: #fd7e14; }
.status-very-unhealthy { color: #dc3545; }
.device-header {
    background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
    color: white;
    font-weight: bold;
    text-align: center;
}
.timestamp {
    font-size: 12px;
    color: #6c757d;
}
.warning {
    background-color: #fff3cd;
    color: #856404;
    padding: 8px;
    border-radius: 4px;
    font-size: 12px;
    margin: 5px 0;
}
.icon {
    margin-right: 5px;
}
"""


if __name__ == "__main__":
    start_bot_thread()


def run_bot_view(request):
    start_bot_thread()
    return JsonResponse({'status': 'Bot is running in the background!'})



