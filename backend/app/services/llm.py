from functools import lru_cache

from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)

from app.config import get_settings

settings = get_settings()


def _require_gemini_key() -> str:
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is required. "
            "Create a free-tier key in Google AI Studio "
            "and add it to the project's .env file."
        )

    return settings.gemini_api_key


@lru_cache(maxsize=1)
def get_chat_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.gemini_chat_model,
        api_key=_require_gemini_key(),
        temperature=0,
        max_retries=2,
    )


@lru_cache(maxsize=1)
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=_require_gemini_key(),
        output_dimensionality=settings.embedding_dimensions,
    )