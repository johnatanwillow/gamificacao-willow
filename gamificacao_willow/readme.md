
# Projeto de Gamificação para Aulas de Inglês - Prof. Johnatan Willow

Bem-vindo ao **Willow**, uma poderosa ferramenta baseada em FastAPI projetada para transformar suas aulas de inglês para jovens em uma experiência **gamificada**, **divertida** e **motivadora**!

O Willow funciona como a "espinha dorsal" do seu sistema de recompensas, permitindo que você:

- **Gerencie Jogadores (Seus Alunos)**: Crie perfis detalhados para cada aluno, incluindo apelidos e guildas.
- **Defina Quests e Níveis de Aprendizagem**: Crie "desafios" ou "módulos" de conteúdo de inglês com recompensas específicas.
- **Rastreie o Progresso e Pontuação**: Monitore o desempenho de cada aluno em tempo real, registrando pontos de experiência (XP), níveis e distintivos (badges).
- **Crie Leaderboards**: Exiba a classificação dos alunos (geral e por guilda!) para promover uma competição saudável e motivadora.

> Este README.md foi criado para professores e educadores (usuários leigos em programação) que desejam utilizar o Willow para enriquecer suas aulas.

---

## ✅ Pré-requisitos (O que você precisa ter instalado)

Para colocar o Willow para funcionar no seu computador, você precisará de:

- **Python 3.10 ou superior**  
  Baixe aqui: [https://www.python.org/downloads/](https://www.python.org/downloads/)

- **Git**  
  Baixe aqui: [https://git-scm.com/downloads](https://git-scm.com/downloads)

- **Docker (Opcional)**  
  Para usuários mais avançados. Não é necessário para começar.

---

## 🚀 Como Colocar o Willow Para Rodar (Passo a Passo para Usuários Leigos)

### 1. Baixe o Projeto Willow:

- Baixe o ZIP: [Download Willow](https://github.com/guilhermeonrails/imersao-devops/archive/refs/heads/main.zip)
- Descompacte o ZIP em uma pasta fácil (ex: `C:\MeusProjetos\Willow`)

### 2. Abra o Terminal (Prompt de Comando ou PowerShell)

- **Windows**: "Prompt de Comando" ou "PowerShell"
- **Mac/Linux**: Terminal

### 3. Navegue até a Pasta do Projeto:

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
venv\Scriptsctivate
```

> Você saberá que deu certo quando aparecer `(venv)` no início da linha do terminal.

### 6. Instale as Dependências:

```bash
pip install -r requirements.txt
```

### 7. Inicie o Willow (API de Gamificação):

> **Importante:** Se alterou os modelos (adicionou campos), apague o arquivo `escola.db` antes.

```bash
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

- **Quests / Cursos:**
  - `nome`
  - `codigo`
  - `descricao`
  - `xp_on_completion`
  - `points_on_completion`

- **Progresso / Matrículas:**
  - `status`: iniciada, em andamento, concluída, reprovada
  - `score_in_quest`

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

---

### 🧭 Definir Quests (Cursos):

**POST /cursos**

```json
{
  "nome": "Hangman: Verbos Irregulares",
  "codigo": "VERB-IRR-01",
  "descricao": "Desafio de vocabulário focado em verbos irregulares.",
  "xp_on_completion": 40,
  "points_on_completion": 150
}
```

---

### 🏁 Início de uma Quest (Matrícula):

**POST /matriculas**

```json
{
  "aluno_id": 1,
  "curso_id": 1
}
```

---

### ⚔️ Ganhando XP e Pontos:

#### Adicionar XP:

**POST /alunos/{aluno_id}/add_xp**

```json
{
  "xp_amount": 10
}
```

#### Concluir uma Quest:

**PUT /matriculas/{matricula_id}/complete**

```json
{
  "score": 90
}
```

---

### 🏅 Conceder Distintivos (Badges):

**POST /alunos/{aluno_id}/award_badge**

```json
{
  "badge_name": "Mestre da Gramática"
}
```

---

## 📊 Visualizar Progresso e Rankings

- **Leaderboard Geral:** `GET /leaderboard`
- **Leaderboard por Guildas:** `GET /guilds/leaderboard`
- **Alunos por Guilda:** `GET /alunos/guilda/{nome_da_guilda}`
- **Perfil do Aluno:** `GET /alunos/{aluno_id}`

---

## 📁 Estrutura do Projeto Willow

```
📦 Willow
├── app.py              # Inicia a API com FastAPI
├── models.py           # Modelos de dados (Alunos, Cursos, etc.)
├── schemas.py          # Estrutura dos dados (entrada/saída da API)
├── database.py         # Conexão com SQLite usando SQLAlchemy 2.0
├── requirements.txt    # Lista de dependências Python
└── routers/
    ├── alunos.py       # Endpoints: alunos, XP, badges, leaderboard
    ├── cursos.py       # Endpoints: quests (cursos)
    └── matriculas.py   # Endpoints: progresso nas quests
```

> 🛑 **Atenção:** Sempre que modificar `models.py`, apague o `escola.db` e reinicie com `uvicorn` para aplicar a nova estrutura.

---

🎉 **Agora é só explorar e transformar suas aulas com gamificação!**
