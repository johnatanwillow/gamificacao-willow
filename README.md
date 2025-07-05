# Projeto de Gamificação para Aulas de Inglês - Prof. Johnatan Willow

Bem-vindo ao **Willow**, uma poderosa ferramenta baseada em FastAPI projetada para transformar suas aulas para jovens em uma experiência **gamificada**, **divertida** e **motivadora**!

O Willow funciona como a "espinha dorsal" seu sistema de recompensas, permitindo que você, como professor:

* **Gerencie Jogadores (Seus Alunos)**: Crie perfis detalhados para cada aluno, incluindo apelidos e guildas.
* **Defina Quests e Níveis de Aprendizagem**: Crie "desafios" ou "módulos" de conteúdo de inglês (ou conteúdos de outras disciplinas) com recompensas específicas.
* **Rastreie o Progresso e Pontuação**: Monitore o desempenho de cada aluno em tempo real, registrando pontos de experiência (XP), níveis e distintivos (badges).
* **Crie Leaderboards**: Exiba a classificação dos alunos (geral e por guilda!) para promover uma competição saudável e motivadora.

> Este README.md foi criado para professores e educadores (usuários leigos em programação) que desejam utilizar o Willow para enriquecer suas aulas.

---

### 🎯 Filosofia de Design e Cenário de Uso

O Willow foi **idealizado para ser uma solução local e para uso por um único professor**, focando em simplicidade e eficiência para esse cenário específico. Isso implica em algumas características importantes:

* **Uso Individual e Local:** O sistema é projetado para ser executado no computador do próprio professor. Não há expectativa de múltiplos usuários acessando e modificando dados simultaneamente, garantindo a performance ideal para um uso individual.
* **Banco de Dados SQLite:** A escolha do SQLite reflete a natureza local e mono-usuário do projeto. É um banco de dados baseado em arquivo, que oferece simplicidade no setup e boa performance para o uso individual, sem a necessidade da complexidade de um banco de dados cliente-servidor para gerenciar alta concorrência.
* **Sem Autenticação/Autorização:** Atualmente, o sistema não possui um mecanismo de login ou controle de permissões de usuário. Esta decisão foi tomada considerando que o uso é exclusivamente local e por um único professor, onde a segurança de acesso é gerenciada pelo ambiente do próprio usuário.
* **API-First (Sem Interface Gráfica Pronta):** A interação com o sistema é primariamente via API (Application Programming Interface). O acesso e a manipulação dos dados são feitos através dos endpoints da API, que podem ser explorados e testados pela documentação interativa (`/docs`). Isso permite flexibilidade para futuras integrações ou para uso por professores que se sintam confortáveis com a interação direta com a API.

---

## ✅ Pré-requisitos (O que você precisa ter instalado)

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
* Descompacte o ZIP em uma pasta fácil (ex: `C:\MeusProjetos\Willow`)

### 2. Abra o Terminal (Prompt de Comando ou PowerShell)

* **Windows**: "Prompt de Comando" ou "PowerShell"
* **Mac/Linux**: Terminal

### 3. Navegue até a Pasta do Projeto:

