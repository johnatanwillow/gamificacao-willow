from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Matricula(BaseModel):
    aluno_id: int
    atividade_id: int
    score_in_quest: Optional[int] = 0
    status: Optional[str] = "iniciado"

    class Config:
        from_attributes = True

Matriculas = List[Matricula]

class TurmaBase(BaseModel):
    nome: str
    ano: Optional[int] = None # 

class TurmaCreate(TurmaBase):
    pass

class Turma(TurmaBase):
    id: int
    guildas: List["Guilda"] = [] # Lista de Guildas pertencentes a esta Turma

    class Config:
        from_attributes = True

class GuildaBase(BaseModel):
    nome: str
    turma_id: int # ID da Turma a qual esta Guilda pertence

class GuildaCreate(GuildaBase):
    pass

class Guilda(GuildaBase):
    id: int
    turma: Optional[TurmaBase] = None # Informações básicas da Turma
    alunos: List["Aluno"] = [] # Lista de Alunos pertencentes a esta Guilda

    class Config:
        from_attributes = True

class Aluno(BaseModel):
    nome: str
    apelido: Optional[str] = None
    guilda_id: Optional[int] = None # MODIFICADO: Agora é um ID para a Guilda
    xp: Optional[int] = 0
    level: Optional[int] = 1
    total_points: Optional[int] = 0
    badges: Optional[List[str]] = []
    academic_score: Optional[float] = 0.0
    
    guilda_nome: Optional[str] = None
    turma_nome: Optional[str] = None

    class Config:
        from_attributes = True

Alunos = List[Aluno]

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

class Atividade(BaseModel):
    nome: str
    codigo: str
    descricao: str
    xp_on_completion: Optional[int] = 0
    points_on_completion: Optional[float] = 0.0

    class Config:
        from_attributes = True

Atividade = List[Atividade]

class GuildLeaderboardEntry(BaseModel):
    guilda_id: int # Referencia a Guilda por ID
    guilda_nome: str # Nome da guilda para exibição
    turma_nome: Optional[str] = None # Nome da turma para exibição
    total_xp: int

class BulkMatriculaCreate(BaseModel):
    atividade_id: int
    guilda_id: int 


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
    aluno_nome: str
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
        
# Atualiza a referência forward para Turma no schema Guilda
Guilda.model_rebuild()
# Atualiza a referência forward para Guilda no schema Turma
Turma.model_rebuild()
# Atualiza a referência forward para Aluno no schema Guilda
Aluno.model_rebuild()