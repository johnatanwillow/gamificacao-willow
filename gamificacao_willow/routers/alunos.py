from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Dict, Union
import json

# Importações atualizadas para Turma e Guilda
from schemas import (
    Aluno,
    AlunoUpdate,
    GuildLeaderboardEntry,
    QuestCompletionPoints,
    XPDeductionRequest,
    GuildPenalizationRequest,
    HistoricoXPPontoSchema,
    HistoricoAlunoDetalhadoSchema,
    Turma, # Novo schema
    TurmaCreate, # Novo schema
    Guilda, # Novo schema
    GuildaCreate # Novo schema
)
from models import (
    Aluno as ModelAluno,
    Atividade as ModelAtividade, 
    HistoricoXPPonto,
    Turma as ModelTurma, # Novo modelo
    Guilda as ModelGuilda # Novo modelo
)
from database import get_db

alunos_router = APIRouter()

# --- Definição dos Tiers de Badges ---
BADGE_TIERS = {
    100: "Explorador Iniciante",
    200: "Explorador Bronze",
    300: "Desbravador Prata",
    400: "Garimpeiro Ouro",
    500: "Alma de Platina",
    600: "Arqueólogo de Jaspe",
    700: "Conquistador de Safira",
    800: "Conquistador de Esmeralda",
    900: "Conquistador de Diamante",
    1000: "Mestre das Gemas",
}

# FUNÇÃO AUXILIAR MODIFICADA: Agora carrega também o nome da guilda e turma
def _load_aluno_for_response(db_aluno_obj: ModelAluno) -> Aluno:
    response_aluno = Aluno.from_orm(db_aluno_obj)
    
    # Carregar badges
    if db_aluno_obj.badges:
        try:
            response_aluno.badges = json.loads(db_aluno_obj.badges)
        except json.JSONDecodeError:
            response_aluno.badges = []
    else:
        response_aluno.badges = []

    # Carregar nome da guilda e turma
    if db_aluno_obj.guilda_obj: # Acessa o objeto relacionado diretamente
        response_aluno.guilda_nome = db_aluno_obj.guilda_obj.nome
        if db_aluno_obj.guilda_obj.turma:
            response_aluno.turma_nome = db_aluno_obj.guilda_obj.turma.nome
    
    return response_aluno

def _award_badge_if_new(db_aluno: ModelAluno, badge_name: str, db: Session):
    current_badges = json.loads(db_aluno.badges) if db_aluno.badges else []
    if badge_name not in current_badges:
        current_badges.append(badge_name)
        db_aluno.badges = json.dumps(current_badges)
        db.add(db_aluno)
        return True
    return False

def _check_and_award_level_badges(db_aluno: ModelAluno, db: Session):
    current_xp = db_aluno.xp
    expected_badges = []
    sorted_tiers = sorted(BADGE_TIERS.items(), key=lambda item: item[0])
    for xp_threshold, badge_name in sorted_tiers:
        if current_xp >= xp_threshold:
            expected_badges.append(badge_name)
        else:
            break
    current_stored_badges = json.loads(db_aluno.badges) if db_aluno.badges else []
    if set(current_stored_badges) != set(expected_badges):
        db_aluno.badges = json.dumps(expected_badges)
        db.add(db_aluno)
        return True
    return False


# NOVO ENDPOINT: Criar Turma
@alunos_router.post("/turmas", response_model=Turma, status_code=status.HTTP_201_CREATED)
def create_turma(turma: TurmaCreate, db: Session = Depends(get_db)):
    db_turma = db.query(ModelTurma).filter(ModelTurma.nome == turma.nome).first()
    if db_turma:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Turma com este nome já existe")
    
    db_turma = ModelTurma(**turma.dict())
    db.add(db_turma)
    db.commit()
    db.refresh(db_turma)
    return db_turma

# NOVO ENDPOINT: Listar Turmas
@alunos_router.get("/turmas", response_model=List[Turma])
def read_turmas(db: Session = Depends(get_db)):
    turmas = db.query(ModelTurma).options(joinedload(ModelTurma.guildas)).all()
    return turmas