```bash
cd C:\meusProjetos\Willow
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

Abra [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), clique em "Try it out", preencha os campos e clique em "Execute". Esta é a sua principal ferramenta para interagir com o sistema Willow.

---

### 📘 Gerenciando Turmas, Guildas e Jogadores (Alunos):

Com esta atualização, o gerenciamento das turmas, guildas e alunos ficou ainda mais completo:

#### Criar uma Nova Turma:
**POST /turmas**
```json
{
  "nome": "5º Ano A",
  "ano": 2025
}
```
---
#### Atualizar uma Turma Existente:
**PUT /turmas/{turma_id}**
```json  
{
  "nome": "5º Ano B - Revisado",
  "ano": 2026
}
```
---
#### Adicionar um Aluno à Turma:
  **POST /turmas/{turma_id}/alunos**

```json
{
  "aluno_id": 1
}
```
---
#### Remover um Aluno de uma Turma:
**DELETE /turmas/{turma_id}/alunos/{aluno_id}**
**AVISO: A exclusão de uma turma resultará na exclusão automática de todas as guildas associadas e, consequentemente, de todos os alunos, matrículas e históricos de XP/pontos dessas guildas.**

---

#### Criar uma Nova Guilda:
**POST /guildas**

```json
{
  "nome": "Dragões da Gramática",
  "turma_id": 1
}   
```
---   
#### Atualizar uma Guilda Existente:
**PUT /guildas/{guilda_id}**

Permite renomear a guilda ou movê-la para uma turma diferente. Ao mover para uma nova turma, todos os alunos da guilda são implicitamente migrados.
```json
{
  "nome": "Feiticeiros do Vocabulário",
  "turma_id": 2
}
```
---

#### Deletar uma Guilda:
**DELETE /guildas/{guilda_id}**

**AVISO: A exclusão de uma guilda resultará na exclusão automática de todos os alunos associados a ela, bem como suas matrículas e históricos de XP/pontos.**

---

#### Criar Jogadores (Alunos):
**POST /alunos**

```json
{
  "nome": "Johnatan",
  "apelido": "  
  "guilda_id": 1
  "xp": 0,
  "total_points": 0,
  "academic_score": 0.0
}
```
---

#### Atualizar um Jogador (Aluno):
  **PUT /alunos/{aluno_id}**
    {
    "nome": "Johnatan",
    "apelido": "  
    "guilda_id": 1
    "xp": 0,
    "total_points": 0,
    "academic_score": 0.0
  }
---

#### Deletar um Jogador (Aluno):
**DELETE /alunos/{aluno_id}** 
**O professor fará uma requisição DELETE para o endpoint /alunos/{aluno_id} através da documentação interativa da API. Ao executar essa requisição, o sistema não apenas remove o registro do aluno da tabela de alunos, mas também, de forma automática e em cascata: Todas as matrículas (Matricula) desse aluno em qualquer atividade são excluídas. Todo o histórico de XP e pontos (HistoricoXPPonto) associado a esse aluno é também removido.**

---

#### Adicionar XP
  **POST /alunos/{aluno_id}/add_xp**

{
  "xp_amount": 10
}
  ---

#### Adicionar Pontos Acadêmicos a um Aluno (por Quest):
POST /alunos/{aluno_id}/add_quest_academic_points
**o valor da pontuação não é informado diretamente no corpo da requisição. Em vez disso, a lógica da aplicação busca o valor dos pontos acadêmicos na própria atividade (quest) referenciada pelo quest_code. Isso garante que a pontuação acadêmica esteja sempre ligada ao valor predefinido de cada atividade, mantendo a consistência.**
```json
{
  "quest_code": "VERB-IRR-01",
  "motivo": "Pontuação extra por demonstrar tardiamente habilidades linguísticas e vocabulares que condizem com o que se buscava com esta atividade"
}
```
---
#### Conceder Distintivos (Badges) Manualmente:
**POST /alunos/{aluno_id}/award_badge**
```json
{
   "badge_name": "Mestre da Gemas"  
    "motivo": "Pela fluencia acima da média dos demais alunos (um aluno estrangeiro ou que já morou em países anglófonos)"
}

