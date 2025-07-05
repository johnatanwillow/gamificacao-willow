from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload # Adicionado joinedload
from typing import List, Dict, Union

# Importações atualizadas para usar os schemas com as novas estruturas
from schemas import (
    Matricula,
    BulkMatriculaCreate, # Este schema foi modificado para usar guilda_id
    HistoricoXPPontoSchema # Mantido, se precisar criar registros aqui
)
from models import (
    Matricula as ModelMatricula,
    Aluno as ModelAluno,
    Atividade as ModelAtividade, # MODIFICADO: Importar Atividade ao invés de Curso
    HistoricoXPPonto, # Modelo do histórico
    Guilda as ModelGuilda, # NOVO: Importar modelo da Guilda
    Turma as ModelTurma # NOVO: Importar modelo da Turma
)
from database import get_db

# Importa _check_and_award_level_badges e _load_aluno_for_response do roteador de alunos
# O _load_aluno_for_response será usado para formatar a resposta do aluno corretamente
from routers.alunos import _check_and_award_level_badges, _load_aluno_for_response

matriculas_router = APIRouter()

@matriculas_router.post("/matriculas", response_model=Matricula, status_code=status.HTTP_201_CREATED)
def create_matricula(matricula: Matricula, db: Session = Depends(get_db)):
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == matricula.aluno_id).first()
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.id == matricula.atividade_id).first() # MODIFICADO: db_atividade e matricula.atividade_id

    if db_aluno is None or db_atividade is None: # MODIFICADO: Atividade não encontrada
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno ou Atividade não encontrada") # MODIFICADO: Atividade não encontrada

    db_matricula = ModelMatricula(**matricula.dict())
    db.add(db_matricula)
    db.commit()
    db.refresh(db_matricula)
    return Matricula.from_orm(db_matricula)


@matriculas_router.get("/matriculas/aluno/{nome_aluno}", response_model=Dict[str, Union[str, List[str]]])
def read_matriculas_por_nome_aluno(nome_aluno: str, db: Session = Depends(get_db)):
    # Modificado para carregar guilda e turma do aluno
    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.nome.ilike(f"%{nome_aluno}%")).first()

    if not db_aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")

    atividades_matriculadas = [] # MODIFICADO: renomeado para atividades_matriculadas
    for matricula in db_aluno.matriculas:
        atividade = matricula.atividade # MODIFICADO: renomeado para atividade
        if atividade: # MODIFICADO: renomeado para atividade
            atividades_matriculadas.append(atividade.nome) # MODIFICADO: renomeado para atividade.nome

    if not atividades_matriculadas: # MODIFICADO: renomeado para atividades_matriculadas
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"O aluno '{db_aluno.nome}' não possui matrículas cadastradas.")
    
    # Retorna o nome da guilda e turma do aluno
    guilda_nome = db_aluno.guilda_obj.nome if db_aluno.guilda_obj else None
    turma_nome = db_aluno.guilda_obj.turma.nome if db_aluno.guilda_obj and db_aluno.guilda_obj.turma else None

    return {
        "aluno_nome": db_aluno.nome,
        "aluno_apelido": db_aluno.apelido,
        "guilda_nome": guilda_nome,
        "turma_nome": turma_nome,
        "atividades_matriculadas": atividades_matriculadas # MODIFICADO: renomeado para atividades_matriculadas
    }

@matriculas_router.get("/matriculas/aluno/{aluno_id}/details", response_model=List[Matricula])
def read_matriculas_details_por_aluno(aluno_id: int, db: Session = Depends(get_db)):
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Aluno com ID {aluno_id} não encontrado.")

    db_matriculas = db.query(ModelMatricula).filter(ModelMatricula.aluno_id == aluno_id).all()
    
    if not db_matriculas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhuma matrícula encontrada para o aluno com ID {aluno_id}.")
    
    return [Matricula.from_orm(m) for m in db_matriculas]


@matriculas_router.get("/matriculas/atividade/{codigo_atividade}", response_model=Dict[str, Union[str, List[str]]]) # MODIFICADO: /atividade/{codigo_atividade}
def read_alunos_matriculados_por_codigo_atividade(codigo_atividade: str, db: Session = Depends(get_db)): # MODIFICADO: codigo_atividade
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.codigo == codigo_atividade).first() # MODIFICADO: db_atividade, ModelAtividade, codigo_atividade

    if not db_atividade: # MODIFICADO: db_atividade
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada") # MODIFICADO: Atividade não encontrada

    alunos_matriculados = []
    # Modificado para carregar guilda e turma do aluno na lista de alunos matriculados
    for matricula in db_atividade.matriculas: # MODIFICADO: db_atividade.matriculas
        aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == matricula.aluno_id).first()
        if aluno:  
            alunos_matriculados.append({
                "aluno_id": aluno.id,
                "aluno_nome": aluno.nome,
                "aluno_apelido": aluno.apelido,
                "guilda_nome": aluno.guilda_obj.nome if aluno.guilda_obj else None,
                "turma_nome": aluno.guilda_obj.turma.nome if aluno.guilda_obj and aluno.guilda_obj.turma else None
            })

    if not alunos_matriculados:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno matriculado na atividade '{db_atividade.nome}'.") # MODIFICADO: na atividade '{db_atividade.nome}'

    return {"atividade": db_atividade.nome, "alunos": alunos_matriculados} # MODIFICADO: "atividade": db_atividade.nome

