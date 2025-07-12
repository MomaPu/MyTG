import requests
from urllib.parse import quote

class TranslationService:
	def translate_text(self, text, target='ru'):

		try:
			return self._translate_via_libertranslate(text,target)
		except Exception:
			try:
				return self._translate_via_mymemory(text,target)
			except Exception:
				raise Exception("Все сервисы временно недоступны")


	def _translate_via_libertranslate(self,text,target):
		url = "https://libretranslate.de/translate"

		data = {
			'q': text,
			'source': "auto",
			'target': target
		}

		response = requests.post(url,json=data,timeout=5)
		response.raise_for_status()
		return response.json()['translatedText']

	def _translate_via_mymemory(self,text,target):
		url = f"https://api.mymemory.translated.net/get?q={quote(text)}&langpair=ZH|{target}"
		response = requests.get(url,timeout=5)
		data = response.json()
		return data["responseData"]["translatedText"]