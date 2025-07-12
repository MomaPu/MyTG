from django.db import transaction
from django.utils import timezone
from bot.models import Words
import random

class WordService:
	@transaction.atomic
	def add_word(self,user_id,word,translation):
		Words.objects.create(
			user_id=user_id,
			word=word,
			translate=translation,
			created_at=timezone.now()
		)

	def get_user_words(self,user_id):
		return list(Words.objects.filter(user_id=user_id).order_by('-created_at').values('word','translate'))

	def get_random_word(self,user_id):
		words = list(Words.objects.filter(user_id=user_id))
		return random.choice(words) if words else None
