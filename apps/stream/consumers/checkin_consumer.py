from apps.stream.utils.connection import broker
from apps.stream.messaging.topic import CHECKIN_SUBMITTED

@broker.subscriber(CHECKIN_SUBMITTED)
async def handle_checkin_submitted(message:dict):
    """
    Consumer que processa eventos de check-in submetidos.
    """
    
    print(f"[WORKER] Evento recebido em '{CHECKIN_SUBMITTED}': {message}")