from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Union
import json

# ESTE É O ÚNICO BLOCO DE IMPORTAÇÃO NECESSÁRIO E COMPLETO.
from schemas import (
    Aluno,
    AlunoUpdate,
    GuildLeaderboardEntry,
    QuestCompletionPoints,
    XPDeductionRequest,
    HistoricoXPPontoSchema
)
from models import Aluno as ModelAluno, Curso as ModelCurso, HistoricoXPPonto 
from database import get_db

alunos_router = APIRouter()

# --- Definição dos Tiers de Badges ---
# Mapeia os níveis de XP necessários para cada badge de tier.
# O sistema concederá o badge cujo XP mínimo foi atingido ou superado.
# O badge será concedido quando o XP do aluno for MAIOR OU IGUAL ao threshold.
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
    # Adicione mais tiers conforme necessário:
}

def _load_badges_for_response(db_aluno_obj: ModelAluno) -> Aluno:
    """Carrega os badges do objeto ModelAluno e converte para o formato do schema Aluno."""
    response_aluno = Aluno.from_orm(db_aluno_obj)
    if db_aluno_obj.badges:
        try:
            response_aluno.badges = json.loads(db_aluno_obj.badges)
        except json.JSONDecodeError:
            response_aluno.badges = []
    else:
        response_aluno.badges = []
    return response_aluno

def _award_badge_if_new(db_aluno: ModelAluno, badge_name: str, db: Session):
    """
    Função auxiliar para adicionar um badge ao aluno se ele ainda não o possuir.
    Atualiza o campo 'badges' no db_aluno e adiciona para persistência.
    Retorna True se um novo badge foi concedido, False caso contrário.
    """
    current_badges = json.loads(db_aluno.badges) if db_aluno.badges else []
    if badge_name not in current_badges:
        current_badges.append(badge_name)
        db_aluno.badges = json.dumps(current_badges)
        db.add(db_aluno)
        return True
    return False

def _check_and_award_level_badges(db_aluno: ModelAluno, db: Session):
    """
    Verifica o XP atual do aluno e gerencia a concessão/remoção de badges de tier automaticamente.
    Esta função deve ser chamada APÓS o XP e o nível do aluno terem sido atualizados.
    Ela garante que a lista de badges do aluno corresponda exatamente aos tiers de XP alcançados.
    """
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

@alunos_router.get("/alunos", response_model=List[Aluno])
def read_alunos(db: Session = Depends(get_db)):
    """
    Retorna uma lista de todos os alunos cadastrados, incluindo seus dados de gamificação.
    """
    alunos = db.query(ModelAluno).all()
    return [_load_badges_for_response(aluno) for aluno in alunos]

