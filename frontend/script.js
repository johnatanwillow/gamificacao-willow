const API_BASE_URL = 'http://127.0.0.1:8000'; // Endereço do seu backend FastAPI

// --- Funções Auxiliares de Comunicação com a API ---

/**
 * Função genérica para fazer requisições à API.
 * Lida com serialização/desserialização JSON e tratamento de erros.
 * Converte PascalCase no JS para snake_case no JSON para o FastAPI.
 * @param {string} endpoint - O endpoint da API (ex: 'alunos', 'turmas/1').
 * @param {string} method - O método HTTP (ex: 'GET', 'POST', 'PUT', 'DELETE').
 * @param {object} [data=null] - Os dados a serem enviados no corpo da requisição (para POST/PUT).
 * @returns {Promise<{success: boolean, data: object|array|string, error: string|object|null}>} Resultado da requisição.
 */
async function apiRequest(endpoint, method, data = null) {
    const url = `${API_BASE_URL}/${endpoint}`;
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    };

    if (data) {
        // Converte as chaves do objeto de PascalCase (usado no JS) para snake_case (esperado pelo FastAPI)
        const preparedData = {};
        for (const k in data) {
            if (Object.prototype.hasOwnProperty.call(data, k)) {
                const snakeCaseKey = k.replace(/([A-Z])/g, '_$1').toLowerCase();
                preparedData[snakeCaseKey] = data[k];
            }
        }
        options.body = JSON.stringify(preparedData);
    }

    try {
        const response = await fetch(url, options);
        let responseData = null;

        // Se a resposta for um PDF, não tente parsear como JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            responseData = await response.json();
        } else if (contentType && contentType.includes('application/pdf')) {
            // Se for PDF, retorne o blob diretamente para download
            return { success: true, data: await response.blob(), error: null, isPdf: true };
        } else {
            responseData = await response.text(); // Para respostas não-JSON (ex: 204 No Content)
        }

        if (response.ok) {
            return { success: true, data: responseData, error: null };
        } else {
            const errorMessage = typeof responseData === 'object' && responseData.detail
                               ? responseData.detail
                               : response.statusText || responseData.toString();
            console.error(`API Error (${response.status} ${response.statusText}):`, errorMessage, responseData);
            return { success: false, data: null, error: errorMessage };
        }
    } catch (error) {
        console.error("Erro na requisição da API (rede/conexão):", error);
        return { success: false, data: null, error: "Ocorreu um erro de rede ou conexão. " + error.message };
    }
}


// --- Funções de Lógica da Aba Turmas ---

/**
 * Carrega e exibe a lista de turmas na tabela.
 */
