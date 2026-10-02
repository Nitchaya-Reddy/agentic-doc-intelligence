from app.config import Settings


def test_gemini_defaults():
    settings = Settings(_env_file=None)
    assert settings.gemini_chat_model == "gemini-3.5-flash-lite"
    assert settings.gemini_embedding_model == "gemini-embedding-2"
    assert settings.embedding_dimensions == 1536
