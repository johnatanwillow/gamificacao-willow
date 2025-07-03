from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func # Importar func para funções de agregação (sum)
from typing import List, Dict, Union
import json # Para lidar com a serialização/desserialização de JSON para badges

# Importar os schemas atualizados
from schemas import Aluno, AlunoUpdate, GuildLeaderboardEntry
# Importar o modelo Aluno atualizado
from models import Aluno as ModelAluno
from database import get_db

alunos_router = APIRouter()

# Helper para converter badges de JSON string para lista (para respostas da API)
def _load_badges_for_response(db_aluno_obj: ModelAluno) -> Aluno:
    """Carrega os badges do objeto ModelAluno e converte para o formato do schema Aluno."""
    response_aluno = Aluno.from_orm(db_aluno_obj)
    if db_aluno_obj.badges:
        try:
            response_aluno.badges = json.loads(db_aluno_obj.badges)
        except json.JSONDecodeError:
            response_aluno.badges = [] # Lidar com JSON malformado
    else:
        response_aluno.badges = [] # Garantir que seja sempre uma lista
    return response_aluno


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

    Args:
        aluno_id: O ID do aluno.

    Raises:
        HTTPException: Se o aluno não for encontrado.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return _load_badges_for_response(db_aluno)

@alunos_router.post("/alunos", response_model=Aluno)
def create_aluno(aluno: Aluno, db: Session = Depends(get_db)):
    """
    Cria um novo aluno com os dados fornecidos, incluindo guilda e atributos de gamificação iniciais.

    Args:
        aluno: Dados do aluno a ser criado (nome, guilda, etc.).

    Returns:
        Aluno: O aluno criado.
    """ 
    # Certifique-se de que o campo badges seja salvo como JSON string se presente no input
    aluno_data = aluno.dict(exclude={"id"})
    if "badges" in aluno_data and aluno_data["badges"] is not None:
        aluno_data["badges"] = json.dumps(aluno_data["badges"])
    
    db_aluno = ModelAluno(**aluno_data) 
    db.add(db_aluno)
    db.commit()
    db.refresh(db_aluno)
    return _load_badges_for_response(db_aluno)


