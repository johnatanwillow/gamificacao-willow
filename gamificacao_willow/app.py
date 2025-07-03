from fastapi import FastAPI
from database import engine, Base
from routers.alunos import alunos_router
from routers.cursos import cursos_router
from routers.matriculas import matriculas_router


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="JWL - JOHNATAN WILLOW LANGUAGES - GAMIFICACAO", 
    description="""
        Esta API fornece endpoints para gerenciar alunos, XP, badges e outros recursos de gamificacao.  
        
        Permite realizar diferentes operações em cada uma dessas entidades.
    """, 
    version="1.0.0",
)

app.include_router(alunos_router, tags=["alunos"])
app.include_router(cursos_router, tags=["cursos"])
app.include_router(matriculas_router, tags=["matriculas"])