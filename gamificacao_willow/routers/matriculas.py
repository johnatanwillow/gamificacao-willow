from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict, Union

# Importações atualizadas para usar os schemas com as novas estruturas
from schemas import (
    Matricula,
    BulkMatriculaCreate,
    HistoricoXPPontoSchema,
    BulkMatriculaByTurmaCreate,
    BulkCompleteMatriculaGuildRequest
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
from routers.alunos import _check_and_award_level_badges, _load_aluno_for_response

matriculas_router = APIRouter()

# --- Funções Auxiliares ---
def _load_matricula_for_response(db_matricula_obj: ModelMatricula) -> Matricula:
    """
    Função auxiliar para carregar e formatar os dados de um objeto Matricula do banco de dados
    para o schema de resposta, incluindo nomes de aluno e atividade.
    Assume que as relações 'aluno' e 'atividade' do ModelMatricula estão carregadas.
    """
    return Matricula(
        id=db_matricula_obj.id,
        aluno_id=db_matricula_obj.aluno_id,
        atividade_id=db_matricula_obj.atividade_id,
        score_in_quest=db_matricula_obj.score_in_quest,
        status=db_matricula_obj.status,
        aluno_nome=db_matricula_obj.aluno.nome if db_matricula_obj.aluno else None,
        atividade_nome=db_matricula_obj.atividade.nome if db_matricula_obj.atividade else None,
    )


@matriculas_router.post("/matriculas/bulk-by-turma", response_model=List[Matricula], status_code=status.HTTP_201_CREATED)
def create_bulk_matriculas_by_turma(bulk_data: BulkMatriculaByTurmaCreate, db: Session = Depends(get_db)):
    """
    Cria matrículas em massa para todos os alunos de uma turma específica (incluindo todas as guildas da turma) em uma dada atividade.
    Evita matricular alunos que já estão matriculados na atividade.

    Args:
        bulk_data: Contém o ID da atividade e o ID da turma para a matrícula em massa.

    Returns:
        List[Matricula]: Uma lista das matrículas criadas ou existentes com nomes de aluno/atividade.

    Raises:
        HTTPException: 404 - Atividade, Turma, Guildas na turma ou Alunos na turma não encontrados.
    """
    # CORREÇÃO AQUI: bulk_data.curso_id no lugar de bulk_data.atividade_id
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.id == bulk_data.curso_id).first()
    if db_atividade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Atividade com ID {bulk_data.curso_id} não encontrada.")

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

    matriculas_to_return = []
    for aluno in all_alunos_in_turma:
        existing_matricula = db.query(ModelMatricula).options(joinedload(ModelMatricula.aluno), joinedload(ModelMatricula.atividade)).filter(
            ModelMatricula.aluno_id == aluno.id,
            ModelMatricula.atividade_id == bulk_data.curso_id # CORREÇÃO AQUI
        ).first()

        if existing_matricula is None:
            new_matricula = ModelMatricula(aluno_id=aluno.id, atividade_id=bulk_data.curso_id) # CORREÇÃO AQUI
            db.add(new_matricula)
            db.flush() # Para gerar o ID da nova matrícula antes do commit
            db.refresh(new_matricula) # Carrega as relações para o _load_matricula_for_response
            matriculas_to_return.append(_load_matricula_for_response(new_matricula))
        else:
            print(f"Aluno {aluno.nome} (ID: {aluno.id}) já matriculado na atividade '{db_atividade.nome}'. Matrícula ignorada.")
            matriculas_to_return.append(_load_matricula_for_response(existing_matricula))

    db.commit()
    return matriculas_to_return

