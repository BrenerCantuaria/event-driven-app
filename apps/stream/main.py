from faststream import FastStream
from apps.stream.utils.connection import broker


# Importa os consumers para que eles sejam registrados automaticamente
from apps.stream.consumers import orchestrator
from apps.stream.consumers import spot_consumer
from apps.stream.consumers import robot_consumer

app = FastStream(broker)

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())