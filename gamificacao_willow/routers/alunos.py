# Arquivo: gamificacao_willow/routers/alunos.py
# Substitua TODO o conteúdo deste arquivo pelo código abaixo.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Dict, Union, Optional
import json # Importação necessária para json.loads()

from fpdf import FPDF # NOVO: Importação para gerar PDF
from fastapi.responses import StreamingResponse # NOVO: Para retornar o PDF

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
    Turma,
    TurmaCreate,
    TurmaUpdate,
    Guilda,
    GuildaCreate,
    GuildaUpdate,
    BadgeAwardRequest,
    AlunoCreateRequest,
    TurmaBase # <--- Certifique-se que TurmaBase está aqui
)
from models import (
    Aluno as ModelAluno,
    Atividade as ModelAtividade,
    HistoricoXPPonto,
    Turma as ModelTurma,
    Guilda as ModelGuilda
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

# --- Funções Auxiliares (CORRIGIDAS) ---

def _load_aluno_for_response(db_aluno_obj: ModelAluno) -> Aluno:
    """
    Função auxiliar para carregar e formatar os dados de um objeto Aluno do banco de dados
    para o schema de resposta, incluindo badges, nome da guilda e nome da turma.
    """
    aluno_data_dict = {}
    for column in db_aluno_obj.__table__.columns:
        aluno_data_dict[column.name] = getattr(db_aluno_obj, column.name)

    if 'badges' in aluno_data_dict and aluno_data_dict['badges'] is not None:
        try:
            aluno_data_dict['badges'] = json.loads(aluno_data_dict['badges'])
        except (json.JSONDecodeError, TypeError):
            aluno_data_dict['badges'] = []
    else:
        aluno_data_dict['badges'] = []

    response_aluno = Aluno.model_validate(aluno_data_dict)

    if db_aluno_obj.guilda_obj:
        response_aluno.guilda_nome = db_aluno_obj.guilda_obj.nome
        if db_aluno_obj.guilda_obj.turma:
            response_aluno.turma_nome = db_aluno_obj.guilda_obj.turma.nome
    else:
        response_aluno.guilda_nome = None
        response_aluno.turma_nome = None

    return response_aluno


def _load_guilda_for_response(db_guilda_obj: ModelGuilda) -> Guilda:
    """
    Função auxiliar para carregar e formatar os dados de uma Guilda,
    incluindo a turma associada e os alunos aninhados.
    """
    guilda_data_dict = {
        "id": db_guilda_obj.id,
        "nome": db_guilda_obj.nome,
        "turma_id": db_guilda_obj.turma_id,
        "turma": None, # Inicializa turma como None para preencher depois
        "alunos": [] # Inicializa alunos como lista vazia
    }

    # Processa alunos aninhados usando _load_aluno_for_response
    if db_guilda_obj.alunos:
        guilda_data_dict['alunos'] = [_load_aluno_for_response(aluno) for aluno in db_guilda_obj.alunos]
    
    # Processa a turma associada usando TurmaBase.model_validate
    if db_guilda_obj.turma:
        turma_data_dict = {
            "nome": db_guilda_obj.turma.nome,
            "ano": db_guilda_obj.turma.ano
        }
        guilda_data_dict['turma'] = TurmaBase.model_validate(turma_data_dict) # <--- CORRIGIDO: Agora usa TurmaBase

    return Guilda.model_validate(guilda_data_dict)


def _load_turma_for_response(db_turma_obj: ModelTurma) -> Turma:
    """
    Função auxiliar para carregar e formatar os dados de uma Turma,
    incluindo as guildas aninhadas.
    """
    turma_data_dict = {
        "id": db_turma_obj.id,
        "nome": db_turma_obj.nome,
        "ano": db_turma_obj.ano,
        "guildas": [] # Inicializa guildas como lista vazia
    }

    # Processa guildas aninhadas usando _load_guilda_for_response
    if db_turma_obj.guildas:
        # Removida a linha 'db.refresh(guilda)' daqui, que causava o NameError.
        # As guildas e seus alunos já devem estar carregados via joinedload na query principal.
        turma_data_dict['guildas'] = [_load_guilda_for_response(guilda) for guilda in db_turma_obj.guildas]
    
    return Turma.model_validate(turma_data_dict)


def _award_badge_if_new(db_aluno: ModelAluno, badge_name: str, db: Session) -> bool:
    """
    Concede um distintivo (badge) a um aluno se ele ainda não o possuir.
    """
    current_badges = json.loads(db_aluno.badges) if db_aluno.badges else []
    if badge_name not in current_badges:
        current_badges.append(badge_name)
        db_aluno.badges = json.dumps(current_badges) # Salva como string JSON no DB
        db.add(db_aluno)
        return True
    return False

def _check_and_award_level_badges(db_aluno: ModelAluno, db: Session) -> bool:
    """
    Verifica o XP atual do aluno e concede/remove distintivos de nível apropriados
    com base nos `BADGE_TIERS`.
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
        db_aluno.badges = json.dumps(expected_badges) # Salva como string JSON no DB
        db.add(db_aluno)
        return True
    return False


# --- Endpoints de Turmas ---

@alunos_router.post("/turmas", response_model=Turma, status_code=status.HTTP_201_CREATED)
def create_turma(turma: TurmaCreate, db: Session = Depends(get_db)):
    """
    Cria uma nova turma de alunos.
    """
    db_turma = db.query(ModelTurma).filter(ModelTurma.nome == turma.nome).first()
    if db_turma:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Turma com este nome já existe")

    db_turma = ModelTurma(**turma.dict())
    db.add(db_turma)
    db.commit()
    db.refresh(db_turma)
    return _load_turma_for_response(db_turma)


@alunos_router.get("/turmas", response_model=List[Turma])
def read_turmas(db: Session = Depends(get_db)):
    """
    Retorna uma lista de todas as turmas cadastradas, incluindo as guildas associadas a cada uma.
    """
    turmas = db.query(ModelTurma).options(
        joinedload(ModelTurma.guildas).joinedload(ModelGuilda.alunos)
    ).all()
    return [_load_turma_for_response(turma) for turma in turmas]


@alunos_router.put("/turmas/{turma_id}", response_model=Turma)
def update_turma(turma_id: int, turma: TurmaUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de uma turma existente.
    """
    db_turma = db.query(ModelTurma).filter(ModelTurma.id == turma_id).first()
    if db_turma is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada")

    if turma.nome is not None and turma.nome != db_turma.nome:
        existing_turma = db.query(ModelTurma).filter(ModelTurma.nome == turma.nome).first()
        if existing_turma:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe uma turma com este nome.")

    for key, value in turma.dict(exclude_unset=True).items():
        setattr(db_turma, key, value)

    db.commit()
    db.refresh(db_turma)
    return _load_turma_for_response(db_turma)


@alunos_router.delete("/turmas/{turma_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_turma(turma_id: int, db: Session = Depends(get_db)):
    """
    Deleta uma turma específica.
    """
    db_turma = db.query(ModelTurma).filter(ModelTurma.id == turma_id).first()
    if db_turma is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada")

    try:
        db.delete(db_turma)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Não foi possível deletar a turma devido a um erro inesperado. Erro: {e}"
        )


# --- Endpoints de Guildas ---

@alunos_router.post("/guildas", response_model=Guilda, status_code=status.HTTP_201_CREATED)
def create_guilda(guilda: GuildaCreate, db: Session = Depends(get_db)):
    """
    Cria uma nova guilda e a associa a uma turma existente.
    """
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

    db_guilda.turma = db_turma
    return _load_guilda_for_response(db_guilda)


@alunos_router.get("/guildas", response_model=List[Guilda])
def read_guildas(db: Session = Depends(get_db)):
    """
    Retorna uma lista de todas as guildas cadastradas, incluindo as informações da turma associada.
    """
    guildas = db.query(ModelGuilda).options(
        joinedload(ModelGuilda.turma),
        joinedload(ModelGuilda.alunos)
    ).all()
    return [_load_guilda_for_response(guilda) for guilda in guildas]


@alunos_router.put("/guildas/{guilda_id}", response_model=Guilda)
def update_guilda(guilda_id: int, guilda: GuildaUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de uma guilda existente.
    """
    db_guilda = db.query(ModelGuilda).filter(ModelGuilda.id == guilda_id).first()
    if db_guilda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guilda não encontrada")

    if guilda.nome is not None and guilda.nome != db_guilda.nome:
        existing_guilda = db.query(ModelGuilda).filter(ModelGuilda.nome == guilda.nome).first()
        if existing_guilda:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe uma guilda com este nome.")

    if guilda.turma_id is not None and guilda.turma_id != db_guilda.turma_id:
        db_new_turma = db.query(ModelTurma).filter(ModelTurma.id == guilda.turma_id).first()
        if not db_new_turma:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nova Turma não encontrada.")

    for key, value in guilda.dict(exclude_unset=True).items():
        setattr(db_guilda, key, value)

    db.commit()
    db.refresh(db_guilda)

    db_guilda = db.query(ModelGuilda).options(joinedload(ModelGuilda.turma)).filter(ModelGuilda.id == guilda_id).first()
    return _load_guilda_for_response(db_guilda)


@alunos_router.delete("/guildas/{guilda_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_guilda(guilda_id: int, db: Session = Depends(get_db)):
    """
    Deleta uma guilda específica.
    """
    db_guilda = db.query(ModelGuilda).filter(ModelGuilda.id == guilda_id).first()
    if db_guilda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guilda não encontrada")

    try:
        db.delete(db_guilda)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Não foi possível deletar a guilda devido a um erro inesperado. Erro: {e}"
        )


# --- Endpoints de Alunos ---

@alunos_router.post("/alunos", response_model=Aluno, status_code=status.HTTP_201_CREATED)
def create_aluno(aluno_request: AlunoCreateRequest, db: Session = Depends(get_db)):
    """
    Cria um novo aluno no sistema de gamificação, encontrando a guilda por nome.
    """
    guilda_id_to_assign = None
    if aluno_request.nome_guilda:
        db_guilda = db.query(ModelGuilda).filter(ModelGuilda.nome == aluno_request.nome_guilda).first()
        if not db_guilda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guilda '{aluno_request.nome_guilda}' não encontrada."
            )
        guilda_id_to_assign = db_guilda.id

    aluno_data_for_model = aluno_request.dict(exclude={"nome_guilda"}, exclude_unset=True)
    aluno_data_for_model["guilda_id"] = guilda_id_to_assign

    if "badges" in aluno_data_for_model and aluno_data_for_model["badges"] is not None:
        aluno_data_for_model["badges"] = json.dumps(aluno_data_for_model["badges"])
    else:
        aluno_data_for_model["badges"] = json.dumps([])

    if "academic_score" not in aluno_data_for_model or aluno_data_for_model["academic_score"] is None:
        aluno_data_for_model["academic_score"] = 0.0

    db_aluno = ModelAluno(**aluno_data_for_model)
    db.add(db_aluno)
    db.commit()
    db.refresh(db_aluno)

    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == db_aluno.id).first()

    if _check_and_award_level_badges(db_aluno, db):
        db.commit()
        db.refresh(db_aluno)

    return _load_aluno_for_response(db_aluno)

@alunos_router.get("/alunos", response_model=List[Aluno])
def read_alunos(db: Session = Depends(get_db)):
    """
    Retorna uma lista de todos os alunos cadastrados, incluindo seus dados de gamificação,
    nome da guilda e nome da turma.
    """
    alunos = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).all()
    return [_load_aluno_for_response(aluno) for aluno in alunos]

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

@alunos_router.put("/alunos/{aluno_id}", response_model=Aluno)
def update_aluno(aluno_id: int, aluno: AlunoUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de um aluno existente, com a possibilidade de registrar o motivo
    das alterações de XP e pontos no histórico.
    Permite renomear o aluno, alterar o apelido ou movê-lo para uma guilda diferente.
    Ao mover para uma nova guilda, caso esta guilda seja de outra turma, o aluno será implicitamente migrado para a turma associada a essa nova guilda. TODOS os alunos precisam estar inseridos numa guilda.
    """
    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    if aluno.guilda_id is not None:
        db_guilda = db.query(ModelGuilda).filter(ModelGuilda.id == aluno.guilda_id).first()
        if not db_guilda:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guilda não encontrada")

    old_xp = db_aluno.xp
    old_total_points = db_aluno.total_points
    old_academic_score = db_aluno.academic_score

    xp_updated = False
    historico_registros = []

    for key, value in aluno.dict(exclude_unset=True).items():
        if key == "badges":
            setattr(db_aluno, key, json.dumps(value))
        elif key == "motivo":
            pass
        else:
            if key == "xp":
                xp_updated = True
            setattr(db_aluno, key, value)

    motivo_alteracao = aluno.motivo if aluno.motivo else "Alteração manual via PUT /alunos/{aluno_id}"

    if xp_updated:
        xp_change = db_aluno.xp - old_xp
        if xp_change != 0:
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

    if "total_points" in aluno.dict(exclude_unset=True):
        if db_aluno.total_points != old_total_points:
            points_change = db_aluno.total_points - old_total_points
            historico_registros.append(
                HistoricoXPPonto(
                    aluno_id=db_aluno.id,
                    tipo_transacao="ajuste_manual_pontos_totais",
                    valor_xp_alterado=0,
                    valor_pontos_alterado=float(points_change),
                    motivo=motivo_alteracao,
                    referencia_entidade="aluno",
                    referencia_id=db_aluno.id
                )
            )

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

    db.add_all(historico_registros)
    db.commit()
    db.refresh(db_aluno)

    if _check_and_award_level_badges(db_aluno, db):
        db.commit()
        db.refresh(db_aluno)

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

    aluno_deletado = _load_aluno_for_response(db_aluno)

    db.delete(db_aluno)
    db.commit()
    return aluno_deletado

@alunos_router.get("/alunos/nome/{nome_aluno}", response_model=Union[Aluno, List[Aluno]])
def read_aluno_por_nome(nome_aluno: str, db: Session = Depends(get_db)):
    """
    Busca alunos pelo nome (parcial ou completo), incluindo nome da guilda e turma.
    """
    db_alunos = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.nome.ilike(f"%{nome_aluno}%")).all()

    if not db_alunos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum aluno encontrado com esse nome")

    if len(db_alunos) == 1:
        return _load_aluno_for_response(db_alunos[0]) # <--- Corrigido aqui (usei _load_aluno_for_response)

    return [_load_aluno_for_response(aluno) for aluno in db_alunos]

@alunos_router.post("/alunos/{aluno_id}/add_quest_academic_points", response_model=Aluno)
def add_quest_academic_points(aluno_id: int, quest_completion_data: QuestCompletionPoints, db: Session = Depends(get_db)):
    """
    Adiciona pontos acadêmicos a um aluno com base na conclusão de uma quest, com motivo.
    """
    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    db_atividade = db.query(ModelAtividade).filter(ModelAtividade.codigo == quest_completion_data.quest_code).first()
    if db_atividade is None:
        raise HTTPException(status_code=404, detail=f"Atividade com código '{quest_completion_data.quest_code}' não encontrada.")

    pontos_adicionados = db_atividade.points_on_completion
    db_aluno.academic_score += pontos_adicionados

    motivo_registro = quest_completion_data.motivo if quest_completion_data.motivo else f"Pontos Acadêmicos por Atividade '{db_atividade.nome}' ({db_atividade.codigo})"

    historico_registro = HistoricoXPPonto(
        aluno_id=db_aluno.id,
        tipo_transacao="ganho_pontos_academicos_manual_atividade",
        valor_xp_alterado=0,
        valor_pontos_alterado=pontos_adicionados,
        motivo=motivo_registro,
        referencia_entidade="atividade",
        referencia_id=db_atividade.id
    )
    db.add(historico_registro)
    
    db.commit()
    db.refresh(db_aluno)
    return _load_aluno_for_response(db_aluno)

@alunos_router.post("/alunos/{aluno_id}/award_badge", response_model=Aluno)
def award_badge_to_aluno(aluno_id: int, badge_data: BadgeAwardRequest, db: Session = Depends(get_db)):
    """
    Concede um distintivo (badge) a um aluno, se ele ainda não o possuir, e registra o motivo.
    Este é um método manual/direto de concessão de badge, separado da evolução por nível.
    """
    db_aluno = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    badge_name = badge_data.badge_name
    motivo = badge_data.motivo if badge_data.motivo else f"Concessão manual do distintivo '{badge_name}'"

    if _award_badge_if_new(db_aluno, badge_name, db):
        historico_registro = HistoricoXPPonto(
            aluno_id=db_aluno.id,
            tipo_transacao="concessao_badge_manual",
            valor_xp_alterado=0, # Badges não alteram XP diretamente neste ponto
            valor_pontos_alterado=0.0, # Badges não alteram pontos directamente neste ponto
            motivo=motivo,
            referencia_entidade="badge", # Entidade de referência para o histórico
            referencia_id=None
        )
        db.add(historico_registro)
        db.commit()
        db.refresh(db_aluno)
    else:
        pass

    return _load_aluno_for_response(db_aluno)

@alunos_router.get("/leaderboard", response_model=List[Aluno])
def get_leaderboard(db: Session = Depends(get_db), limit: int = 10):
    """
    Retorna um leaderboard dos alunos, classificados por XP, incluindo nome da guilda e turma.
    """
    leaderboard = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).order_by(ModelAluno.xp.desc()).limit(limit).all()

    return [_load_aluno_for_response(aluno) for aluno in leaderboard]

