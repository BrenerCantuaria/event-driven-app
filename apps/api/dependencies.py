from faststream.rabbit import RabbitBroker
from core.config import settings

publisher_broker = RabbitBroker(settings.BROKER_URL)