# Makefile para automação do projeto Event-Driven-App

# Variáveis
PYTHONPATH=.
UVICORN= uvicorn apps.api.main:app --reload
WORKER=python -m faststream run apps.stream.main:app 
ESP32_SIMULATOR = python -m apps.stream.simulator.esp32_simulador
RABBIT_IMAGE=rabbitmq:3-management

# ==============================
# Comandos principais
# ==============================

# Inicia a API FastAPI
api:
	PYTHONPATH=$(PYTHONPATH) $(UVICORN)

# Inicia o Worker FastStream
worker:
	PYTHONPATH=$(PYTHONPATH) $(WORKER)

# Inicia um simulador de ESP32
simulador:
	PYTHONPATH= $(ESP32_SIMULATOR)

# Sobe RabbitMQ no Docker
rabbit:
	docker run -d --name rabbitmq \
	-p 5672:5672 \
	-p 15672:15672 \
	$(RABBIT_IMAGE)

# Para e remove o container RabbitMQ
rabbit-stop:
	docker stop rabbitmq || true && docker rm rabbitmq || true

# Sobe API, Worker e RabbitMQ juntos (em segundo plano)
up:
	make rabbit
	sleep 3
	@echo "Iniciando API e Worker em terminais separados..."
	@echo "Para a API: make api"
	@echo "Para o Worker: make worker"

# Encerra tudo
down:
	make rabbit-stop

# Roda testes
test:
	PYTHONPATH=$(PYTHONPATH) pytest -v

# Limpa caches Python (__pycache__ e arquivos .pyc)
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
