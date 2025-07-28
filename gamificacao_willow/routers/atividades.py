from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from schemas import Atividade, AtividadeCreate, AtividadeBase # Importar AtividadeBase e AtividadeCreate
from models import Atividade as ModelAtividade
from database import get_db

atividades_router = APIRouter()

@atividades_router.get("/atividades", response_model=List[Atividade])
def read_atividades(db: Session = Depends(get_db)):
    """
    Retorna uma lista de todas as atividades (quests) disponíveis, incluindo informações de gamificação.

    Returns:
        List[Atividade]: Uma lista de objetos Atividade.
    """
    atividades = db.query(ModelAtividade).all()
    return [Atividade.from_orm(atividade) for atividade in atividades]

@atividades_router.post("/atividades", response_model=Atividade, status_code=status.HTTP_201_CREATED)
def create_atividade(atividade: AtividadeCreate, db: Session = Depends(get_db)): # Usar AtividadeCreate
    """
    Cria uma nova atividade (quest) com seus atributos, incluindo XP e pontos de recompensa por conclusão.

    Args:
        atividade: Dados da atividade a ser criada (incluindo nome, codigo, descricao, xp_on_completion e points_on_completion).

    Returns:
        Atividade: A atividade criada.
    """
    db_atividade = ModelAtividade(**atividade.dict()) # Remover exclude={"id"}
    db.add(db_atividade)
    db.commit()
    db.refresh(db_atividade)
    return Atividade.from_orm(db_atividade)

@atividades_router.put("/atividades/{codigo_atividade}", response_model=Atividade)
def update_atividade(codigo_atividade: str, atividade: AtividadeBase, db: Session = Depends(get_db)): # Usar AtividadeBase
    """
    Atualiza os dados de uma atividade (quest) existente pelo seu código.
    Permite atualizar o nome, descrição, XP e pontos de recompensa.

    Args:
        codigo_atividade: O código da atividade a ser atualizada.
        atividade: Os novos dados da atividade.

    Returns:
        Atividade: A atividade atualizada.

    Raises:
        HTTPException: 404 - Atividade não encontrada.
    """
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.codigo == codigo_atividade).first()
    if db_atividade is None:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")

    for key, value in atividade.dict(exclude_unset=True).items(): # Remover exclude={"id", "codigo"}
        setattr(db_atividade, key, value)

    db.commit()
    db.refresh(db_atividade)
    return Atividade.from_orm(db_atividade)

@atividades_router.get("/atividades/{codigo_atividade}", response_model=Atividade)
def read_atividade_por_codigo(codigo_atividade: str, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de uma atividade (quest) específica com base no código fornecido.

    Args:
        codigo_atividade: O código da atividade para buscar os detalhes.

    Returns:
        Atividade: O objeto Atividade correspondente ao código.

    Raises:
        HTTPException: 404 - Nenhuma atividade encontrada com o código fornecido.
    """
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.codigo == codigo_atividade).first()
    if db_atividade is None:
        raise HTTPException(status_code=404, detail="Nenhuma atividade encontrada com esse código")
    return Atividade.from_orm(db_atividade)