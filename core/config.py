from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME:str = "Event Driven App"
    BROKER_URL: str = "amqp://guest:guest@localhost:5672/"  # Corrigido: localhost
    API_HOST:str = "0.0.0.0"
    API_PORT:int = 8000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
# Devolve uma instância de settings
settings = Settings()