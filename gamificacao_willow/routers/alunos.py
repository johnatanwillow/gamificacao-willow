from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Dict, Union, Optional
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
    Turma,
    TurmaCreate,
    TurmaUpdate, # Adicionado TurmaUpdate
    Guilda,
    GuildaCreate,
    GuildaUpdate, # Adicionado GuildaUpdate
    BadgeAwardRequest # Novo schema para o motivo do badge
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

# --- Funções Auxiliares ---

def _load_aluno_for_response(db_aluno_obj: ModelAluno) -> Aluno:
    """
    Função auxiliar para carregar e formatar os dados de um objeto Aluno do banco de dados
    para o schema de resposta, incluindo badges, nome da guilda e nome da turma.

    Args:
        db_aluno_obj: O objeto Aluno do SQLAlchemy a ser formatado.

    Returns:
        Aluno: O objeto Aluno formatado com dados adicionais para a resposta da API.
    """
    response_aluno = Aluno.from_orm(db_aluno_obj)
    
    if db_aluno_obj.badges:
        try:
            response_aluno.badges = json.loads(db_aluno_obj.badges)
        except json.JSONDecodeError:
            response_aluno.badges = []
    else:
        response_aluno.badges = []

    if db_aluno_obj.guilda_obj:
        response_aluno.guilda_nome = db_aluno_obj.guilda_obj.nome
        if db_aluno_obj.guilda_obj.turma:
            response_aluno.turma_nome = db_aluno_obj.guilda_obj.turma.nome
    
    return response_aluno

def _award_badge_if_new(db_aluno: ModelAluno, badge_name: str, db: Session) -> bool:
    """
    Concede um distintivo (badge) a um aluno se ele ainda não o possuir.

    Args:
        db_aluno: O objeto Aluno do SQLAlchemy.
        badge_name: O nome do distintivo a ser concedido.
        db: A sessão do banco de dados.

    Returns:
        bool: True se o distintivo foi concedido, False caso contrário (já possuía).
    """
    current_badges = json.loads(db_aluno.badges) if db_aluno.badges else []
    if badge_name not in current_badges:
        current_badges.append(badge_name)
        db_aluno.badges = json.dumps(current_badges)
        db.add(db_aluno)
        return True
    return False

def _check_and_award_level_badges(db_aluno: ModelAluno, db: Session) -> bool:
    """
    Verifica o XP atual do aluno e concede/remove distintivos de nível apropriados
    com base nos `BADGE_TIERS`.

    Args:
        db_aluno: O objeto Aluno do SQLAlchemy.
        db: A sessão do banco de dados.

    Returns:
        bool: True se houve alteração nos distintivos do aluno, False caso contrário.
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


# --- Endpoints de Turmas ---

@alunos_router.post("/turmas", response_model=Turma, status_code=status.HTTP_201_CREATED)
def create_turma(turma: TurmaCreate, db: Session = Depends(get_db)):
    """
    Cria uma nova turma de alunos.

    Args:
        turma: Os dados da turma a ser criada (nome, ano opcional).

    Returns:
        Turma: A turma criada.

    Raises:
        HTTPException: 400 - Se uma turma com o mesmo nome já existe.
    """
    db_turma = db.query(ModelTurma).filter(ModelTurma.nome == turma.nome).first()
    if db_turma:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Turma com este nome já existe")
    
    db_turma = ModelTurma(**turma.dict())
    db.add(db_turma)
    db.commit()
    db.refresh(db_turma)
    return db_turma

@alunos_router.get("/turmas", response_model=List[Turma])
def read_turmas(db: Session = Depends(get_db)):
    """
    Retorna uma lista de todas as turmas cadastradas, incluindo as guildas associadas a cada uma.

    Returns:
        List[Turma]: Uma lista de objetos Turma.
    """
    turmas = db.query(ModelTurma).options(joinedload(ModelTurma.guildas)).all()
    return turmas

@alunos_router.put("/turmas/{turma_id}", response_model=Turma)
def update_turma(turma_id: int, turma: TurmaUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de uma turma existente.

    Args:
        turma_id: O ID da turma a ser atualizada.
        turma: Os novos dados da turma (nome, ano).

    Returns:
        Turma: A turma atualizada.

    Raises:
        HTTPException: 404 - Se a turma não for encontrada.
        HTTPException: 400 - Se o novo nome da turma já estiver em uso.
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
    return db_turma

@alunos_router.delete("/turmas/{turma_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_turma(turma_id: int, db: Session = Depends(get_db)):
    """
    Deleta uma turma específica.

    AVISO: Com a configuração de cascata no models.py, a exclusão de uma turma
    resultará na exclusão automática de TODAS as guildas associadas a ela e,
    consequentemente, de TODOS os alunos dessas guildas, suas matrículas e históricos de XP/pontos.
    Esta é uma operação irreversível.

    Args:
        turma_id: O ID da turma a ser deletada.

    Raises:
        HTTPException: 404 - Se a turma não for encontrada.
        HTTPException: 500 - Se ocorrer um erro inesperado durante a exclusão.
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

    Args:
        guilda: Os dados da guilda a ser criada (nome, turma_id).

    Returns:
        Guilda: A guilda criada, incluindo informações básicas da turma.

    Raises:
        HTTPException: 404 - Se a turma especificada não for encontrada.
        HTTPException: 400 - Se uma guilda com o mesmo nome já existe.
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
    
    # Carregar o objeto turma para a resposta
    db_guilda.turma = db_turma
    return db_guilda

