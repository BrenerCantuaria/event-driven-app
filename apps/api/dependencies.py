import sys
from pathlib import Path

# Adiciona o diretório raiz do projeto ao Python path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))


from faststream.rabbit import RabbitBroker
from core.config import settings

publisher_broker = RabbitBroker(settings.BROKER_URL)
