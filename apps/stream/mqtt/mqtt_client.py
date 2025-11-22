# apps/stream/mqtt/mqtt_client.py
import json
import asyncio
from typing import Callable, Dict, Optional

from paho.mqtt import client as paho
from apps.stream.logging.logger import get_logger
from core.config import settings
logger = get_logger("MQTT_CLIENT")


class MQTTManager:
    """
    Gerencia a conexão com RabbitMQ via MQTT usando paho-mqtt.
    - Protocolo MQTT 3.1.1 (MQTTv311), compatível com RabbitMQ.
    - Suporte a tópicos com wildcard (+ e #).
    - Integração com asyncio via connect() assíncrono.
    """

    def __init__(
        self,
        client_id: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        keepalive: int = 60,
    ) -> None:
        """
        Inicializa o cliente MQTT.
        
        Se os parâmetros não forem fornecidos, usa valores do .env.
        
        Args:
            client_id: ID único do cliente MQTT
            host: Hostname do broker (default: do .env)
            port: Porta do broker (default: do .env)
            username: Usuário MQTT (default: do .env)
            password: Senha MQTT (default: do .env)
            keepalive: Intervalo keepalive em segundos
        """
        self.client_id = client_id
        
        # Usa valores do .env como fallback
        self.host = host or settings.MQTT_HOST
        self.port = port or int(settings.MQTT_PORT)
        self.username = username or settings.MQTT_USERNAME
        self.password = password or settings.MQTT_PASSWORD
        self.keepalive = keepalive

        # Handlers registrados: pattern -> coroutine(topic, message: dict)
        self._message_handlers: Dict[str, Callable] = {}

        # Loop asyncio e evento de conexão serão definidos no connect()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connected_event: asyncio.Event | None = None

        # Cliente paho
        self.client = paho.Client(
            client_id=self.client_id,
            protocol=paho.MQTTv311,
        )
        
        # Configura credenciais apenas se fornecidas
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
            logger.debug(f"[INIT] Autenticação configurada para usuário: {self.username}")
        else:
            logger.debug("[INIT] Modo anônimo (sem autenticação)")

        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Log de inicialização (sem expor senha)
        logger.info(
            f"[INIT] Cliente MQTT inicializado | "
            f"client_id={self.client_id} | "
            f"broker={self.host}:{self.port}"
        )

    
    # ------------------------------------------------------------------
    # Conexão
    # ------------------------------------------------------------------
    async def connect(self) -> None:
        """
        Conecta ao broker MQTT e inicia o loop de rede em background (loop_start).
        Aguarda até que o on_connect sinalize sucesso.
        """
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        if self._connected_event is None:
            self._connected_event = asyncio.Event()

        logger.info(
            f"[CONNECTING] Conectando ao broker MQTT {self.host}:{self.port} "
            f"(client_id={self.client_id})..."
        )

        try:
            # Chamada síncrona, mas bem rápida
            self.client.connect(self.host, self.port, self.keepalive)
        except Exception as e:
            logger.error(f"[CONNECT ERROR] Erro ao conectar ao broker MQTT: {e}")
            raise

        # Inicia loop interno do paho em thread própria
        self.client.loop_start()

        # Espera até o _on_connect sinalizar
        await self._connected_event.wait()

    async def disconnect(self) -> None:
        """
        Desconecta do broker MQTT e para o loop interno.
        """
        logger.info("[DISCONNECTING] Encerrando MQTT...")
        try:
            self.client.loop_stop()  # para o loop em background
            self.client.disconnect()
        except Exception as e:
            logger.error(f"[DISCONNECT ERROR] Erro ao desconectar: {e}")
        else:
            logger.info("[DISCONNECTED] Cliente MQTT desconectado.")

    # ------------------------------------------------------------------
    # Callbacks de conexão
    # ------------------------------------------------------------------
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(
                f"[CONNECTED] MQTT conectado com sucesso! (client_id={self.client_id})"
            )
            if self._loop and self._connected_event:
                # Sinaliza o connect() assíncrono
                self._loop.call_soon_threadsafe(self._connected_event.set)
        else:
            logger.error(f"[CONNECT FAILED] Código de retorno: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"[DISCONNECTED] MQTT desconectado. Código={rc}")

    # ------------------------------------------------------------------
    # Inscrição
    # ------------------------------------------------------------------
    def subscribe(self, topic: str, handler: Callable, qos: int = 1) -> None:
        """
        Assina um tópico (que pode conter +/#) e registra o handler assíncrono
        que será chamado como: await handler(topic: str, message: dict).
        """
        self._message_handlers[topic] = handler
        self.client.subscribe(topic, qos)
        logger.info(f"[SUBSCRIBED] {topic} (QoS={qos})")

    # ------------------------------------------------------------------
    # Publicação
    # ------------------------------------------------------------------
    def publish(self, topic: str, message: dict, qos: int = 1, retain: bool = False):
        """
        Publica uma mensagem JSON em um tópico MQTT.
        """
        payload = json.dumps(message)
        self.client.publish(topic, payload, qos=qos, retain=retain)
        logger.info(f"[PUBLISHED] topic={topic} message={payload}")

    # ------------------------------------------------------------------
    # Mensagens recebidas
    # ------------------------------------------------------------------
    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")

        logger.debug(f"[RECEIVED] topic={topic} payload={payload}")

        handler: Callable | None = None

        # Faz match de tópico recebido com os patterns registrados
        for pattern, h in self._message_handlers.items():
            if self._topic_matches(pattern, topic):
                handler = h
                break

        if handler and self._loop:
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.error(
                    f"[INVALID JSON] Tópico={topic} | Payload bruto: {payload}"
                )
                return

            # Executa o handler no event loop asyncio (já existente)
            asyncio.run_coroutine_threadsafe(handler(topic, data), self._loop)
        else:
            logger.warning(f"[UNHANDLED] Mensagem sem handler | {topic}")


    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """Implementação correta de match MQTT com wildcards"""
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")

        for i in range(max(len(pattern_parts), len(topic_parts))):
            if i >= len(pattern_parts):
                return False
            if i >= len(topic_parts):
                return pattern_parts[i] == "#"

            if pattern_parts[i] == "#":
                return True
            if pattern_parts[i] == "+":
                continue
            if pattern_parts[i] != topic_parts[i]:
                return False

        return True

    # ------------------------------------------------------------------
    # Loop assíncrono "infinito" (apenas para manter o serviço vivo)
    # ------------------------------------------------------------------
    async def loop_forever(self):
        """
        Mantém o contexto async vivo enquanto o loop do Paho
        roda em background (loop_start).

        Útil em scripts como o ESP32Simulator, que fazem:
            await mqtt.connect()
            await mqtt.loop_forever()
        """
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("[LOOP] loop_forever cancelado")