# NOVO ENDPOINT: Criar Guilda
@alunos_router.post("/guildas", response_model=Guilda, status_code=status.HTTP_201_CREATED)
def create_guilda(guilda: GuildaCreate, db: Session = Depends(get_db)):
    db_turma = db.query(ModelTurma).filter(ModelTurma.id == guilda.turma_id).first()
    if not db_turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada")

    db_guilda = db.query(ModelGuilda).filter(ModelGuilda.nome == guilda.nome).first()
    if db_guilda:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Guilda com este nome já existe")

    db_guilda = ModelGuilda(**guilda.dict())
    db.add(db_guilda)
    db.commit()
    db.refresh(db_guilda)
    
    # Carregar o objeto turma para a resposta
    db_guilda.turma = db_turma
    return db_guilda

# NOVO ENDPOINT: Listar Guildas
@alunos_router.get("/guildas", response_model=List[Guilda])
def read_guildas(db: Session = Depends(get_db)):
    guildas = db.query(ModelGuilda).options(joinedload(ModelGuilda.turma)).all()
    return guildas

# MODIFICADO: read_alunos agora carrega guilda e turma
@alunos_router.get("/alunos", response_model=List[Aluno])
def read_alunos(db: Session = Depends(get_db)):
    """
    Retorna uma lista de todos os alunos cadastrados, incluindo seus dados de gamificação,
    nome da guilda e nome da turma.
    """
    alunos = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).all()
    return [_load_aluno_for_response(aluno) for aluno in alunos]

