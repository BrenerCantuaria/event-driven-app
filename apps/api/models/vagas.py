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
            "example" : {
                "spotId": "S-12",
                "level": "2",
                "position": "A3",
                "isAvailable": True,
                "reservedUntil": None
            }
        }