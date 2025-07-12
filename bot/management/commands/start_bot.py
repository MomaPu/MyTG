from django.core.management.base import BaseCommand
from bot.core import TelegramBot

class Command(BaseCommand):
    help = 'Telegram translation bot'

    def handle(self, *args, **options):
        bot = TelegramBot()
        bot.run()