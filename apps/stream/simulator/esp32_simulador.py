# apps/stream/simulator/esp32_simularor.py
import asyncio
import json
import random
import time
import uuid
import paho.mqtt.client as paho
from apps.stream.logging.logger import get_logger
from apps.stream.mqtt.mqtt_client import MQTTManager
from core.config import settings

logger = get_logger("ESP32_SIMULATOR")


class ESP32Simulator:
    """
    Simula um robô físico (ESP32) interagindo com o servidor via MQTT (RabbitMQ).
    Pode ser executado em múltiplas instâncias, cada uma representando um robô único.
    """

    def __init__(
        self,
        robot_id: str,
        mqtt_host: str = str(settings.MQTT_HOST),
        mqtt_port: int = int(settings.MQTT_PORT),
    ):
        self.robot_id = robot_id
        self.mqtt = MQTTManager(
            client_id=f"sim_{robot_id}", host=mqtt_host, port=mqtt_port
        )

    # ----------------------------------------------------------------------
    # Callback: Receber broadcast de chamada
    # ----------------------------------------------------------------------
    async def on_job_call(self, topic: str, message: dict):
        """
        Quando o servidor solicita bids, esse método responde com um lance automático.
        """
        check_in_id = message.get("checkInId")
        if not check_in_id:
            logger.warning(f"[INVALID_CALL] Mensagem sem checkInId recebida em {topic}")
            return

        logger.info(
            f"[CALL_RECEIVED] Robô {self.robot_id} recebeu job call para checkInId={check_in_id}"
        )

        # Simula tempo de resposta variável
        await asyncio.sleep(random.uniform(0.2, 1.0))

        bid = {
            "robotId": self.robot_id,
            "battery": random.randint(50, 100),
            "eta": random.randint(5, 20),
            "location": random.choice(["A-1", "B-3", "C-2"]),
        }

        bid_topic = f"jobs/bid/{check_in_id}/{self.robot_id}"
        self.mqtt.publish(bid_topic, bid)
        logger.info(f"[BID_SENT] Robô {self.robot_id} enviou bid: {bid}")

    # ----------------------------------------------------------------------
    # Callback: Receber atribuição do servidor
    # ----------------------------------------------------------------------
    async def on_assignment(self, topic: str, message: dict):
        """
        Quando o servidor escolhe esse robô, ele confirma que aceitou a tarefa.
        """
        parts = topic.split("/")
        if len(parts) < 4:
            logger.warning(f"[INVALID_ASSIGN_TOPIC] {topic}")
            return

        check_in_id = parts[2]
        assigned_robot_id = parts[3]

        if assigned_robot_id != self.robot_id:
            logger.debug(
                f"[ASSIGN_IGNORED] Mensagem destinada a outro robô: {assigned_robot_id}"
            )
            return

        logger.info(
            f"[ASSIGN_RECEIVED] Robô {self.robot_id} foi selecionado para checkInId={check_in_id}"
        )

        # Confirma recebimento
        ack_topic = f"jobs/accept/{check_in_id}/{self.robot_id}"
        ack_message = {
            "robotId": self.robot_id,
            "timestamp": time.time(),
            "status": "ACKNOWLEDGED",
        }
        self.mqtt.publish(ack_topic, ack_message)
        logger.info(
            f"[ACK_SENT] Robô {self.robot_id} confirmou atribuição para checkInId={check_in_id}"
        )

        # Simula início da operação
        await self.simulate_operation(check_in_id)

    # ----------------------------------------------------------------------
    # Simular operação em andamento
    # ----------------------------------------------------------------------
    async def simulate_operation(self, check_in_id: str):
        """
        Simula o robô executando a operação e enviando telemetria periódica.
        """
        logger.info(
            f"[OPERATION_START] Robô {self.robot_id} iniciou operação para checkInId={check_in_id}"
        )

        for i in range(5):  # simula 5 atualizações
            status_topic = f"robots/{self.robot_id}/status"
            status_message = {
                "robotId": self.robot_id,
                "checkInId": check_in_id,
                "progress": (i + 1) * 20,
                "battery": random.randint(40, 100),
                "timestamp": time.time(),
            }
            self.mqtt.publish(status_topic, status_message)
            logger.debug(f"[STATUS_UPDATE] {status_message}")
            await asyncio.sleep(1)

        logger.info(
            f"[OPERATION_COMPLETE] Robô {self.robot_id} concluiu operação para checkInId={check_in_id}"
        )

    # ----------------------------------------------------------------------
    # Inicialização do simulador
    # ----------------------------------------------------------------------
    async def start(self):
        """
        Inicia o simulador conectando ao broker e assinando os tópicos necessários.

        IMPORTANTE: A ordem correta é:
        1. Conectar ao broker
        2. Aguardar conexão estabelecida
        3. Inscrever-se nos tópicos
        """
        logger.info(f"[STARTUP] Iniciando robô {self.robot_id}")

        # Primeiro: Conecta ao broker
        await self.mqtt.connect()
        logger.info(f"[CONNECTED] Robô {self.robot_id} conectado ao MQTT")

        # Aguarda um pouco para garantir que a conexão está estável
        await asyncio.sleep(0.5)

        # Segundo: Registra os tópicos (DEPOIS de conectar!)
        logger.info(f"[SUBSCRIBING] Registrando tópicos para robô {self.robot_id}")
        self.mqtt.subscribe("jobs/call/+", self.on_job_call)
        self.mqtt.subscribe(f"jobs/assign/+/{self.robot_id}", self.on_assignment)

        logger.info(f"[READY] Robô {self.robot_id} pronto para receber jobs!")

        # Mantém loop ativo aguardando mensagens
        await asyncio.Event().wait()


# ----------------------------------------------------------------------
# Execução direta para testes locais
# ----------------------------------------------------------------------
# No final do esp32_simulador.py
if __name__ == "__main__":
    robot_id = f"R-{random.randint(1, 1000)}"  # Remove :02d para IDs únicos
    simulator = ESP32Simulator(robot_id)

    logger.info(f"[INIT] Iniciando simulador para robô {robot_id}")
    try:
        asyncio.run(simulator.start())
    except KeyboardInterrupt:
        logger.info(f"[SHUTDOWN] Simulador {robot_id} finalizado")
