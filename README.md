# Projeto de Gamificação para Aulas de Inglês - Prof. Johnatan Willow

![Banner Placeholder](https://via.placeholder.com/800x200?text=Willow+-+Gamification+for+Learning)

Bem-vindo ao **Willow**, uma poderosa ferramenta baseada em FastAPI projetada para transformar suas aulas para jovens em uma experiência **gamificada**, **divertida** e **motivadora**!

O Willow funciona como a "espinha dorsal" do seu sistema de recompensas, permitindo que você, como professor:

* **Gerencie Jogadores (Seus Alunos)**: Crie perfis detalhados para cada aluno, incluindo apelidos e guildas.
* **Defina Quests e Níveis de Aprendizagem**: Crie "desafios" ou "módulos" de conteúdo de inglês (ou conteúdos de outras disciplinas) com recompensas específicas.
* **Rastreie o Progresso e Pontuação**: Monitore o desempenho de cada aluno em tempo real, registrando pontos de experiência (XP), níveis e distintivos (badges).
* **Crie Leaderboards**: Exiba a classificação dos alunos (geral e por guilda!) para promover uma competição saudável e motivadora.

> Este README.md foi criado para professores e educadores (usuários leigos em programação) que desejam utilizar o Willow para enriquecer suas aulas.

---

## ✅ Pré-requisitos

Para colocar o Willow para funcionar no seu computador, você precisará de:

* **Python 3.10 ou superior**
    Baixe aqui: [https://www.python.org/downloads/](https://www.python.org/downloads/)
* **Git**
    Baixe aqui: [https://git-scm.com/downloads](https://git-scm.com/downloads)
* **Docker (Opcional)**
    Para usuários mais avançados. Não é necessário para começar.

---

## 🚀 Como Colocar o Willow Para Rodar (Passo a Passo para Usuários Leigos)

### 1. Baixe o Projeto Willow:

* [Download Willow](https://github.com/johnatanwillow/gamificacao-willow)
* Descompacte o ZIP em uma pasta fácil de acessar (ex: `C:\MeusProjetos\Willow`).

### 2. Abra o Terminal (Prompt de Comando ou PowerShell)

* **Windows**: Pesquise por "Prompt de Comando" ou "PowerShell" no menu Iniciar.
* **Mac/Linux**: Abra o aplicativo "Terminal".

### 3. Navegue até a Pasta do Projeto:

Use o comando `cd` (change directory) para ir até a pasta onde você descompactou o projeto.
Exemplo:
```bash
cd C:\MeusProjetos\Willow
```

### 4. Crie um Ambiente Virtual:

```bash
python3 -m venv ./venv
```

### 5. Ative o Ambiente Virtual:

- **Linux/Mac:**

```bash
source venv/bin/activate
```

- **Windows (PowerShell):**

```bash
venv\Scripts\Activate
```
- **Windows (Prompt de Comando):**
```bash
venv\Scripts\activate
```
> Você saberá que deu certo quando aparecer `(venv)` no início da linha do terminal.

### 6. Instale as Dependências:

```bash
pip install -r gamificacao_willow/requirements.txt
```

### 7. Inicie o Willow (API de Gamificação):

> **Importante:** Se alterou os modelos (adicionou campos), apague o arquivo `escola.db` antes.

```bash
cd gamificacao_willow
uvicorn app:app --reload
```

### 8. Acesse a Documentação Interativa (Painel de Controle):

Abra no navegador:  
👉 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🎮 Mecânica da Gamificação no Willow

O Willow gerencia o progresso, recompensas e status dos alunos como **jogadores**.

### Entidades do Jogo:

- **Jogadores (Alunos):**
  - `nome`
  - `apelido`
  - `guilda`
  - `xp`
  - `nível`
  - `pontos_totais`
  - `distintivos (badges)`
  - `academic_score (pontuação acadêmica adicional)`

- **Quests / Cursos:**
  - `nome`
  - `codigo`
  - `descricao`
  - `xp_on_completion (XP ganho ao completar)`
  - `points_on_completion (pontos ganhos ao completar)`

- **Progresso / Matrículas:**
  - `status`: iniciada, em andamento, concluída, reprovada
  - `score_in_quest (pontuação específica na quest)`

---

## 🧪 Como Usar a Documentação Interativa

Abra [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), clique em "Try it out", preencha os campos e clique em "Execute".

---

### 📘 Criar Jogadores (Alunos):

**POST /alunos**

```json
{
  "nome": "Maria Silva",
  "apelido": "MestraM",
  "guilda": "Dragões da Gramática"
}
```
 - Atualizar Aluno: PUT /alunos/{aluno_id}
 - Deletar Aluno: DELETE /alunos/{aluno_id}
 - Adicionar Pontos Acadêmicos a um Aluno (por Quest): POST /alunos/{aluno_id}/add_quest_academic_points

```json
{
  "quest_code": "CODIGO_DA_QUEST"
}
```
 - Conceder Distintivos (Badges) Manualmente: POST /alunos/{aluno_id}/award_badge
```json
{
  "badge_name": "Mestre da Gramática"
}
```
 - Penalizar XP de uma Guilda: POST /guilds/{guild_name}/penalize_xp
```json
{
  "xp_deduction": 50
}
```

---

### 🧭 Definir Quests (Cursos):

**POST /cursos**

```json
{
  "nome": "Hangman: Verbos Irregulares",
  "codigo": "VERB-IRR-01",
  "descricao": "Desafio de vocabulário focado em verbos irregulares.",
  "xp_on_completion": 50,
  "points_on_completion": 0.5
}
```
 - Atualizar Quest: PUT /cursos/{codigo_curso}

---
## 🏁 Gerenciamento de Matrículas (Progresso nas Quests):Iniciar uma Quest (Matrícula): POST /matriculas

### 🏁 Início de uma Quest (Matrícula):

```json
{
  "aluno_id": 1,
  "curso_id": 1
}
```
### Concluir uma Quest (Matrícula): PUT /matriculas/{matricula_id}/complete

```json
{
  "score": 90
}
```
### Matricular Alunos em Massa por Guilda: POST /matriculas/bulk-by-guild


```json
{
  "curso_id": 1,
  "guild_name": "Dragões da Gramática"
}
``` 
---

## 📊 Visualizar Progresso e Rankings

- **Leaderboard Geral:** `GET /leaderboard`
- **Leaderboard por Guildas:** `GET /guilds/leaderboard`
- **Alunos por Guilda:** `GET /alunos/guilda/{nome_da_guilda}`
- **Perfil do Aluno:** `GET /alunos/{aluno_id}`
- **Listar Todos os Alunos:** `GET /alunos`
- **Buscar Aluno por Nome:** `GET /alunos/nome/{nome_aluno}`
- **Filtrar Alunos por Nível:** `GET /alunos/level/{level}`
- **Listar Todas as Quests (Cursos):** `GET /cursos`
- **Ver Detalhes de uma Quest por Código:** `GET /cursos/{codigo_curso}`
- **Ver Matrículas de um Aluno por Nome:** `GET /matriculas/aluno/{nome_aluno}`
- **Ver Detalhes das Matrículas de um Aluno por ID:** `GET /matriculas/aluno/{aluno_id}/details`
- **Ver Alunos Matriculados em um Curso por Código:** `GET /matriculas/curso/{codigo_curso}`

---

## 📁 Estrutura do Projeto Willow

```
📦 gamificacao-willow/
├── gamificacao_willow/
│   ├── app.py              # Ponto de entrada da aplicação FastAPI.
│   ├── models.py           # Definição dos modelos de dados (Alunos, Cursos, Matrículas).
│   ├── schemas.py          # Schemas Pydantic para validação e serialização de dados (entrada/saída da API).
│   ├── database.py         # Configuração da conexão com o banco de dados SQLite (escola.db) usando SQLAlchemy.
│   ├── requirements.txt    # Lista de dependências Python do projeto.
│   ├── readme.md           # Este arquivo README detalhado.
│   └── routers/
│       ├── alunos.py       # Endpoints para gerenciamento de alunos, XP, badges e leaderboards.
│       ├── cursos.py       # Endpoints para gerenciamento de quests (cursos).
│       └── matriculas.py   # Endpoints para gerenciamento do progresso dos alunos nas quests.
├── .gitignore              # Regras para ignorar arquivos no controle de versão Git.
└── README.md               # README principal do repositório (este arquivo).
```

> 🛑 **Atenção:** Sempre que modificar `models.py`, apague o `escola.db` e reinicie com `uvicorn` para aplicar a nova estrutura.

---

🎉 **Agora é só explorar e transformar suas aulas com gamificação!**


