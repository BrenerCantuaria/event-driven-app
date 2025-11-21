# apps/stream/consumers/robot_consumer.py
import asyncio
import uuid

from apps.stream.utils.connection import broker
from apps.stream.logging.logger import get_logger
from apps.stream.mqtt.mqtt_client import MQTTManager
from apps.stream.mqtt.robot_service import RobotService
from apps.stream.messaging import topic

logger = get_logger("ROBOT_CONSUMER")

# Instância global de MQTT + serviço de robôs
mqtt_manager = MQTTManager(
    client_id=f"robot_consumer_{uuid.uuid4().hex[:8]}",
    host="localhost",
    port=1883,
)
robot_service = RobotService(mqtt_manager)

# Flags de inicialização lazy
_mqtt_started = False
_mqtt_lock = asyncio.Lock()


async def ensure_mqtt_started():
    """
    Inicializa MQTT apenas uma vez, na primeira vez que for necessário.
    Evita travar o startup do FastStream.
    """
    global _mqtt_started

    if _mqtt_started:
        return

    async with _mqtt_lock:
        if _mqtt_started:
            return

        # Assina callbacks de bid e ack
        mqtt_manager.subscribe("jobs/bid/+/+", robot_service.on_bid_received)
        mqtt_manager.subscribe("jobs/accept/+/+", robot_service.on_assignment_ack)

        await mqtt_manager.connect()
        logger.info("[MQTT] Conexão inicializada e tópicos assinados.")

        # Loop MQTT em paralelo
        asyncio.create_task(mqtt_manager.loop_forever())
        logger.info("[MQTT] Loop MQTT iniciado em background.")

        _mqtt_started = True


@broker.subscriber(topic.ROBOT_ASSIGN_REQUESTED)
async def on_robot_assign_requested(event: dict):
    """
    Pipeline de atribuição de robô:
    1. Garante que MQTT está inicializado (lazy)
    2. Envia broadcast para robôs
    3. Aguarda bids e seleciona vencedor
    4. Publica resultado via MQTT e RabbitMQ
    """
    # Garante que MQTT e callbacks estão ativos
    await ensure_mqtt_started()

    check_in_id = event["checkInId"]
    spot_info = event.get("spot", {})

    logger.info(
        f"[EVENT_RECEIVED] {topic.ROBOT_ASSIGN_REQUESTED} | "
        f"checkInId={check_in_id} | spot={spot_info}"
    )

    # 1. Broadcast para robôs
    job_info = {"checkInId": check_in_id, "spot": spot_info}
    robot_service.call_for_bids(check_in_id, job_info)

    # 2. Coletar bids
    bids = await robot_service.collect_bids(check_in_id)
    if not bids:
        logger.warning(f"[NO_BIDS] Nenhum robô respondeu | checkInId={check_in_id}")
        await broker.publish(
            {"checkInId": check_in_id, "message": "Nenhum robô disponível"},
            routing_key=topic.ROBOT_NONE,
        )
        return

    # 3. Escolher vencedor
    winner = robot_service.choose_winner(bids)
    if not winner:
        logger.error(
            f"[SELECTION_ERROR] Falha ao selecionar robô | checkInId={check_in_id}"
        )
        await broker.publish(
            {"checkInId": check_in_id, "message": "Erro na seleção do robô"},
            routing_key=topic.ROBOT_NONE,
        )
        return

    robot_id = winner["robotId"]

    # 4. Enviar atribuição ao vencedor
    robot_service.assign_robot(check_in_id, robot_id, job_info)

    # 5. Aguardar confirmação
    logger.info(f"[WAITING_ACK] Aguardando ACK do robô {robot_id}")
    await asyncio.sleep(2)
    ack_robot = robot_service.get_ack(check_in_id)

    if ack_robot == robot_id:
        logger.info(
            f"[ASSIGNMENT_CONFIRMED] Robô {robot_id} confirmado | checkInId={check_in_id}"
        )

        await broker.publish(
            {
                "checkInId": check_in_id,
                "robotId": robot_id,
                "spot": spot_info,
                "message": "Robô atribuído com sucesso",
            },
            routing_key=topic.ROBOT_ASSIGNED,
        )

        # opcional: início da operação
        robot_service.start_operation(check_in_id, robot_id)

    else:
        logger.error(
            f"[ACK_TIMEOUT] Robô {robot_id} não confirmou no tempo esperado | "
            f"checkInId={check_in_id}"
        )
        await broker.publish(
            {"checkInId": check_in_id, "message": "Robô não confirmou atribuição"},
            routing_key=topic.ROBOT_NONE,
        )
