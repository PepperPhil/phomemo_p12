// Label queue state
let labelQueue = [];
let nextId = 1;
let availableFonts = [];
let symbolPickerTargetId = null;

// Symbol categories
const SYMBOLS = {
    common: ['★', '☆', '✓', '✗', '●', '○', '■', '□', '▲', '△', '▼', '▽', '◆', '◇', '♠', '♣', '♥', '♦', '✦', '✧', '⬟', '⬡'],
    arrows: ['→', '←', '↑', '↓', '↔', '↕', '⇒', '⇐', '⇑', '⇓', '⇔', '⇕', '➜', '➤', '▶', '◀', '▷', '◁', '↗', '↘', '↙', '↖'],
    warning: ['⚠', '⛔', '☠', '⚡', '☢', '☣', '⚑', '⚐', '⛏', '⚒', '⛑', '🔥'],
    misc: ['☎', '✉', '⚡', '♻', '☀', '❄', '☁', '☂', '✈', '⚓', '⚙', '✂', '☕', '♫', '♪', '⌛', '⌚', '☮', '☯', '⚽', '⚾', '♟'],
    math: ['±', '×', '÷', '≠', '≈', '≤', '≥', '∞', '∑', '∏', '√', '∂', '∫', '∆', '∇', 'π', 'Ω', 'µ', '∅', '∈', '∉', '⊂'],
    shapes: ['◐', '◑', '◒', '◓', '⬤', '⬮', '⬯', '▰', '▱', '▬', '▭', '▮', '▯', '⬛', '⬜', '◼', '◻', '▪', '▫', '⬝', '⬞', '⬠']
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadFonts();
    loadConfig();
    renderTable();
});

async function loadFonts() {
    try {
        const resp = await fetch('/api/fonts');
        const data = await resp.json();
        availableFonts = data.fonts || [];
    } catch (e) {
        console.error('Failed to load fonts:', e);
        availableFonts = ['sans-serif', 'serif', 'monospace'];
    }
}

async function loadConfig() {
    try {
        const resp = await fetch('/api/config');
        const data = await resp.json();
        if (data.port) {
            document.getElementById('port-input').value = data.port;
            document.getElementById('dots-input').value = data.dots || 96;
            setConfigStatus('connected', 'Connected: ' + data.port);
        }
    } catch (e) {
        // Not configured yet, that's fine
    }
}

async function updateConfig() {
    const port = document.getElementById('port-input').value.trim();
    const dots = parseInt(document.getElementById('dots-input').value);

    if (!port) {
        setConfigStatus('error', 'Port cannot be empty');
        return;
    }

    try {
        const resp = await fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({port, dots})
        });
        const data = await resp.json();
        if (data.status === 'ok') {
            setConfigStatus('connected', 'Connected: ' + port);
        } else {
            setConfigStatus('error', data.message || 'Failed');
        }
    } catch (e) {
        setConfigStatus('error', 'Connection error: ' + e.message);
    }
}

function setConfigStatus(type, text) {
    const el = document.getElementById('config-status');
    el.textContent = text;
    el.className = 'status-indicator status-' + type;
}

function addTextRow() {
    labelQueue.push({
        id: nextId++,
        type: 'text',
        text: '',
        font: availableFonts.length > 0 ? availableFonts[0] : '',
        fontSize: 88,
        fontWeight: 'NORMAL',
        fontSlant: 'NORMAL',
        preview: null,
        filename: null,
        status: ''
    });
    renderTable();
}

function triggerImageUpload() {
    document.getElementById('image-upload-input').click();
}

async function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const resp = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();
        if (data.status === 'ok') {
            labelQueue.push({
                id: nextId++,
                type: 'image',
                text: file.name,
                font: '',
                fontSize: 0,
                fontWeight: 'NORMAL',
                fontSlant: 'NORMAL',
                preview: data.preview,
                filename: data.filename,
                fileId: data.fileId,
                status: ''
            });
            renderTable();
        } else {
            alert('Upload failed: ' + (data.message || 'Unknown error'));
        }
    } catch (e) {
        alert('Upload error: ' + e.message);
    }

    // Reset the file input
    event.target.value = '';
}

function removeRow(id) {
    labelQueue = labelQueue.filter(l => l.id !== id);
    renderTable();
}