@alunos_router.put("/alunos/{aluno_id}", response_model=Aluno)
def update_aluno(aluno_id: int, aluno: AlunoUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de um aluno existente, incluindo seus atributos de gamificação.

    Args:
        aluno_id: O ID do aluno a ser atualizado.
        aluno: Os novos dados do aluno (nome, guilda, xp, level, total_points, badges).

    Raises:
        HTTPException: 404 - Aluno não encontrado.

    Returns:
        Aluno: O aluno atualizado.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    for key, value in aluno.dict(exclude_unset=True).items():
        if key == "badges":
            # Converte a lista de strings para uma string JSON antes de salvar
            setattr(db_aluno, key, json.dumps(value))
        else:
            setattr(db_aluno, key, value)

    # Lógica para recalcular o nível se o XP foi atualizado
    if aluno.xp is not None:
        db_aluno.level = (db_aluno.xp // 100) + 1 # Exemplo: cada 100 XP é um novo nível

    db.commit()
    db.refresh(db_aluno)
    return _load_badges_for_response(db_aluno)


@alunos_router.delete("/alunos/{aluno_id}", response_model=Aluno)
def delete_aluno(aluno_id: int, db: Session = Depends(get_db)):
    """
    Exclui um aluno do sistema.

    Args:
        aluno_id: O ID do aluno a ser excluído.

    Raises:
        HTTPException: 404 - Aluno não encontrado.

    Returns:
        Aluno: O aluno excluído.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    aluno_deletado = _load_badges_for_response(db_aluno) # Carrega os badges antes de deletar

    db.delete(db_aluno)
    db.commit()
    return aluno_deletado

@alunos_router.get("/alunos/nome/{nome_aluno}", response_model=Union[Aluno, List[Aluno]]) 
def read_aluno_por_nome(nome_aluno: str, db: Session = Depends(get_db)):
    """
    Busca alunos pelo nome (parcial ou completo).
    
    Args:
        nome_aluno: O nome (ou parte do nome) do aluno a ser buscado.
    
    Raises:
        HTTPException: 404 - Nenhum aluno encontrado com esse nome.
        
    Returns:
        Union[Aluno, List[Aluno]]: Um único objeto `Aluno` se houver apenas uma correspondência, 
        ou uma lista de `Aluno` se houver várias correspondências.
    """
    db_alunos = db.query(ModelAluno).filter(ModelAluno.nome.ilike(f"%{nome_aluno}%")).all() # ilike para case-insensitive

    if not db_alunos:
        raise HTTPException(status_code=404, detail="Nenhum aluno encontrado com esse nome")

    if len(db_alunos) == 1:  # Retorna um único Aluno se houver apenas uma correspondência
        return _load_badges_for_response(db_alunos[0])

    return [_load_badges_for_response(aluno) for aluno in db_alunos]

# @alunos_router.get("/alunos/email/{email_aluno}", response_model=Aluno)
# def read_aluno_por_email(email_aluno: str, db: Session = Depends(get_db)):
#     """
#     Busca um aluno pelo email. (REMOVIDO: Campo 'email' não existe mais no modelo Aluno)
#     """
#     # Este endpoint foi removido ou deve ser ignorado, pois o campo 'email' não está mais no ModelAluno.
#     # Se descomentado, causará erro.
#     pass


# --- NOVAS ROTAS DE GAMIFICAÇÃO ---

@alunos_router.post("/alunos/{aluno_id}/add_xp", response_model=Aluno)
def add_xp_to_aluno(aluno_id: int, xp_amount: int, db: Session = Depends(get_db)):
    """
    Adiciona pontos de experiência (XP) a um aluno e recalcula seu nível.

    Args:
        aluno_id: O ID do aluno.
        xp_amount: A quantidade de XP a ser adicionada.

    Raises:
        HTTPException: 404 - Aluno não encontrado.

    Returns:
        Aluno: O aluno atualizado.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    db_aluno.xp += xp_amount
    db_aluno.total_points += xp_amount # Se XP também contar como pontos totais
    db_aluno.level = (db_aluno.xp // 100) + 1 # Exemplo: cada 100 XP é um novo nível

    db.commit()
    db.refresh(db_aluno)
    return _load_badges_for_response(db_aluno)

@alunos_router.post("/alunos/{aluno_id}/award_badge", response_model=Aluno)
def award_badge_to_aluno(aluno_id: int, badge_name: str, db: Session = Depends(get_db)):
    """
    Concede um distintivo (badge) a um aluno, se ele ainda não o possuir.

    Args:
        aluno_id: O ID do aluno.
        badge_name: O nome do distintivo a ser concedido.

    Raises:
        HTTPException: 404 - Aluno não encontrado.

    Returns:
        Aluno: O aluno atualizado com o novo distintivo.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    current_badges = json.loads(db_aluno.badges) if db_aluno.badges else []
    if badge_name not in current_badges:
        current_badges.append(badge_name)
        db_aluno.badges = json.dumps(current_badges)
        db.commit()
        db.refresh(db_aluno)
        
    return _load_badges_for_response(db_aluno)

@alunos_router.get("/leaderboard", response_model=List[Aluno])
def get_leaderboard(db: Session = Depends(get_db), limit: int = 10):
    """
    Retorna um leaderboard dos alunos, classificados por XP.

    Args:
        limit: O número máximo de alunos a serem retornados no leaderboard.

    Returns:
        List[Aluno]: Uma lista dos alunos no leaderboard.
    """
    leaderboard = db.query(ModelAluno).order_by(ModelAluno.xp.desc()).limit(limit).all()
    
    return [_load_badges_for_response(aluno) for aluno in leaderboard]

@alunos_router.get("/guilds/leaderboard", response_model=List[GuildLeaderboardEntry])
def get_guild_leaderboard(db: Session = Depends(get_db)):
    """
    Retorna um leaderboard das guildas, classificadas pela soma total de XP de seus membros.

    Returns:
        List[GuildLeaderboardEntry]: Uma lista de guildas e suas pontuações totais de XP.
    """
    guild_scores = db.query(
        ModelAluno.guilda,
        func.sum(ModelAluno.xp).label("total_xp")
    ).group_by(ModelAluno.guilda).order_by(func.sum(ModelAluno.xp).desc()).all()

    # Filtra entradas onde a guilda é None (alunos sem uma guilda atribuída)
    guild_scores_filtered = [
        {"guilda": entry.guilda, "total_xp": entry.total_xp}
        for entry in guild_scores if entry.guilda is not None
    ]

    if not guild_scores_filtered:
        raise HTTPException(status_code=404, detail="Nenhuma guilda com XP registrada.")

    return guild_scores_filtered

@alunos_router.get("/alunos/guilda/{guild_name}", response_model=List[Aluno])
def read_alunos_by_guild(guild_name: str, db: Session = Depends(get_db)):
    """
    Retorna uma lista de todos os alunos de uma guilda específica, ordenados por XP.

    Args:
        guild_name: O nome da guilda para filtrar os alunos.

    Raises:
        HTTPException: 404 - Nenhum aluno encontrado na guilda especificada.

    Returns:
        List[Aluno]: Uma lista dos alunos pertencentes à guilda.
    """
    db_alunos = db.query(ModelAluno).filter(ModelAluno.guilda == guild_name).order_by(ModelAluno.xp.desc()).all()

    if not db_alunos:
        raise HTTPException(status_code=404, detail=f"Nenhum aluno encontrado na guilda '{guild_name}'.")

    return [_load_badges_for_response(aluno) for aluno in db_alunos]