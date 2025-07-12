from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
import requests
from urllib.parse import quote
from bot.models import Words


class StartHandler:
	async def start(self, update, context):
		await update.message.reply_text(
			"Привет! Я бот-переводчик. Просто отправь мне текст, и я переведу его на русский.\n\n"
			"Доступные команды:\n"
			"/help - справка\n"
			"/lang - изменить язык перевода"
		)


class HelpHandler:
	async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		await update.message.reply_text(
			"Для перевода отправьте текст или воспользуйтесь командами\n"
			"/add - Добавить слово\n"
			"/list - Посмотреть сохраненные слова\n"
			"/test - Тестирование по изученным словам"
		)


class AddWordHandler:

	@sync_to_async
	def __init__(self, word_service:WordService,translation_service:TranslationService):

