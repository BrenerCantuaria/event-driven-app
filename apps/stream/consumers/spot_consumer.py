from datetime import datetime, timedelta
from apps.stream.utils.connection import broker
from apps.stream.messaging import topic
from apps.stream.read_models.flow_status_repo import (
    save_spot_list,
    get_status,
    set_reserved_spot
)


# --------------- Consulta de vagas -----------------------
@broker.subscriber(topic.SPOT_RESERVE_REQUESTED)
async def on_spot_consult_requested(msg:dict):
    """
    Simula a consulta de vagas disponíveis
    """
    
    cid = msg["checkInId"]
    
     # MOCK de vagas disponíveis
    available_spots = [
        {"spotId": "S-12", "level": "2", "position": "A3", "isAvailable": True, "reservedUntil": None},
        {"spotId": "S-15", "level": "2", "position": "B1", "isAvailable": True, "reservedUntil": None},
    ]

    # persiste no read model
    await save_spot_list(cid, available_spots)

    # publica conclusão
    await broker.publish(
        {"checkInId": cid, "vehicleCategory": msg.get("vehicleCategory"), "spots": available_spots},
        topic=topics.SPOT_CONSULT_COMPLETED,
    )
