from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str
    BROKER_URL: str  # Corrigido: localhost
    API_HOST: str
    API_PORT: int

    # MQTT
    MQTT_HOST: str
    MQTT_PORT: str
    MQTT_USERNAME: str | None
    MQTT_PASSWORD: str | None
    MQTT_CLIENT_PREFIX: str
    MQTT_TLS: bool = False

    # Janelas temporais (ms)
    ROBOT_BID_WINDOW_MS: int
    ROBOT_ACK_WINDOW_MS: int

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Devolve uma instância de settings
settings = Settings()