@matriculas_router.post("/matriculas/bulk-by-guild", response_model=List[Matricula], status_code=status.HTTP_201_CREATED)
def create_bulk_matriculas_by_guild(bulk_data: BulkMatriculaCreate, db: Session = Depends(get_db)):
    """
    Cria matrículas em massa para todos os alunos de uma guilda específica em uma dada atividade.
    Evita matricular alunos que já estão matriculados na atividade.

    Args:
        bulk_data: Contém o ID da atividade e o ID da guilda para a matrícula em massa.

    Returns:
        List[Matricula]: Uma lista das matrículas criadas ou existentes com nomes de aluno/atividade.

    Raises:
        HTTPException: 404 - Atividade, Guilda ou Alunos na guilda não encontrados.
    """
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.id == bulk_data.curso_id).first()
    if db_atividade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Atividade com ID {bulk_data.curso_id} não encontrada.")

    db_guilda = db.query(ModelGuilda).options(joinedload(ModelGuilda.alunos)).filter(ModelGuilda.id == bulk_data.guilda_id).first()
    if not db_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Guilda com ID {bulk_data.guilda_id} não encontrada.")

    db_alunos_na_guilda = db_guilda.alunos # Já carregado com joinedload
    if not db_alunos_na_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado na guilda com ID {bulk_data.guilda_id}.")

    matriculas_to_return = []
    for aluno in db_alunos_na_guilda:
        existing_matricula = db.query(ModelMatricula).options(joinedload(ModelMatricula.aluno), joinedload(ModelMatricula.atividade)).filter(
            ModelMatricula.aluno_id == aluno.id,
            ModelMatricula.atividade_id == bulk_data.curso_id
        ).first()

        if existing_matricula is None:
            new_matricula = ModelMatricula(aluno_id=aluno.id, atividade_id=bulk_data.curso_id)
            db.add(new_matricula)
            db.flush() # Para gerar o ID da nova matrícula antes do commit
            db.refresh(new_matricula) # Carrega as relações para o _load_matricula_for_response
            matriculas_to_return.append(_load_matricula_for_response(new_matricula))
        else:
            print(f"Aluno {aluno.nome} (ID: {aluno.id}) já matriculado na atividade '{db_atividade.nome}'. Matrícula ignorada.")
            matriculas_to_return.append(_load_matricula_for_response(existing_matricula))

    db.commit()
    return matriculas_to_return

