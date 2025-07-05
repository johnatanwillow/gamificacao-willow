from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func 

from database import Base

# NOVO MODELO: Turma
class Turma(Base):
    __tablename__ = "turmas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, unique=True) # Ex: "5º A", "6º B"
    ano = Column(Integer, nullable=True) # Ex: 2025, para organizar turmas por ano

    guildas = relationship("Guilda", back_populates="turma")


# NOVO MODELO: Guilda (formalizada como entidade separada)
class Guilda(Base):
    __tablename__ = "guildas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, unique=True)
    turma_id = Column(Integer, ForeignKey("turmas.id"), nullable=False) # Chave estrangeira para Turma

    turma = relationship("Turma", back_populates="guildas")
    alunos = relationship("Aluno", back_populates="guilda_obj") # Relacionamento com Aluno


class Matricula(Base):
    __tablename__ = "matriculas"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    atividade_id = Column(Integer, ForeignKey("atividades.id"))
    score_in_quest = Column(Integer, default=0)
    status = Column(String, default="iniciado")

    aluno = relationship("Aluno", back_populates="matriculas")
    atividade = relationship("Atividade", back_populates="matriculas")


class Aluno(Base):
    __tablename__ = "alunos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    apelido = Column(String, nullable=True)
    # MODIFICADO: guilda agora é uma chave estrangeira para o modelo Guilda
    guilda_id = Column(Integer, ForeignKey("guildas.id"), nullable=True) 
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    total_points = Column(Integer, default=0)
    badges = Column(Text, default="[]")
    academic_score = Column(Float, default=0.0)

    # NOVO: Relacionamento com o objeto Guilda
    guilda_obj = relationship("Guilda", back_populates="alunos") 
    matriculas = relationship("Matricula", back_populates="aluno")
    historico_xp_pontos = relationship("HistoricoXPPonto", back_populates="aluno")


class Atividade(Base):
    __tablename__ = "atividades"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    codigo = Column(String, nullable=False, unique=True)
    descricao = Column(Text)
    xp_on_completion = Column(Integer, default=0)
    points_on_completion = Column(Float, default=0.0)

    matriculas = relationship("Matricula", back_populates="atividade")


class HistoricoXPPonto(Base):
    __tablename__ = "historico_xp_pontos"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=False)
    tipo_transacao = Column(String, nullable=False) 
    valor_xp_alterado = Column(Integer, default=0) 
    valor_pontos_alterado = Column(Float, default=0.0) 
    motivo = Column(Text, nullable=True) 
    data_hora = Column(DateTime, default=func.now()) 
    referencia_entidade = Column(String, nullable=True) 
    referencia_id = Column(Integer, nullable=True) 

    aluno = relationship("Aluno", back_populates="historico_xp_pontos")