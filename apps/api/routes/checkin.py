from fastapi import APIRouter
from apps.api.models.checkin import VehicleCheckInData, ProcessingApiResponse
from apps.api.dependencies import publisher_broker


router = APIRouter()

# Dependência para injetar o broker
async def get_publisher():
    return publisher_broker

@router.post('/submeterCheckin', response_model=ProcessingApiResponse)
async def submeter_checkin(data: VehicleCheckInData):
    """
    Endpoint para receber os dados do Kiosk na etapa de checkin
    """

    if not all(data.securityChecks.dict().values):
        return ProcessingApiResponse(
            success=False,
            message= "Todos os itens de segurança devem ser selecionados"
        )
        