from faststream import Logger
from apps.stream.utils.connection import broker
from apps.stream.messaging import topic
from apps.stream.read_models.flow_status_repo import (
    set_status,
)

from time import sleep

@broker.subscriber(topic.CHECKIN_SUBMITTED)
async def on_checkin_submitted(msg: dict, logger: Logger):
    # mensagem esperada : { checkInId, vehicleCategory, licensePlate}
    cid = msg["checkInId"]
    logger.info(
        f"[Orchestrator] Novo check-in recebido. ID={cid} Categoria={msg.get('vehicleCategory')}"
    )

    await set_status(cid, "checkin_submitted", extra=msg)
    sleep(10)
    
    # 1 solicitar consulta vagas

    await broker.publish(
        {"checkInId": cid, "vehicleCategory": msg["vehicleCategory"]},
        routing_key=topic.SPOT_CONSULT_REQUESTED,
    )

    logger.info(
        f"[Orchestrator] Evento publicado -> {topic.SPOT_CONSULT_REQUESTED} para ID={cid}"
    )


@broker.subscriber(topic.SPOT_CONSULT_COMPLETED)
async def on_spot_consult_completed(msg: dict, logger: Logger):
    cid = msg["checkInId"]

    spots = msg.get("spots", [])
    logger.info(
        f"[Orchestrator] Consulta concluída para ID={cid}, {len(spots)} vagas encontradas."
    )


    await set_status(cid, "spots_consulted", extra={"spots": msg.get("spots", [])})
    sleep(30)

    # 2) solicitar reserva de vaga
    await broker.publish(
        {"checkInId": cid, "vehicleCategory": msg.get("vehicleCategory")},
        routing_key=topic.SPOT_RESERVE_REQUESTED,
    )

    logger.info(
        f"[Orchestrator] Evento publicado -> {topic.SPOT_RESERVE_REQUESTED} para ID={cid}"
    )


@broker.subscriber(topic.SPOT_RESERVED)
async def on_spot_reserved(msg: dict, logger: Logger):
    """
    3 Recebe a confirmação de vaga reservada,
    salva no read model e inicia a etapa de seleção de robô.
    """
    cid = msg["checkInId"]
    spot = msg.get("spot")
    sleep(30)

    if not spot:
        logger.warning(f"[Orchestrator] Nenhuma vaga reservada para ID={cid}.")
        return

    logger.info(f"[Orchestrator] Vaga reservada para ID={cid}, Vaga={spot['spotId']}")

    await set_status(cid, "spot_reserved", extra={"spot": spot})

    await broker.publish(
        {"checkInId": cid, "spot": spot},
        topic=topic.ROBOT_ASSIGN_REQUESTED,
    )

    logger.info(
        # f"[ROBÔS] Evento publicado -> {topic.ROBOT_ASSIGN_REQUESTED} para ID={cid}"
        f"[ROBÔS] Evento publicado -> Robo assino para ID={cid}"
    )
