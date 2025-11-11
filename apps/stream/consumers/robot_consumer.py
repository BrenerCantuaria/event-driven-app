import asyncio
from apps.stream.utils.connection import broker
from apps.stream.logging.logger import get_logger
from apps.stream.mqtt.mqtt_client import MQTTManager
from apps.stream.mqtt.robot_service import RobotService
from apps.stream.messaging import topic

logger = get_logger("ROBOT_CONSUMER")

# Inicializa cliente MQTT e serviço de robôs
mqtt_manager = MQTTManager(client_id="robot_consumer", host="localhost", port=1883)
robot_service = RobotService(mqtt_manager)

# ------------------------------------------------------------
# Inicialização MQTT
# ------------------------------------------------------------
async def init_mqtt():
    """
    Inicializa conexão MQTT e inscrições nos tópicos necessários.
    """
    # Assinar bids dos robôs
    mqtt_manager.subscribe("jobs/bid/+/+", robot_service.on_bid_received)
    # Assinar confirmações dos robôs
    mqtt_manager.subscribe("jobs/accept/+/+", robot_service.on_assignment_ack)

    await mqtt_manager.connect()
    logger.info("[MQTT] Conexão inicializada e tópicos assinados.")

# ------------------------------------------------------------
# Função principal: Gerenciar atribuição de robô
# ------------------------------------------------------------
@broker.subscriber(topic.ROBOT_ASSIGN_REQUESTED)
async def on_robot_assign_requested(event: dict):
    """
    Pipeline de atribuição de robô:
    1. Recebe solicitação do Orquestrador
    2. Envia broadcast para robôs
    3. Aguarda bids e seleciona vencedor
    4. Publica resultado via MQTT e RabbitMQ
    """
    check_in_id = event["checkInId"]
    spot_info = event.get("spot", {})

    logger.info(f"[EVENT_RECEIVED] robot.assign.requested.v1 | checkInId={check_in_id} | spot={spot_info}")

    # Passo 1: Broadcast para robôs
    job_info = {
        "checkInId": check_in_id,
        "spot": spot_info
    }
    robot_service.call_for_bids(check_in_id, job_info)

    # Passo 2: Coletar bids
    bids = await robot_service.collect_bids(check_in_id)
    if not bids:
        logger.warning(f"[NO_BIDS] Nenhum robô respondeu para checkInId={check_in_id}")

        await broker.publish(
            {"checkInId": check_in_id, "message": "Nenhum robô disponível"},
            routing_key=topic.ROBOT_NONE
        )
        return

    # Passo 3: Escolher vencedor
    winner = robot_service.choose_winner(bids)
    if not winner:
        logger.error(f"[SELECTION_ERROR] Falha ao selecionar robô para checkInId={check_in_id}")
        await broker.publish(
            {"checkInId": check_in_id, "message": "Erro na seleção do robô"},
            routing_key=topic.ROBOT_NONE
        )
        return

    robot_id = winner["robotId"]

    # Passo 4: Enviar atribuição ao vencedor
    robot_service.assign_robot(check_in_id, robot_id, job_info)

    # Passo 5: Aguardar confirmação do robô vencedor
    logger.info(f"[WAITING_ACK] Aguardando confirmação do robô {robot_id}")
    await asyncio.sleep(2)  # tempo limite para receber confirmação
    ack_robot = robot_service.get_ack(check_in_id)

    if ack_robot == robot_id:
        logger.info(f"[ASSIGNMENT_CONFIRMED] Robô {robot_id} confirmado para checkInId={check_in_id}")

        # Publica evento de sucesso no RabbitMQ
        await broker.publish(
            {
                "checkInId": check_in_id,
                "robotId": robot_id,
                "spot": spot_info,
                "message": "Robô atribuído com sucesso"
            },
            routing_key=topic.ROBOT_ASSIGNED
        )
    else:
        logger.error(f"[ACK_TIMEOUT] Robô {robot_id} não confirmou atribuição no tempo esperado")
        await broker.publish(
            {"checkInId": check_in_id, "message": "Robô não confirmou atribuição"},
            routing_key=topic.ROBOT_NONE
        )

# ------------------------------------------------------------
# Inicialização conjunta: FastStream + MQTT
# ------------------------------------------------------------
async def start_robot_consumer():
    """
    Inicializa o MQTT e mantém em execução paralela ao FastStream.
    """
    await init_mqtt()

    # Mantém loop MQTT ativo em paralelo ao FastStream
    asyncio.create_task(mqtt_manager.loop_forever())
    logger.info("[STARTUP] Robot Consumer inicializado e aguardando eventos")
