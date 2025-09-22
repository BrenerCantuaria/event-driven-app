import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from faststream.rabbit import RabbitBroker
from core.config import settings

# NOME CORRETO: RabbitBroker (não RabbitBrokerBroker)
broker = RabbitBroker(settings.BROKER_URL)