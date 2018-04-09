#!/usr/bin/env python3
from googletrans import Translator
from google.cloud import translate
from ansicolor import green, red
import os

__all__ = ["TranslationDriver"]

class TranslationDriver(object):
    def __init__(self, lang="de"):
        self.lang = lang
        if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
            self.mode = "google-api"
            self.client = translate.Client(target_language=lang)
            self.translate = self._googleapi_translate
            print(green("Using google cloud translation API"))
        else:
            self.mode = "googletrans"
            self.translate = self._googletrans_translate
            print(red("Using googletrans"))

    def _googleapi_translate(self, txt):
        transObj = self.client.translate(txt)
        try:
            return transObj.translatedText
        except:
            print(red("Translation failed: "), red(transObj))
            return None
        
    def _googletrans_translate(self, txt):
        translator = Translator()
        result = translator.translate(txt, src="en", dest=self.lang)
        return result.text



