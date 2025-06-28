from django.db import models

class Words(models.Model):
	user_id = models.IntegerField()  # ID пользователя Telegram
	word = models.CharField(max_length=100)
	translate = models.CharField(max_length=100)
	created_at = models.DateTimeField(auto_now_add=True)

# Create your models here.
