from pydantic import BaseModel
from typing import List, Optional

class Matricula(BaseModel):
    aluno_id: int
    curso_id: int
    score_in_quest: Optional[int] = 0
    status: Optional[str] = "iniciado"

    class Config:
        from_attributes = True

Matriculas = List[Matricula]

class Aluno(BaseModel):
    nome: str
    apelido: Optional[str] = None
    guilda: Optional[str] = None
    xp: Optional[int] = 0
    level: Optional[int] = 1
    total_points: Optional[int] = 0
    badges: Optional[List[str]] = []
    academic_score: Optional[float] = 0.0 

    class Config:
        from_attributes = True

Alunos = List[Aluno]

class AlunoUpdate(BaseModel):
    nome: Optional[str] = None
    apelido: Optional[str] = None
    guilda: Optional[str] = None
    xp: Optional[int] = None
    level: Optional[int] = None
    total_points: Optional[int] = None
    badges: Optional[List[str]] = None
    academic_score: Optional[float] = None 

    class Config:
        from_attributes = True

class Curso(BaseModel):
    nome: str
    codigo: str
    descricao: str
    xp_on_completion: Optional[int] = 0
    points_on_completion: Optional[float] = 0.0

    class Config:
        from_attributes = True

Cursos = List[Curso]

class GuildLeaderboardEntry(BaseModel):
    guilda: str
    total_xp: int

class BulkMatriculaCreate(BaseModel):
    curso_id: int
    guild_name: str

class QuestCompletionPoints(BaseModel): 
    quest_code: str
