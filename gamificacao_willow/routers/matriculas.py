from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict, Union

# Importações atualizadas para usar os schemas com as novas estruturas
from schemas import (
    Matricula,
    BulkMatriculaCreate,
    HistoricoXPPontoSchema,
    BulkMatriculaByTurmaCreate,
    BulkCompleteMatriculaGuildRequest # NOVO SCHEMA IMPORTADO
)
from models import (
    Matricula as ModelMatricula,
    Aluno as ModelAluno,
    Atividade as ModelAtividade, 
    HistoricoXPPonto,
    Guilda as ModelGuilda,
    Turma as ModelTurma 
)
from database import get_db

# Importa _check_and_award_level_badges e _load_aluno_for_response do roteador de alunos
# O _load_aluno_for_response será usado para formatar a resposta do aluno corretamente
from routers.alunos import _check_and_award_level_badges, _load_aluno_for_response

matriculas_router = APIRouter()

@matriculas_router.post("/matriculas/bulk-by-turma", response_model=List[Matricula], status_code=status.HTTP_201_CREATED)
def create_bulk_matriculas_by_turma(bulk_data: BulkMatriculaByTurmaCreate, db: Session = Depends(get_db)):
    """
    Cria matrículas em massa para todos os alunos de uma turma específica (incluindo todas as guildas da turma) em uma dada atividade.
    Evita matricular alunos que já estão matriculados na atividade.

    Args:
        bulk_data: Contém o ID da atividade e o ID da turma para a matrícula em massa.

    Returns:
        List[Matricula]: Uma lista das matrículas criadas ou existentes.

    Raises:
        HTTPException: 404 - Atividade, Turma, Guildas na turma ou Alunos na turma não encontrados.
    """
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.id == bulk_data.atividade_id).first()
    if db_atividade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Atividade com ID {bulk_data.atividade_id} não encontrada.")

    db_turma = db.query(ModelTurma).options(joinedload(ModelTurma.guildas).joinedload(ModelGuilda.alunos)).filter(ModelTurma.id == bulk_data.turma_id).first()
    if not db_turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Turma com ID {bulk_data.turma_id} não encontrada.")
    
    if not db_turma.guildas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhuma guilda encontrada para a Turma com ID {bulk_data.turma_id}. Não é possível matricular alunos.")

    all_alunos_in_turma = set()
    for guilda in db_turma.guildas:
        for aluno in guilda.alunos:
            all_alunos_in_turma.add(aluno)

    if not all_alunos_in_turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado nas guildas da Turma com ID {bulk_data.turma_id}.")

    created_matriculas = []
    for aluno in all_alunos_in_turma:
        existing_matricula = db.query(ModelMatricula).filter(
            ModelMatricula.aluno_id == aluno.id,
            ModelMatricula.atividade_id == bulk_data.atividade_id
        ).first()

        if existing_matricula is None:
            new_matricula = ModelMatricula(aluno_id=aluno.id, atividade_id=bulk_data.atividade_id)
            db.add(new_matricula)
            created_matriculas.append(Matricula.from_orm(new_matricula))
        else:
            print(f"Aluno {aluno.nome} (ID: {aluno.id}) já matriculado na atividade '{db_atividade.nome}'. Matrícula ignorada.")
            created_matriculas.append(Matricula.from_orm(existing_matricula))

    db.commit()
    for matricula_obj in created_matriculas:
        db.refresh(matricula_obj._sa_instance_state.obj) 
    
    return created_matriculas

