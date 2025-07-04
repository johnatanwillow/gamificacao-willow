from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Union
from schemas import Matricula, BulkMatriculaCreate # Importe seu schema de Matricula
from models import Matricula as ModelMatricula, Aluno as ModelAluno, Curso as ModelCurso, HistoricoXPPonto # Importe o novo modelo HistoricoXPPonto
from database import get_db

from routers.alunos import _check_and_award_level_badges 

matriculas_router = APIRouter()

@matriculas_router.post("/matriculas", response_model=Matricula, status_code=status.HTTP_201_CREATED)
def create_matricula(matricula: Matricula, db: Session = Depends(get_db)):
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == matricula.aluno_id).first()
    db_curso = db.query(ModelCurso).filter(ModelCurso.id == matricula.curso_id).first()

    if db_aluno is None or db_curso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno ou Curso não encontrado")

    db_matricula = ModelMatricula(**matricula.dict())
    db.add(db_matricula)
    db.commit()
    db.refresh(db_matricula)
    return Matricula.from_orm(db_matricula)


@matriculas_router.get("/matriculas/aluno/{nome_aluno}", response_model=Dict[str, Union[str, List[str]]])
def read_matriculas_por_nome_aluno(nome_aluno: str, db: Session = Depends(get_db)):
    db_aluno = db.query(ModelAluno).filter(ModelAluno.nome.ilike(f"%{nome_aluno}%")).first()

    if not db_aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")

    cursos_matriculados = []
    for matricula in db_aluno.matriculas:
        curso = matricula.curso  
        if curso:  
            cursos_matriculados.append(curso.nome)

    if not cursos_matriculados:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"O aluno '{nome_aluno}' não possui matrículas cadastradas.")

    return {"aluno": db_aluno.nome, "cursos": cursos_matriculados}

@matriculas_router.get("/matriculas/aluno/{aluno_id}/details", response_model=List[Matricula])
def read_matriculas_details_por_aluno(aluno_id: int, db: Session = Depends(get_db)):
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Aluno com ID {aluno_id} não encontrado.")

    db_matriculas = db.query(ModelMatricula).filter(ModelMatricula.aluno_id == aluno_id).all()
    
    if not db_matriculas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhuma matrícula encontrada para o aluno com ID {aluno_id}.")
    
    return [Matricula.from_orm(m) for m in db_matriculas]


@matriculas_router.get("/matriculas/curso/{codigo_curso}", response_model=Dict[str, Union[str, List[str]]])
def read_alunos_matriculados_por_codigo_curso(codigo_curso: str, db: Session = Depends(get_db)):
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

@matriculas_router.put("/matriculas/{matricula_id}/complete", response_model=Matricula)
def complete_matricula(matricula_id: int, score: int, db: Session = Depends(get_db)):
    db_matricula = db.query(ModelMatricula).filter(ModelMatricula.id == matricula_id).first()
    if db_matricula is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada")

    db_matricula.status = "concluido"
    db_matricula.score_in_quest = score
    
    aluno = db.query(ModelAluno).filter(ModelAluno.id == db_matricula.aluno_id).first()
    curso = db.query(ModelCurso).filter(ModelCurso.id == db_matricula.curso_id).first()
    
    xp_ganho = 0
    pontos_totais_ganhos = 0
    pontos_academicos_ganhos = 0

    if aluno and curso:
        xp_ganho = curso.xp_on_completion
        pontos_totais_ganhos = score
        pontos_academicos_ganhos = curso.points_on_completion

        aluno.xp += xp_ganho
        aluno.total_points += pontos_totais_ganhos
        aluno.academic_score += pontos_academicos_ganhos # Garante que o academic_score seja atualizado aqui
        aluno.level = (aluno.xp // 100) + 1
        db.add(aluno)

    db.commit()
    db.refresh(db_matricula)
    
    if aluno and curso:
        historico_xp = HistoricoXPPonto(
            aluno_id=aluno.id,
            tipo_transacao="ganho_xp_quest",
            valor_xp_alterado=xp_ganho,
            valor_pontos_alterado=pontos_totais_ganhos,
            motivo=f"Conclusão da Quest '{curso.nome}' ({curso.codigo}) com score {score}",
            referencia_entidade="matricula",
            referencia_id=db_matricula.id
        )
        db.add(historico_xp)

        # Se os pontos acadêmicos forem registrados separadamente no histórico
        if pontos_academicos_ganhos > 0:
            historico_pontos_academicos = HistoricoXPPonto(
                aluno_id=aluno.id,
                tipo_transacao="ganho_pontos_academicos_quest",
                valor_xp_alterado=0, # Não altera XP neste tipo de transação
                valor_pontos_alterado=pontos_academicos_ganhos,
                motivo=f"Pontos Acadêmicos pela Quest '{curso.nome}' ({curso.codigo})",
                referencia_entidade="curso", # Referencia o curso para pontos acadêmicos
                referencia_id=curso.id
            )
            db.add(historico_pontos_academicos)

    db.commit() # Commit dos registros de histórico

    if aluno:
        _check_and_award_level_badges(aluno, db)
        db.commit()
        db.refresh(aluno)
    
    return Matricula.from_orm(db_matricula)

@matriculas_router.post("/matriculas/bulk-by-guild", response_model=List[Matricula], status_code=status.HTTP_201_CREATED)
def create_bulk_matriculas_by_guild(bulk_data: BulkMatriculaCreate, db: Session = Depends(get_db)):
    db_curso = db.query(ModelCurso).filter(ModelCurso.id == bulk_data.curso_id).first()
    if db_curso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Curso com ID {bulk_data.curso_id} não encontrado.")

    db_alunos_na_guilda = db.query(ModelAluno).filter(ModelAluno.guilda == bulk_data.guild_name).all()
    if not db_alunos_na_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado na guilda '{bulk_data.guild_name}'.")

    created_matriculas = []
    for aluno in db_alunos_na_guilda:
        existing_matricula = db.query(ModelMatricula).filter(
            ModelMatricula.aluno_id == aluno.id,
            ModelMatricula.curso_id == bulk_data.curso_id
        ).first()

        if existing_matricula is None:
            new_matricula = ModelMatricula(aluno_id=aluno.id, curso_id=bulk_data.curso_id)
            db.add(new_matricula)
            created_matriculas.append(Matricula.from_orm(new_matricula))
        else:
            print(f"Aluno {aluno.nome} (ID: {aluno.id}) já matriculado no curso '{db_curso.nome}'. Matrícula ignorada.")
            created_matriculas.append(Matricula.from_orm(existing_matricula))

    db.commit()
    for matricula_obj in created_matriculas:
        pass

    return created_matriculas