@alunos_router.get("/guilds/leaderboard", response_model=List[GuildLeaderboardEntry])
def get_guild_leaderboard(db: Session = Depends(get_db)):
    """
    Retorna um leaderboard das guildas, classificadas pela soma total de XP de seus membros,
    incluindo o nome da turma.
    """
    guild_scores = db.query(
        ModelGuilda.id,
        ModelGuilda.nome,
        ModelTurma.nome.label("turma_nome"), # CORREÇÃO AQUI: Alias explícito para o nome da turma
        func.sum(ModelAluno.xp).label("total_xp")
    ).join(ModelAluno, ModelGuilda.id == ModelAluno.guilda_id).join(ModelTurma, ModelGuilda.turma_id == ModelTurma.id).group_by(ModelGuilda.id, ModelGuilda.nome, ModelTurma.nome).order_by(func.sum(ModelAluno.xp).desc()).all()

    guild_leaderboard = [
        {"guilda_id": entry.id, "guilda_nome": entry.nome, "turma_nome": entry.turma_nome, "total_xp": entry.total_xp} # CORREÇÃO AQUI: Acessa via 'turma_nome'
        for entry in guild_scores
    ]

    if not guild_leaderboard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma guilda com XP registrada.")

    return guild_leaderboard

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

    return [_load_aluno_for_response(aluno) for aluno in db_alunos]