BADGE_TIERS = {
    100: "Explorador Iniciante",
    200: "Explorador Bronze",
    300: "Desbravador Prata",
    400: "Garimpeiro Ouro",
    500: "Alma de Platina",
    600: "Arqueólogo de Jaspe",
    700: "Conquistador de Safira",
    800: "Conquistador de Esmeralda",
    900: "Conquistador de Diamante",
    1000: "Mestre das Gemas",
}
```
---
#### Penalizar XP de um Aluno Específico:
**POST /alunos/{aluno_id}/penalize_xp**
```json
{
  "xp_deduction": 20
  "motivo": "Atraso na entrega da atividade"
}   
```
---

#### Penalizar XP de uma Guilda:
POST /guilds/{guild_name}/penalize_xp
```json
{
  "xp_deduction": 50
  "motivo": "Comportamento inadequado da guilda e Fair Play"
}
```
---
#### 📈 Histórico de XP e Pontos
**Histórico de um Aluno: GET /alunos/historico_xp_pontos**

Retorna o histórico detalhado de todas as transações de XP e pontos de um aluno.
Use aluno_id ou nome_aluno como parâmetros de consulta para filtrar.

#### Histórico de uma Turma:
**Histórico de Turma: GET /turmas/{turma_id}/historico_xp_pontos**

Retorna o histórico detalhado de todas as transações de XP e pontos de todos os alunos de uma turma específica.

---
### Visualizar Progresso e Rankings
**Leaderboard Geral: GET /leaderboard**
**Leaderboard por Turma: GET /turmas/{turma_id}/leaderboard**
**Leaderboard por Guilda: GET /guilds/leaderboard**
**Alunos por Guilda: GET /alunos/guilda/{nome_da_guilda}**
---

### 🧭 Gerenciamento de Quests (Atividades)

#### Definir Nova Quest (Atividades): POST /atividades

```json
{
  "nome": "Hangman: Verbos Irregulares",
  "codigo": "VERB-IRR-01",
  "descricao": "Desafio de vocabulário focado em verbos irregulares.",
  "xp_on_completion": 50,
  "points_on_completion": 0.5
}
```
---

**Listar Todas as Quests (Atividades): GET /atividades**
**Ver Detalhes de uma Quest por Código: GET /atividades/{codigo_atividade}**
**Atualizar Quest: PUT /atividades/{codigo_atividade}**

---
### 🏁 Gerenciamento de Matrículas (Progresso nas Quests)

#### Matricular Alunos em Massa por Turma: 
**POST /matriculas/bulk-by-turma**
```json
{
  "curso_id": 1,
  "turma_id": 1
}
```
---
#### Matricular Alunos em Massa por Guilda: 
**POST /matriculas/bulk-by-guild**
```json
{
  "curso_id": 1,
  "guilda_id": 1
}
```

#### Iniciar uma Quest (Matrícula): POST /matriculas
```json
{
  "aluno_id": 0,
  "atividade_id": 0,
  "score_in_quest": 0,
  "status": "iniciado"
}
```
#### Complete uma Quest (Matrícula):
**PUT /matriculas/{matricula_id}/complete**
```json
{
  "aluno_id": 10,
  "atividade_id": 90,
  "score_in_quest": 0.5,
  "status": "concluido"
}
```
## Simulação de um Aluno Concluindo uma Atividade
**Vamos simular o processo para um aluno fictício.**

Cenário Inicial:
```json
{
  "Aluno: "Alice" (ID: 101)"
  "XP Atual: 180",
  "Nível Atual: 2 (pois 180 XP está entre 100 e 199 para o Nível 2)"
  "Pontos Totais: 200",
  "Pontos Acadêmicos: 2.0",
  "Distintivos: ["Explorador Iniciante"]"
}
```
```json
{
  "Atividade: "Verbos Irregulares - Parte 1" (ID: 201)"
  "Descrição: Desafio de vocabulário focado em verbos irregulares."
  "XP ao Concluir (xp_on_completion): 50"
  "Pontos ao Concluir (points_on_completion): 0.5"
}
```
```json

 - "Aluno Alice (ID 101) na Atividade (ID 201)",
{
  ""aluno_id": 101,
  "atividade_id": 90,
  "score_in_quest": 0.5,
  "status": "concluido""
}
```
**Ação do Professor (Chamada da API):**

O professor avalia que Alice completou a atividade "Verbos Irregulares - Parte 1" com uma pontuação de 95. Ele então faz uma requisição PUT para o endpoint complete_matricula:

**PUT /matriculas/3001/complete**

{
  "score": 50
}

**Processamento Automático pelo Sistema Willow:**
 - Busca da Matrícula, Aluno e Atividade: O sistema localiza a Matricula com ID 3001, o Aluno com ID 101 e a Atividade com ID 201 no banco de dados.
 
**Atualização da Matrícula:**

O status da Matrícula 3001 é alterado para "concluido".
O score_in_quest da Matrícula 3001 é definido como 50.

**Cálculo e Atualização dos Atributos do Aluno:**

 - XP: O XP da atividade (50) é adicionado ao XP de Alice.
 - Novo XP de Alice: 180(atual)+50(da atividade)= 230 XP.

**Nível: O nível de Alice é recalculado com base no novo XP.**

- 230//100+1=2+1=3. Novo Nível de Alice: 3.

- Pontos Totais: A pontuação (score) da atividade (50) é adicionada aos pontos totais de Alice.
 - Novos Pontos Totais de Alice: 200(atual)+50(daatividade)= 350pontos.

**Pontos Acadêmicos: Os pontos de conclusão da atividade (0.5) são adicionados aos pontos acadêmicos de Alice.**

 - Novos Pontos Acadêmicos de Alice: 2.0(atual)+ 0.5(daatividade)= 2.5 pontos na média.

**Verificação e Concessão de Distintivos de Nível:**
 - O sistema verifica o novo XP de Alice (230) contra os BADGE_TIERS.

 - Alice já tinha "Explorador Iniciante" (100 XP).
 - Com 230 XP, ela agora se qualifica para "Explorador Bronze" (200 XP).
 - Os distintivos de Alice são atualizados para: ["Explorador Iniciante", "Explorador Bronze"].

**Registro no Histórico (HistoricoXPPonto):**

 - São criados dois novos registros no histórico de Alice:
 - Um para o ganho de XP (tipo: "ganho_xp_atividade", valor_xp_alterado: 50, motivo: "Conclusão da Atividade 'Verbos Irregulares - Parte 1' com score 50").

 - Um para o ganho de Pontos Acadêmicos (tipo: "ganho_pontos_academicos_atividade", valor_pontos_alterado: 2.5, motivo: "Pontos Acadêmicos pela Atividade 'Verbos Irregulares - Parte 1'").

**Confirmação no Banco de Dados: Todas essas alterações são persistidas no banco de dados.**
- Estado Final (Após a Simulação):
Cenário Inicial:
```json
{
  "Aluno: "Alice" (ID: 101)"
  "Matrícula: 3001",
  "XP Atual: 230",
  "Nível Atual: 3 (pois 180 XP está entre 100 e 199 para o Nível 2)"
  "Pontos Totais: 350",
  "Pontos Acadêmicos: 2.5",
  "Distintivos: ["Explorador Iniciante", "Explorador Bronze"]",
  "Status: "concluido"
}
```
**A simulação demonstra como uma única ação manual (chamar o endpoint com a pontuação) desencadeia uma série de atualizações automáticas e complexas no perfil do aluno, garantindo que o sistema de gamificação esteja sempre atualizado.**


---
#### Ver Matrículas de um Aluno por Nome:
**GET /matriculas/aluno/{nome_aluno}**
 - Retorna Retorna uma lista de atividades nas quais um aluno (identificado pelo nome) está matriculado, incluindo informações sobre a guilda e turma do aluno.
#### Ver Detalhes das Matrículas de um Aluno por ID:
**GET /matriculas/aluno/{aluno_id}/details**
#### Ver Alunos Matriculados em uma Atividade por Código:
**GET /matriculas/atividade/{codigo_atividade}**
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
│       ├── atividades.py   # Endpoints para gerenciamento de quests (cursos).
│       └── matriculas.py   # Endpoints para gerenciamento do progresso dos alunos nas quests.
├── .gitignore              # Regras para ignorar arquivos no controle de versão Git.
└── README.md               # README principal do repositório (este arquivo).
```

> 🛑 **Atenção:** Sempre que modificar `models.py`, apague o `escola.db` e reinicie com `uvicorn` para aplicar a nova estrutura.

---

# 🎉 **Agora é só explorar e transformar suas aulas com gamificação!**



