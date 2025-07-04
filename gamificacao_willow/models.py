from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func 

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
    apelido = Column(String, nullable=True)
    guilda = Column(String, nullable=True)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    total_points = Column(Integer, default=0)
    badges = Column(Text, default="[]")
    academic_score = Column(Float, default=0.0)

    matriculas = relationship("Matricula", back_populates="aluno")
    historico_xp_pontos = relationship("HistoricoXPPonto", back_populates="aluno")


class Curso(Base):
    __tablename__ = "cursos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    codigo = Column(String, nullable=False, unique=True)
    descricao = Column(Text)
    xp_on_completion = Column(Integer, default=0)
    points_on_completion = Column(Float, default=0.0)

    matriculas = relationship("Matricula", back_populates="curso")


# >>> ADICIONE ESTA NOVA CLASSE HistoricoXPPonto ABAIXO <<<
class HistoricoXPPonto(Base):
    __tablename__ = "historico_xp_pontos"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=False)
    tipo_transacao = Column(String, nullable=False) # Ex: "ganho_xp_quest", "penalizacao_xp", "ganho_pontos_academicos", "ganho_xp_manual"
    valor_xp_alterado = Column(Integer, default=0) # Valor de XP ganho ou deduzido
    valor_pontos_alterado = Column(Float, default=0.0) # Valor de Pontos Totais ou Academicos alterado
    motivo = Column(Text, nullable=True) # Descrição do motivo (ex: "Conclusão da Quest XYZ", "Penalidade por...")
    data_hora = Column(DateTime, default=func.now()) # Data e hora da transação
    referencia_entidade = Column(String, nullable=True) # Ex: "matricula", "curso", "manual", "guilda"
    referencia_id = Column(Integer, nullable=True) # ID da entidade referenciada (matricula_id, curso_id, etc.)

    aluno = relationship("Aluno", back_populates="historico_xp_pontos")