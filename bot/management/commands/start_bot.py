import random

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone
from django.core.management.base import BaseCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
import requests
from urllib.parse import quote

from bot.models import Words

TESTING, ANSWER = range(2)

class Command(BaseCommand):
    help = 'Telegram translation bot'

    async def start(self, update, context):
        await update.message.reply_text(
            "Привет! Я бот-переводчик. Просто отправь мне текст, и я переведу его на русский.\n\n"
            "Доступные команды:\n"
            "/help - справка\n"
            "/lang - изменить язык перевода"
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Для перевода отправьте текст или воспользуйтесь командами\n"
            "/add - Добавить слово\n"
            "/list - Посмотреть сохраненные слова\n"
        )

    @sync_to_async
    def _add_word_to_db(self, user_id, word, translation):
        with transaction.atomic():
            Words.objects.create(
                user_id=user_id,
                word=word,
                translate=translation,
                created_at=timezone.now()
            )

    async def add_word(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    @sync_to_async
    def _get_user_words(self, user_id):
        return list(Words.objects.filter(user_id=user_id).order_by('-created_at').values('word', 'translate'))
    async def get_list_word(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        words = await self._get_user_words(user_id)

        if not words:
            await update.message.reply_text(f'Словарь пуст')

        message = '📚 Ваш словарь:\n\n'

        for word in words:

            message += f"• {word['word']} - {word['translate']}\n"

        await update.message.reply_text(message)

    @sync_to_async
    def _get_random_word(self, user_id):
        words = list(Words.objects.filter(user_id=user_id))
        return random.choice(words) if words else None



    async def start_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        word = await self._get_random_word(user_id)

        if not word:
            await update.message.reply_text(f'Словарь пуст')

        context.user_data['current_word'] = word
        context.user_data['correct_answers'] = 0
        context.user_data['total_questions'] = 0

        reply_keyboard = [['Показать ответ', 'Закончить тест']]

        await update.message.reply_text(
            f'Как переводится слово {word.word}?',
            reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

        return ANSWER

    async def check_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        user_answer = update.message.text.lower()
        word = context.user_data['current_word']
        correct_translation = word.translate.lower()

        if user_answer == "показать ответ":
            await update.message.reply_text(
                f"Правильный ответ:{word.translate}",
                reply_markup = ReplyKeyboardRemove()
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
        word = await self._get_random_word(user_id)

        if not word:
            await update.message.reply_text('Словарь пуст!')
            return await self.finish_test(update,context)

        context.user_data['current_word'] = word
        reply_keyboard = [['Показать ответ', 'Закончить тест']]

        await update.message.reply_text(
            f'Как переводится слово {word.word}?',
            reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return ANSWER

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

        context.user_data.pop('current_word', None)
        context.user_data.pop('correct_answers', None)
        context.user_data.pop('total_questions', None)

        return ConversationHandler.END

    def translate_text(self, text, target='ru'):
        try:
            url = "https://libretranslate.de/translate"
            data = {
                "q": text,
                "source": "auto",
                "target": target
            }
            response = requests.post(url, json=data, timeout=5)
            response.raise_for_status()
            return response.json()["translatedText"]

        except Exception as e:

            try:
                url = f"https://api.mymemory.translated.net/get?q={quote(text)}&langpair=ZH|{target}"
                response = requests.get(url, timeout=5)
                data = response.json()
                return data["responseData"]["translatedText"]
            except:
                raise Exception("Все сервисы перевода временно недоступны")

    async def handle_message(self, update, context):
        text = update.message.text.strip()

        if not text:
            await update.message.reply_text("Пожалуйста, отправьте текст для перевода")
            return

        try:
            translated = self.translate_text(text)
            await update.message.reply_text(f"🔹 Перевод:\n{translated}")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

    async def cancel_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        await update.message.reply_text(
            "Тестирование отменено",
            reply_markup=ReplyKeyboardRemove()
        )

        # Очищаем данные теста
        context.user_data.pop('current_word', None)
        context.user_data.pop('correct_answers', None)
        context.user_data.pop('total_questions', None)

        return ConversationHandler.END

    def handle(self, *args, **options):
        app = Application.builder().token('7895528124:AAHedbHd2-adhm0c1Vr5v6Cisvl3v5Unu28').build()

        # Обычные команды
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help))
        app.add_handler(CommandHandler("add", self.add_word))
        app.add_handler(CommandHandler("list", self.get_list_word))


        test_handler = ConversationHandler(
            entry_points=[CommandHandler("test", self.start_test)],
            states={
                ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.check_answer)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_test)],
        )
        app.add_handler(test_handler)

        # Обработка обычных сообщений
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        print("Бот запущен и готов к работе...")
        app.run_polling()