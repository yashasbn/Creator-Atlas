from app.config import settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.ollama_provider import OllamaProvider

class AIService:
    @staticmethod
    def get_provider() -> BaseAIProvider:
        provider = (settings.AI_PROVIDER or "gemini").lower()
        if provider == "ollama":
            return OllamaProvider(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
        else:
            return GeminiProvider(api_key=settings.GEMINI_API_KEY)
