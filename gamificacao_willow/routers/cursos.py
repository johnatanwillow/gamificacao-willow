from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from schemas import Curso # Assumindo que schemas.Curso foi atualizado com xp_on_completion e points_on_completion
from models import Curso as ModelCurso # Importe o modelo atualizado
from database import get_db

cursos_router = APIRouter()

@cursos_router.get("/cursos", response_model=List[Curso])
def read_cursos(db: Session = Depends(get_db)):
    """
    Retorna uma lista de todos os cursos (quests) disponíveis, incluindo informações de gamificação.
    """
    cursos = db.query(ModelCurso).all()
    return [Curso.from_orm(curso) for curso in cursos]

@cursos_router.post("/cursos", response_model=Curso, status_code=status.HTTP_201_CREATED)
def create_curso(curso: Curso, db: Session = Depends(get_db)):
    """
    Cria um novo curso (quest) com seus atributos, incluindo XP e pontos de recompensa.

    Args:
        curso: Dados do curso a ser criado (incluindo xp_on_completion e points_on_completion).

    Returns:
        Curso: O curso criado.
    """
    # Exclua 'id' na criação, ele é gerado automaticamente
    db_curso = ModelCurso(**curso.dict(exclude={"id"}))
    db.add(db_curso)
    db.commit()
    db.refresh(db_curso)
    return Curso.from_orm(db_curso)

@cursos_router.put("/cursos/{codigo_curso}", response_model=Curso)
def update_curso(codigo_curso: str, curso: Curso, db: Session = Depends(get_db)):
    """
    Atualiza os dados de um curso (quest) existente pelo seu código.

    Args:
        codigo_curso: O código do curso a ser atualizado.
        curso: Os novos dados do curso (incluindo xp_on_completion e points_on_completion).

    Raises:
        HTTPException: 404 - Curso não encontrado.

    Returns:
        Curso: O curso atualizado.
    """
    db_curso = db.query(ModelCurso).filter(ModelCurso.codigo == codigo_curso).first()
    if db_curso is None:
        raise HTTPException(status_code=404, detail="Curso não encontrado")

    # Itera sobre os campos do Pydantic model 'curso' e atualiza o objeto do DB
    # Exclua 'id' e 'codigo' da atualização se eles não devem ser alterados via PUT
    for key, value in curso.dict(exclude_unset=True, exclude={"id", "codigo"}).items():
        setattr(db_curso, key, value)

    db.commit()
    db.refresh(db_curso)
    return Curso.from_orm(db_curso)

@cursos_router.get("/cursos/{codigo_curso}", response_model=Curso)
def read_curso_por_codigo(codigo_curso: str, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de um curso (quest) específico com base no código fornecido.
    """
    db_curso = db.query(ModelCurso).filter(ModelCurso.codigo == codigo_curso).first()
    if db_curso is None:
        raise HTTPException(status_code=404, detail="Nenhum curso encontrado com esse código")
    return Curso.from_orm(db_curso)

# As rotas para buscar por ID e deletar cursos são mantidas comentadas conforme o README original.