@alunos_router.get("/guildas", response_model=List[Guilda])
def read_guildas(db: Session = Depends(get_db)):
    """
    Retorna uma lista de todas as guildas cadastradas, incluindo as informações da turma associada.

    Returns:
        List[Guilda]: Uma lista de objetos Guilda.
    """
    guildas = db.query(ModelGuilda).options(joinedload(ModelGuilda.turma)).all()
    return guildas

@alunos_router.put("/guildas/{guilda_id}", response_model=Guilda)
def update_guilda(guilda_id: int, guilda: GuildaUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de uma guilda existente.
    Permite renomear a guilda ou movê-la para uma turma diferente.
    Ao mover para uma nova turma, todos os alunos da guilda são implicitamente migrados para a nova turma.

    Args:
        guilda_id: O ID da guilda a ser atualizada.
        guilda: Os novos dados da guilda (nome opcional, turma_id opcional).

    Returns:
        Guilda: A guilda atualizada, com informações básicas da turma.

    Raises:
        HTTPException: 404 - Se a guilda não for encontrada ou se a nova turma não existir.
        HTTPException: 400 - Se o novo nome da guilda já estiver em uso.
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
    
    # Recarrega o objeto guilda com as informações atualizadas da turma para a resposta
    db_guilda = db.query(ModelGuilda).options(joinedload(ModelGuilda.turma)).filter(ModelGuilda.id == guilda_id).first()
    return db_guilda

@alunos_router.delete("/guildas/{guilda_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_guilda(guilda_id: int, db: Session = Depends(get_db)):
    """
    Deleta uma guilda específica.

    AVISO: Com a configuração de cascata no models.py, a exclusão de uma guilda
    resultará na exclusão automática de TODOS os alunos associados a ela,
    bem como suas matrículas e históricos de XP/pontos. Esta é uma operação irreversível.

    Args:
        guilda_id: O ID da guilda a ser deletada.

    Raises:
        HTTPException: 404 - Se a guilda não for encontrada.
        HTTPException: 500 - Se ocorrer um erro inesperado durante a exclusão.
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
def create_aluno(aluno: Aluno, db: Session = Depends(get_db)):
    """
    Cria um novo aluno no sistema de gamificação.

    Args:
        aluno: Os dados do aluno a ser criado (nome, apelido, guilda_id opcional, etc.).

    Returns:
        Aluno: O aluno criado, com XP inicial, nível, pontos e quaisquer distintivos de nível concedidos.

    Raises:
        HTTPException: 404 - Se a guilda_id fornecida não for encontrada.
    """
    # Valida se a guilda_id existe
    if aluno.guilda_id:
        db_guilda = db.query(ModelGuilda).filter(ModelGuilda.id == aluno.guilda_id).first()
        if not db_guilda:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guilda não encontrada")

    aluno_data = aluno.dict(exclude={"id"})
    # Converte a lista de badges para JSON string antes de salvar no DB
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

    # Verifica e concede distintivos de nível ao criar o aluno, se aplicável
    if _check_and_award_level_badges(db_aluno, db):
        db.commit()
        db.refresh(db_aluno)

    return _load_aluno_for_response(db_aluno)

@alunos_router.get("/alunos", response_model=List[Aluno])
def read_alunos(db: Session = Depends(get_db)):
    """
    Retorna uma lista de todos os alunos cadastrados, incluindo seus dados de gamificação,
    nome da guilda e nome da turma.

    Returns:
        List[Aluno]: Uma lista de objetos Aluno formatados.
    """
    alunos = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma)).all()
    return [_load_aluno_for_response(aluno) for aluno in alunos]

@alunos_router.get("/alunos/{aluno_id}", response_model=Aluno)
def read_aluno(aluno_id: int, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de um aluno específico com base no ID fornecido,
    incluindo nome da guilda e nome da turma.

    Args:
        aluno_id: O ID do aluno a ser buscado.

    Returns:
        Aluno: O objeto Aluno formatado.

    Raises:
        HTTPException: 404 - Se o aluno não for encontrado.
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

    Args:
        aluno_id: O ID do aluno a ser atualizado.
        aluno: Os novos dados do aluno a serem aplicados.

    Returns:
        Aluno: O aluno atualizado, com os relacionamentos carregados e badges formatados.

    Raises:
        HTTPException: 404 - Se o aluno ou a guilda (se fornecida) não forem encontrados.
    """
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
        return _load_aluno_for_response(db_alunos[0])

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
        # Registrar a concessão do badge no histórico
        historico_registro = HistoricoXPPonto(
            aluno_id=db_aluno.id,
            tipo_transacao="concessao_badge_manual",
            valor_xp_alterado=0, # Badges não alteram XP diretamente neste ponto
            valor_pontos_alterado=0.0, # Badges não alteram pontos diretamente neste ponto
            motivo=motivo,
            referencia_entidade="badge", # Entidade de referência para o histórico
            referencia_id=None # Não há um ID específico para badges, pode ser None ou outro identificador
        )
        db.add(historico_registro)
        db.commit()
        db.refresh(db_aluno)
    else:
        # Se o badge já existia, podemos retornar uma mensagem indicando isso (opcional)
        # Por simplicidade, neste caso, apenas retornamos o aluno sem erro.
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
        ModelTurma.nome,
        func.sum(ModelAluno.xp).label("total_xp")
    ).join(ModelAluno, ModelGuilda.id == ModelAluno.guilda_id).join(ModelTurma, ModelGuilda.turma_id == ModelTurma.id).group_by(ModelGuilda.id, ModelGuilda.nome, ModelTurma.nome).order_by(func.sum(ModelAluno.xp).desc()).all()

    guild_leaderboard = [
        {"guilda_id": entry.id, "guilda_nome": entry.nome, "turma_nome": entry.nome_2, "total_xp": entry.total_xp}
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

@alunos_router.post("/guilds/{guild_name}/penalize_xp", response_model=List[Aluno])
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
    historico_registros = []

    for aluno in db_alunos_na_guilda:
        xp_antes = aluno.xp 
        aluno.xp -= xp_deduction
        if aluno.xp < 0:
            aluno.xp = 0
        aluno.level = (aluno.xp // 100) + 1

        db.add(aluno)
        
        historico_registros.append(HistoricoXPPonto(
            aluno_id=aluno.id,
            tipo_transacao="penalizacao_xp_guilda", 
            valor_xp_alterado=-xp_deduction, 
            valor_pontos_alterado=0.0,
            motivo=motivo_penalizacao, 
            referencia_entidade="guilda",
            referencia_id=db_guilda.id
        ))

    db.commit() 

    db.add_all(historico_registros)
    db.commit() 

    for aluno in db_alunos_na_guilda:
        db.refresh(aluno)
        if _check_and_award_level_badges(aluno, db):
            db.commit()
            db.refresh(aluno)
        updated_alunos_response.append(_load_aluno_for_response(aluno))

    return updated_alunos_response

@alunos_router.post("/alunos/{aluno_id}/penalize_xp", response_model=Aluno)
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
            
    return _load_aluno_for_response(db_aluno)

@alunos_router.get("/alunos/level/{level}", response_model=List[Aluno])
def read_alunos_by_level(
    level: int,
    db: Session = Depends(get_db),
    turma_id: Optional[int] = None,
    turma_nome: Optional[str] = None
):
    """
    Retorna uma lista de todos os alunos de um nível específico, ordenados por XP,
    incluindo nome da guilda e turma. Opcionalmente, pode filtrar por turma,
    usando ID ou nome da turma.

    Args:
        level: O nível dos alunos a serem buscados.
        turma_id: O ID da turma para filtrar os alunos (opcional).
        turma_nome: O nome (ou parte do nome) da turma para filtrar os alunos (opcional).

    Returns:
        List[Aluno]: Uma lista de objetos Aluno formatados.

    Raises:
        HTTPException: 400 - Se o nível fornecido for não positivo, ou se a busca por nome da turma for ambígua.
        HTTPException: 404 - Se nenhum aluno for encontrado no nível ou na turma especificada.
    """
    if level <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O nível deve ser um número positivo."
        )

    query = db.query(ModelAluno).options(joinedload(ModelAluno.guilda_obj).joinedload(ModelGuilda.turma))
    
    target_turma_id = None

    if turma_id is not None:
        target_turma_id = turma_id
    elif turma_nome is not None:
        db_turmas_matches = db.query(ModelTurma).filter(ModelTurma.nome.ilike(f"%{turma_nome}%")).all()
        
        if not db_turmas_matches:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhuma turma encontrada com o nome '{turma_nome}'.")
        
        if len(db_turmas_matches) > 1:
            matched_turmas_names = [f"{t.nome} (ID: {t.id})" for t in db_turmas_matches]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Múltiplas turmas encontradas com o nome '{turma_nome}'. Por favor, use o ID da turma para filtrar: {', '.join(matched_turmas_names)}"
            )
        
        target_turma_id = db_turmas_matches[0].id
    
    if target_turma_id is not None:
        db_turma = db.query(ModelTurma).filter(ModelTurma.id == target_turma_id).first()
        if db_turma is None: # Redundante se target_turma_id veio de uma busca por nome bem-sucedida, mas seguro
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Turma com ID {target_turma_id} não encontrada.")
        
        guild_ids_in_turma = [guilda.id for guilda in db_turma.guildas]
        if not guild_ids_in_turma:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhuma guilda encontrada para a Turma com ID {target_turma_id}. Não é possível filtrar alunos.")
        
        query = query.filter(ModelAluno.guilda_id.in_(guild_ids_in_turma))

    db_alunos = query.filter(ModelAluno.level == level).order_by(ModelAluno.xp.desc()).all()

    if not db_alunos:
        if target_turma_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado no nível '{level}' para a Turma com ID {target_turma_id}.")
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado no nível '{level}'.")

    return [_load_aluno_for_response(aluno) for aluno in db_alunos]


# --- Endpoints de Histórico ---

@alunos_router.get("/alunos/historico_xp_pontos", response_model=List[HistoricoAlunoDetalhadoSchema])
def get_historico_aluno_xp_pontos(
    aluno_id: Optional[int] = None,
    nome_aluno: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna o histórico detalhado de todas as transações de XP e pontos de um aluno,
    identificado por ID ou nome.

    Prioriza a busca por ID se fornecido. Se buscar por nome e houver ambiguidade,
    retorna um erro sugerindo o uso do ID.

    Args:
        aluno_id: O ID do aluno para buscar o histórico (opcional).
        nome_aluno: O nome (ou parte do nome) do aluno para buscar o histórico (opcional).

    Returns:
        List[HistoricoAlunoDetalhadoSchema]: Uma lista de registros de histórico detalhados.

    Raises:
        HTTPException:
            400 - Se nenhum identificador for fornecido ou se houver ambiguidade na busca por nome.
            404 - Se o aluno ou nenhum registro de histórico for encontrado.
    """
    db_aluno = None

    if aluno_id:
        # Prioriza a busca por ID, que é a mais eficiente e precisa
        db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
        if db_aluno is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Aluno com ID {aluno_id} não encontrado.")
    elif nome_aluno:
        # Busca por nome, com tratamento de ambiguidade
        db_alunos_matches = db.query(ModelAluno).filter(ModelAluno.nome.ilike(f"%{nome_aluno}%")).all()

        if not db_alunos_matches:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado com o nome '{nome_aluno}'.")
        
        if len(db_alunos_matches) > 1:
            matched_names = [f"{aluno.nome} (ID: {aluno.id})" for aluno in db_alunos_matches]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Múltiplos alunos encontrados com o nome '{nome_aluno}'. Por favor, use o ID do aluno para consultar o histórico: {', '.join(matched_names)}"
            )
        
        db_aluno = db_alunos_matches[0]
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Por favor, forneça 'aluno_id' ou 'nome_aluno'.")

    historico_com_detalhes = (
        db.query(HistoricoXPPonto, ModelAluno, ModelGuilda, ModelTurma)
        .join(ModelAluno, HistoricoXPPonto.aluno_id == ModelAluno.id)
        .outerjoin(ModelGuilda, ModelAluno.guilda_id == ModelGuilda.id)
        .outerjoin(ModelTurma, ModelGuilda.turma_id == ModelTurma.id) 
        .filter(HistoricoXPPonto.aluno_id == db_aluno.id)
        .order_by(HistoricoXPPonto.data_hora.asc())
        .all()
    )

    if not historico_com_detalhes:
        if aluno_id:
            detail_msg = f"Nenhum registro de histórico encontrado para o aluno com ID {aluno_id}."
        else:
            detail_msg = f"Nenhum registro de histórico encontrado para o aluno com nome '{nome_aluno}' (ID: {db_aluno.id})."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail_msg)

    response_list = []
    for historico_registro, aluno_info, guilda_info, turma_info in historico_com_detalhes:
        response_list.append(
            HistoricoAlunoDetalhadoSchema(
                id=historico_registro.id,
                aluno_id=historico_registro.aluno_id,
                aluno_nome=aluno_info.nome,
                aluno_apelido=aluno_info.apelido,
                guilda_nome=guilda_info.nome if guilda_info else None,
                turma_nome=turma_info.nome if turma_info else None,
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

@alunos_router.get("/turmas/{turma_id}/historico_xp_pontos", response_model=List[HistoricoAlunoDetalhadoSchema])
def get_historico_turma_xp_pontos(turma_id: int, db: Session = Depends(get_db)):
    """
    Retorna o histórico detalhado de todas as transações de XP e pontos de todos os alunos
    de uma turma específica.

    Args:
        turma_id: O ID da turma para buscar o histórico dos alunos.

    Returns:
        List[HistoricoAlunoDetalhadoSchema]: Uma lista de registros de histórico detalhados
                                             para todos os alunos da turma.

    Raises:
        HTTPException: 404 - Se a turma não for encontrada ou se nenhum histórico for encontrado
                             para os alunos da turma.
    """
    db_turma = db.query(ModelTurma).filter(ModelTurma.id == turma_id).first()
    if db_turma is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Turma com ID {turma_id} não encontrada.")

    # Obter IDs de todas as guildas nesta turma
    guild_ids_in_turma = [guilda.id for guilda in db_turma.guildas]
    if not guild_ids_in_turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhuma guilda encontrada para a Turma com ID {turma_id}.")

    # Obter IDs de todos os alunos nestas guildas
    aluno_ids_in_turma = [
        aluno.id for guilda_id in guild_ids_in_turma
        for aluno in db.query(ModelAluno).filter(ModelAluno.guilda_id == guilda_id).all()
    ]
    if not aluno_ids_in_turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum aluno encontrado na Turma com ID {turma_id}.")

    # Realiza JOINs para obter dados do Aluno, Guilda e Turma para os registros de histórico
    historico_com_detalhes = (
        db.query(HistoricoXPPonto, ModelAluno, ModelGuilda, ModelTurma)
        .join(ModelAluno, HistoricoXPPonto.aluno_id == ModelAluno.id)
        .outerjoin(ModelGuilda, ModelAluno.guilda_id == ModelGuilda.id)
        .outerjoin(ModelTurma, ModelGuilda.turma_id == ModelTurma.id) # Corrected typo: ModelGuilda.turma_id -> ModelTurma.id
        .filter(HistoricoXPPonto.aluno_id.in_(aluno_ids_in_turma)) # Filtra pelos alunos da turma
        .order_by(HistoricoXPPonto.data_hora.asc())
        .all()
    )

    if not historico_com_detalhes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nenhum registro de histórico encontrado para os alunos da Turma com ID {turma_id}.")

    response_list = []
    for historico_registro, aluno_info, guilda_info, turma_info in historico_com_detalhes:
        response_list.append(
            HistoricoAlunoDetalhadoSchema(
                id=historico_registro.id,
                aluno_id=historico_registro.aluno_id,
                aluno_nome=aluno_info.nome,
                aluno_apelido=aluno_info.apelido,
                guilda_nome=guilda_info.nome if guilda_info else None,
                turma_nome=turma_info.nome if turma_info else None,
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