async function loadTurmas() {
    const tbody = document.querySelector('#turmas-tab #dgTurmas tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="3">Carregando turmas...</td></tr>';

    const result = await apiRequest('turmas', 'GET');

    if (result.success) {
        tbody.innerHTML = '';
        if (result.data && result.data.length > 0) {
            result.data.forEach(turma => {
                const row = tbody.insertRow();
                row.insertCell().textContent = turma.id;
                row.insertCell().textContent = turma.nome;
                row.insertCell().textContent = turma.ano || 'N/A';
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="3">Nenhuma turma cadastrada.</td></tr>';
        }
    } else {
        alert('Erro ao carregar turmas: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="3">Erro: ${result.error}</td></tr>`;
    }
}

/**
 * Cria uma nova turma com base nos dados do formulário.
 */
async function createTurma() {
    const nome = document.getElementById('txtNomeTurma').value;
    const ano = document.getElementById('txtAnoTurma').value;

    if (!nome) {
        alert('O nome da turma é obrigatório!');
        return;
    }

    const turmaData = { nome: nome, ano: ano || null };
    const result = await apiRequest('turmas', 'POST', turmaData);

    if (result.success) {
        alert(`Turma "${result.data.nome}" criada com sucesso! ID: ${result.data.id}`);
        document.getElementById('txtNomeTurma').value = '';
        document.getElementById('txtAnoTurma').value = '';
        loadTurmas();
    } else {
        alert('Erro ao criar turma: ' + result.error);
    }
}

/**
 * Atualiza uma turma existente.
 */
async function updateTurma() {
    const turmaId = document.getElementById('txtIdTurmaAcao').value;
    if (!turmaId) { alert('ID da Turma é obrigatório para atualização.'); return; }
    const parsedTurmaId = parseInt(turmaId);
    if (isNaN(parsedTurmaId)) { alert('ID da Turma inválido.'); return; }

    const nome = document.getElementById('txtNomeTurma').value;
    const ano = document.getElementById('txtAnoTurma').value;

    const updateData = {};
    if (nome) updateData.nome = nome;
    if (ano) updateData.ano = ano;

    if (Object.keys(updateData).length === 0) {
        alert('Nenhum campo preenchido para atualização da turma.');
        return;
    }

    const result = await apiRequest(`turmas/${parsedTurmaId}`, 'PUT', updateData);
    if (result.success) {
        alert(`Turma ID ${parsedTurmaId} atualizada com sucesso!`);
        document.getElementById('txtIdTurmaAcao').value = '';
        document.getElementById('txtNomeTurma').value = '';
        document.getElementById('txtAnoTurma').value = '';
        loadTurmas();
    } else {
        alert('Erro ao atualizar turma: ' + result.error);
    }
}

/**
 * Deleta uma turma existente.
 */
async function deleteTurma() {
    const turmaId = document.getElementById('txtIdTurmaAcao').value;
    if (!turmaId) { alert('ID da Turma é obrigatório para deletar.'); return; }
    const parsedTurmaId = parseInt(turmaId);
    if (isNaN(parsedTurmaId)) { alert('ID da Turma inválido.'); return; }

    if (!confirm(`Tem certeza que deseja deletar a turma com ID ${parsedTurmaId}? Esta ação é irreversível e deletará GUILDAS E ALUNOS associados!`)) {
        return;
    }

    const result = await apiRequest(`turmas/${parsedTurmaId}`, 'DELETE');
    if (result.success) {
        alert(`Turma ID ${parsedTurmaId} deletada com sucesso!`);
        document.getElementById('txtIdTurmaAcao').value = '';
        loadTurmas();
    } else {
        alert('Erro ao deletar turma: ' + result.error);
    }
}


// --- Funções de Lógica da Aba Guildas ---

/**
 * Carrega e exibe a lista de guildas na tabela.
 */
async function loadGuildas() {
    const tbody = document.querySelector('#guildas-tab #dgGuildas tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="5">Carregando guildas...</td></tr>';

    const result = await apiRequest('guildas', 'GET');

    if (result.success) {
        tbody.innerHTML = '';
        if (result.data && result.data.length > 0) {
            result.data.forEach(guilda => {
                const row = tbody.insertRow();
                row.insertCell().textContent = guilda.id;
                row.insertCell().textContent = guilda.nome;
                row.insertCell().textContent = guilda.turma_id || 'N/A';
                row.insertCell().textContent = guilda.turma ? guilda.turma.nome : 'N/A';
                row.insertCell().textContent = guilda.turma ? guilda.turma.ano : 'N/A';
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="5">Nenhuma guilda cadastrada.</td></tr>';
        }
    } else {
        alert('Erro ao carregar guildas: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="5">Erro: ${result.error}</td></tr>`;
    }
}

/**
 * Cria uma nova guilda com base nos dados do formulário.
 */
async function createGuilda() {
    const nome = document.getElementById('txtNomeGuilda').value;
    const turmaId = document.getElementById('txtTurmaIdGuilda').value;

    if (!nome || !turmaId) {
        alert('Nome da Guilda e ID da Turma são obrigatórios!');
        return;
    }

    const parsedTurmaId = parseInt(turmaId);
    if (isNaN(parsedTurmaId)) { alert('ID da Turma inválido.'); return; }

    const guildaData = { nome: nome, turmaId: parsedTurmaId };
    const result = await apiRequest('guildas', 'POST', guildaData);

    if (result.success) {
        alert(`Guilda "${result.data.nome}" criada com sucesso! ID: ${result.data.id}`);
        document.getElementById('txtNomeGuilda').value = '';
        document.getElementById('txtTurmaIdGuilda').value = '';
        loadGuildas();
    } else {
        alert('Erro ao criar guilda: ' + result.error);
    }
}

/**
 * Atualiza uma guilda existente.
 */
async function updateGuilda() {
    const guildaId = document.getElementById('txtIdGuildaAcao').value;
    if (!guildaId) { alert('ID da Guilda é obrigatório para atualização.'); return; }
    const parsedGuildaId = parseInt(guildaId);
    if (isNaN(parsedGuildaId)) { alert('ID da Guilda inválido.'); return; }

    const nome = document.getElementById('txtNomeGuilda').value;
    const turmaId = document.getElementById('txtTurmaIdGuilda').value;

    const updateData = {};
    if (nome) updateData.nome = nome;
    if (turmaId) {
        const parsedTurmaId = parseInt(turmaId);
        if (isNaN(parsedTurmaId)) { alert('ID da Turma inválido.'); return; }
        updateData.turmaId = parsedTurmaId;
    }

    if (Object.keys(updateData).length === 0) {
        alert('Nenhum campo preenchido para atualização da guilda.');
        return;
    }

    const result = await apiRequest(`guildas/${parsedGuildaId}`, 'PUT', updateData);
    if (result.success) {
        alert(`Guilda ID ${parsedGuildaId} atualizada com sucesso!`);
        document.getElementById('txtIdGuildaAcao').value = '';
        document.getElementById('txtNomeGuilda').value = '';
        document.getElementById('txtTurmaIdGuilda').value = '';
        loadGuildas();
    } else {
        alert('Erro ao atualizar guilda: ' + result.error);
    }
}

/**
 * Deleta uma guilda existente.
 */
async function deleteGuilda() {
    const guildaId = document.getElementById('txtIdGuildaAcao').value;
    if (!guildaId) { alert('ID da Guilda é obrigatório para deletar.'); return; }
    const parsedGuildaId = parseInt(guildaId);
    if (isNaN(parsedGuildaId)) { alert('ID da Guilda inválido.'); return; }

    if (!confirm(`Tem certeza que deseja deletar a guilda com ID ${parsedGuildaId}? Esta ação é irreversível e deletará ALUNOS associados!`)) {
        return;
    }

    const result = await apiRequest(`guildas/${parsedGuildaId}`, 'DELETE');
    if (result.success) {
        alert(`Guilda ID ${parsedGuildaId} deletada com sucesso!`);
        document.getElementById('txtIdGuildaAcao').value = '';
        loadGuildas();
    } else {
        alert('Erro ao deletar guilda: ' + result.error);
    }
}

/**
 * Penaliza XP de uma guilda específica.
 */
async function penalizeGuildXp() {
    const nomeGuilda = document.getElementById('txtNomeGuildaPenalizar').value;
    const xpDeduction = parseInt(document.getElementById('txtXpDeductionGuilda').value);
    const motivo = document.getElementById('txtMotivoPenalidadeGuilda').value;

    if (!nomeGuilda || isNaN(xpDeduction) || xpDeduction <= 0) {
        alert('Nome da Guilda e XP para deduzir (positivo) são obrigatórios.');
        return;
    }

    const penalizeData = { xpDeduction: xpDeduction, motivo: motivo || null };
    const result = await apiRequest(`guilds/${encodeURIComponent(nomeGuilda)}/penalize_xp`, 'POST', penalizeData);

    if (result.success) {
        alert(`Penalizado ${xpDeduction} XP da guilda "${nomeGuilda}".`);
        document.getElementById('txtNomeGuildaPenalizar').value = '';
        document.getElementById('txtXpDeductionGuilda').value = '';
        document.getElementById('txtMotivoPenalidadeGuilda').value = '';
        loadGuildas(); // Recarrega a lista para mostrar impacto (se tiver um aluno atualizado)
        loadAlunos(); // Atualiza a aba de alunos, pois o XP dos alunos é afetado
    } else {
        alert('Erro ao penalizar XP da guilda: ' + result.error);
    }
}


// --- Funções de Lógica da Aba Alunos ---

/**
 * Carrega e exibe a lista de alunos na tabela.
 */
async function loadAlunos() {
    const tbody = document.querySelector('#alunos-tab #dgAlunos tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="11">Carregando alunos...</td></tr>';

    const result = await apiRequest('alunos', 'GET');

    if (result.success) {
        tbody.innerHTML = '';
        if (result.data && result.data.length > 0) {
            result.data.forEach(aluno => {
                const row = tbody.insertRow();
                row.insertCell().textContent = aluno.id;
                row.insertCell().textContent = aluno.nome;
                row.insertCell().textContent = aluno.apelido;
                row.insertCell().textContent = aluno.guilda_id || 'N/A';
                row.insertCell().textContent = aluno.guilda_nome || 'N/A'; // Alterado para guilda_nome
                row.insertCell().textContent = aluno.xp;
                row.insertCell().textContent = aluno.level;
                row.insertCell().textContent = aluno.total_points;
                row.insertCell().textContent = aluno.academic_score;
                row.insertCell().textContent = aluno.badges ? aluno.badges.join(', ') : '';
                row.insertCell().textContent = aluno.turma_nome || 'N/A'; // Alterado para turma_nome
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="11">Nenhum aluno cadastrado.</td></tr>';
        }
    } else {
        alert('Erro ao carregar alunos: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="11">Erro: ${result.error}</td></tr>`;
    }
}

/**
 * Cria um novo aluno com base nos dados do formulário.
 */
async function createAluno() {
    const nome = document.getElementById('txtNomeAluno').value;
    const apelido = document.getElementById('txtApelidoAluno').value;
    const nomeGuilda = document.getElementById('txtNomeGuildaAluno').value; // Usando o nome da guilda
    const xp = parseInt(document.getElementById('txtXpAluno').value);
    const totalPoints = parseInt(document.getElementById('txtTotalPointsAluno').value);
    const academicScore = parseFloat(document.getElementById('txtAcademicScoreAluno').value);
    const badgesText = document.getElementById('txtBadgesAluno').value;

    if (!nome) {
        alert('O campo Nome do Aluno é obrigatório!');
        return;
    }

    const badges = badgesText ? badgesText.split(',').map(b => b.trim()) : [];

    const alunoData = {
        nome: nome,
        apelido: apelido || null,
        nomeGuilda: nomeGuilda || null, // Corrigido para nomeGuilda para o backend
        xp: isNaN(xp) ? 0 : xp,
        // Level será definido pelo backend, não enviado aqui
        totalPoints: isNaN(totalPoints) ? 0 : totalPoints,
        badges: badges,
        academicScore: isNaN(academicScore) ? 0.0 : academicScore
    };

    const result = await apiRequest('alunos', 'POST', alunoData);

    if (result.success) {
        alert(`Aluno "${result.data.nome}" criado com sucesso! ID: ${result.data.id}`);
        // Limpar campos
        document.getElementById('txtNomeAluno').value = '';
        document.getElementById('txtApelidoAluno').value = '';
        document.getElementById('txtNomeGuildaAluno').value = '';
        document.getElementById('txtXpAluno').value = '0';
        document.getElementById('txtTotalPointsAluno').value = '0';
        document.getElementById('txtAcademicScoreAluno').value = '0.0';
        document.getElementById('txtBadgesAluno').value = '';

        loadAlunos(); // Recarrega a lista de alunos para mostrar o novo
    } else {
        alert('Erro ao criar aluno: ' + result.error);
    }
}

// --- Funções para Ações Específicas de Aluno (Aba Alunos) ---
async function updateAluno() {
    const alunoId = document.getElementById('txtAlunoIdAcao').value;
    if (!alunoId) { alert('ID do Aluno é obrigatório para esta ação.'); return; }
    const parsedAlunoId = parseInt(alunoId);
    if (isNaN(parsedAlunoId)) { alert('ID do Aluno inválido.'); return; }

    const nome = document.getElementById('txtNomeAluno').value;
    const apelido = document.getElementById('txtApelidoAluno').value;
    const nomeGuilda = document.getElementById('txtNomeGuildaAluno').value;
    const xp = parseInt(document.getElementById('txtXpAluno').value);
    const totalPoints = parseInt(document.getElementById('txtTotalPointsAluno').value);
    const academicScore = parseFloat(document.getElementById('txtAcademicScoreAluno').value);
    const badgesText = document.getElementById('txtBadgesAluno').value;
    const motivo = document.getElementById('txtMotivoAcao').value;

    const updateData = {};
    if (nome) updateData.nome = nome;
    if (apelido) updateData.apelido = apelido;
    if (nomeGuilda) {
        // Para atualizar a guilda por nome, precisamos primeiro obter o ID
        const resultGuildId = await apiRequest(`guildas?nome=${nomeGuilda}`, 'GET'); // Endpoint para buscar guilda por nome
        if (resultGuildId.success && resultGuildId.data.length > 0) {
            updateData.guildaId = resultGuildId.data[0].id; // Pega o ID da primeira guilda encontrada
        } else {
            alert(`Guilda "${nomeGuilda}" não encontrada para atualização.`);
            return;
        }
    }
    if (!isNaN(xp)) updateData.xp = xp;
    if (!isNaN(totalPoints)) updateData.totalPoints = totalPoints;
    if (!isNaN(academicScore)) updateData.academicScore = academicScore;
    if (badgesText) updateData.badges = badgesText.split(',').map(b => b.trim());
    if (motivo) updateData.motivo = motivo;

    // Se nenhum campo foi preenchido para atualização, avisa o usuário
    if (Object.keys(updateData).length === 0) {
        alert('Nenhum campo preenchido para atualização do aluno.');
        return;
    }

    const result = await apiRequest(`alunos/${parsedAlunoId}`, 'PUT', updateData);
    if (result.success) {
        alert(`Aluno ID ${parsedAlunoId} atualizado com sucesso!`);
        loadAlunos();
    } else {
        alert('Erro ao atualizar aluno: ' + result.error);
    }
}

async function deleteAluno() {
    const alunoId = document.getElementById('txtAlunoIdAcao').value;
    if (!alunoId) { alert('ID do Aluno é obrigatório para esta ação.'); return; }
    const parsedAlunoId = parseInt(alunoId);
    if (isNaN(parsedAlunoId)) { alert('ID do Aluno inválido.'); return; }

    if (!confirm(`Tem certeza que deseja deletar o aluno com ID ${parsedAlunoId}? Esta ação é irreversível!`)) {
        return;
    }

    const result = await apiRequest(`alunos/${parsedAlunoId}`, 'DELETE');
    if (result.success) {
        alert(`Aluno ID ${parsedAlunoId} deletado com sucesso!`);
        loadAlunos();
    } else {
        alert('Erro ao deletar aluno: ' + result.error);
    }
}

async function addXp() {
    const alunoId = document.getElementById('txtAlunoIdAcao').value;
    const xpAmount = parseInt(document.getElementById('txtXpAmount').value);

    if (!alunoId || isNaN(xpAmount) || xpAmount <= 0) {
        alert('ID do Aluno e quantidade de XP (positiva) são obrigatórios.');
        return;
    }
    const parsedAlunoId = parseInt(alunoId);
    if (isNaN(parsedAlunoId)) { alert('ID do Aluno inválido.'); return; }

    const result = await apiRequest(`alunos/${parsedAlunoId}/add_xp`, 'POST', { xpAmount: xpAmount });
    if (result.success) {
        alert(`Adicionado ${xpAmount} XP ao aluno ID ${parsedAlunoId}. Novo XP: ${result.data.xp}`);
        loadAlunos();
    } else {
        alert('Erro ao adicionar XP: ' + result.error);
    }
}

async function penalizeXpAluno() {
    const alunoId = document.getElementById('txtAlunoIdAcao').value;
    const xpDeduction = parseInt(document.getElementById('txtXpAmount').value);
    const motivo = document.getElementById('txtMotivoAcao').value;

    if (!alunoId || isNaN(xpDeduction) || xpDeduction <= 0) {
        alert('ID do Aluno e XP para deduzir (positivo) são obrigatórios.');
        return;
    }
    const parsedAlunoId = parseInt(alunoId);
    if (isNaN(parsedAlunoId)) { alert('ID do Aluno inválido.'); return; }

    const penalizeData = { xpDeduction: xpDeduction, motivo: motivo || null };
    const result = await apiRequest(`alunos/${parsedAlunoId}/penalize_xp`, 'POST', penalizeData);
    if (result.success) {
        alert(`Penalizado ${xpDeduction} XP do aluno ID ${parsedAlunoId}. Novo XP: ${result.data.xp}`);
        loadAlunos();
    } else {
        alert('Erro ao penalizar XP do aluno: ' + result.error);
    }
}

async function concederBadge() {
    const alunoId = document.getElementById('txtAlunoIdAcao').value;
    const badgeName = document.getElementById('txtBadgeName').value;
    const motivo = document.getElementById('txtMotivoAcao').value;

    if (!alunoId || !badgeName) {
        alert('ID do Aluno e Nome do Badge são obrigatórios.');
        return;
    }
    const parsedAlunoId = parseInt(alunoId);
    if (isNaN(parsedAlunoId)) { alert('ID do Aluno inválido.'); return; }

    const badgeData = { badgeName: badgeName, motivo: motivo || null };
    const result = await apiRequest(`alunos/${parsedAlunoId}/award_badge`, 'POST', badgeData);
    if (result.success) {
        alert(`Badge "${badgeName}" concedido ao aluno ID ${parsedAlunoId}.`);
        loadAlunos();
    } else {
        alert('Erro ao conceder badge: ' + result.error);
    }
}

async function addPontosAcademicos() {
    const alunoId = document.getElementById('txtAlunoIdAcao').value;
    const questCode = document.getElementById('txtQuestCodePontos').value;
    const motivo = document.getElementById('txtMotivoAcao').value;

    if (!alunoId || !questCode) {
        alert('ID do Aluno e Código da Quest são obrigatórios.');
        return;
    }
    const parsedAlunoId = parseInt(alunoId);
    if (isNaN(parsedAlunoId)) { alert('ID do Aluno inválido.'); return; }

    const pointsData = { questCode: questCode, motivo: motivo || null };
    const result = await apiRequest(`alunos/${parsedAlunoId}/add_quest_academic_points`, 'POST', pointsData);
    if (result.success) {
        alert(`Pontos acadêmicos adicionados ao aluno ID ${parsedAlunoId}. Nova pontuação: ${result.data.academic_score}`);
        loadAlunos();
    } else {
        alert('Erro ao adicionar pontos acadêmicos: ' + result.error);
    }
}


// --- Funções de Lógica da Aba Atividades ---

async function loadAtividades() {
    const tbody = document.querySelector('#atividades-tab #dgAtividades tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6">Carregando atividades...</td></tr>';

    const result = await apiRequest('atividades', 'GET');

    if (result.success) {
        tbody.innerHTML = '';
        if (result.data && result.data.length > 0) {
            result.data.forEach(atividade => {
                const row = tbody.insertRow();
                row.insertCell().textContent = atividade.id;
                row.insertCell().textContent = atividade.nome;
                row.insertCell().textContent = atividade.codigo;
                row.insertCell().textContent = atividade.descricao || '';
                row.insertCell().textContent = atividade.xp_on_completion;
                row.insertCell().textContent = atividade.points_on_completion;
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="6">Nenhuma atividade cadastrada.</td></tr>';
        }
    } else {
        alert('Erro ao carregar atividades: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="6">Erro: ${result.error}</td></tr>`;
    }
}

async function createAtividade() {
    const nome = document.getElementById('txtNomeAtividade').value;
    const codigo = document.getElementById('txtCodigoAtividade').value;
    const descricao = document.getElementById('txtDescricaoAtividade').value;
    const xpOnCompletion = parseInt(document.getElementById('txtXpOnCompletion').value);
    const pointsOnCompletion = parseFloat(document.getElementById('txtPointsOnCompletion').value);

    if (!nome || !codigo || !descricao) {
        alert('Nome, Código e Descrição da Atividade são obrigatórios!');
        return;
    }

    const atividadeData = {
        nome: nome,
        codigo: codigo,
        descricao: descricao,
        xpOnCompletion: isNaN(xpOnCompletion) ? 0 : xpOnCompletion,
        pointsOnCompletion: isNaN(pointsOnCompletion) ? 0.0 : pointsOnCompletion
    };

    const result = await apiRequest('atividades', 'POST', atividadeData);

    if (result.success) {
        alert(`Atividade "${result.data.nome}" criada com sucesso! Código: ${result.data.codigo}`);
        document.getElementById('txtNomeAtividade').value = '';
        document.getElementById('txtCodigoAtividade').value = '';
        document.getElementById('txtDescricaoAtividade').value = '';
        document.getElementById('txtXpOnCompletion').value = '0';
        document.getElementById('txtPointsOnCompletion').value = '0.0';
        loadAtividades();
    } else {
        alert('Erro ao criar atividade: ' + result.error);
    }
}

async function updateAtividade() {
    const codigoAtividadeAcao = document.getElementById('txtCodigoAtividadeAcao').value;
    if (!codigoAtividadeAcao) { alert('Código da Atividade é obrigatório para atualização!'); return; }

    const nome = document.getElementById('txtNomeAtividade').value;
    const descricao = document.getElementById('txtDescricaoAtividade').value;
    const xpOnCompletion = parseInt(document.getElementById('txtXpOnCompletion').value);
    const pointsOnCompletion = parseFloat(document.getElementById('txtPointsOnCompletion').value);

    const updateData = {};
    if (nome) updateData.nome = nome;
    if (descricao) updateData.descricao = descricao;
    if (!isNaN(xpOnCompletion)) updateData.xpOnCompletion = xpOnCompletion;
    if (!isNaN(pointsOnCompletion)) updateData.pointsOnCompletion = pointsOnCompletion;

    if (Object.keys(updateData).length === 0) {
        alert('Nenhum campo preenchido para atualização da atividade.');
        return;
    }

    const result = await apiRequest(`atividades/${codigoAtividadeAcao}`, 'PUT', updateData);

    if (result.success) {
        alert(`Atividade Código ${codigoAtividadeAcao} atualizada com sucesso!`);
        document.getElementById('txtNomeAtividade').value = '';
        document.getElementById('txtCodigoAtividade').value = '';
        document.getElementById('txtDescricaoAtividade').value = '';
        document.getElementById('txtXpOnCompletion').value = '0';
        document.getElementById('txtPointsOnCompletion').value = '0.0';
        document.getElementById('txtCodigoAtividadeAcao').value = '';
        loadAtividades();
    } else {
        alert('Erro ao atualizar atividade: ' + result.error);
    }
}

async function buscarAtividadePorCodigo() {
    const codigoAtividadeAcao = document.getElementById('txtCodigoAtividadeAcao').value;
    if (!codigoAtividadeAcao) { alert('Código da Atividade é obrigatório para busca!'); return; }

    const result = await apiRequest(`atividades/${codigoAtividadeAcao}`, 'GET');

    const tbody = document.querySelector('#atividades-tab #dgAtividades tbody');
    if (!tbody) return;

    if (result.success && result.data) {
        tbody.innerHTML = '';
        const atividade = result.data;
        const row = tbody.insertRow();
        row.insertCell().textContent = atividade.id;
        row.insertCell().textContent = atividade.nome;
        row.insertCell().textContent = atividade.codigo;
        row.insertCell().textContent = atividade.descricao || '';
        row.insertCell().textContent = atividade.xp_on_completion;
        row.insertCell().textContent = atividade.points_on_completion;
        alert(`Atividade "${atividade.nome}" encontrada!`);
    } else {
        alert('Erro ao buscar atividade: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="6">Erro: ${result.error}</td></tr>`;
    }
}

// --- Funções de Lógica da Aba Matrículas/Progresso ---

/**
 * Função auxiliar para exibir uma lista de objetos de matrícula na tabela dgMatriculas.
 * @param {Array<Object>} matriculasArray - Um array de objetos de matrícula.
 */
function displayMatriculasInTable(matriculasArray) {
    const tbody = document.querySelector('#matriculas-tab #dgMatriculas tbody');
    if (!tbody) return;
    tbody.innerHTML = ''; // Limpa o conteúdo existente

    if (matriculasArray && matriculasArray.length > 0) {
        matriculasArray.forEach(matricula => {
            const row = tbody.insertRow();
            row.insertCell().textContent = matricula.id;
            row.insertCell().textContent = matricula.aluno_id;
            row.insertCell().textContent = matricula.atividade_id;
            row.insertCell().textContent = matricula.score_in_quest;
            row.insertCell().textContent = matricula.status;
            // Estes campos não vêm diretamente na resposta de POST/PUT, mas vêm em GET de detalhes.
            // Para consistência com a estrutura da tabela, adicionamos N/A se não existirem.
            row.insertCell().textContent = matricula.aluno_nome || 'N/A';
            row.insertCell().textContent = matricula.atividade_nome || 'N/A';
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="7">Nenhuma matrícula para exibir.</td></tr>';
    }
}

async function createMatricula() {
    const alunoId = document.getElementById('txtAlunoIdMatricula').value;
    const atividadeId = document.getElementById('txtAtividadeIdMatricula').value;

    if (!alunoId || !atividadeId) {
        alert('ID do Aluno e ID da Atividade são obrigatórios para matrícula individual!');
        return;
    }
    const parsedAlunoId = parseInt(alunoId);
    const parsedAtividadeId = parseInt(atividadeId);
    if (isNaN(parsedAlunoId) || isNaN(parsedAtividadeId)) {
        alert('IDs de Aluno ou Atividade inválidos!');
        return;
    }

    const matriculaData = {
        alunoId: parsedAlunoId,
        atividadeId: parsedAtividadeId,
        scoreInQuest: 0,
        status: "iniciado"
    };

    const result = await apiRequest('matriculas', 'POST', matriculaData);
    if (result.success) {
        alert(`Matrícula criada com sucesso! ID: ${result.data.id}`);
        document.getElementById('txtAlunoIdMatricula').value = '';
        document.getElementById('txtAtividadeIdMatricula').value = '';
        // Após criar uma matrícula individual, podemos exibir ela na tabela
        displayMatriculasInTable([result.data]);
    } else {
        alert('Erro ao criar matrícula: ' + result.error);
    }
}

async function bulkMatriculaTurma() {
    const cursoId = document.getElementById('txtCursoIdBulk').value;
    const turmaId = document.getElementById('txtTurmaIdBulk').value;

    if (!cursoId || !turmaId) {
        alert('ID do Curso e ID da Turma são obrigatórios para matrícula em massa por turma!');
        return;
    }
    const parsedCursoId = parseInt(cursoId);
    const parsedTurmaId = parseInt(turmaId);
    if (isNaN(parsedCursoId) || isNaN(parsedTurmaId)) {
        alert('IDs de Curso ou Turma inválidos!');
        return;
    }

    const bulkData = {
        cursoId: parsedCursoId,
        turmaId: parsedTurmaId
    };

    const result = await apiRequest('matriculas/bulk-by-turma', 'POST', bulkData);
    if (result.success) {
        alert(`${result.data.length} matrículas criadas/atualizadas para a turma com sucesso!`);
        document.getElementById('txtCursoIdBulk').value = '';
        document.getElementById('txtTurmaIdBulk').value = '';
        displayMatriculasInTable(result.data); // Exibe os dados na tabela
    } else {
        alert('Erro ao matricular por turma: ' + result.error);
    }
}

async function bulkMatriculaGuilda() {
    const cursoId = document.getElementById('txtCursoIdBulk').value;
    const guildaId = document.getElementById('txtGuildaIdBulk').value;

    if (!cursoId || !guildaId) {
        alert('ID do Curso e ID da Guilda são obrigatórios para matrícula em massa por guilda!');
        return;
    }
    const parsedCursoId = parseInt(cursoId);
    const parsedGuildaId = parseInt(guildaId);
    if (isNaN(parsedCursoId) || isNaN(parsedGuildaId)) {
        alert('IDs de Curso ou Guilda inválidos!');
        return;
    }

    const bulkData = {
        cursoId: parsedCursoId,
        guildaId: parsedGuildaId
    };

    const result = await apiRequest('matriculas/bulk-by-guild', 'POST', bulkData);
    if (result.success) {
        alert(`${result.data.length} matrículas criadas/atualizadas para a guilda com sucesso!`);
        document.getElementById('txtCursoIdBulk').value = '';
        document.getElementById('txtGuildaIdBulk').value = '';
        displayMatriculasInTable(result.data); // Exibe os dados na tabela
    } else {
        alert('Erro ao matricular por guilda: ' + result.error);
    }
}

async function completeMatricula() {
    const matriculaId = document.getElementById('txtMatriculaIdComplete').value;
    const score = parseInt(document.getElementById('txtScoreQuest').value);

    if (!matriculaId || isNaN(score) || score < 0 || score > 100) {
        alert('ID da Matrícula e Score (0-100) são obrigatórios!');
        return;
    }
    const parsedMatriculaId = parseInt(matriculaId);
    if (isNaN(parsedMatriculaId)) { alert('ID da Matrícula inválido.'); return; }

    const scoreData = { score: score };
    const result = await apiRequest(`matriculas/${parsedMatriculaId}/complete`, 'PUT', scoreData);
    if (result.success) {
        alert(`Matrícula ID ${parsedMatriculaId} concluída com sucesso!`);
        document.getElementById('txtMatriculaIdComplete').value = '';
        document.getElementById('txtScoreQuest').value = '';
        // Podemos tentar carregar os detalhes desta matrícula específica se o endpoint suportar
        // Por enquanto, apenas o alerta, ou o usuário terá que buscar manualmente.
        // displayMatriculasInTable([result.data]); // Se a API retornar a matrícula atualizada completa
    } else {
        alert('Erro ao concluir matrícula: ' + result.error);
    }
}

async function bulkCompleteGuilda() {
    const atividadeId = document.getElementById('txtAtividadeIdBulkComplete').value;
    const guildaId = document.getElementById('txtGuildaIdBulkComplete').value;
    const score = parseInt(document.getElementById('txtScoreBulkCompleteGuild').value);

    if (!atividadeId || !guildaId || isNaN(score) || score < 0 || score > 100) {
        alert('ID da Atividade, ID da Guilda e Score (0-100) são obrigatórios!');
        return;
    }
    const parsedAtividadeId = parseInt(atividadeId);
    const parsedGuildaId = parseInt(guildaId);
    if (isNaN(parsedAtividadeId) || isNaN(parsedGuildaId)) { alert('IDs inválidos!'); return; }

    const bulkData = {
        atividadeId: parsedAtividadeId,
        guildaId: parsedGuildaId,
        score: score
    };

    const result = await apiRequest('matriculas/complete-by-guild', 'PUT', bulkData);
    if (result.success) {
        alert(`${result.data.length} matrículas concluídas em massa para a guilda!`);
        document.getElementById('txtAtividadeIdBulkComplete').value = '';
        document.getElementById('txtGuildaIdBulkComplete').value = '';
        document.getElementById('txtScoreBulkCompleteGuild').value = '';
        displayMatriculasInTable(result.data); // Exibe os dados na tabela
    } else {
        alert('Erro ao concluir matrículas em massa: ' + result.error);
    }
}

async function buscarMatriculasPorNomeAluno() {
    const nomeAluno = document.getElementById('txtNomeAlunoBuscaMatricula').value;
    if (!nomeAluno) { alert('Nome do Aluno é obrigatório para busca!'); return; }

    const result = await apiRequest(`matriculas/aluno/${encodeURIComponent(nomeAluno)}`, 'GET');
    const tbody = document.querySelector('#matriculas-tab #dgMatriculas tbody');
    if (!tbody) return;

    if (result.success && result.data) {
        tbody.innerHTML = '';
        // Este endpoint retorna um objeto com várias propriedades, não uma lista direta para a tabela
        // O endpoint em si não retorna uma lista de objetos Matricula para preencher a tabela dgMatriculas
        // Ele retorna um resumo das atividades matriculadas.
        alert(`Matrículas de ${result.data.aluno_nome || 'Aluno'} (Guilda: ${result.data.guilda_nome || 'N/A'}, Turma: ${result.data.turma_nome || 'N/A'})\nAtividades: ${result.data.atividades_matriculadas.join(', ')}`);
        // Para exibir na tabela dgMatriculas, seria necessário adaptar o formato dos dados ou o endpoint.
        // Por enquanto, apenas um alerta para mostrar que funcionou.
        tbody.innerHTML = '<tr><td colspan="7">Resultado da busca por nome exibido no alerta. Use "Buscar Detalhes por ID Aluno" para preencher a tabela.</td></tr>';
    } else {
        alert('Erro ao buscar matrículas por nome: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="7">Erro: ${result.error}</td></tr>`;
    }
}

async function buscarDetalhesMatriculaPorId() {
    const alunoId = document.getElementById('txtAlunoIdDetalhesMatricula').value;
    if (!alunoId) { alert('ID do Aluno é obrigatório para buscar detalhes!'); return; }
    const parsedAlunoId = parseInt(alunoId);
    if (isNaN(parsedAlunoId)) { alert('ID do Aluno inválido.'); return; }

    const result = await apiRequest(`matriculas/aluno/${parsedAlunoId}/details`, 'GET');
    
    if (result.success && result.data) {
        displayMatriculasInTable(result.data); // Exibe os dados na tabela
    } else {
        alert('Erro ao buscar detalhes das matrículas: ' + result.error);
        const tbody = document.querySelector('#matriculas-tab #dgMatriculas tbody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="7">Erro: ${result.error}</td></tr>`;
        }
    }
}

async function buscarAlunosMatriculadosAtividade() {
    const codigoAtividade = document.getElementById('txtCodigoAtividadeAlunosMatriculados').value;
    if (!codigoAtividade) { alert('Código da Atividade é obrigatório!'); return; }

    const result = await apiRequest(`matriculas/atividade/${encodeURIComponent(codigoAtividade)}`, 'GET');
    const tbody = document.querySelector('#matriculas-tab #dgMatriculas tbody');
    if (!tbody) return;

    if (result.success && result.data && result.data.alunos) {
        tbody.innerHTML = '';
        // Este endpoint retorna uma lista de alunos, não de matrículas.
        // Adaptamos a exibição na tabela de matrículas para mostrar os alunos matriculados.
        result.data.alunos.forEach(aluno => {
            const row = tbody.insertRow();
            row.insertCell().textContent = aluno.aluno_id; // Coluna ID da Matrícula (usamos ID do Aluno)
            row.insertCell().textContent = aluno.aluno_nome || 'N/A'; // Coluna Aluno ID (usamos Nome do Aluno)
            row.insertCell().textContent = result.data.atividade; // Coluna Atividade ID (usamos Nome da Atividade)
            row.insertCell().textContent = 'N/A'; // Score
            row.insertCell().textContent = 'N/A'; // Status
            row.insertCell().textContent = aluno.guilda_nome || 'N/A'; // Aluno Nome (usamos Guilda Nome)
            row.insertCell().textContent = aluno.turma_nome || 'N/A'; // Atividade Nome (usamos Turma Nome)
        });
        alert(`Alunos matriculados na atividade "${result.data.atividade}" carregados!`);
    } else {
        alert('Erro ao buscar alunos matriculados: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="7">Erro: ${result.error}</td></tr>`;
    }
}

// --- Funções de Lógica da Aba Rankings/Históricos ---

async function loadLeaderboardGeral() {
    const tbody = document.querySelector('#rankings-tab #dgLeaderboardsHistorico tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="4">Carregando Leaderboard Geral...</td></tr>';

    const result = await apiRequest('leaderboard', 'GET');

    if (result.success) {
        tbody.innerHTML = '';
        if (result.data && result.data.length > 0) {
            result.data.forEach(aluno => {
                const row = tbody.insertRow();
                row.insertCell().textContent = aluno.id;
                row.insertCell().textContent = aluno.nome;
                row.insertCell().textContent = aluno.xp;
                row.insertCell().textContent = aluno.level;
                // Adicionar outras colunas conforme necessário
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="4">Nenhum aluno no Leaderboard Geral.</td></tr>';
        }
    } else {
        alert('Erro ao carregar Leaderboard Geral: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="4">Erro: ${result.error}</td></tr>`;
    }
}

async function loadLeaderboardTurma() {
    const turmaId = document.getElementById('txtTurmaIdLeaderboard').value;
    if (!turmaId) { alert('ID da Turma é obrigatório para o Leaderboard por Turma!'); return; }
    const parsedTurmaId = parseInt(turmaId);
    if (isNaN(parsedTurmaId)) { alert('ID da Turma inválido.'); return; }

    const tbody = document.querySelector('#rankings-tab #dgLeaderboardsHistorico tbody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="4">Carregando Leaderboard da Turma ID ${parsedTurmaId}...</td></tr>`;

    const result = await apiRequest(`turmas/${parsedTurmaId}/leaderboard`, 'GET');

    if (result.success) {
        tbody.innerHTML = '';
        if (result.data && result.data.length > 0) {
            result.data.forEach(aluno => {
                const row = tbody.insertRow();
                row.insertCell().textContent = aluno.id;
                row.insertCell().textContent = aluno.nome;
                row.insertCell().textContent = aluno.xp;
                row.insertCell().textContent = aluno.level;
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="4">Nenhum aluno no Leaderboard da Turma ID ${parsedTurmaId}.</td></tr>`;
        }
    } else {
        alert('Erro ao carregar Leaderboard por Turma: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="4">Erro: ${result.error}</td></tr>`;
    }
}

async function loadLeaderboardGuilda() {
    const tbody = document.querySelector('#rankings-tab #dgLeaderboardsHistorico tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="4">Carregando Leaderboard por Guilda...</td></tr>';

    const result = await apiRequest('guilds/leaderboard', 'GET');

    if (result.success) {
        tbody.innerHTML = '';
        if (result.data && result.data.length > 0) {
            result.data.forEach(guildaEntry => {
                const row = tbody.insertRow();
                row.insertCell().textContent = guildaEntry.guilda_id;
                row.insertCell().textContent = guildaEntry.guilda_nome;
                row.insertCell().textContent = guildaEntry.total_xp;
                row.insertCell().textContent = guildaEntry.turma_nome || 'N/A';
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="4">Nenhuma guilda no Leaderboard.</td></tr>';
        }
    } else {
        alert('Erro ao carregar Leaderboard por Guilda: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="4">Erro: ${result.error}</td></tr>`;
    }
}

async function loadAlunosPorGuilda() {
    const nomeGuilda = document.getElementById('txtNomeGuildaAlunos').value;
    if (!nomeGuilda) { alert('Nome da Guilda é obrigatório para listar alunos!'); return; }

    const tbody = document.querySelector('#rankings-tab #dgLeaderboardsHistorico tbody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="4">Carregando alunos da Guilda "${nomeGuilda}"...</td></tr>`;

    const result = await apiRequest(`alunos/guilda/${encodeURIComponent(nomeGuilda)}`, 'GET');

    if (result.success) {
        tbody.innerHTML = '';
        if (result.data && result.data.length > 0) {
            result.data.forEach(aluno => {
                const row = tbody.insertRow();
                row.insertCell().textContent = aluno.id;
                row.insertCell().textContent = aluno.nome;
                row.insertCell().textContent = aluno.xp;
                row.insertCell().textContent = aluno.guilda_nome || 'N/A';
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="4">Nenhum aluno encontrado na Guilda "${nomeGuilda}".</td></tr>`;
        }
    } else {
        alert('Erro ao carregar alunos por Guilda: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="4">Erro: ${result.error}</td></tr>`;
    }
}

async function loadHistoricoAluno() {
    const alunoId = document.getElementById('txtAlunoIdHistorico').value;
    const nomeAluno = document.getElementById('txtNomeAlunoHistorico').value;

    let endpoint = 'alunos/historico_xp_pontos';
    if (alunoId) {
        const parsedAlunoId = parseInt(alunoId);
        if (isNaN(parsedAlunoId)) { alert('ID do Aluno inválido!'); return; }
        endpoint += `?aluno_id=${parsedAlunoId}`;
    } else if (nomeAluno) {
        endpoint += `?nome_aluno=${encodeURIComponent(nomeAluno)}`;
    } else {
        alert('Forneça o ID ou o Nome do Aluno para buscar o histórico.');
        return;
    }

    const tbody = document.querySelector('#rankings-tab #dgLeaderboardsHistorico tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="8">Carregando Histórico do Aluno...</td></tr>';

    const result = await apiRequest(endpoint, 'GET');

    if (result.success) {
        tbody.innerHTML = '';
        if (result.data && result.data.length > 0) {
            result.data.forEach(historico => {
                const row = tbody.insertRow();
                row.insertCell().textContent = historico.id;
                row.insertCell().textContent = historico.aluno_nome || 'N/A';
                row.insertCell().textContent = historico.tipo_transacao;
                row.insertCell().textContent = historico.valor_xp_alterado;
                row.insertCell().textContent = historico.valor_pontos_alterado;
                row.insertCell().textContent = historico.motivo || '';
                row.insertCell().textContent = new Date(historico.data_hora).toLocaleString();
                row.insertCell().textContent = historico.referencia_entidade || 'N/A';
                row.insertCell().textContent = historico.referencia_id || 'N/A';
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="8">Nenhum histórico encontrado para o aluno.</td></tr>';
        }
    } else {
        alert('Erro ao carregar histórico do aluno: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="8">Erro: ${result.error}</td></tr>`;
    }
}

async function loadHistoricoTurma() {
    const turmaId = document.getElementById('txtTurmaIdHistorico').value;
    if (!turmaId) { alert('ID da Turma é obrigatório para o histórico da turma!'); return; }
    const parsedTurmaId = parseInt(turmaId);
    if (isNaN(parsedTurmaId)) { alert('ID da Turma inválido.'); return; }

    const tbody = document.querySelector('#rankings-tab #dgLeaderboardsHistorico tbody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="8">Carregando Histórico da Turma ID ${parsedTurmaId}...</td></tr>`;

    const result = await apiRequest(`turmas/${parsedTurmaId}/historico_xp_pontos`, 'GET');

    if (result.success) {
        tbody.innerHTML = '';
        if (result.data && result.data.length > 0) {
            result.data.forEach(historico => {
                const row = tbody.insertRow();
                row.insertCell().textContent = historico.id;
                row.insertCell().textContent = historico.aluno_nome || 'N/A';
                row.insertCell().textContent = historico.tipo_transacao;
                row.insertCell().textContent = historico.valor_xp_alterado;
                row.insertCell().textContent = historico.valor_pontos_alterado;
                row.insertCell().textContent = historico.motivo || '';
                row.insertCell().textContent = new Date(historico.data_hora).toLocaleString();
                row.insertCell().textContent = historico.referencia_entidade || 'N/A';
                row.insertCell().textContent = historico.referencia_id || 'N/A';
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="8">Nenhum histórico encontrado para a Turma ID ${parsedTurmaId}.</td></tr>`;
        }
    } else {
        alert('Erro ao carregar histórico da turma: ' + result.error);
        tbody.innerHTML = `<tr><td colspan="8">Erro: ${result.error}</td></tr>`;
    }
}

// --- NOVA FUNÇÃO PARA GERAR RELATÓRIO PDF ---
async function generatePdfReport() {
    alert('Gerando relatório PDF... Isso pode levar alguns segundos.');
    const result = await apiRequest('relatorio-pdf', 'GET'); // Endpoint que você precisará criar no backend

    if (result.success && result.isPdf) {
        // Cria um link temporário para fazer o download do PDF
        const url = window.URL.createObjectURL(result.data);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Relatorio_Willow_Gamificacao.pdf'; // Nome do arquivo a ser baixado
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url); // Libera o URL do objeto
        document.body.removeChild(a); // Remove o link temporário
        alert('Relatório PDF gerado e baixado com sucesso!');
    } else if (result.success && !result.isPdf) {
        alert('A API não retornou um PDF. Verifique o backend.');
    } else {
        alert('Erro ao gerar relatório PDF: ' + result.error);
    }
}


// --- Lógica de Inicialização e Event Listeners ---

document.addEventListener('DOMContentLoaded', () => {
    // --- Lógica de Troca de Abas ---
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    // Função para ativar uma aba específica e carregar seus dados
    const activateTab = (tabId) => {
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));

        const targetButton = document.querySelector(`.tab-button[data-tab="${tabId}"]`);
        const targetContent = document.getElementById(`${tabId}-tab`);

        if (targetButton && targetContent) {
            targetButton.classList.add('active');
            targetContent.classList.add('active');

            // Carregar dados específicos da aba quando ela é ativada
            switch (tabId) {
                case 'turmas':
                    loadTurmas();
                    break;
                case 'guildas':
                    loadGuildas();
                    break;
                case 'alunos':
                    loadAlunos();
                    break;
                case 'atividades':
                    loadAtividades();
                    break;
                case 'matriculas':
                    // Limpa a tabela e exibe uma mensagem ou apenas a deixa vazia
                    document.querySelector('#matriculas-tab #dgMatriculas tbody').innerHTML = '<tr><td colspan="7">Use as opções para criar ou buscar matrículas.</td></tr>';
                    break;
                case 'rankings':
                    // loadLeaderboardGeral(); // Carrega Leaderboard Geral por padrão na aba Rankings
                    document.querySelector('#rankings-tab #dgLeaderboardsHistorico tbody').innerHTML = '<tr><td colspan="4">Use os botões para carregar rankings ou históricos.</td></tr>';
                    break;
            }
        }
    };

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.dataset.tab;
            activateTab(tabId);
        });
    });

    // Ativar a aba de Turmas por padrão ao carregar a página
    activateTab('turmas');

    // --- Conexão de Event Listeners para TODOS os botões ---

    // Aba Turmas
    document.getElementById('btnCarregarTurmas')?.addEventListener('click', loadTurmas);
    document.getElementById('btnCriarTurma')?.addEventListener('click', createTurma);
    document.getElementById('btnAtualizarTurma')?.addEventListener('click', updateTurma);
    document.getElementById('btnDeletarTurma')?.addEventListener('click', deleteTurma);

    // Aba Guildas
    document.getElementById('btnCarregarGuildas')?.addEventListener('click', loadGuildas);
    document.getElementById('btnCriarGuilda')?.addEventListener('click', createGuilda);
    document.getElementById('btnAtualizarGuilda')?.addEventListener('click', updateGuilda);
    document.getElementById('btnDeletarGuilda')?.addEventListener('click', deleteGuilda);
    document.getElementById('btnPenalizarXpGuilda')?.addEventListener('click', penalizeGuildXp);

    // Aba Alunos
    document.getElementById('btnCarregarAlunos')?.addEventListener('click', loadAlunos);
    document.getElementById('btnCriarAluno')?.addEventListener('click', createAluno);
    document.getElementById('btnAtualizarAluno')?.addEventListener('click', updateAluno);
    document.getElementById('btnDeletarAluno')?.addEventListener('click', deleteAluno);
    document.getElementById('btnAddXp')?.addEventListener('click', addXp);
    document.getElementById('btnPenalizarXpAluno')?.addEventListener('click', penalizeXpAluno);
    document.getElementById('btnConcederBadge')?.addEventListener('click', concederBadge);
    document.getElementById('btnAddPontosAcademicos')?.addEventListener('click', addPontosAcademicos);

    // Aba Atividades
    document.getElementById('btnCarregarAtividades')?.addEventListener('click', loadAtividades);
    document.getElementById('btnCriarAtividade')?.addEventListener('click', createAtividade);
    document.getElementById('btnAtualizarAtividade')?.addEventListener('click', updateAtividade);
    document.getElementById('btnBuscarAtividadePorCodigo')?.addEventListener('click', buscarAtividadePorCodigo);

    // Aba Matrículas/Progresso
    document.getElementById('btnCriarMatricula')?.addEventListener('click', createMatricula);
    document.getElementById('btnBulkMatriculaTurma')?.addEventListener('click', bulkMatriculaTurma);
    document.getElementById('btnBulkMatriculaGuilda')?.addEventListener('click', bulkMatriculaGuilda);
    document.getElementById('btnCompleteMatricula')?.addEventListener('click', completeMatricula);
    document.getElementById('btnBulkCompleteGuilda')?.addEventListener('click', bulkCompleteGuilda);
    document.getElementById('btnBuscarMatriculasPorNomeAluno')?.addEventListener('click', buscarMatriculasPorNomeAluno);
    document.getElementById('btnBuscarDetalhesMatriculaPorId')?.addEventListener('click', buscarDetalhesMatriculaPorId);
    document.getElementById('btnBuscarAlunosMatriculadosAtividade')?.addEventListener('click', buscarAlunosMatriculadosAtividade);

    // Aba Rankings/Históricos
    document.getElementById('btnLeaderboardGeral')?.addEventListener('click', loadLeaderboardGeral);
    document.getElementById('btnLeaderboardTurma')?.addEventListener('click', loadLeaderboardTurma);
    document.getElementById('btnLeaderboardGuilda')?.addEventListener('click', loadLeaderboardGuilda);
    document.getElementById('btnAlunosPorGuilda')?.addEventListener('click', loadAlunosPorGuilda);
    document.getElementById('btnHistoricoAluno')?.addEventListener('click', loadHistoricoAluno);
    document.getElementById('btnHistoricoTurma')?.addEventListener('click', loadHistoricoTurma);
    
    // NOVO: Adicionar evento de clique para o botão Gerar Relatório PDF
    document.getElementById('btnGerarRelatorioPdf')?.addEventListener('click', generatePdfReport);
});