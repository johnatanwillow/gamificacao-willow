from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func 

from database import Base

class Turma(Base):
    __tablename__ = "turmas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, unique=True) # Ex: "5º A", "6º B"
    ano = Column(Integer, nullable=True) # Ex: 2025, para organizar turmas por ano

    guildas = relationship("Guilda", back_populates="turma", cascade="all, delete-orphan", passive_deletes=True)


class Guilda(Base):
    __tablename__ = "guildas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, unique=True)
    turma_id = Column(Integer, ForeignKey("turmas.id", ondelete="CASCADE"), nullable=False) 

    turma = relationship("Turma", back_populates="guildas")
    alunos = relationship("Aluno", back_populates="guilda_obj", cascade="all, delete-orphan", passive_deletes=True)


class Matricula(Base):
    __tablename__ = "matriculas"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="CASCADE")) 
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
    guilda_id = Column(Integer, ForeignKey("guildas.id", ondelete="SET NULL"), nullable=True) 
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    total_points = Column(Integer, default=0)
    badges = Column(Text, default="[]")
    academic_score = Column(Float, default=0.0)

    guilda_obj = relationship("Guilda", back_populates="alunos") 
    # Adicionado cascade para deletar matrículas e histórico de XP quando o aluno é deletado
    matriculas = relationship("Matricula", back_populates="aluno", cascade="all, delete-orphan", passive_deletes=True)
    historico_xp_pontos = relationship("HistoricoXPPonto", back_populates="aluno", cascade="all, delete-orphan", passive_deletes=True)


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
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False) # Adicionado ondelete="CASCADE"
    tipo_transacao = Column(String, nullable=False) 
    valor_xp_alterado = Column(Integer, default=0) 
    valor_pontos_alterado = Column(Float, default=0.0) 
    motivo = Column(Text, nullable=True) 
    data_hora = Column(DateTime, default=func.now()) 
    referencia_entidade = Column(String, nullable=True) 
    referencia_id = Column(Integer, nullable=True) 

    aluno = relationship("Aluno", back_populates="historico_xp_pontos")