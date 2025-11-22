from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str 
    BROKER_URL: str 
    API_HOST: str 
    API_PORT: int 
    
    # MQTT
    MQTT_HOST: str
    MQTT_PORT: str
    MQTT_USERNAME: str | None
    MQTT_PASSWORD: str | None
    MQTT_CLIENT_PREFIX: str
    MQTT_TLS: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Devolve uma instância de settings
settings = Settings()
