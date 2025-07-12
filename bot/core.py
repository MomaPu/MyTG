import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.handlers.command_handlers import StartHandler, HelpHandler, AddWordHandler, ListWordsHandler, TestHandler
from bot.services.translation_services import TranslationService
from bot.services.word_service import WordService

load_dotenv()

class TelegramBot:
	def __init__(self):
		self.token = os.goten("TELEGRAM_BOT_TOKEN")
		self.word_service = WordService()
		self.translation_service = TranslationService()
		self.app = Application.builder().token(self.token).build()

	def setup_handlers(self):
		# Инициализация обработчиков
		start_handler = StartHandler()
		help_handler = HelpHandler()
		add_word_handler = AddWordHandler(self.word_service, self.translation_service)
		list_words_handler = ListWordsHandler(self.word_service)
		test_handler = TestHandler(self.word_service)

		# Регистрация обработчиков
		self.app.add_handler(CommandHandler("start", start_handler.handle))
		self.app.add_handler(CommandHandler("help", help_handler.handle))
		self.app.add_handler(CommandHandler("add", add_word_handler.handle))
		self.app.add_handler(CommandHandler("list", list_words_handler.handle))
		self.app.add_handler(test_handler.create_conversation_handler())

		# Обработчик обычных сообщений для перевода
		self.app.add_handler(MessageHandler(
			filters.TEXT & ~filters.COMMAND,
			self.handle_message
		))

	async def handle_message(self, update, context):
		text = update.message.text.strip()

		if not text:
			await update.message.reply_text("Пожалуйста, отправьте текст для перевода")
			return

		try:
			translated = self.translation_service.translate_text(text)
			await update.message.reply_text(f"🔹 Перевод:\n{translated}")
		except Exception as e:
			await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

	def run(self):
		self.setup_handlers()
		print("Бот запущен и готов к работе...")
		self.app.run_polling()