@matriculas_router.post("/matriculas/bulk-by-guild", response_model=List[Matricula], status_code=status.HTTP_201_CREATED)
def create_bulk_matriculas_by_guild(bulk_data: BulkMatriculaCreate, db: Session = Depends(get_db)):
    """
    Cria matrículas em massa para todos os alunos de uma guilda específica em uma dada atividade.
    Evita matricular alunos que já estão matriculados na atividade.

    Args:
        bulk_data: Contém o ID da atividade e o ID da guilda para a matrícula em massa.

    Returns:
        List[Matricula]: Uma lista das matrículas criadas ou existentes.

    Raises:
        HTTPException: 404 - Atividade, Guilda ou Alunos na guilda não encontrados.
    """
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.id == bulk_data.atividade_id).first()
    if db_atividade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Atividade com ID {bulk_data.atividade_id} não encontrada.")

    db_guilda = db.query(ModelGuilda).filter(ModelGuilda.id == bulk_data.guilda_id).first()
    if not db_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Guilda com ID {bulk_data.guilda_id} não encontrada.")

    db_alunos_na_guilda = db.query(ModelAluno).filter(ModelAluno.guilda_id == bulk_data.guilda_id).all()
    if not db_alunos_na_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado na guilda com ID {bulk_data.guilda_id}.")

    created_matriculas = []
    for aluno in db_alunos_na_guilda:
        existing_matricula = db.query(ModelMatricula).filter(
            ModelMatricula.aluno_id == aluno.id,
            ModelMatricula.atividade_id == bulk_data.atividade_id
        ).first()

        if existing_matricula is None:
            new_matricula = ModelMatricula(aluno_id=aluno.id, atividade_id=bulk_data.atividade_id)
            db.add(new_matricula)
            created_matriculas.append(Matricula.from_orm(new_matricula))
        else:
            print(f"Aluno {aluno.nome} (ID: {aluno.id}) já matriculado na atividade '{db_atividade.nome}'. Matrícula ignorada.")
            created_matriculas.append(Matricula.from_orm(existing_matricula))

    db.commit()
    for matricula_obj in created_matriculas:
        pass

    return created_matriculas

