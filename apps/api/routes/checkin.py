from fastapi import APIRouter, Depends

from uuid import uuid4

from apps.api.models.checkin import VehicleCheckInData, ProcessingApiResponse
from apps.api.dependencies import publisher_broker
from apps.stream.messaging.topic import CHECKIN_SUBMITTED

router = APIRouter()


# Dependência para injetar o broker
async def get_publisher():
    return publisher_broker


@router.post("/submeterCheckin", response_model=ProcessingApiResponse)
async def submeter_checkin(data: VehicleCheckInData, broker=Depends(get_publisher)):
    """
    Endpoint para receber os dados do Kiosk na etapa de checkin
    """

    if not all(data.securityChecks.dict().values()):
        return ProcessingApiResponse(
            success=False, message="Todos os itens de segurança devem ser selecionados"
        )

    # Gera um checkInId único
    check_in_id = str(uuid4())

    # Cria um payload
    event_payload = {
        "checkInId": check_in_id,
        "vehicleCategory": data.vehicleCategory,
        "cpf": data.cpf,
        "phone": data.phone,
        "licensePlate": data.licensePlate,
    }

    # Publica no broker a mensagem
    await broker.publish(event_payload, CHECKIN_SUBMITTED)

    return ProcessingApiResponse(
        success=True,
        message="Check-in submetido com sucesso",
        data={"checkInId": check_in_id},
    )
