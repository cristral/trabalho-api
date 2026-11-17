
const API_URL = window.location.port === '3000'
    ? '/personagens'
    : `http://${window.location.hostname || 'localhost'}:3000/personagens`;
const characterList = document.getElementById('character-list');
const characterDialog = document.getElementById('character-dialog');
const characterForm = document.getElementById('character-form');
const formError = document.getElementById('form-error');
const fields = ['nome', 'classe', 'nivel', 'pontos_vida', 'forca', 'destreza', 'constituicao', 'inteligencia', 'sabedoria', 'carisma'];
let editingId = null;

// Carrega os personagens assim que a página é aberta
document.addEventListener('DOMContentLoaded', fetchPersonagens);
document.getElementById('create-character').addEventListener('click', () => openDialog());
document.getElementById('close-dialog').addEventListener('click', () => characterDialog.close());
characterList.addEventListener('click', handleCharacterAction);
characterForm.addEventListener('submit', saveCharacter);

// Buscar os personagens na API (GET)
async function fetchPersonagens() {
    try {
        const response = await fetch(API_URL);
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Não foi possível carregar personagens.');
        renderCharacters(result.data || []);
    } catch (error) {
        characterList.replaceChildren();
        const message = document.createElement('p');
        message.className = 'list-message';
        message.textContent = `Não foi possível conectar à API. Confirme se o servidor api.py está em execução e atualize a página. (${error.message})`;
        characterList.appendChild(message);
    }
}

// Renderizar os cards na tela
function renderCharacters(characters) {
    characterList.replaceChildren();

    if (characters.length === 0) {
        const message = document.createElement('p');
        message.className = 'list-message';
        message.textContent = 'Nenhum herói cadastrado ainda. Clique no botão acima para criar o primeiro!';
        characterList.appendChild(message);
        return;
    }

    characters.forEach(char => {
        const card = document.createElement('article');
        card.className = 'char-card';

        const header = document.createElement('div');
        header.className = 'char-header';
        const name = document.createElement('span');
        name.className = 'char-name';
        name.textContent = char.nome;
        const badge = document.createElement('span');
        badge.className = 'char-badge';
        badge.textContent = `${char.classe} • Nv. ${char.nivel}`;
        header.append(name, badge);

        const hp = document.createElement('div');
        hp.className = 'char-hp';
        hp.textContent = `❤️ PV: ${char.pontos_vida}`;

        const stats = document.createElement('div');
        stats.className = 'char-stats-grid';
        [
            ['FOR', char.forca], ['DES', char.destreza], ['CON', char.constituicao],
            ['INT', char.inteligencia], ['SAB', char.sabedoria], ['CAR', char.carisma],
        ].forEach(([label, value]) => {
            const stat = document.createElement('span');
            stat.textContent = `${label}: ${value}`;
            stats.appendChild(stat);
        });

        const actions = document.createElement('div');
        actions.className = 'char-actions';
        const editButton = document.createElement('button');
        editButton.type = 'button';
        editButton.className = 'btn-sm btn-edit';
        editButton.dataset.action = 'edit';
        editButton.dataset.id = char.id;
        editButton.textContent = '✏️ Editar';
        const deleteButton = document.createElement('button');
        deleteButton.type = 'button';
        deleteButton.className = 'btn-sm btn-delete';
        deleteButton.dataset.action = 'delete';
        deleteButton.dataset.id = char.id;
        deleteButton.textContent = '🗑️ Excluir';
        actions.append(editButton, deleteButton);
        card.append(header, hp, stats, actions);
        characterList.appendChild(card);
    });
}

function openDialog(character = null) {
    editingId = character?.id ?? null;
    characterForm.reset();
    formError.textContent = '';
    document.getElementById('dialog-title').textContent = editingId === null
        ? 'Criar personagem'
        : 'Editar personagem';
    if (character) {
        fields.forEach(field => {
            characterForm.elements[field].value = character[field];
        });
    }
    characterDialog.showModal();
}

async function handleCharacterAction(event) {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    const id = button.dataset.id;
    if (button.dataset.action === 'edit') {
        try {
            const response = await fetch(`${API_URL}/${encodeURIComponent(id)}`);
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Não foi possível carregar o personagem.');
            openDialog(result.data);
        } catch (error) {
            alert(error.message);
        }
        return;
    }
    if (button.dataset.action === 'delete' && confirm('Tem certeza que deseja banir este herói do grimório?')) {
        try {
            const response = await fetch(`${API_URL}/${encodeURIComponent(id)}`, { method: 'DELETE' });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Não foi possível excluir o personagem.');
            await fetchPersonagens();
        } catch (error) {
            alert(error.message);
        }
    }
}

async function saveCharacter(event) {
    event.preventDefault();
    formError.textContent = '';
    const character = Object.fromEntries(new FormData(characterForm));
    fields.slice(2).forEach(field => {
        character[field] = Number(character[field]);
    });

    try {
        const response = await fetch(
            editingId === null ? API_URL : `${API_URL}/${encodeURIComponent(editingId)}`,
            {
                method: editingId === null ? 'POST' : 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(character),
            },
        );
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Não foi possível salvar o personagem.');
        characterDialog.close();
        await fetchPersonagens();
    } catch (error) {
        formError.textContent = error.message;
    }
}