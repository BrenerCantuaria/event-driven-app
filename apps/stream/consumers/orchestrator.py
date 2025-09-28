from apps.stream.utils.connection import broker
from apps.stream.messaging import topic
from apps.stream.read_models.flow_status_repo import (
    set_status,
)


@broker.subscriber(topic.CHECKIN_SUBMITTED)
async def on_checkin_submitted(msg: dict):
    # mensagem esperada : { checkInId, vehicleCategory, licensePlate}
    cid = msg["checkInId"]
    await set_status(cid, "checkin_submitted", extra=msg)

    # 1 solicitar consulta vagas

    await broker.publish(
        {"checkInId": cid, "vehicleCategory": msg["vehicleCategory"]},
        topic=topic.SPOT_CONSULT_REQUESTED,
    )


@broker.subscriber(topic.SPOT_CONSULT_COMPLETED)
async def on_spot_consult_completed(msg: dict):
    cid = msg["checkInId"]
    await set_status(cid, "spots_consulted", extra={"spots": msg.get("spots", [])})

    # 2) solicitar reserva de vaga
    await broker.publish(
        {"checkInId": cid, "vehicleCategory": msg.get("vehicleCategory")},
        topic=topics.SPOT_RESERVE_REQUESTED,
    )

