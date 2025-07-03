from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Union
from schemas import Matricula # Assumindo que schemas.Matricula foi atualizado com score_in_quest e status
from models import Matricula as ModelMatricula, Aluno as ModelAluno, Curso as ModelCurso # Importe os modelos atualizados com os campos de gamificação
from database import get_db

matriculas_router = APIRouter()

@matriculas_router.post("/matriculas", response_model=Matricula, status_code=status.HTTP_201_CREATED)
def create_matricula(matricula: Matricula, db: Session = Depends(get_db)):
    """
    Cria uma nova matrícula de um aluno em um curso.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == matricula.aluno_id).first()
    db_curso = db.query(ModelCurso).filter(ModelCurso.id == matricula.curso_id).first()

    if db_aluno is None or db_curso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno ou Curso não encontrado")

    # Garante que os campos de gamificação (score_in_quest, status) sejam considerados na criação
    db_matricula = ModelMatricula(**matricula.dict())
    db.add(db_matricula)
    db.commit()
    db.refresh(db_matricula)
    return Matricula.from_orm(db_matricula)


@matriculas_router.get("/matriculas/aluno/{nome_aluno}", response_model=Dict[str, Union[str, List[str]]])
def read_matriculas_por_nome_aluno(nome_aluno: str, db: Session = Depends(get_db)):
    """
    Retorna o nome do aluno e uma lista dos cursos (quests) em que ele está matriculado.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.nome.ilike(f"%{nome_aluno}%")).first()

    if not db_aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")

    cursos_matriculados = []
    for matricula in db_aluno.matriculas:
        curso = matricula.curso  
        if curso:  
            cursos_matriculados.append(curso.nome)

    if not cursos_matriculados:
        raise HTTPException(status_code=404, detail=f"O aluno '{nome_aluno}' não possui matrículas cadastradas.")

    return {"aluno": db_aluno.nome, "cursos": cursos_matriculados}

@matriculas_router.get("/matriculas/curso/{codigo_curso}", response_model=Dict[str, Union[str, List[str]]])
def read_alunos_matriculados_por_codigo_curso(codigo_curso: str, db: Session = Depends(get_db)):
    """
    Retorna o nome do curso (quest) e uma lista com os nomes dos alunos matriculados nele.
    """
    db_curso = db.query(ModelCurso).filter(ModelCurso.codigo == codigo_curso).first()

    if not db_curso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso não encontrado")

    alunos_matriculados = []
    for matricula in db_curso.matriculas:  
        aluno = matricula.aluno  
        if aluno:  
            alunos_matriculados.append(aluno.nome)

    if not alunos_matriculados:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno matriculado no curso '{db_curso.nome}'.")

    return {"curso": db_curso.nome, "alunos": alunos_matriculados}

# --- Nova rota para Gamificação: Concluir uma Matrícula/Quest ---
@matriculas_router.put("/matriculas/{matricula_id}/complete", response_model=Matricula)
def complete_matricula(matricula_id: int, score: int, db: Session = Depends(get_db)):
    """
    Atualiza o status de uma matrícula para 'concluído' e registra a pontuação final da quest.
    Também adiciona XP e pontos ao aluno com base na conclusão do curso.

    Args:
        matricula_id: O ID da matrícula a ser atualizada.
        score: A pontuação final obtida pelo aluno nesta quest.

    Raises:
        HTTPException: 404 - Matrícula não encontrada.

    Returns:
        Matricula: A matrícula atualizada com o novo status e pontuação.
    """
    db_matricula = db.query(ModelMatricula).filter(ModelMatricula.id == matricula_id).first()
    if db_matricula is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada")

    db_matricula.status = "concluido"
    db_matricula.score_in_quest = score
    
    # Opcional: Adicionar XP/pontos ao aluno automaticamente ao completar uma quest/curso
    aluno = db.query(ModelAluno).filter(ModelAluno.id == db_matricula.aluno_id).first()
    curso = db.query(ModelCurso).filter(ModelCurso.id == db_matricula.curso_id).first()
    if aluno and curso:
        aluno.xp += curso.xp_on_completion # Usa XP definido no curso
        aluno.total_points += score # Adiciona a pontuação da quest aos pontos totais
        aluno.level = (aluno.xp // 100) + 1 # Recalcula o nível (exemplo: cada 100 XP é um nível)
        db.add(aluno) # Garante que as mudanças no aluno sejam salvas

    db.commit()
    db.refresh(db_matricula)
    return Matricula.from_orm(db_matricula)