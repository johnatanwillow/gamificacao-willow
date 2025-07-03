from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY # Se for usar PostgreSQL, ou ajuste para SQLite JSON
from sqlalchemy import JSON # Para SQLite, se a versão do SQLAlchemy suportar JSON ou Text para JSON string

from database import Base

class Matricula(Base):
    __tablename__ = "matriculas"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    curso_id = Column(Integer, ForeignKey("cursos.id"))
    score_in_quest = Column(Integer, default=0)
    status = Column(String, default="iniciado")

    aluno = relationship("Aluno", back_populates="matriculas")
    curso = relationship("Curso", back_populates="matriculas")

class Aluno(Base):
    __tablename__ = "alunos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    apelido = Column(String, nullable=True) # NOVO CAMPO: Apelido do aluno
    guilda = Column(String, nullable=True)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    total_points = Column(Integer, default=0)
    badges = Column(Text, default="[]") # Armazenado como JSON string

    matriculas = relationship("Matricula", back_populates="aluno")

class Curso(Base):
    __tablename__ = "cursos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    codigo = Column(String, nullable=False, unique=True)
    descricao = Column(Text)
    xp_on_completion = Column(Integer, default=0)
    points_on_completion = Column(Integer, default=0)

    matriculas = relationship("Matricula", back_populates="curso")