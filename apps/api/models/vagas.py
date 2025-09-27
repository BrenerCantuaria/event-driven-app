from pydantic import BaseModel, Field, constr
from typing import Optional, List
from uuid import UUID


# -------------------------------
# 1. Representação de uma vaga individual
# -------------------------------


class Spot(BaseModel):
    """
    Representa uma vaga de estacionamento disponível ou reservada
    """

    spotId: str = Field(..., description="Identificador único da vaga")
    level: Optional[str] = Field(
        None, description="Nível/andar onde a vaga está localizada"
    )
    position: Optional[str] = Field(None, description="Posições dentro do nível")
    isAvailable: bool = Field(
        None, description="Indica se a vaga está disponível para uso"
    )
    reservedUntil: Optional[str] = Field(
        ...,
        description="Data/hora limite para uso da vaga qunado esiver reservada (ISO 8610)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "spotId": "S-12",
                "level": "2",
                "position": "A3",
                "isAvailable": True,
                "reservedUntil": None,
            }
        }


# -------------------------------
# 2. Consulta de vagas disponíveis (GET /api/consultar-vagas)
# -------------------------------


class SpotQueryRequest(BaseModel):
    """
    Estrutura opcinal para a consulta de vagas
    Permite filtrar por categoria ou outros critérios
    """

    checkInId: UUID = Field(..., description="Id único do check-in")
    vehicleCategory: constr(strip_whitespace=True, min_length=3) = Field(
        ..., description="Categoria do veículo (sedan, hatch, caminhonete, SUV, picape)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "checkInId": "b12d2c77-51db-4eaf-89dc-482c9f88f650",
                "vehicleCategory": "carro",
            }
        }


class SpotQueryResponse(BaseModel):
    """
    Resposta para a consulta de vagas
    """

    totalAvailable: int = Field(..., description="Número total de vagas disponíveis")
    spots: List[Spot] = Field(..., description="Lista de vagas encontradas")

    class Config:
        json_schema_extra = {
            "example": {
                "totalAvailable": 2,
                "spots": {
                    {
                        "spotId": "S-12",
                        "level": "2",
                        "position": "A3",
                        "isAvailable": True,
                        "reservedUntil": None,
                    },
                    {
                        "spotId": "S-15",
                        "level": "2",
                        "position": "B1",
                        "isAvailable": True,
                        "reservedUntil": None,
                    },
                },
            }
        }


