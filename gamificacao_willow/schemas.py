from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Matricula(BaseModel):
    id: Optional[int] = None # Adicionado id como opcional para POST
    aluno_id: int
    atividade_id: int
    score_in_quest: Optional[int] = 0
    status: Optional[str] = "iniciado"
    aluno_nome: Optional[str] = None # NOVO: Nome do aluno para exibição
    atividade_nome: Optional[str] = None # NOVO: Nome da atividade para exibição

    class Config:
        from_attributes = True

class TurmaBase(BaseModel):
    nome: str
    ano: Optional[str] = None # Ex: "3", "7", "8" ou "3° Ano", para indicar o ano da série

    class Config:
        from_attributes = True

class TurmaCreate(TurmaBase):
    pass

class Turma(TurmaBase):
    id: int
    guildas: List["Guilda"] = [] # Lista de Guildas pertencentes a esta Turma

    class Config:
        from_attributes = True

class TurmaUpdate(BaseModel):
    nome: Optional[str] = None
    ano: Optional[str] = None

    class Config:
        from_attributes = True

class GuildaBase(BaseModel):
    nome: str
    turma_id: int # ID da Turma a qual esta Guilda pertence

    class Config:
        from_attributes = True

class GuildaCreate(GuildaBase):
    pass

class Guilda(BaseModel): # Removido GuildaBase na herança direta para evitar campos duplicados no from_attributes
    id: int
    nome: str # Adicionado diretamente aqui
    turma_id: int # Adicionado diretamente aqui
    turma: Optional[TurmaBase] = None
    alunos: List["Aluno"] = [] # Relação para carregar alunos na resposta da guilda

    class Config:
        from_attributes = True

class GuildaUpdate(BaseModel):
    nome: Optional[str] = None
    turma_id: Optional[int] = None

    class Config:
        from_attributes = True

class Aluno(BaseModel):
    id: int # ID do aluno
    nome: str
    apelido: Optional[str] = None
    guilda_id: Optional[int] = None
    xp: Optional[int] = 0
    level: Optional[int] = 1
    total_points: Optional[int] = 0
    badges: Optional[List[str]] = []
    academic_score: Optional[float] = 0.0

    guilda_nome: Optional[str] = None # Campo para a resposta, não para entrada
    turma_nome: Optional[str] = None # Campo para a resposta, não para entrada

    class Config:
        from_attributes = True

# --- SCHEMAS PARA ATIVIDADE ---
class AtividadeBase(BaseModel):
    nome: str
    codigo: str
    descricao: str
    xp_on_completion: Optional[int] = 0
    points_on_completion: Optional[float] = 0.0

    class Config:
        from_attributes = True

class AtividadeCreate(AtividadeBase):
    pass

class Atividade(AtividadeBase):
    id: int # ID da atividade

    class Config:
        from_attributes = True
# --- FIM DOS SCHEMAS PARA ATIVIDADE ---


class AlunoCreateRequest(BaseModel):
    nome: str
    apelido: Optional[str] = None
    nome_guilda: Optional[str] = None # Campo para o nome da guilda na criação
    xp: Optional[int] = 0
    level: Optional[int] = 1
    total_points: Optional[int] = 0
    badges: Optional[List[str]] = []
    academic_score: Optional[float] = 0.0

    class Config:
        from_attributes = True

class AlunoUpdate(BaseModel):
    nome: Optional[str] = None
    apelido: Optional[str] = None
    guilda_id: Optional[int] = None
    xp: Optional[int] = None
    level: Optional[int] = None
    total_points: Optional[int] = None
    badges: Optional[List[str]] = None
    academic_score: Optional[float] = None
    motivo: Optional[str] = None

    class Config:
        from_attributes = True

class GuildLeaderboardEntry(BaseModel):
    guilda_id: int
    guilda_nome: str
    turma_nome: Optional[str] = None
    total_xp: int

class BulkMatriculaCreate(BaseModel):
    curso_id: int
    guilda_id: int

class BulkMatriculaByTurmaCreate(BaseModel):
    curso_id: int
    turma_id: int

class BulkCompleteMatriculaGuildRequest(BaseModel):
    atividade_id: int
    guilda_id: int
    score: int

class XPDeductionRequest(BaseModel):
    xp_deduction: int
    motivo: Optional[str] = None

class GuildPenalizationRequest(BaseModel):
    xp_deduction: int
    motivo: Optional[str] = None

class QuestCompletionPoints(BaseModel):
    quest_code: str
    motivo: Optional[str] = None

class HistoricoXPPontoSchema(BaseModel):
    id: int
    aluno_id: int
    tipo_transacao: str
    valor_xp_alterado: Optional[int] = 0
    valor_pontos_alterado: Optional[float] = 0.0
    motivo: Optional[str] = None
    data_hora: datetime
    referencia_entidade: Optional[str] = None
    referencia_id: Optional[int] = None

    class Config:
        from_attributes = True

class HistoricoAlunoDetalhadoSchema(BaseModel):
    id: int
    aluno_id: int
    aluno_nome: Optional[str] = None # CORRIGIDO: Tornar aluno_nome opcional
    aluno_apelido: Optional[str] = None
    guilda_nome: Optional[str] = None
    turma_nome: Optional[str] = None
    tipo_transacao: str
    valor_xp_alterado: Optional[int] = 0
    valor_pontos_alterado: Optional[float] = 0.0
    motivo: Optional[str] = None
    data_hora: datetime
    referencia_entidade: Optional[str] = None
    referencia_id: Optional[int] = None

    class Config:
        from_attributes = True

class BadgeAwardRequest(BaseModel):
    badge_name: str
    motivo: Optional[str] = None

# Reconstruir modelos após definir todos para evitar erros de referência circular
Guilda.model_rebuild()
Turma.model_rebuild()
Aluno.model_rebuild()
Matricula.model_rebuild()
Atividade.model_rebuild()