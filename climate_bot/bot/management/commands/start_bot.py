# bot/management/commands/start_bot.py

from django.core.management.base import BaseCommand
from bot.views import start_bot_thread
import threading
import time

class Command(BaseCommand):
    help = 'Starts the bot'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting bot...')

        # Start the bot in a separate thread
        bot_thread = threading.Thread(target=self.start_bot_in_thread)
        bot_thread.daemon = True  # Daemon thread will end when the main program ends
        bot_thread.start()

        self.stdout.write('Bot started.')

        # Keep the process alive
        while True:
            time.sleep(1)  # Add a small sleep to reduce CPU usage
            # The loop is needed to keep the management command running
            # The bot runs in the background thread

    def start_bot_in_thread(self):
        """ Wrapper to start the bot in a new thread """
        start_bot_thread()