@matriculas_router.post("/matriculas", response_model=Matricula, status_code=status.HTTP_201_CREATED)
def create_matricula(matricula: Matricula, db: Session = Depends(get_db)):
    """
    Cria uma nova matrícula de um aluno em uma atividade.
    Verifica se o aluno e a atividade existem antes de criar a matrícula.

    Args:
        matricula: Dados da matrícula a ser criada (aluno_id, atividade_id).

    Returns:
        Matricula: A matrícula criada.

    Raises:
        HTTPException: 404 - Aluno ou Atividade não encontrada.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == matricula.aluno_id).first()
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.id == matricula.atividade_id).first()

    if db_aluno is None or db_atividade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno ou Atividade não encontrada")

    db_matricula = ModelMatricula(**matricula.dict())
    db.add(db_matricula)
    db.commit()
    db.refresh(db_matricula)
    return Matricula.from_orm(db_matricula)

@matriculas_router.put("/matriculas/{matricula_id}/complete", response_model=Matricula)
def atividade_completa(matricula_id: int, score: int, db: Session = Depends(get_db)):
    """
    Marca uma atividade como concluída, registra a pontuação do aluno na atividade,
    e atualiza o XP, pontos totais e pontos acadêmicos do aluno, além de verificar
    e conceder distintivos de nível.

    Args:
        matricula_id: O ID da matrícula a ser concluída.
        score: A pontuação do aluno na atividade.

    Returns:
        Matricula: A matrícula atualizada.

    Raises:
        HTTPException: 404 - Matrícula não encontrada.
    """
    db_matricula = db.query(ModelMatricula).filter(ModelMatricula.id == matricula_id).first()
    if db_matricula is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada")

    db_matricula.status = "concluido"
    db_matricula.score_in_quest = score
    
    aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == db_matricula.aluno_id).first()
    atividade = db.query(ModelAtividade).filter(ModelAtividade.id == db_matricula.atividade_id).first()
    
    xp_ganho = 0
    pontos_totais_ganhos = 0
    pontos_academicos_ganhos = 0

    if aluno and atividade:
        xp_ganho = atividade.xp_on_completion
        pontos_totais_ganhos = score
        pontos_academicos_ganhos = atividade.points_on_completion

        aluno.xp += xp_ganho
        aluno.total_points += pontos_totais_ganhos
        aluno.academic_score += pontos_academicos_ganhos
        aluno.level = (aluno.xp // 100) + 1
        db.add(aluno)

    db.commit()
    db.refresh(db_matricula)
    
    if aluno and atividade:
        historico_xp = HistoricoXPPonto(
            aluno_id=aluno.id,
            tipo_transacao="ganho_xp_atividade",
            valor_xp_alterado=xp_ganho,
            valor_pontos_alterado=float(pontos_totais_ganhos),
            motivo=f"Conclusão da Atividade '{atividade.nome}' ({atividade.codigo}) com score {score}",
            referencia_entidade="matricula",
            referencia_id=db_matricula.id
        )
        db.add(historico_xp)

        if pontos_academicos_ganhos > 0:
            historico_pontos_academicos = HistoricoXPPonto(
                aluno_id=aluno.id,
                tipo_transacao="ganho_pontos_academicos_atividade",
                valor_xp_alterado=0, 
                valor_pontos_alterado=pontos_academicos_ganhos,
                motivo=f"Pontos Acadêmicos pela Atividade '{atividade.nome}' ({atividade.codigo})",
                referencia_entidade="atividade",
                referencia_id=atividade.id
            )
            db.add(historico_pontos_academicos)

    db.commit()

    if aluno:
        _check_and_award_level_badges(aluno, db)
        db.commit()
        db.refresh(aluno)
    
    return Matricula.from_orm(db_matricula)

@matriculas_router.put("/matriculas/complete-by-guild", response_model=List[Matricula])
def complete_atividade_for_guild(complete_data: BulkCompleteMatriculaGuildRequest, db: Session = Depends(get_db)):
    """
    Marca uma atividade como concluída para todos os alunos de uma guilda específica.
    Atualiza o XP, pontos totais e pontos acadêmicos de cada aluno, além de verificar
    e conceder distintivos de nível.

    Args:
        complete_data: Contém o ID da atividade, o ID da guilda e a pontuação a ser aplicada.

    Returns:
        List[Matricula]: Uma lista das matrículas que foram atualizadas.

    Raises:
        HTTPException: 404 - Atividade, Guilda ou Alunos na guilda não encontrados,
                             ou se nenhum aluno tiver matrícula para a atividade.
    """
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.id == complete_data.atividade_id).first()
    if db_atividade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Atividade com ID {complete_data.atividade_id} não encontrada.")

    db_guilda = db.query(ModelGuilda).filter(ModelGuilda.id == complete_data.guilda_id).first()
    if not db_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Guilda com ID {complete_data.guilda_id} não encontrada.")

    db_alunos_na_guilda = db.query(ModelAluno).options(joinedload(ModelAluno.matriculas)).filter(ModelAluno.guilda_id == complete_data.guilda_id).all()
    if not db_alunos_na_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado na guilda com ID {complete_data.guilda_id}.")

    updated_matriculas = []
    historico_registros = []

    for aluno in db_alunos_na_guilda:
        # Tenta encontrar uma matrícula existente para o aluno e a atividade
        db_matricula = next(
            (m for m in aluno.matriculas if m.atividade_id == complete_data.atividade_id),
            None
        )

        if db_matricula:
            if db_matricula.status == "concluido":
                print(f"Matrícula do aluno {aluno.nome} (ID: {aluno.id}) na atividade '{db_atividade.nome}' já está concluída. Ignorando.")
                updated_matriculas.append(Matricula.from_orm(db_matricula))
                continue

            db_matricula.status = "concluido"
            db_matricula.score_in_quest = complete_data.score
            
            xp_ganho = db_atividade.xp_on_completion
            pontos_totais_ganhos = complete_data.score
            pontos_academicos_ganhos = db_atividade.points_on_completion

            aluno.xp += xp_ganho
            aluno.total_points += pontos_totais_ganhos
            aluno.academic_score += pontos_academicos_ganhos
            aluno.level = (aluno.xp // 100) + 1
            
            db.add(aluno)
            db.add(db_matricula)
            
            historico_registros.append(HistoricoXPPonto(
                aluno_id=aluno.id,
                tipo_transacao="ganho_xp_atividade_em_massa",
                valor_xp_alterado=xp_ganho,
                valor_pontos_alterado=float(pontos_totais_ganhos),
                motivo=f"Conclusão em massa da Atividade '{db_atividade.nome}' ({db_atividade.codigo}) para a guilda '{db_guilda.nome}' com score {complete_data.score}",
                referencia_entidade="matricula",
                referencia_id=db_matricula.id
            ))

            if pontos_academicos_ganhos > 0:
                historico_registros.append(HistoricoXPPonto(
                    aluno_id=aluno.id,
                    tipo_transacao="ganho_pontos_academicos_atividade_em_massa",
                    valor_xp_alterado=0, 
                    valor_pontos_alterado=pontos_academicos_ganhos,
                    motivo=f"Pontos Acadêmicos em massa pela Atividade '{db_atividade.nome}' ({db_atividade.codigo}) para a guilda '{db_guilda.nome}'",
                    referencia_entidade="atividade",
                    referencia_id=db_atividade.id
                ))
            updated_matriculas.append(Matricula.from_orm(db_matricula))
        else:
            print(f"Aluno {aluno.nome} (ID: {aluno.id}) não possui matrícula para a atividade '{db_atividade.nome}'. Ignorando.")

    if not updated_matriculas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno da guilda com ID {complete_data.guilda_id} possui matrícula para a atividade com ID {complete_data.atividade_id} para ser concluída.")

    db.add_all(historico_registros)
    db.commit()

    # Refresh all updated students and check for badges after commit
    for matricula_data in updated_matriculas:
        db_aluno = db.query(ModelAluno).filter(ModelAluno.id == matricula_data.aluno_id).first()
        if db_aluno:
            db.refresh(db_aluno)
            _check_and_award_level_badges(db_aluno, db)
            db.commit() # Commit after badge check for each student

    return updated_matriculas

@matriculas_router.get("/matriculas/aluno/{nome_aluno}", response_model=Dict[str, Union[str, List[str]]])
def read_matriculas_por_nome_aluno(nome_aluno: str, db: Session = Depends(get_db)):
    """
    Retorna uma lista de atividades nas quais um aluno (identificado pelo nome) está matriculado,
    incluindo informações sobre a guilda e turma do aluno.

    Args:
        nome_aluno: O nome do aluno para buscar as matrículas.

    Returns:
        Dict: Um dicionário contendo o nome, apelido, guilda, turma do aluno e as atividades matriculadas.

    Raises:
        HTTPException: 404 - Aluno ou matrículas não encontradas.
    """
    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.nome.ilike(f"%{nome_aluno}%")).first()

    if not db_aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")

    atividades_matriculadas = []
    for matricula in db_aluno.matriculas:
        atividade = matricula.atividade
        if atividade:
            atividades_matriculadas.append(atividade.nome)

    if not atividades_matriculadas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"O aluno '{db_aluno.nome}' não possui matrículas cadastradas.")
    
    guilda_nome = db_aluno.guilda_obj.nome if db_aluno.guilda_obj else None
    turma_nome = db_aluno.guilda_obj.turma.nome if db_aluno.guilda_obj and db_aluno.guilda_obj.turma else None

    return {
        "aluno_nome": db_aluno.nome,
        "aluno_apelido": db_aluno.apelido,
        "guilda_nome": guilda_nome,
        "turma_nome": turma_nome,
        "atividades_matriculadas": atividades_matriculadas
    }

@matriculas_router.get("/matriculas/aluno/{aluno_id}/details", response_model=List[Matricula])
def read_matriculas_details_por_aluno(aluno_id: int, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de todas as matrículas de um aluno específico, com base no ID fornecido.

    Args:
        aluno_id: O ID do aluno para buscar os detalhes das matrículas.

    Returns:
        List[Matricula]: Uma lista de objetos Matrícula com todos os detalhes.

    Raises:
        HTTPException: 404 - Aluno ou matrículas não encontradas.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Aluno com ID {aluno_id} não encontrado.")

    db_matriculas = db.query(ModelMatricula).filter(ModelMatricula.aluno_id == aluno_id).all()
    
    if not db_matriculas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhuma matrícula encontrada para o aluno com ID {aluno_id}.")
    
    return [Matricula.from_orm(m) for m in db_matriculas]

@matriculas_router.get("/matriculas/atividade/{codigo_atividade}", response_model=Dict[str, Union[str, List[str]]])
def read_alunos_matriculados_por_codigo_atividade(codigo_atividade: str, db: Session = Depends(get_db)):
    """
    Retorna uma lista de alunos matriculados em uma atividade específica, identificada pelo seu código.
    Inclui informações da guilda e turma dos alunos.

    Args:
        codigo_atividade: O código da atividade para buscar os alunos matriculados.

    Returns:
        Dict: Um dicionário contendo o nome da atividade e a lista de alunos matriculados.

    Raises:
        HTTPException: 404 - Atividade ou alunos matriculados não encontrados.
    """
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.codigo == codigo_atividade).first()

    if not db_atividade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada")

    alunos_matriculados = []
    for matricula in db_atividade.matriculas:
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno matriculado na atividade '{db_atividade.nome}'.")

    return {"atividade": db_atividade.nome, "alunos": alunos_matriculados}