@matriculas_router.put("/matriculas/{matricula_id}/complete", response_model=Matricula)
def complete_matricula(matricula_id: int, score: int, db: Session = Depends(get_db)):
    db_matricula = db.query(ModelMatricula).filter(ModelMatricula.id == matricula_id).first()
    if db_matricula is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada")

    db_matricula.status = "concluido"
    db_matricula.score_in_quest = score
    
    # Carrega o aluno e atividade com os relacionamentos necessários para o histórico e badges
    aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == db_matricula.aluno_id).first()
    atividade = db.query(ModelAtividade).filter(ModelAtividade.id == db_matricula.atividade_id).first() # MODIFICADO: atividade e db_matricula.atividade_id
    
    xp_ganho = 0
    pontos_totais_ganhos = 0
    pontos_academicos_ganhos = 0

    if aluno and atividade: # MODIFICADO: atividade
        xp_ganho = atividade.xp_on_completion # MODIFICADO: atividade.xp_on_completion
        pontos_totais_ganhos = score
        pontos_academicos_ganhos = atividade.points_on_completion # MODIFICADO: atividade.points_on_completion

        aluno.xp += xp_ganho
        aluno.total_points += pontos_totais_ganhos
        aluno.academic_score += pontos_academicos_ganhos
        aluno.level = (aluno.xp // 100) + 1
        db.add(aluno)

    db.commit()
    db.refresh(db_matricula)
    
    if aluno and atividade: # MODIFICADO: atividade
        # Registro de histórico para XP ganho na quest
        historico_xp = HistoricoXPPonto(
            aluno_id=aluno.id,
            tipo_transacao="ganho_xp_atividade", # MODIFICADO: ganho_xp_atividade
            valor_xp_alterado=xp_ganho,
            valor_pontos_alterado=float(pontos_totais_ganhos), # total_points, convertido para float para consistência
            motivo=f"Conclusão da Atividade '{atividade.nome}' ({atividade.codigo}) com score {score}", # MODIFICADO: Atividade '{atividade.nome}' ({atividade.codigo})
            referencia_entidade="matricula",
            referencia_id=db_matricula.id
        )
        db.add(historico_xp)

        # Registro de histórico para pontos acadêmicos ganhos na quest
        if pontos_academicos_ganhos > 0:
            historico_pontos_academicos = HistoricoXPPonto(
                aluno_id=aluno.id,
                tipo_transacao="ganho_pontos_academicos_atividade", # MODIFICADO: ganho_pontos_academicos_atividade
                valor_xp_alterado=0, 
                valor_pontos_alterado=pontos_academicos_ganhos,
                motivo=f"Pontos Acadêmicos pela Atividade '{atividade.nome}' ({atividade.codigo})", # MODIFICADO: Atividade '{atividade.nome}' ({atividade.codigo})
                referencia_entidade="atividade", # MODIFICADO: atividade
                referencia_id=atividade.id # MODIFICADO: atividade.id
            )
            db.add(historico_pontos_academicos)

    db.commit() # Commit dos registros de histórico

    if aluno:
        _check_and_award_level_badges(aluno, db)
        db.commit()
        db.refresh(aluno)
    
    return Matricula.from_orm(db_matricula)

@matriculas_router.post("/matriculas/bulk-by-guild", response_model=List[Matricula], status_code=status.HTTP_201_CREATED)
# MODIFICADO: Agora usa guilda_id do schema BulkMatriculaCreate
def create_bulk_matriculas_by_guild(bulk_data: BulkMatriculaCreate, db: Session = Depends(get_db)):
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.id == bulk_data.atividade_id).first() # MODIFICADO: db_atividade e bulk_data.atividade_id
    if db_atividade is None: # MODIFICADO: db_atividade
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Atividade com ID {bulk_data.atividade_id} não encontrada.") # MODIFICADO: Atividade com ID e bulk_data.atividade_id

    # NOVO: Valida se a guilda_id existe
    db_guilda = db.query(ModelGuilda).filter(ModelGuilda.id == bulk_data.guilda_id).first()
    if not db_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Guilda com ID {bulk_data.guilda_id} não encontrada.")

    # MODIFICADO: Filtra alunos por guilda_id
    db_alunos_na_guilda = db.query(ModelAluno).filter(ModelAluno.guilda_id == bulk_data.guilda_id).all()
    if not db_alunos_na_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado na guilda com ID {bulk_data.guilda_id}.")

    created_matriculas = []
    for aluno in db_alunos_na_guilda:
        existing_matricula = db.query(ModelMatricula).filter(
            ModelMatricula.aluno_id == aluno.id,
            ModelMatricula.atividade_id == bulk_data.atividade_id # MODIFICADO: atividade_id
        ).first()

        if existing_matricula is None:
            new_matricula = ModelMatricula(aluno_id=aluno.id, atividade_id=bulk_data.atividade_id) # MODIFICADO: atividade_id
            db.add(new_matricula)
            created_matriculas.append(Matricula.from_orm(new_matricula))
        else:
            print(f"Aluno {aluno.nome} (ID: {aluno.id}) já matriculado na atividade '{db_atividade.nome}'. Matrícula ignorada.") # MODIFICADO: na atividade '{db_atividade.nome}'
            created_matriculas.append(Matricula.from_orm(existing_matricula))

    db.commit()
    for matricula_obj in created_matriculas:
        pass # Apenas para refresh, mas o objeto já é um schema

    return created_matriculas