@matriculas_router.post("/matriculas", response_model=Matricula, status_code=status.HTTP_201_CREATED)
def create_matricula(matricula: Matricula, db: Session = Depends(get_db)):
    """
    Cria uma nova matrícula de um aluno em uma atividade.
    Verifica se o aluno e a atividade existem antes de criar a matrícula.

    Args:
        matricula: Dados da matrícula a ser criada (aluno_id, atividade_id).

    Returns:
        Matricula: A matrícula criada com nomes de aluno/atividade.

    Raises:
        HTTPException: 404 - Aluno ou Atividade não encontrada.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == matricula.aluno_id).first()
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.id == matricula.atividade_id).first()

    if db_aluno is None or db_atividade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno ou Atividade não encontrada")

    db_matricula = ModelMatricula(aluno_id=matricula.aluno_id, atividade_id=matricula.atividade_id)
    db.add(db_matricula)
    db.commit()
    db.refresh(db_matricula) # Refresh para carregar as relações aluno e atividade no db_matricula

    return _load_matricula_for_response(db_matricula)

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
        Matricula: A matrícula atualizada com nomes de aluno/atividade.

    Raises:
        HTTPException: 404 - Matrícula não encontrada.
    """
    db_matricula = db.query(ModelMatricula).options(joinedload(ModelMatricula.aluno).joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma), joinedload(ModelMatricula.atividade)).filter(ModelMatricula.id == matricula_id).first()
    if db_matricula is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada")

    db_matricula.status = "concluido"
    db_matricula.score_in_quest = score
    
    aluno = db_matricula.aluno
    atividade = db_matricula.atividade
    
    xp_ganho = 0
    pontos_totais_ganhos = 0
    pontos_academicos_ganhos = 0

    if aluno and atividade:
        xp_ganho = atividade.xp_on_completion
        pontos_totais_ganhos = score # A pontuação da atividade é o que o professor enviou no 'score'
        pontos_academicos_ganhos = atividade.points_on_completion

        aluno.xp += xp_ganho
        aluno.total_points += pontos_totais_ganhos
        aluno.academic_score += pontos_academicos_ganhos
        aluno.level = (aluno.xp // 100) + 1
        db.add(aluno) # Adiciona o aluno atualizado à sessão, se não estiver já lá

    db.commit()
    db.refresh(db_matricula) # Refresh para garantir que as relações estejam carregadas para o retorno
    
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
        db.commit() # Commit após a verificação de badges
        db.refresh(aluno) # Refresh final do aluno
    
    # Recarrega a matrícula para garantir que todas as relações e atributos estejam atualizados para o retorno
    db.refresh(db_matricula)
    return _load_matricula_for_response(db_matricula)

@matriculas_router.put("/matriculas/complete-by-guild", response_model=List[Matricula])
def complete_atividade_for_guild(complete_data: BulkCompleteMatriculaGuildRequest, db: Session = Depends(get_db)):
    """
    Marca uma atividade como concluída para todos os alunos de uma guilda específica.
    Atualiza o XP, pontos totais e pontos acadêmicos de cada aluno, além de verificar
    e conceder distintivos de nível.

    Args:
        complete_data: Contém o ID da atividade, o ID da guilda e a pontuação a ser aplicada.

    Returns:
        List[Matricula]: Uma lista das matrículas que foram atualizadas com nomes de aluno/atividade.

    Raises:
        HTTPException: 404 - Atividade, Guilda ou Alunos na guilda não encontrados,
                             ou se nenhum aluno tiver matrícula para a atividade.
    """
    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.id == complete_data.atividade_id).first()
    if db_atividade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Atividade com ID {complete_data.atividade_id} não encontrada.")

    db_guilda = db.query(ModelGuilda).options(joinedload(ModelGuilda.alunos).joinedload(ModelAluno.matriculas).joinedload(ModelMatricula.atividade)).filter(ModelGuilda.id == complete_data.guilda_id).first()
    if not db_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Guilda com ID {complete_data.guilda_id} não encontrada.")

    db_alunos_na_guilda = db_guilda.alunos
    if not db_alunos_na_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado na guilda com ID {complete_data.guilda_id}.")

    updated_matriculas_list = []
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
                updated_matriculas_list.append(_load_matricula_for_response(db_matricula))
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
            db.add(db_matricula) # Adiciona a matrícula atualizada à sessão
            db.flush() # Para garantir que as alterações sejam conhecidas antes de criar histórico

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
            updated_matriculas_list.append(_load_matricula_for_response(db_matricula))
        else:
            print(f"Aluno {aluno.nome} (ID: {aluno.id}) não possui matrícula para a atividade '{db_atividade.nome}'. Ignorando.")

    if not updated_matriculas_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno da guilda com ID {complete_data.guilda_id} possui matrícula para a atividade com ID {complete_data.atividade_id} para ser concluída.")

    db.add_all(historico_registros)
    db.commit()

    # Refresh all updated students and check for badges after commit
    for matricula_data in updated_matriculas_list:
        db_aluno = db.query(ModelAluno).filter(ModelAluno.id == matricula_data.aluno_id).first()
        if db_aluno:
            db.refresh(db_aluno)
            _check_and_award_level_badges(db_aluno, db)
            db.commit() # Commit after badge check for each student

    return updated_matriculas_list

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
    # Garante que as matrículas do aluno estão carregadas para acessar atividade.nome
    db.refresh(db_aluno)
    # Acessar relações diretamente para carregar as atividades
    for matricula in db.query(ModelMatricula).options(joinedload(ModelMatricula.atividade)).filter(ModelMatricula.aluno_id == db_aluno.id).all():
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
    Retorna os detalhes de todas as matrículas de um aluno específico, com base no ID fornecido,
    incluindo nomes de aluno e atividade.

    Args:
        aluno_id: O ID do aluno para buscar os detalhes das matrículas.

    Returns:
        List[Matricula]: Uma lista de objetos Matrícula com todos os detalhes e nomes.

    Raises:
        HTTPException: 404 - Aluno ou matrículas não encontradas.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Aluno com ID {aluno_id} não encontrado.")

    # Eager load 'aluno' e 'atividade' para popular os nomes no schema Matricula
    db_matriculas = db.query(ModelMatricula).options(joinedload(ModelMatricula.aluno), joinedload(ModelMatricula.atividade)).filter(ModelMatricula.aluno_id == aluno_id).all()
    
    if not db_matriculas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhuma matrícula encontrada para o aluno com ID {aluno_id}.")
    
    return [_load_matricula_for_response(m) for m in db_matriculas]

@matriculas_router.get("/matriculas/atividade/{codigo_atividade}", response_model=Dict[str, Union[str, List[Dict[str, Union[int, str]]]]])
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
    db_atividade = db.query(ModelAtividade).options(joinedload(ModelAtividade.matriculas).joinedload(ModelMatricula.aluno).joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAtividade.codigo == codigo_atividade).first()

    if not db_atividade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada")

    alunos_matriculados = []
    for matricula in db_atividade.matriculas:
        aluno = matricula.aluno # Aluno já carregado via joinedload
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