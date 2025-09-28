# apps/api/routes/vagas.py
from fastapi import APIRouter, Query
from uuid import UUID
from apps.api.models.vagas import Spot, SpotQueryResponse, SpotSelectionResponse
from apps.stream.read_models.flow_status_repo import get_status

router = APIRouter()

@router.get("/consultar-vagas", response_model=SpotQueryResponse)
async def consultar_vagas(
    checkInId: UUID = Query(..., description="ID do check-in"),
    vehicleCategory: str = Query(..., description="Categoria do veículo")
):
    """
    GET: apenas lê o read model.
    Retorna a última lista de vagas consultadas para este checkInId.
    """
    status = await get_status(str(checkInId))
    spots = (status or {}).get("spots") or []
    return SpotQueryResponse(totalAvailable=len(spots), spots=[Spot(**s) for s in spots])

@router.get("/selecionar-vaga", response_model=SpotSelectionResponse)
async def selecionar_vaga(
    checkInId: UUID = Query(..., description="ID do check-in")
):
    """
    GET: retorna a vaga já reservada pela pipeline.
    Se ainda não houver vaga, informa status pendente.
    """
    status = await get_status(str(checkInId))
    if not status or not status.get("spot"):
        return SpotSelectionResponse(success=False, message="Seleção de vaga em processamento", assignedSpot=None)

    spot = status["spot"]
    return SpotSelectionResponse(
        success=True,
        message="Vaga reservada com sucesso",
        assignedSpot=Spot(**spot)
    )
