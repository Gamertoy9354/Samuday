import os
import json
from contextvars import ContextVar
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable to store the selected language per async execution context
current_locale: ContextVar[str] = ContextVar("current_locale", default="en")

class TranslationManager:
    def __init__(self, locales_dir: str):
        self.locales_dir = locales_dir
        self.translations = {}
        self.load_translations()

    def load_translations(self):
        """Loads translation JSON dictionaries from disk."""
        for lang in ["en", "hi", "gu"]:
            path = os.path.join(self.locales_dir, f"{lang}.json")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.translations[lang] = json.load(f)
                except Exception:
                    self.translations[lang] = {}
            else:
                self.translations[lang] = {}

    def translate(self, key: str, locale: str = "en") -> str:
        """Retrieves translated text for the given key, falling back to English or the key itself."""
        lang_dict = self.translations.get(locale, self.translations.get("en", {}))
        return lang_dict.get(key, self.translations.get("en", {}).get(key, key))

# Instantiate translator globally
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
translator = TranslationManager(os.path.join(BASE_DIR, "locales"))

def t(key: str) -> str:
    """Convenience helper to translate a key using the request-local locale context."""
    locale = current_locale.get()
    return translator.translate(key, locale)

class LocaleMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware to detect locale from Accept-Language header and bind to current request context."""
    async def dispatch(self, request: Request, call_next):
        accept_language = request.headers.get("accept-language", "en")
        
        # Match gu, hi, or en
        locale = "en"
        for lang in ["gu", "hi", "en"]:
            if lang in accept_language.lower():
                locale = lang
                break
        
        token = current_locale.set(locale)
        try:
            response = await call_next(request)
            return response
        finally:
            current_locale.reset(token)
