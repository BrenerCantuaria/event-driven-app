# apps/stream/mqtt/robot_service.py
import asyncio
import time
from typing import Dict, List, Optional

from apps.stream.logging.logger import get_logger
from apps.stream.mqtt.mqtt_client import MQTTManager

logger = get_logger("ROBOT_SERVICE")

# Tempo (segundos) para receber bids dos robôs
BID_TIMEOUT = 3


class RobotService:
    """
    Serviço especializado em gerenciar a comunicação com robôs via MQTT.
    - Publica chamadas de bid
    - Coleta respostas dos robôs
    - Define vencedor e envia atribuição
    """

    def __init__(self, mqtt_manager: MQTTManager):
        self.mqtt = mqtt_manager
        self._bids: Dict[str, List[dict]] = {}
        self._acknowledgments: Dict[str, str] = {}
        # opcional: trava para evitar condições de corrida
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------
    # 1. Broadcast: Chamar robôs para um novo check-in
    # -------------------------------------------------------------------
    def call_for_bids(self, check_in_id: str, job_info: dict) -> None:
        """
        Envia broadcast para que todos os robôs disponíveis enviem seus bids.
        """
        topic = f"jobs/call/{check_in_id}"
        self.mqtt.publish(topic, job_info)
        logger.info(
            f"[CALL_FOR_BIDS] Broadcast enviado para robôs | "
            f"checkInId={check_in_id} | job_info={job_info}"
        )

        # Inicializa a lista de bids para esse check-in
        self._bids[check_in_id] = []

    # -------------------------------------------------------------------
    # 2. Callback: Receber bids dos robôs
    # -------------------------------------------------------------------
    async def on_bid_received(self, topic: str, message: dict) -> None:
        """
        Callback acionado quando um robô envia um bid.
        """
        parts = topic.split("/")
        if len(parts) < 4:
            logger.warning(f"[INVALID_BID_TOPIC] {topic}")
            return

        check_in_id = parts[2]
        robot_id = parts[3]

        bid_data = {
            "robotId": robot_id,
            "battery": message.get("battery"),
            "eta": message.get("eta"),
            "location": message.get("location"),
            "timestamp": time.time(),
        }

        async with self._lock:
            if check_in_id not in self._bids:
                self._bids[check_in_id] = []
            self._bids[check_in_id].append(bid_data)

        logger.info(
            f"[BID_RECEIVED] checkInId={check_in_id} | "
            f"robotId={robot_id} | bid={bid_data}"
        )

    # -------------------------------------------------------------------
    # 3. Coletar bids com timeout
    # -------------------------------------------------------------------
    async def collect_bids(
        self, check_in_id: str, timeout: int = BID_TIMEOUT
    ) -> List[dict]:
        """
        Aguarda bids por um tempo determinado.
        Retorna todos os bids recebidos no período.
        """
        logger.info(
            f"[WAITING_BIDS] Aguardando bids por {timeout}s | "
            f"checkInId={check_in_id}"
        )
        await asyncio.sleep(timeout)

        async with self._lock:
            bids = list(self._bids.get(check_in_id, []))

        logger.info(
            f"[BIDS_COLLECTED] Total de bids recebidos: {len(bids)} | "
            f"checkInId={check_in_id}"
        )
        return bids

    # -------------------------------------------------------------------
    # 4. Selecionar o robô vencedor
    # -------------------------------------------------------------------
    def choose_winner(self, bids: List[dict]) -> Optional[dict]:
        """
        Critério simples: maior bateria, depois menor ETA.
        """
        if not bids:
            logger.warning("[NO_BIDS] Nenhum bid disponível para seleção.")
            return None

        sorted_bids = sorted(bids, key=lambda x: (-x["battery"], x["eta"]))
        winner = sorted_bids[0]
        logger.info(f"[WINNER_SELECTED] Vencedor definido: {winner}")
        return winner

    # -------------------------------------------------------------------
    # 5. Enviar atribuição ao vencedor
    # -------------------------------------------------------------------
    def assign_robot(self, check_in_id: str, robot_id: str, job_info: dict) -> None:
        """
        Notifica o robô vencedor para assumir o trabalho.
        """
        topic = f"jobs/assign/{check_in_id}/{robot_id}"
        self.mqtt.publish(topic, job_info)
        logger.info(
            f"[ASSIGN] Robô {robot_id} atribuído ao job {check_in_id}"
        )

    # -------------------------------------------------------------------
    # 6. Callback: Receber confirmação de atribuição
    # -------------------------------------------------------------------
    async def on_assignment_ack(self, topic: str, message: dict) -> None:
        """
        Callback acionado quando o robô vencedor confirma a atribuição.
        """
        parts = topic.split("/")
        if len(parts) < 4:
            logger.warning(f"[INVALID_ACK_TOPIC] {topic}")
            return

        check_in_id = parts[2]
        robot_id = parts[3]

        async with self._lock:
            self._acknowledgments[check_in_id] = robot_id

        logger.info(
            f"[ACK_RECEIVED] Robô {robot_id} confirmou atribuição "
            f"para checkInId={check_in_id}"
        )

    def get_ack(self, check_in_id: str) -> Optional[str]:
        """
        Retorna o ID do robô que confirmou a atribuição.
        """
        return self._acknowledgments.get(check_in_id)

    # -------------------------------------------------------------------
    # 7. Enviar comando de início de operação
    # -------------------------------------------------------------------
    def start_operation(self, check_in_id: str, robot_id: str) -> None:
        """
        Envia comando final para o robô iniciar a operação física.
        """
        topic = f"jobs/start/{check_in_id}/{robot_id}"
        message = {
            "checkInId": check_in_id,
            "robotId": robot_id,
            "command": "START_OPERATION",
            "timestamp": time.time(),
        }
        self.mqtt.publish(topic, message)
        logger.info(
            f"[START_OPERATION] Enviado comando de início para robô "
            f"{robot_id} | checkInId={check_in_id}"
        )
