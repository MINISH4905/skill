from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AI_API_KEY: str = "dummy_api_key_replace_me"
    
    class Config:
        env_file = ".env"

settings = Settings()