# MODIFICADO: read_aluno agora carrega guilda e turma
@alunos_router.get("/alunos/{aluno_id}", response_model=Aluno)
def read_aluno(aluno_id: int, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de um aluno específico com base no ID fornecido,
    incluindo nome da guilda e nome da turma.
    """
    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return _load_aluno_for_response(db_aluno)

# MODIFICADO: create_aluno agora usa guilda_id
@alunos_router.post("/alunos", response_model=Aluno, status_code=status.HTTP_201_CREATED)
def create_aluno(aluno: Aluno, db: Session = Depends(get_db)):
    # Valida se a guilda_id existe
    if aluno.guilda_id:
        db_guilda = db.query(ModelGuilda).filter(ModelGuilda.id == aluno.guilda_id).first()
        if not db_guilda:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guilda não encontrada")

    aluno_data = aluno.dict(exclude={"id"})
    # json.dumps para badges
    if "badges" in aluno_data and aluno_data["badges"] is not None:
        aluno_data["badges"] = json.dumps(aluno_data["badges"])
    else:
        aluno_data["badges"] = json.dumps([])

    if "academic_score" not in aluno_data or aluno_data["academic_score"] is None:
        aluno_data["academic_score"] = 0.0

    db_aluno = ModelAluno(**aluno_data)
    db.add(db_aluno)
    db.commit()
    db.refresh(db_aluno)
    
    # Recarrega o aluno com os relacionamentos para a resposta formatada
    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == db_aluno.id).first()

    if _check_and_award_level_badges(db_aluno, db):
        db.commit()
        db.refresh(db_aluno)

    return _load_aluno_for_response(db_aluno)

# MODIFICADO: update_aluno agora usa guilda_id
@alunos_router.put("/alunos/{aluno_id}", response_model=Aluno)
def update_aluno(aluno_id: int, aluno: AlunoUpdate, db: Session = Depends(get_db)):
    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    # Valida se a guilda_id existe, se for fornecida
    if aluno.guilda_id is not None:
        db_guilda = db.query(ModelGuilda).filter(ModelGuilda.id == aluno.guilda_id).first()
        if not db_guilda:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guilda não encontrada")

    # Guardar os valores antigos antes da atualização para calcular a diferença
    old_xp = db_aluno.xp
    old_total_points = db_aluno.total_points
    old_academic_score = db_aluno.academic_score

    xp_updated = False
    historico_registros = [] # Lista para coletar novos registros de histórico

    # Iterar sobre os campos fornecidos na atualização
    for key, value in aluno.dict(exclude_unset=True).items():
        if key == "badges":
            setattr(db_aluno, key, json.dumps(value))
        elif key == "motivo":
            # O motivo será usado para o histórico, não é um campo do ModelAluno
            pass
        else:
            if key == "xp":
                xp_updated = True
            setattr(db_aluno, key, value)

    # Capturar o motivo da atualização (se fornecido)
    motivo_alteracao = aluno.motivo if aluno.motivo else "Alteração manual via PUT /alunos/{aluno_id}"

    # Registrar alterações de XP no histórico (se xp_updated for True)
    if xp_updated:
        xp_change = db_aluno.xp - old_xp
        if xp_change != 0: # Registrar apenas se houve mudança real no XP
            historico_registros.append(
                HistoricoXPPonto(
                    aluno_id=db_aluno.id,
                    tipo_transacao="ajuste_manual_xp",
                    valor_xp_alterado=xp_change,
                    valor_pontos_alterado=0.0,
                    motivo=motivo_alteracao,
                    referencia_entidade="aluno",
                    referencia_id=db_aluno.id
                )
            )
    
    # Registrar alterações de total_points no histórico
    if "total_points" in aluno.dict(exclude_unset=True):
        if db_aluno.total_points != old_total_points:
            points_change = db_aluno.total_points - old_total_points
            historico_registros.append(
                HistoricoXPPonto(
                    aluno_id=db_aluno.id,
                    tipo_transacao="ajuste_manual_pontos_totais",
                    valor_xp_alterado=0,
                    valor_pontos_alterado=float(points_change), # Armazenar como float
                    motivo=motivo_alteracao,
                    referencia_entidade="aluno",
                    referencia_id=db_aluno.id
                )
            )

    # Registrar alterações de academic_score no histórico
    if "academic_score" in aluno.dict(exclude_unset=True):
        if db_aluno.academic_score != old_academic_score:
            academic_score_change = db_aluno.academic_score - old_academic_score
            historico_registros.append(
                HistoricoXPPonto(
                    aluno_id=db_aluno.id,
                    tipo_transacao="ajuste_manual_academic_score",
                    valor_xp_alterado=0,
                    valor_pontos_alterado=academic_score_change,
                    motivo=motivo_alteracao,
                    referencia_entidade="aluno",
                    referencia_id=db_aluno.id
                )
            )

    db.add_all(historico_registros) # Adicionar todos os registros de histórico coletados
    db.commit() 
    db.refresh(db_aluno) 

    # Verifica e concede/remove badges de nível se o XP foi atualizado
    if xp_updated:
        if _check_and_award_level_badges(db_aluno, db):
            db.commit()
            db.refresh(db_aluno)
            
    # Recarrega o aluno com os relacionamentos para a resposta formatada
    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == db_aluno.id).first()
    return _load_aluno_for_response(db_aluno) 

@alunos_router.delete("/alunos/{aluno_id}", response_model=Aluno)
def delete_aluno(aluno_id: int, db: Session = Depends(get_db)):
    """
    Exclui um aluno do sistema.
    """
    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    aluno_deletado = _load_aluno_for_response(db_aluno) # Usa a função auxiliar modificada

    db.delete(db_aluno)
    db.commit()
    return aluno_deletado

# MODIFICADO: read_aluno_por_nome agora carrega guilda e turma
@alunos_router.get("/alunos/nome/{nome_aluno}", response_model=Union[Aluno, List[Aluno]])
def read_aluno_por_nome(nome_aluno: str, db: Session = Depends(get_db)):
    """
    Busca alunos pelo nome (parcial ou completo), incluindo nome da guilda e turma.
    """
    db_alunos = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.nome.ilike(f"%{nome_aluno}%")).all()

    if not db_alunos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum aluno encontrado com esse nome")

    if len(db_alunos) == 1:
        return _load_aluno_for_response(db_alunos[0]) # Usa a função auxiliar modificada

    return [_load_aluno_for_response(aluno) for aluno in db_alunos] # Usa a função auxiliar modificada

@alunos_router.post("/alunos/{aluno_id}/add_quest_academic_points", response_model=Aluno)
# MODIFICADO: Adicionado 'motivo' e lógica de registro no HistoricoXPPonto
def add_quest_academic_points(aluno_id: int, quest_completion_data: QuestCompletionPoints, db: Session = Depends(get_db)):
    """
    Adiciona pontos acadêmicos a um aluno com base na conclusão de uma quest, com motivo.
    """
    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.codigo == quest_completion_data.quest_code).first() # MODIFICADO: db_atividade e ModelAtividade
    if db_atividade is None: # MODIFICADO: db_atividade
        raise HTTPException(status_code=404, detail=f"Atividade com código '{quest_completion_data.quest_code}' não encontrada.") # MODIFICADO: Atividade com código

    pontos_adicionados = db_atividade.points_on_completion # MODIFICADO: db_atividade.points_on_completion
    db_aluno.academic_score += pontos_adicionados

    motivo_registro = quest_completion_data.motivo if quest_completion_data.motivo else f"Pontos Acadêmicos por Atividade '{db_atividade.nome}' ({db_atividade.codigo})" # MODIFICADO: Atividade '{db_atividade.nome}' ({db_atividade.codigo})

    # NOVO: Registrar a adição de pontos acadêmicos no histórico
    historico_registro = HistoricoXPPonto(
        aluno_id=db_aluno.id,
        tipo_transacao="ganho_pontos_academicos_manual_atividade", # MODIFICADO: ganho_pontos_academicos_manual_atividade
        valor_xp_alterado=0,
        valor_pontos_alterado=pontos_adicionados,
        motivo=motivo_registro,
        referencia_entidade="atividade", # MODIFICADO: atividade
        referencia_id=db_atividade.id # MODIFICADO: db_atividade.id
    )
    db.add(historico_registro)
    
    db.commit()
    db.refresh(db_aluno)
    return _load_aluno_for_response(db_aluno) # Usa a função auxiliar modificada

@alunos_router.post("/alunos/{aluno_id}/award_badge", response_model=Aluno)
def award_badge_to_aluno(aluno_id: int, badge_name: str, db: Session = Depends(get_db)):
    """
    Concede um distintivo (badge) a um aluno, se ele ainda não o possuir.
    Este é um método manual/direto de concessão de badge, separado da evolução por nível.
    """
    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    if _award_badge_if_new(db_aluno, badge_name, db):
        db.commit()
        db.refresh(db_aluno)

    return _load_aluno_for_response(db_aluno) # Usa a função auxiliar modificada

# MODIFICADO: get_leaderboard agora carrega guilda e turma
@alunos_router.get("/leaderboard", response_model=List[Aluno])
def get_leaderboard(db: Session = Depends(get_db), limit: int = 10):
    """
    Retorna um leaderboard dos alunos, classificados por XP, incluindo nome da guilda e turma.
    """
    leaderboard = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).order_by(ModelAluno.xp.desc()).limit(limit).all()

    return [_load_aluno_for_response(aluno) for aluno in leaderboard] # Usa a função auxiliar modificada

# MODIFICADO: get_guild_leaderboard agora usa IDs e nomes de guilda/turma
@alunos_router.get("/guilds/leaderboard", response_model=List[GuildLeaderboardEntry])
def get_guild_leaderboard(db: Session = Depends(get_db)):
    """
    Retorna um leaderboard das guildas, classificadas pela soma total de XP de seus membros,
    incluindo o nome da turma.
    """
    guild_scores = db.query(
        ModelGuilda.id,
        ModelGuilda.nome,
        ModelTurma.nome, # Adicionado nome da turma
        func.sum(ModelAluno.xp).label("total_xp")
    ).join(ModelAluno, ModelGuilda.id == ModelAluno.guilda_id).join(ModelTurma, ModelGuilda.turma_id == ModelTurma.id).group_by(ModelGuilda.id, ModelGuilda.nome, ModelTurma.nome).order_by(func.sum(ModelAluno.xp).desc()).all()

    # O filtro 'if entry.guilda is not None' não é mais necessário, pois estamos agrupando por ID
    guild_leaderboard = [
        {"guilda_id": entry.id, "guilda_nome": entry.nome, "turma_nome": entry.nome_2, "total_xp": entry.total_xp} # Usar nome_2 para ModelTurma.nome
        for entry in guild_scores
    ]

    if not guild_leaderboard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma guilda com XP registrada.")

    return guild_leaderboard

# MODIFICADO: read_alunos_by_guild agora usa guilda_id e carrega nomes
@alunos_router.get("/alunos/guilda/{guild_name}", response_model=List[Aluno])
def read_alunos_by_guild(guild_name: str, db: Session = Depends(get_db)):
    """
    Retorna uma lista de todos os alunos de uma guilda específica (por nome), ordenados por XP,
    incluindo nome da guilda e turma.
    """
    db_guilda = db.query(ModelGuilda).filter(ModelGuilda.nome.ilike(guild_name)).first()
    if not db_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Guilda '{guild_name}' não encontrada.")

    db_alunos = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.guilda_id == db_guilda.id).order_by(ModelAluno.xp.desc()).all()

    if not db_alunos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado na guilda '{guild_name}'.")

    return [_load_aluno_for_response(aluno) for aluno in db_alunos] # Usa a função auxiliar modificada

@alunos_router.post("/guilds/{guild_name}/penalize_xp", response_model=List[Aluno])
# MODIFICADO: Aceita GuildPenalizationRequest para incluir motivo, busca guilda por nome
def penalize_guild_xp(guild_name: str, guild_penalization_data: GuildPenalizationRequest, db: Session = Depends(get_db)):
    """
    Penaliza todos os alunos de uma guilda específica (por nome), deduzindo XP, com motivo.
    O xp_deduction deve ser um valor positivo, que será subtraído.
    """
    xp_deduction = guild_penalization_data.xp_deduction
    motivo_penalizacao = guild_penalization_data.motivo if guild_penalization_data.motivo else f"Penalidade de XP para a guilda '{guild_name}' (motivo não especificado)"
    
    if xp_deduction <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O valor de dedução de XP deve ser um número positivo."
        )

    db_guilda = db.query(ModelGuilda).filter(ModelGuilda.nome.ilike(guild_name)).first()
    if not db_guilda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Guilda '{guild_name}' não encontrada.")

    db_alunos_na_guilda = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.guilda_id == db_guilda.id).all()

    if not db_alunos_na_guilda:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum aluno encontrado na guilda '{guild_name}' para aplicar a penalidade."
        )

    updated_alunos_response = []
    historico_registros = [] # Lista para coletar os registros de histórico

    for aluno in db_alunos_na_guilda:
        xp_antes = aluno.xp 
        aluno.xp -= xp_deduction
        if aluno.xp < 0:
            aluno.xp = 0
        aluno.level = (aluno.xp // 100) + 1

        db.add(aluno)
        
        # Preparar registro de histórico
        historico_registros.append(HistoricoXPPonto(
            aluno_id=aluno.id,
            tipo_transacao="penalizacao_xp_guilda", 
            valor_xp_alterado=-xp_deduction, 
            valor_pontos_alterado=0.0,
            motivo=motivo_penalizacao, 
            referencia_entidade="guilda",
            referencia_id=db_guilda.id # Agora referencia o ID da Guilda
        ))

    db.commit() 

    # Adicionar todos os registros de histórico de uma vez
    db.add_all(historico_registros)
    db.commit() 

    for aluno in db_alunos_na_guilda:
        db.refresh(aluno)
        if _check_and_award_level_badges(aluno, db):
            db.commit()
            db.refresh(aluno)
        updated_alunos_response.append(_load_aluno_for_response(aluno)) # Usa a função auxiliar modificada

    return updated_alunos_response

@alunos_router.post("/alunos/{aluno_id}/penalize_xp", response_model=Aluno)
# MODIFICADO: Retorna Aluno com guilda e turma, usa _load_aluno_for_response
def penalize_aluno_xp(aluno_id: int, xp_data: XPDeductionRequest, db: Session = Depends(get_db)):
    """
    Penaliza um aluno específico, deduzindo XP, com motivo.
    O xp_deduction deve ser um valor positivo, que será subtraído.
    """
    xp_deduction = xp_data.xp_deduction
    motivo_penalizacao = xp_data.motivo if xp_data.motivo else "Penalidade de XP manual para o aluno (motivo não especificado)"
    
    if xp_deduction <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O valor de dedução de XP deve ser um número positivo."
        )

    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aluno com ID {aluno_id} não encontrado para aplicar a penalidade."
        )

    xp_antes = db_aluno.xp 
    db_aluno.xp -= xp_deduction
    if db_aluno.xp < 0:
        db_aluno.xp = 0
    db_aluno.level = (db_aluno.xp // 100) + 1 

    db.add(db_aluno)
    
    historico_registro = HistoricoXPPonto(
        aluno_id=db_aluno.id,
        tipo_transacao="penalizacao_xp_manual", 
        valor_xp_alterado=-xp_deduction, 
        valor_pontos_alterado=0.0,
        motivo=motivo_penalizacao, 
        referencia_entidade="aluno",
        referencia_id=db_aluno.id
    )
    db.add(historico_registro)
    
    db.commit() 
    db.refresh(db_aluno) 

    if _check_and_award_level_badges(db_aluno, db):
        db.commit()
        db.refresh(db_aluno)
            
    return _load_aluno_for_response(db_aluno) # Usa a função auxiliar modificada

# MODIFICADO: read_alunos_by_level agora carrega guilda e turma
@alunos_router.get("/alunos/level/{level}", response_model=List[Aluno])
def read_alunos_by_level(level: int, db: Session = Depends(get_db)):
    """
    Retorna uma lista de todos os alunos de um nível específico, ordenados por XP,
    incluindo nome da guilda e turma.
    """
    if level <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O nível deve ser um número positivo."
        )

    db_alunos = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.level == level).order_by(ModelAluno.xp.desc()).all()

    if not db_alunos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado no nível '{level}'.")

    return [_load_aluno_for_response(aluno) for aluno in db_alunos] # Usa a função auxiliar modificada

# MODIFICADO: get_aluno_historico_xp_pontos agora usa join para guilda e turma
@alunos_router.get("/alunos/{aluno_id}/historico_xp_pontos", response_model=List[HistoricoAlunoDetalhadoSchema])
def get_aluno_historico_xp_pontos(aluno_id: int, db: Session = Depends(get_db)):
    """
    Retorna o histórico detalhado de todas as transações de XP e pontos de um aluno específico,
    incluindo o nome e apelido do aluno, nome da guilda e nome da turma em cada registro.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    # Realiza JOINs para obter dados do Aluno, Guilda e Turma
    historico_com_detalhes = (
        db.query(HistoricoXPPonto, ModelAluno, ModelGuilda, ModelTurma)
        .join(ModelAluno, HistoricoXPPonto.aluno_id == ModelAluno.id)
        .outerjoin(ModelGuilda, ModelAluno.guilda_id == ModelGuilda.id) # Usar outerjoin para alunos sem guilda
        .outerjoin(ModelTurma, ModelGuilda.turma_id == ModelTurma.id) # Usar outerjoin para guildas sem turma
        .filter(HistoricoXPPonto.aluno_id == aluno_id)
        .order_by(HistoricoXPPonto.data_hora.asc())
        .all()
    )

    if not historico_com_detalhes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum registro de histórico encontrado para o aluno com ID {aluno_id}.")

    # Mapeia os resultados da junção para o novo schema detalhado
    response_list = []
    for historico_registro, aluno_info, guilda_info, turma_info in historico_com_detalhes:
        response_list.append(
            HistoricoAlunoDetalhadoSchema(
                id=historico_registro.id,
                aluno_id=historico_registro.aluno_id,
                aluno_nome=aluno_info.nome,
                aluno_apelido=aluno_info.apelido,
                guilda_nome=guilda_info.nome if guilda_info else None, # Acessa o nome da guilda
                turma_nome=turma_info.nome if turma_info else None,    # Acessa o nome da turma
                tipo_transacao=historico_registro.tipo_transacao,
                valor_xp_alterado=historico_registro.valor_xp_alterado,
                valor_pontos_alterado=historico_registro.valor_pontos_alterado,
                motivo=historico_registro.motivo,
                data_hora=historico_registro.data_hora,
                referencia_entidade=historico_registro.referencia_entidade,
                referencia_id=historico_registro.referencia_id
            )
        )
    return response_list

# MODIFICADO: get_aluno_historico_xp_pontos_por_nome agora usa join para guilda e turma
@alunos_router.get("/alunos/nome/{nome_aluno}/historico_xp_pontos", response_model=List[HistoricoAlunoDetalhadoSchema])
def get_aluno_historico_xp_pontos_por_nome(nome_aluno: str, db: Session = Depends(get_db)):
    """
    Retorna o histórico detalhado de todas as transações de XP e pontos de um aluno específico,
    encontrado pelo nome (parcial ou completo), incluindo nome da guilda e nome da turma.
    Se múltiplos alunos forem encontrados com o mesmo nome, uma exceção será levantada.
    """
    # Busca alunos que correspondem ao nome (case-insensitive e parcial)
    db_alunos_matches = db.query(ModelAluno).filter(ModelAluno.nome.ilike(f"%{nome_aluno}%")).all()

    if not db_alunos_matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum aluno encontrado com o nome '{nome_aluno}'."
        )
    
    if len(db_alunos_matches) > 1:
        # Se múltiplos alunos corresponderem, evite ambiguidade na recuperação do histórico
        matched_names = [f"{aluno.nome} (ID: {aluno.id})" for aluno in db_alunos_matches]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Múltiplos alunos encontrados com o nome '{nome_aluno}'. Por favor, use o ID do aluno para consultar o histórico: {', '.join(matched_names)}"
        )
            
    # Se apenas um aluno for encontrado, obtenha o ID para buscar o histórico
    db_aluno = db_alunos_matches[0]
    aluno_id = db_aluno.id

    # Realiza JOINs para obter dados do Aluno, Guilda e Turma
    historico_com_detalhes = (
        db.query(HistoricoXPPonto, ModelAluno, ModelGuilda, ModelTurma)
        .join(ModelAluno, HistoricoXPPonto.aluno_id == ModelAluno.id)
        .outerjoin(ModelGuilda, ModelAluno.guilda_id == ModelGuilda.id) # Usar outerjoin para alunos sem guilda
        .outerjoin(ModelTurma, ModelGuilda.turma_id == ModelTurma.id) # Usar outerjoin para guildas sem turma
        .filter(HistoricoXPPonto.aluno_id == aluno_id)
        .order_by(HistoricoXPPonto.data_hora.asc())
        .all()
    )

    if not historico_com_detalhes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum registro de histórico encontrado para o aluno com nome '{nome_aluno}' (ID: {aluno_id}).")

    # Mapeia os resultados da junção para o novo schema detalhado
    response_list = []
    for historico_registro, aluno_info, guilda_info, turma_info in historico_com_detalhes:
        response_list.append(
            HistoricoAlunoDetalhadoSchema(
                id=historico_registro.id,
                aluno_id=historico_registro.aluno_id,
                aluno_nome=aluno_info.nome,
                aluno_apelido=aluno_info.apelido,
                guilda_nome=guilda_info.nome if guilda_info else None, # Acessa o nome da guilda
                turma_nome=turma_info.nome if turma_info else None,    # Acessa o nome da turma
                tipo_transacao=historico_registro.tipo_transacao,
                valor_xp_alterado=historico_registro.valor_xp_alterado,
                valor_pontos_alterado=historico_registro.valor_pontos_alterado,
                motivo=historico_registro.motivo,
                data_hora=historico_registro.data_hora,
                referencia_entidade=historico_registro.referencia_entidade,
                referencia_id=historico_registro.referencia_id
            )
        )
    return response_list