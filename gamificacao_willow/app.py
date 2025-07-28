# Arquivo: gamificacao_willow/app.py
# Apague todo o conteúdo atual e cole este código.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routers.alunos import alunos_router
from routers.atividades import atividades_router # Adicionado import do router de atividades
from routers.matriculas import matriculas_router # Adicionado import do router de matriculas

# Cria todas as tabelas no banco de dados, se ainda não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Gamificação WILLOW",
    description="API para gerenciar alunos, turmas, guildas e gamificação no ambiente educacional WILLOW.",
    version="1.0.0",
    docs_url="/documentacao",
    redoc_url=None
)

# --- Adicionado/Atualizado: Configuração do CORSMiddleware para desenvolvimento local ---
# Permitir todas as origens (temporariamente para desenvolvimento)
# Ou definir explicitamente as origens, incluindo o protocolo 'file://'
origins = [
    "http://localhost",
    "http://localhost:8000", # Se o frontend estiver rodando na mesma porta do backend (improvável, mas para segurança)
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "null", # <--- CRUCIAL: Permite origens nulas (para arquivos abertos diretamente do sistema de arquivos)
    "file://", # <--- Adiciona explicitamente o protocolo file://
    "http://0.0.0.0:8000", # Para algumas configurações de Docker ou rede
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # <--- ALTERADO PARA "*" para permitir QUALQUER origem em desenvolvimento
    allow_credentials=True,
    allow_methods=["*"],            # Permitir todos os métodos (GET, POST, PUT, DELETE, OPTIONS)
    allow_headers=["*"],            # Permitir todos os cabeçalhos
)
# --- Fim da Configuração do CORSMiddleware ---


# Inclui os roteadores da aplicação
app.include_router(alunos_router)
app.include_router(atividades_router) # Inclui o roteador de atividades
app.include_router(matriculas_router) # Inclui o roteador de matrículas


@app.get("/")
async def read_root():
    return {"message": "Bem-vindo à API de Gamificação WILLOW!"}