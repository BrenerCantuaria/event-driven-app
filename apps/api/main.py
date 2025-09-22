import sys
from pathlib import Path

# Adiciona o diretório raiz do projeto ao Python path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))



from fastapi import FastAPI
from core.config import settings
from apps.api.routes import checkin, vagas, robos, operacao
from apps.api.dependencies import publisher_broker


def create_app() -> FastAPI:
    """
    Cria uma aplicacao FastAPI, configura rotas e eventos de inicializacao

    """

    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="API para integração orientada a eventos",
    )

    # registrando rotas

    app.include_router(checkin.router, prefix="/api", tags=["check-in"])
    # app.include_router(vagas.router, prefix="/api", tags=["vagas"])
    # app.include_router(robos.router, prefix="/api", tags=["robos"])
    # app.include_router(operacao.router, prefix="/api", tags=["operacoes"])

    @app.on_event("startup")
    async def startup_event():
        """
        Conecta o publisher da API ao RabbitMQ no início da aplicação
        """
        await publisher_broker.connect()
        print("[API] Conectado ao RabbitMQ para publicação de eventos")

    @app.on_event("shutdown")
    async def shutdown_event():
        """
        Fecha a conexão do publisher com RabbitMQ ao desligar a API
        """
        await publisher_broker.close()
        print("[API] Conexão com RabbitMQ encerrada")

    return app


# Cria uma instância global usada pelo uvicorn
app = create_app()
