# apps/stream/mqtt/mqtt_client.py
import json
import asyncio
import threading
from paho.mqtt import client as paho
from apps.stream.logging.logger import get_logger

logger = get_logger("MQTT_CLIENT")


class MQTTManager:
    """
    Gerencia a conexão com RabbitMQ via MQTT usando a biblioteca paho-mqtt.
    Configurado para MQTT 3.1.1, padrão suportado pelo RabbitMQ.
    """

    def __init__(self, client_id: str, host: str = "localhost", port: int = 1883,
                 username: str = "guest", password: str = "guest", keepalive: int = 60):
        self.client_id = client_id
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.keepalive = keepalive

        # Armazena handlers para cada tópico
        self._message_handlers = {}

        # Captura o event loop principal
        self._loop = asyncio.get_event_loop()

        # Configuração do cliente paho
        self.client = paho.Client(client_id=self.client_id, protocol=paho.MQTTv311)
        self.client.username_pw_set(self.username, self.password)

        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        # Controle do loop
        self._loop_thread = None
        self._connected_event = asyncio.Event()

    # -----------------------------------------------------------
    # Conexão
    # -----------------------------------------------------------
    async def connect(self):
        """
        Conecta ao broker MQTT e inicia o loop em thread separada.
        """
        def run_loop():
            try:
                logger.info("[LOOP] Iniciando loop de rede MQTT em thread separada")
                self.client.loop_forever()
            except Exception as e:
                logger.error(f"[LOOP ERROR] Erro no loop MQTT: {e}")

        logger.info(f"[CONNECTING] Conectando ao broker MQTT {self.host}:{self.port} ...")

        # Conecta ao broker
        self.client.connect(self.host, self.port, self.keepalive)

        # Inicia thread para rodar loop_forever
        self._loop_thread = threading.Thread(target=run_loop, daemon=True)
        self._loop_thread.start()

        # Aguarda confirmação de conexão
        await self._connected_event.wait()

    async def disconnect(self):
        """
        Desconecta do broker MQTT e encerra a thread.
        """
        logger.info("[DISCONNECTING] Encerrando conexão MQTT...")
        self.client.disconnect()
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=2)
        logger.info("[DISCONNECTED] Cliente desconectado do broker MQTT.")

    # -----------------------------------------------------------
    # Callbacks de conexão
    # -----------------------------------------------------------
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"[CONNECTED] MQTT conectado com sucesso! (client_id={self.client_id})")
            self._loop.call_soon_threadsafe(self._connected_event.set)
        else:
            logger.error(f"[CONNECT FAILED] Código de retorno: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"[DISCONNECTED] MQTT desconectado! Código={rc}")

    # -----------------------------------------------------------
    # Inscrição
    # -----------------------------------------------------------
    def subscribe(self, topic: str, handler, qos: int = 1):
        """
        Assina um tópico e registra um handler para processar mensagens recebidas.
        """
        self._message_handlers[topic] = handler
        self.client.subscribe(topic, qos)
        logger.info(f"[SUBSCRIBED] {topic} (QoS={qos})")

    # -----------------------------------------------------------
    # Publicação
    # -----------------------------------------------------------
    def publish(self, topic: str, message: dict, qos: int = 1, retain: bool = False):
        """
        Publica uma mensagem JSON em um tópico MQTT.
        """
        payload = json.dumps(message)
        self.client.publish(topic, payload, qos=qos, retain=retain)
        logger.info(f"[PUBLISHED] topic={topic} message={payload}")

    # -----------------------------------------------------------
    # Callback de mensagens
    # -----------------------------------------------------------
    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")

        logger.debug(f"[RECEIVED] topic={topic} payload={payload}")

        handler = self._message_handlers.get(topic)
        if handler:
            try:
                data = json.loads(payload)
                asyncio.run_coroutine_threadsafe(handler(topic, data), self._loop)
            except json.JSONDecodeError:
                logger.error(f"[INVALID JSON] Tópico: {topic} | Payload bruto: {payload}")
        else:
            logger.warning(f"[UNHANDLED] Mensagem sem handler | Tópico: {topic}")