function buildFontSelect(selectedFont, id) {
    let html = '<select class="font-select" data-id="' + id + '" onchange="onFieldChange(' + id + ')">';
    // Add generic families first
    const generics = ['sans-serif', 'serif', 'monospace'];
    for (const g of generics) {
        const sel = (selectedFont === g) ? ' selected' : '';
        html += '<option value="' + g + '"' + sel + '>' + g + '</option>';
    }
    // Add system fonts
    for (const f of availableFonts) {
        if (generics.includes(f)) continue;
        const sel = (selectedFont === f) ? ' selected' : '';
        html += '<option value="' + escapeHtml(f) + '"' + sel + '>' + escapeHtml(f) + '</option>';
    }
    html += '</select>';
    return html;
}

function renderTable() {
    const tbody = document.getElementById('label-tbody');
    if (labelQueue.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-msg">No labels in queue. Click "Add Text Label" or "Upload Image Label" to start.</td></tr>';
        return;
    }

    let html = '';
    labelQueue.forEach((label, index) => {
        const isText = label.type === 'text';
        const previewImg = label.preview
            ? '<img src="data:image/png;base64,' + label.preview + '" class="preview-thumb" alt="preview">'
            : '<span class="no-preview">--</span>';

        const statusClass = label.status === 'ok' ? 'row-ok' : label.status === 'error' ? 'row-error' : '';

        html += '<tr class="' + statusClass + '">';
        html += '<td>' + (index + 1) + '</td>';
        html += '<td>' + (isText ? 'Text' : 'Image') + '</td>';

        if (isText) {
            html += '<td class="content-cell">';
            html += '<div class="text-input-wrapper">';
            html += '<input type="text" class="text-input" id="text-' + label.id + '" value="' + escapeHtml(label.text) + '" placeholder="Enter label text..." onchange="onFieldChange(' + label.id + ')" onkeyup="onFieldChange(' + label.id + ')">';
            html += '<button class="btn-symbol" onclick="openSymbolPicker(' + label.id + ')" title="Insert symbol">&#9733;</button>';
            html += '</div>';
            html += '</td>';
        } else {
            html += '<td class="content-cell">' + escapeHtml(label.text) + '</td>';
        }

        html += '<td>' + previewImg + '</td>';

        if (isText) {
            html += '<td>' + buildFontSelect(label.font, label.id) + '</td>';
            html += '<td><select data-id="' + label.id + '" onchange="onFieldChange(' + label.id + ')">';
            for (const s of [24, 32, 48, 64, 72, 88]) {
                html += '<option value="' + s + '"' + (label.fontSize === s ? ' selected' : '') + '>' + s + '</option>';
            }
            html += '</select></td>';
            html += '<td><select data-id="' + label.id + '" onchange="onFieldChange(' + label.id + ')">';
            html += '<option value="NORMAL"' + (label.fontWeight === 'NORMAL' ? ' selected' : '') + '>Normal</option>';
            html += '<option value="BOLD"' + (label.fontWeight === 'BOLD' ? ' selected' : '') + '>Bold</option>';
            html += '</select></td>';
            html += '<td><select data-id="' + label.id + '" onchange="onFieldChange(' + label.id + ')">';
            html += '<option value="NORMAL"' + (label.fontSlant === 'NORMAL' ? ' selected' : '') + '>Normal</option>';
            html += '<option value="ITALIC"' + (label.fontSlant === 'ITALIC' ? ' selected' : '') + '>Italic</option>';
            html += '</select></td>';
        } else {
            html += '<td>--</td><td>--</td><td>--</td><td>--</td>';
        }

        html += '<td class="actions-cell">';
        if (isText) {
            html += '<button onclick="fetchPreview(' + label.id + ')">Preview</button> ';
        }
        html += '<button onclick="printRow(' + label.id + ')">Print</button> ';
        html += '<button class="btn-delete" onclick="removeRow(' + label.id + ')">Delete</button>';
        html += '</td>';
        html += '</tr>';
    });

    tbody.innerHTML = html;
}

function readRowFields(id) {
    const label = labelQueue.find(l => l.id === id);
    if (!label || label.type !== 'text') return;

    const textInput = document.getElementById('text-' + id);
    if (textInput) label.text = textInput.value;

    // Read selects - they are in order: font, size, weight, slant
    const row = textInput ? textInput.closest('tr') : null;
    if (row) {
        const selects = row.querySelectorAll('select');
        if (selects.length >= 4) {
            label.font = selects[0].value;
            label.fontSize = parseInt(selects[1].value);
            label.fontWeight = selects[2].value;
            label.fontSlant = selects[3].value;
        }
    }
}

