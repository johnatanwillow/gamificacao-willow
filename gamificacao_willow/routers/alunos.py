from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func # Import func
from typing import List, Dict, Union # Ensure Union is imported
import json

from schemas import Aluno, AlunoUpdate, GuildLeaderboardEntry, QuestCompletionPoints
from models import Aluno as ModelAluno
from models import Curso as ModelCurso
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
    Verifica o XP atual do aluno e concede badges de tier automaticamente.
    Esta função deve ser chamada APÓS o XP e o nível do aluno terem sido atualizados.
    Ela garante que apenas o badge de maior tier aplicável que o aluno ainda não possui seja adicionado.
    """
    current_xp = db_aluno.xp
    awarded_any_new_badge = False
   
    sorted_tiers = sorted(BADGE_TIERS.items(), key=lambda item: item[0], reverse=True)

    for xp_threshold, badge_name in sorted_tiers:
        if current_xp >= xp_threshold:
            if _award_badge_if_new(db_aluno, badge_name, db):
                awarded_any_new_badge = True
                
            
    return awarded_any_new_badge

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

    _check_and_award_level_badges(db_aluno, db)
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

    if xp_updated and db_aluno.xp is not None:
        db_aluno.level = (db_aluno.xp // 100) + 1

    db.commit()
    db.refresh(db_aluno)

    if xp_updated:
        _check_and_award_level_badges(db_aluno, db)
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

    _award_badge_if_new(db_aluno, badge_name, db)
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

    updated_alunos = []
    for aluno in db_alunos_na_guilda:
        aluno.xp -= xp_deduction
        if aluno.xp < 0:
            aluno.xp = 0
        aluno.level = (aluno.xp // 100) + 1 

        db.add(aluno) 

    db.commit() 
    
    for aluno in db_alunos_na_guilda:
        db.refresh(aluno)
        
        _check_and_award_level_badges(aluno, db)
        db.refresh(aluno) 
        updated_alunos.append(_load_badges_for_response(aluno)) 

    db.commit()
        
    return updated_alunos