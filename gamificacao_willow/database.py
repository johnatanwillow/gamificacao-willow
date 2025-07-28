# Arquivo: gamificacao_willow/database.py
# Apague todo o conteúdo atual e cole este código.

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL do banco de dados SQLite
# Adicionado check_same_thread=False para compatibilidade com SQLite em múltiplos threads
SQLALCHEMY_DATABASE_URL = "sqlite:///./escola.db?check_same_thread=False"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependência para obter a sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()