@alunos_router.get("/alunos/{aluno_id}", response_model=Aluno)
def read_aluno(aluno_id: int, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de um aluno específico com base no ID fornecido, incluindo seus dados de gamificação.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return _load_badges_for_response(db_aluno)

@alunos_router.post("/alunos", response_model=Aluno, status_code=status.HTTP_201_CREATED)
def create_aluno(aluno: Aluno, db: Session = Depends(get_db)):
    aluno_data = aluno.dict(exclude={"id"})
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

    if _check_and_award_level_badges(db_aluno, db):
        db.commit()
        db.refresh(db_aluno)

    return _load_badges_for_response(db_aluno)

@alunos_router.put("/alunos/{aluno_id}", response_model=Aluno)
def update_aluno(aluno_id: int, aluno: AlunoUpdate, db: Session = Depends(get_db)):
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    xp_updated = False
    for key, value in aluno.dict(exclude_unset=True).items():
        if key == "badges":
            setattr(db_aluno, key, json.dumps(value))
        else:
            if key == "xp":
                xp_updated = True
            setattr(db_aluno, key, value)

    db.commit()
    db.refresh(db_aluno)

    if xp_updated:
        if _check_and_award_level_badges(db_aluno, db):
            db.commit()
            db.refresh(db_aluno)
    return _load_badges_for_response(db_aluno)

@alunos_router.delete("/alunos/{aluno_id}", response_model=Aluno)
def delete_aluno(aluno_id: int, db: Session = Depends(get_db)):
    """
    Exclui um aluno do sistema.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    aluno_deletado = _load_badges_for_response(db_aluno)

    db.delete(db_aluno)
    db.commit()
    return aluno_deletado

@alunos_router.get("/alunos/nome/{nome_aluno}", response_model=Union[Aluno, List[Aluno]])
def read_aluno_por_nome(nome_aluno: str, db: Session = Depends(get_db)):
    """
    Busca alunos pelo nome (parcial ou completo).
    """
    db_alunos = db.query(ModelAluno).filter(ModelAluno.nome.ilike(f"%{nome_aluno}%")).all()

    if not db_alunos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum aluno encontrado com esse nome")

    if len(db_alunos) == 1:
        return _load_badges_for_response(db_alunos[0])

    return [_load_badges_for_response(aluno) for aluno in db_alunos]

@alunos_router.post("/alunos/{aluno_id}/add_quest_academic_points", response_model=Aluno)
def add_quest_academic_points(aluno_id: int, quest_completion_data: QuestCompletionPoints, db: Session = Depends(get_db)):
    """
    Adiciona pontos acadêmicos a um aluno com base na conclusão de uma quest.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    db_curso = db.query(ModelCurso).filter(ModelCurso.codigo == quest_completion_data.quest_code).first()
    if db_curso is None:
        raise HTTPException(status_code=404, detail=f"Quest com código '{quest_completion_data.quest_code}' não encontrada.")

    db_aluno.academic_score += db_curso.points_on_completion

    db.commit()
    db.refresh(db_aluno)
    return _load_badges_for_response(db_aluno)

@alunos_router.post("/alunos/{aluno_id}/award_badge", response_model=Aluno)
def award_badge_to_aluno(aluno_id: int, badge_name: str, db: Session = Depends(get_db)):
    """
    Concede um distintivo (badge) a um aluno, se ele ainda não o possuir.
    Este é um método manual/direto de concessão de badge, separado da evolução por nível.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    if _award_badge_if_new(db_aluno, badge_name, db):
        db.commit()
        db.refresh(db_aluno)

    return _load_badges_for_response(db_aluno)

@alunos_router.get("/leaderboard", response_model=List[Aluno])
def get_leaderboard(db: Session = Depends(get_db), limit: int = 10):
    """
    Retorna um leaderboard dos alunos, classificados por XP.
    """
    leaderboard = db.query(ModelAluno).order_by(ModelAluno.xp.desc()).limit(limit).all()

    return [_load_badges_for_response(aluno) for aluno in leaderboard]

@alunos_router.get("/guilds/leaderboard", response_model=List[GuildLeaderboardEntry])
def get_guild_leaderboard(db: Session = Depends(get_db)):
    """
    Retorna um leaderboard das guildas, classificadas pela soma total de XP de seus membros.
    """
    guild_scores = db.query(
        ModelAluno.guilda,
        func.sum(ModelAluno.xp).label("total_xp")
    ).group_by(ModelAluno.guilda).order_by(func.sum(ModelAluno.xp).desc()).all()

    guild_scores_filtered = [
        {"guilda": entry.guilda, "total_xp": entry.total_xp}
        for entry in guild_scores if entry.guilda is not None
    ]

    if not guild_scores_filtered:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma guilda com XP registrada.")

    return guild_scores_filtered

@alunos_router.get("/alunos/guilda/{guild_name}", response_model=List[Aluno])
def read_alunos_by_guild(guild_name: str, db: Session = Depends(get_db)):
    """
    Retorna uma lista de todos os alunos de uma guilda específica, ordenados por XP.
    """
    db_alunos = db.query(ModelAluno).filter(ModelAluno.guilda == guild_name).order_by(ModelAluno.xp.desc()).all()

    if not db_alunos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado na guilda '{guild_name}'.")

    return [_load_badges_for_response(aluno) for aluno in db_alunos]

@alunos_router.post("/guilds/{guild_name}/penalize_xp", response_model=List[Aluno])
def penalize_guild_xp(guild_name: str, xp_deduction: int, db: Session = Depends(get_db)):
    """
    Penaliza todos os alunos de uma guilda específica, deduzindo XP.
    O xp_deduction deve ser um valor positivo, que será subtraído.
    """
    if xp_deduction <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O valor de dedução de XP deve ser um número positivo."
        )

    db_alunos_na_guilda = db.query(ModelAluno).filter(ModelAluno.guilda == guild_name).all()

    if not db_alunos_na_guilda:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum aluno encontrado na guilda '{guild_name}' para aplicar a penalidade."
        )

    updated_alunos_response = []
    historico_registros = [] # Lista para coletar os registros de histórico

    for aluno in db_alunos_na_guilda:
        xp_antes = aluno.xp # Opcional: para logar o valor exato deduzido
        aluno.xp -= xp_deduction
        if aluno.xp < 0:
            aluno.xp = 0
        aluno.level = (aluno.xp // 100) + 1

        db.add(aluno)
        
        # Preparar registro de histórico
        historico_registros.append(HistoricoXPPonto(
            aluno_id=aluno.id,
            tipo_transacao="penalizacao_xp",
            valor_xp_alterado=-xp_deduction, # Armazenar como valor negativo
            valor_pontos_alterado=0.0,
            motivo=f"Penalidade de XP para a guilda '{guild_name}'",
            referencia_entidade="guilda",
            referencia_id=None # Ou um ID de guilda se você tiver uma tabela de guildas
        ))

    db.commit() # Commit das alterações nos alunos

    # Adicionar todos os registros de histórico de uma vez
    db.add_all(historico_registros)
    db.commit() # Commit dos registros de histórico

    for aluno in db_alunos_na_guilda:
        db.refresh(aluno)
        if _check_and_award_level_badges(aluno, db):
            db.commit()
            db.refresh(aluno)
        updated_alunos_response.append(_load_badges_for_response(aluno))

    return updated_alunos_response

@alunos_router.post("/alunos/{aluno_id}/penalize_xp", response_model=Aluno)
def penalize_aluno_xp(aluno_id: int, xp_data: XPDeductionRequest, db: Session = Depends(get_db)):
    """
    Penaliza um aluno específico, deduzindo XP.
    O xp_deduction deve ser um valor positivo, que será subtraído.
    """
    xp_deduction = xp_data.xp_deduction
    
    if xp_deduction <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O valor de dedução de XP deve ser um número positivo."
        )

    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
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
        tipo_transacao="penalizacao_xp",
        valor_xp_alterado=-xp_deduction, 
        valor_pontos_alterado=0.0,
        motivo=f"Penalidade de XP manual para o aluno",
        referencia_entidade="aluno",
        referencia_id=db_aluno.id
    )
    db.add(historico_registro)
    
    db.commit() 
    db.refresh(db_aluno) 

    if _check_and_award_level_badges(db_aluno, db):
        db.commit()
        db.refresh(db_aluno)
            
    return _load_badges_for_response(db_aluno) 


@alunos_router.get("/alunos/level/{level}", response_model=List[Aluno])
def read_alunos_by_level(level: int, db: Session = Depends(get_db)):
    """
    Retorna uma lista de todos os alunos de um nível específico, ordenados por XP.
    """
    if level <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O nível deve ser um número positivo."
        )

    db_alunos = db.query(ModelAluno).filter(ModelAluno.level == level).order_by(ModelAluno.xp.desc()).all()

    if not db_alunos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado no nível '{level}'.")

    return [_load_badges_for_response(aluno) for aluno in db_alunos]

@alunos_router.get("/alunos/{aluno_id}/historico_xp_pontos", response_model=List[HistoricoXPPontoSchema])
def get_aluno_historico_xp_pontos(aluno_id: int, db: Session = Depends(get_db)):
    """
    Retorna o histórico de todas as transações de XP e pontos de um aluno específico.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    historico = db.query(HistoricoXPPonto).filter(HistoricoXPPonto.aluno_id == aluno_id).order_by(HistoricoXPPonto.data_hora.asc()).all()

    if not historico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum registro de histórico encontrado para o aluno com ID {aluno_id}.")

    return [HistoricoXPPontoSchema.from_orm(registro) for registro in historico]

@alunos_router.post("/alunos/nome/{nome_aluno}/penalize_xp", response_model=Aluno)
def penalize_aluno_xp_por_nome(nome_aluno: str, xp_data: XPDeductionRequest, db: Session = Depends(get_db)):
    """
    Penaliza um aluno específico encontrado pelo nome (parcial ou completo), deduzindo XP.
    Se múltiplos alunos forem encontrados com o mesmo nome, uma exceção será levantada.
    """
    xp_deduction = xp_data.xp_deduction
    
    if xp_deduction <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O valor de dedução de XP deve ser um número positivo."
        )

    # Busca alunos que correspondem ao nome (case-insensitive e parcial)
    db_alunos_matches = db.query(ModelAluno).filter(ModelAluno.nome.ilike(f"%{nome_aluno}%")).all() #

    if not db_alunos_matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum aluno encontrado com o nome '{nome_aluno}'."
        )
    
    if len(db_alunos_matches) > 1:
        # Se múltiplos alunos corresponderem, evite penalidade ambígua
        matched_names = [f"{aluno.nome} (ID: {aluno.id})" for aluno in db_alunos_matches]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Múltiplos alunos encontrados com o nome '{nome_aluno}'. Por favor, use o ID do aluno para penalizar: {', '.join(matched_names)}"
        )
            
    # Se apenas um aluno for encontrado, proceed
    db_aluno = db_alunos_matches[0]

    db_aluno.xp -= xp_deduction
    if db_aluno.xp < 0:
        db_aluno.xp = 0
    db_aluno.level = (db_aluno.xp // 100) + 1 # Recalcula o nível

    db.add(db_aluno)
    
    historico_registro = HistoricoXPPonto(
        aluno_id=db_aluno.id,
        tipo_transacao="penalizacao_xp",
        valor_xp_alterado=-xp_deduction, 
        valor_pontos_alterado=0.0,
        motivo=f"Penalidade de XP por nome para o aluno '{nome_aluno}'",
        referencia_entidade="aluno",
        referencia_id=db_aluno.id
    )
    db.add(historico_registro)
    
    db.commit() 
    db.refresh(db_aluno) 

    if _check_and_award_level_badges(db_aluno, db):
        db.commit()
        db.refresh(db_aluno)
            
    return _load_badges_for_response(db_aluno)