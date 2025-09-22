from pydantic import BaseModel, Field, constr
from typing import Optional, Dict
from uuid import UUID, uuid4


class SecurityChecks(BaseModel):
    """
    Representa as verificações de segurança realizadas no veículo
    antes do processo de check-in
    """

    doors: bool = Field(..., description="Confirma que todas as portas estão fechadas")
    windows: bool = Field(
        ..., description="Confirma que todos os vidros estão fechadas"
    )
    handbrake: bool = Field(..., description="Confirma que freio de mão está puxado")
    seatbelt: bool = Field(..., description="Cinto está desafivelado")
    mirrors: bool = Field(..., description="Retrovisores estão ajustados")


class VehicleCheckInData(BaseModel):
    """
    Dados iniciais submetidos pelo usuário no modo Kiosk
    Todos os campos boolean devem ser TRUE, para permitir submissão
    """

    vehicleCategory: constr(strip_whitespace=True, min_length=3) = Field(
        ..., description="Categoria do veículo, ex: carro"
    )

    cpf: constr(strip_whitespace=True, min_length=10, max_length=15) = Field(
        ..., description="Telefone de contato, ex: XX XXXXX-XXXX"
    )

    phone: constr(strip_whitespace=True, min_length=10, max_length=15) = Field(
        ..., description="Placa do veículo, ex: ABC-1234"
    )

    licensePlate: constr(strip_whitespace=True, min_length=6, max_length=8) = Field(
        ..., description="Placa do veículo, ex: ABC-1234"
    )

    securityChecks: SecurityChecks = Field(
        ..., description="Checklist de segurança obrigatório"
    )

    termsAccepted: bool = Field(
        ..., description="Confirmação de que os termos foram aceitos"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vehicleCategory": "carro",
                "cpf": "123.456.789-00",
                "phone": "(11) 99999-9999",
                "licensePlate": "ABC-1234",
                "securityChecks": {
                    "doors": True,
                    "windows": True,
                    "handbrake": True,
                    "seatbelt": True,
                    "mirrors": True,
                },
                "termsAccepted": True,
            }
        }


# ---------------------------------------------
# 2. Dados usados para confirmar operação
# ---------------------------------------------


class ProcessingRequest(BaseModel):
    """
    Estrutura enviada no POST /api/confirmar-operacao
    Utiliza o checkInId gerado na etapa incial

    """
    checkInId: UUID = Field(..., description="ID único do check-in gerado na primeira etapa")
    
    vehicleCategory: str = Field(..., description="Categoria do veículo")
    
    licensePlate: str = Field(..., description="Placa do veículo")
    
    class Config:
        json_schema_extra = {
            "example": {
                "checkInId": "b12d2c77-51db-4eaf-89dc-482c9f88f650",
                "vehicleCategory": "carro",
                "licensePlate": "ABC-1234"
            }
        }

# -------------------------------
# 3. Resposta padrão da API
# -------------------------------
class ProcessingApiResponse(BaseModel):
    """
    Resposta padrão para qualquer chamada da API,
    incluindo sucesso, mensagem e dados opcionais.
    """
    success: bool = Field(..., description="Indica se a operação foi bem sucedida")
    message: str = Field(..., description="Mensagem explicativa do resultado")
    data: Optional[Dict] = Field(default=None, description="Payload com dados adicionais, opcional")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Check-in submetido com sucesso",
                "data": {
                    "checkInId": "b12d2c77-51db-4eaf-89dc-482c9f88f650"
                }
            }
        }