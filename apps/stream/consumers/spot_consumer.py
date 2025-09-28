from datetime import datetime, timedelta
from apps.stream.utils.connection import broker
from apps.stream.messaging import topic
from apps.stream.read_models.flow_status_repo import save_spot_list, get_status, set_reserved_spot
from faststream import Logger

# ---------- Consulta de vagas ----------
@broker.subscriber(topic.SPOT_CONSULT_REQUESTED)
async def on_spot_consult_requested(msg: dict, logger: Logger):
    cid = msg["checkInId"]
    logger.info(f"[SpotConsumer] Evento recebido: {topic.SPOT_CONSULT_REQUESTED} | checkInId={cid}")

    # MOCK de vagas disponíveis
    available_spots = [
        {"spotId": "S-12", "level": "2", "position": "A3", "isAvailable": True, "reservedUntil": None},
        {"spotId": "S-15", "level": "2", "position": "B1", "isAvailable": True, "reservedUntil": None},
    ]
    logger.info(f"[SpotConsumer] Vagas encontradas: {available_spots}")

    await save_spot_list(cid, available_spots)

    logger.info(f"[SpotConsumer] Publicando {topic.SPOT_CONSULT_COMPLETED} para checkInId={cid}")
    await broker.publish(
        {"checkInId": cid, "vehicleCategory": msg.get("vehicleCategory"), "spots": available_spots},
        routing_key=topic.SPOT_CONSULT_COMPLETED,
    )

# ---------- Reserva automática de vaga ----------
@broker.subscriber(topic.SPOT_RESERVE_REQUESTED)
async def on_spot_reserve_requested(msg: dict, logger: Logger):
    cid = msg["checkInId"]
    logger.info(f"[SpotConsumer] Evento recebido: {topic.SPOT_RESERVE_REQUESTED} | checkInId={cid}")

    current = await get_status(cid)

    # Caso já exista vaga reservada, evita duplicidade
    if current and current.get("spot"):
        reserved_spot = current["spot"]
        logger.warning(f"[SpotConsumer] Vaga já reservada previamente para checkInId={cid}: {reserved_spot}")
    else:
        spots = (current or {}).get("spots") or []
        if not spots:
            logger.error(f"[SpotConsumer] Nenhuma vaga disponível para checkInId={cid}")
            await broker.publish({"checkInId": cid, "spot": None}, topic=topic.SPOT_RESERVED)
            return

        reserved_spot = {**spots[0]}
        reserved_spot["isAvailable"] = False
        reserved_spot["reservedUntil"] = (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z"

        await set_reserved_spot(cid, reserved_spot)
        logger.info(f"[SpotConsumer] Vaga reservada com sucesso para checkInId={cid}: {reserved_spot}")

    logger.info(f"[SpotConsumer] Publicando {topic.SPOT_RESERVED} para checkInId={cid}")
    await broker.publish({"checkInId": cid, "spot": reserved_spot}, routing_key=topic.SPOT_RESERVED)
