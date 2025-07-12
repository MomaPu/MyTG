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
from bot.services.translation_services import TranslationService
from bot.services.word_service import WordService


class StartHandler:
	async def handle(self, update, context):
		await update.message.reply_text(
			"Привет! Я бот-переводчик. Просто отправь мне текст, и я переведу его на русский.\n\n"
			"Доступные команды:\n"
			"/help - справка\n"
			"/lang - изменить язык перевода"
		)


class HelpHandler:
	async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		await update.message.reply_text(
			"Для перевода отправьте текст или воспользуйтесь командами\n"
			"/add - Добавить слово\n"
			"/list - Посмотреть сохраненные слова\n"
			"/test - Тестирование по изученным словам"
		)


class AddWordHandler:

	@sync_to_async
	def __init__(self, word_service:WordService,translation_service:TranslationService):
			self.word_service = word_service
			self.translation_service = translation_service

	async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		user_id = update.message.from_user.id
		text = ''.join(context.args) if context else None

		if not text:
			await update.message.reply_text("Введите слово после /add")
			return

		try:
			translated = self.translate_text(text)

			await self._add_word_to_db(user_id, text, translated)
			await update.message.reply_text((f"✅ Слово '{text}' добавлено в словарь"))

		except Exception as e:

			await update.message.reply_text((f"⚠️ Ошибка: {str(e)}"))

class ListWordsHandler:

	def __init__(self, word_service: WordService):
		self.word_service = word_service

	async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		user_id = update.message.from_user.id
		words = self.word_service.get_user_words(user_id)

		if not words:
			await update.message.reply_text('Словарь пуст')
			return

		message = '📚 Ваш словарь:\n\n'
		for word in words:
			message += f"• {word['word']} - {word['translate']}\n"

		await update.message.reply_text(message)

class TestHandler:

	def __init__(self, word_service=WordService):
		self.word_service=WordService
		self.ANSWER = 2

	async def start_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		user_id = update.message.from_user.id
		word = self.word_service.get_random_word(user_id)

		if not word:
			await update.message.reply_text('Словарь пуст')
			return ConversationHandler.END

		context.user_data['current_word'] = word
		context.user_data['correct_answers'] = 0
		context.user_data['total_questions'] = 0

		reply_keyboard = [['Показать ответ', 'Закончить тест']]

		await update.message.reply_text(
			f'Как переводится слово {word.word}?',
			reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

		return self.ANSWER

	async def check_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		user_answer = update.message.text.lower()
		word = context.user_data['current_word']
		correct_translation = word.translate.lower()

		if user_answer == "показать ответ":
			await update.message.reply_text(
				f"Правильный ответ: {word.translate}",
				reply_markup=ReplyKeyboardRemove()
			)
		elif user_answer == "закончить тест":
			return await self.finish_test(update, context)
		elif user_answer == correct_translation:
			context.user_data['correct_answers'] += 1
			await update.message.reply_text("✅ Верно!")
		else:
			await update.message.reply_text(f"❌ Неверно. Правильно: {word.translate}")

		context.user_data['total_questions'] += 1
		return await self.next_question(update, context)

	async def next_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		user_id = update.message.from_user.id
		word = self.word_service.get_random_word(user_id)

		if not word:
			await update.message.reply_text('Словарь пуст!')
			return await self.finish_test(update, context)

		context.user_data['current_word'] = word
		reply_keyboard = [['Показать ответ', 'Закончить тест']]

		await update.message.reply_text(
			f'Как переводится слово {word.word}?',
			reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
		return self.ANSWER

	async def finish_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		correct = context.user_data.get('correct_answers', 0)
		total = context.user_data.get('total_questions', 0)
		score = (correct / total * 100) if total > 0 else 0

		await update.message.reply_text(
			f"Тест завершен!\n"
			f"Правильных ответов: {correct} из {total}\n"
			f"Успешность: {score:.1f}%",
			reply_markup=ReplyKeyboardRemove()
		)

		context.user_data.clear()
		return ConversationHandler.END

	async def cancel_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		await update.message.reply_text(
			"Тестирование отменено",
			reply_markup=ReplyKeyboardRemove()
		)
		context.user_data.clear()
		return ConversationHandler.END

	def create_conversation_handler(self):
		return ConversationHandler(
			entry_points=[CommandHandler("test", self.start_test)],
			states={
				self.ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.check_answer)],
			},
			fallbacks=[CommandHandler("cancel", self.cancel_test)],
		)