# NOVO ENDPOINT: Gerar Relatório PDF Completo
@alunos_router.get("/relatorio-pdf", tags=["Relatórios"])
async def gerar_relatorio_pdf_completo(db: Session = Depends(get_db)):
    """
    Gera um relatório completo do sistema (turmas, guildas, alunos, rankings, atividades) em PDF.
    """
    pdf = FPDF()
    pdf.add_page()
    
    # Adicionar suporte a fontes Unicode ou usar fontes que suportem caracteres especiais se necessário
    # pdf.add_font('DejaVuSans', '', 'DejaVuSansCondensed.ttf', uni=True)
    # pdf.set_font('DejaVuSans', size=12)

    # Usando fonte padrão que suporta caracteres básicos para esta demonstração
    pdf.set_font("Arial", size=16, style='B')
    pdf.cell(0, 10, txt="Relatório Completo do Sistema WILLOW de Gamificação", ln=True, align="C")
    pdf.ln(10)

    # --- Seção de Turmas ---
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(0, 10, txt="1. Turmas e suas Guildas/Alunos", ln=True, align="L")
    pdf.set_font("Arial", size=10)
    turmas = db.query(ModelTurma).options(
        joinedload(ModelTurma.guildas).joinedload(ModelGuilda.alunos)
    ).all()
    if turmas:
        for turma in turmas:
            pdf.set_font("Arial", size=12, style='B')
            pdf.cell(0, 7, txt=f"Turma: {turma.nome} (Ano: {turma.ano if turma.ano else 'N/A'}) [ID: {turma.id}]", ln=True)
            if turma.guildas:
                pdf.set_font("Arial", size=11, style='I')
                pdf.cell(0, 7, txt="  Guildas:", ln=True)
                for guilda in turma.guildas:
                    pdf.set_font("Arial", size=10)
                    pdf.cell(0, 6, txt=f"    - {guilda.nome} [ID: {guilda.id}]", ln=True)
                    if guilda.alunos:
                        pdf.set_font("Arial", size=9)
                        for aluno in guilda.alunos:
                            pdf.cell(0, 5, txt=f"      * {aluno.nome} ({aluno.apelido or 'S/Apelido'}) - XP: {aluno.xp} - Nível: {aluno.level} (Pontos: {aluno.total_points})", ln=True)
                            if aluno.badges:
                                try:
                                    badges_list = json.loads(aluno.badges)
                                    if isinstance(badges_list, list):
                                        pdf.cell(0, 5, txt=f"        Badges: {', '.join(badges_list)}", ln=True)
                                except (json.JSONDecodeError, TypeError):
                                    pdf.cell(0, 5, txt="        Badges: (Formato inválido)", ln=True)
                            else:
                                pdf.cell(0, 5, txt="        Badges: Nenhum", ln=True)
                        pdf.ln(1)
                    else:
                        pdf.set_font("Arial", size=9)
                        pdf.cell(0, 5, txt="      (Nenhum aluno nesta guilda)", ln=True)
                pdf.ln(3)
            else:
                pdf.set_font("Arial", size=10)
                pdf.cell(0, 7, txt="  (Nenhuma guilda nesta turma)", ln=True)
            pdf.ln(5)
    else:
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, txt="Nenhuma turma cadastrada.", ln=True)
    
    pdf.add_page() # Adiciona nova página para Leaderboards se necessário
    pdf.set_font("Arial", size=16, style='B')
    pdf.cell(0, 10, txt="Relatório Completo do Sistema WILLOW de Gamificação", ln=True, align="C")
    pdf.ln(10)

    # --- Seção de Leaderboard Geral (Top 20 Alunos) ---
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(0, 10, txt="2. Leaderboard Geral (Top 20 Alunos)", ln=True, align="L")
    pdf.set_font("Arial", size=10)
    leaderboard = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).order_by(ModelAluno.xp.desc()).limit(20).all() 
    if leaderboard:
        # Tabela para Leaderboard
        col_widths = [15, 55, 20, 20, 50, 25] # ID, Nome, XP, Nível, Guilda(Turma), Pontos Totais
        pdf.set_font("Arial", size=9, style='B')
        pdf.cell(col_widths[0], 7, "ID", 1, 0, 'C')
        pdf.cell(col_widths[1], 7, "Nome (Apelido)", 1, 0, 'C')
        pdf.cell(col_widths[2], 7, "XP", 1, 0, 'C')
        pdf.cell(col_widths[3], 7, "Nível", 1, 0, 'C')
        pdf.cell(col_widths[4], 7, "Guilda (Turma)", 1, 0, 'C')
        pdf.cell(col_widths[5], 7, "Pts Totais", 1, 1, 'C') # ln=1 para nova linha

        pdf.set_font("Arial", size=9)
        for aluno in leaderboard:
            guild_turma = f"{aluno.guilda_obj.nome} ({aluno.guilda_obj.turma.nome})" if aluno.guilda_obj and aluno.guilda_obj.turma else "N/A"
            pdf.cell(col_widths[0], 7, str(aluno.id), 1, 0, 'C')
            pdf.cell(col_widths[1], 7, f"{aluno.nome} ({aluno.apelido or '-'})", 1, 0, 'L')
            pdf.cell(col_widths[2], 7, str(aluno.xp), 1, 0, 'C')
            pdf.cell(col_widths[3], 7, str(aluno.level), 1, 0, 'C')
            pdf.cell(col_widths[4], 7, guild_turma, 1, 0, 'L')
            pdf.cell(col_widths[5], 7, str(aluno.total_points), 1, 1, 'C') # ln=1 para nova linha
    else:
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, txt="Nenhum aluno no leaderboard.", ln=True)
    pdf.ln(10)

    # --- Seção de Leaderboard por Guilda ---
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(0, 10, txt="3. Leaderboard por Guilda", ln=True, align="L")
    pdf.set_font("Arial", size=10)
    guild_scores = db.query(
        ModelGuilda.id,
        ModelGuilda.nome,
        ModelTurma.nome.label("turma_nome"), # CORREÇÃO AQUI: Alias explícito para o nome da turma
        func.sum(ModelAluno.xp).label("total_xp")
    ).join(ModelAluno, ModelGuilda.id == ModelAluno.guilda_id).join(ModelTurma, ModelGuilda.turma_id == ModelTurma.id).group_by(ModelGuilda.id, ModelGuilda.nome, ModelTurma.nome).order_by(func.sum(ModelAluno.xp).desc()).all()

    if guild_scores:
        col_widths = [15, 60, 40, 40] # ID, Nome Guilda, Turma, Total XP
        pdf.set_font("Arial", size=9, style='B')
        pdf.cell(col_widths[0], 7, "ID", 1, 0, 'C')
        pdf.cell(col_widths[1], 7, "Guilda", 1, 0, 'C')
        pdf.cell(col_widths[2], 7, "Turma", 1, 0, 'C')
        pdf.cell(col_widths[3], 7, "Total XP", 1, 1, 'C') # ln=1 para nova linha
        
        pdf.set_font("Arial", size=9)
        for entry in guild_scores:
            pdf.cell(col_widths[0], 7, str(entry.id), 1, 0, 'C')
            pdf.cell(col_widths[1], 7, entry.nome, 1, 0, 'L')
            pdf.cell(col_widths[2], 7, entry.turma_nome, 1, 0, 'L') # CORREÇÃO AQUI: Acessa via 'turma_nome'
            pdf.cell(col_widths[3], 7, str(entry.total_xp), 1, 1, 'C') # ln=1 para nova linha
    else:
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, txt="Nenhuma guilda com XP registrada.", ln=True)
    pdf.ln(10)

    # --- Seção de Atividades ---
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(0, 10, txt="4. Atividades Cadastradas", ln=True, align="L")
    pdf.set_font("Arial", size=10)
    atividades = db.query(ModelAtividade).all()
    if atividades:
        for atividade in atividades:
            pdf.set_font("Arial", size=11, style='B')
            pdf.cell(0, 7, txt=f"Código: {atividade.codigo} - {atividade.nome}", ln=True)
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 5, txt=f"  Descrição: {atividade.descricao}")
            pdf.cell(0, 5, txt=f"  XP ao Concluir: {atividade.xp_on_completion} | Pontos ao Concluir: {atividade.points_on_completion}", ln=True)
            pdf.ln(2)
    else:
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, txt="Nenhuma atividade cadastrada.", ln=True)
    pdf.ln(10)

    # Gera o PDF como bytes
    # Usar 'latin-1' para compatibilidade se não houver caracteres muito complexos
    pdf_bytes = pdf.output(dest='S') # CORREÇÃO AQUI: Removido .encode('latin-1')

    # Retorna o PDF como um StreamingResponse
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=relatorio_completo_willow.pdf"}
    )