function onFieldChange(id) {
    readRowFields(id);
}

async function fetchPreview(id) {
    const label = labelQueue.find(l => l.id === id);
    if (!label) return;

    readRowFields(id);

    if (label.type === 'text' && !label.text.trim()) {
        alert('Please enter some text first.');
        return;
    }

    try {
        const resp = await fetch('/api/preview', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                text: label.text,
                font: label.font,
                fontSize: label.fontSize,
                fontWeight: label.fontWeight,
                fontSlant: label.fontSlant
            })
        });
        const data = await resp.json();
        if (data.status === 'ok') {
            label.preview = data.preview;
            renderTable();
        } else {
            alert('Preview failed: ' + (data.message || 'Unknown error'));
        }
    } catch (e) {
        alert('Preview error: ' + e.message);
    }
}

async function printRow(id) {
    const label = labelQueue.find(l => l.id === id);
    if (!label) return;

    readRowFields(id);
    label.status = 'printing';
    renderTable();

    const body = label.type === 'text'
        ? {type: 'text', text: label.text, font: label.font, fontSize: label.fontSize, fontWeight: label.fontWeight, fontSlant: label.fontSlant}
        : {type: 'image', filename: label.filename};

    try {
        const resp = await fetch('/api/print', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        const data = await resp.json();
        label.status = data.status === 'ok' ? 'ok' : 'error';
        if (data.status !== 'ok') {
            alert('Print failed: ' + (data.message || 'Unknown error'));
        }
    } catch (e) {
        label.status = 'error';
        alert('Print error: ' + e.message);
    }
    renderTable();
}

async function printAll() {
    if (labelQueue.length === 0) {
        alert('No labels in queue.');
        return;
    }

    // Read all text fields first
    labelQueue.forEach(l => { if (l.type === 'text') readRowFields(l.id); });

    const labels = labelQueue.map(l => {
        if (l.type === 'text') {
            return {type: 'text', text: l.text, font: l.font, fontSize: l.fontSize, fontWeight: l.fontWeight, fontSlant: l.fontSlant};
        } else {
            return {type: 'image', filename: l.filename};
        }
    });

    const btn = document.getElementById('btn-print-all');
    btn.disabled = true;
    btn.textContent = 'Printing...';

    try {
        const resp = await fetch('/api/print-all', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({labels})
        });
        const data = await resp.json();
        if (data.results) {
            data.results.forEach(r => {
                if (r.index < labelQueue.length) {
                    labelQueue[r.index].status = r.status;
                }
            });
        }
    } catch (e) {
        alert('Print all error: ' + e.message);
    }

    btn.disabled = false;
    btn.textContent = 'Print All';
    renderTable();
}

// Symbol picker
function openSymbolPicker(id) {
    symbolPickerTargetId = id;
    document.getElementById('symbol-modal').style.display = 'flex';
    showSymbolCategory('common');
}

function closeSymbolPicker() {
    document.getElementById('symbol-modal').style.display = 'none';
    symbolPickerTargetId = null;
}

function showSymbolCategory(category) {
    const grid = document.getElementById('symbol-grid');
    const symbols = SYMBOLS[category] || [];

    // Update active button
    document.querySelectorAll('.symbol-cat-btn').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.toLowerCase() === category);
    });

    let html = '';
    symbols.forEach(s => {
        html += '<button class="symbol-btn" onclick="insertSymbol(\'' + s + '\')">' + s + '</button>';
    });
    grid.innerHTML = html;
}

function insertSymbol(symbol) {
    if (symbolPickerTargetId === null) return;

    const input = document.getElementById('text-' + symbolPickerTargetId);
    if (!input) return;

    const start = input.selectionStart;
    const end = input.selectionEnd;
    const text = input.value;
    input.value = text.substring(0, start) + symbol + text.substring(end);
    input.selectionStart = input.selectionEnd = start + symbol.length;
    input.focus();

    // Update state
    const label = labelQueue.find(l => l.id === symbolPickerTargetId);
    if (label) label.text = input.value;

    closeSymbolPicker();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
