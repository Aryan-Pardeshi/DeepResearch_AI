/**
 * Literature Review - Dynamic Evidence Matrix UI Module
 */

export function initMatrixUI(apiBase = '') {
    const genBtn = document.getElementById('lr-generate-matrix-btn');
    if (genBtn) {
        genBtn.addEventListener('click', () => refreshMatrix(apiBase));
    }
    const csvBtn = document.getElementById('lr-export-matrix-csv');
    if (csvBtn) {
        csvBtn.addEventListener('click', () => exportMatrixCSV());
    }
}

export async function refreshMatrix(apiBase = '') {
    const corpusId = window.getCurrentCorpusId ? window.getCurrentCorpusId() : null;
    if (!corpusId) return;

    const header = document.getElementById('lr-matrix-header');
    const body = document.getElementById('lr-matrix-body');
    if (!header || !body) return;

    header.innerHTML = `<th>Paper Title</th><th>Loading Matrix...</th>`;
    body.innerHTML = '';

    try {
        const resp = await fetch(`${apiBase}/api/literature-review/corpus/${corpusId}/matrix`, {
            method: 'POST'
        });
        if (!resp.ok) throw new Error(`Matrix generation failed: HTTP ${resp.status}`);
        const matrix = await resp.json();
        renderMatrixTable(matrix, corpusId, apiBase);
    } catch (e) {
        console.error('Matrix error:', e);
        header.innerHTML = `<th>Error</th><th>Failed to load matrix: ${e.message}</th>`;
    }
}

export function renderMatrixTable(matrix, corpusId, apiBase = '') {
    const header = document.getElementById('lr-matrix-header');
    const body = document.getElementById('lr-matrix-body');
    if (!header || !body) return;

    header.innerHTML = `<th>Paper Title</th>`;
    (matrix.columns || []).forEach(col => {
        const th = document.createElement('th');
        th.textContent = col.label || col.key;
        th.title = col.description || '';
        header.appendChild(th);
    });

    body.innerHTML = '';
    const rowsMap = matrix.rows || {};

    Object.keys(rowsMap).forEach(pid => {
        const tr = document.createElement('tr');

        const titleTd = document.createElement('td');
        titleTd.className = 'sticky-col';
        titleTd.textContent = pid;
        tr.appendChild(titleTd);

        (matrix.columns || []).forEach(col => {
            const colKey = col.key;
            const cell = (rowsMap[pid] || {})[colKey] || { cell_value: 'N/A', origin: 'ai' };
            const td = document.createElement('td');
            td.className = cell.origin === 'human' ? 'cell-edited' : 'cell-ai';

            const valueSpan = document.createElement('span');
            valueSpan.contentEditable = 'true';
            valueSpan.textContent = cell.cell_value || '';

            const originBadge = document.createElement('span');
            originBadge.contentEditable = 'false';
            originBadge.className = cell.origin === 'human' ? 'cell-provenance-badge human' : 'cell-provenance-badge ai';
            originBadge.title = cell.origin === 'human' ? 'Edited by user' : 'AI Extracted';
            originBadge.textContent = cell.origin === 'human' ? 'Human' : 'AI';

            td.appendChild(valueSpan);
            td.appendChild(originBadge);

            valueSpan.addEventListener('blur', async () => {
                const newValue = valueSpan.textContent.trim();
                await updateCellInBackend(corpusId, pid, colKey, newValue, apiBase);
            });

            tr.appendChild(td);
        });

        body.appendChild(tr);
    });
}

async function updateCellInBackend(corpusId, paperId, columnKey, newValue, apiBase = '') {
    try {
        const resp = await fetch(`${apiBase}/api/literature-review/corpus/${corpusId}/matrix/cell`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_id: paperId, column_key: columnKey, new_value: newValue })
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            console.error('Cell update failed:', resp.status, errData);
            alert(`Cell save failed (${resp.status}): ${errData.detail || 'Server error'}`);
        }
    } catch (e) {
        console.error('Cell update network error:', e);
        alert(`Cell save failed: ${e.message}`);
    }
}

export function exportMatrixCSV() {
    const table = document.getElementById('lr-matrix-table');
    if (!table) return;

    let csv = [];
    const rows = table.querySelectorAll('tr');
    rows.forEach(row => {
        const cols = row.querySelectorAll('th, td');
        let rowData = [];
        cols.forEach(col => {
            let val = col.innerText.replace(/\b(Human|AI)\b/g, '').replace(/"/g, '""').trim();
            rowData.push(`"${val}"`);
        });
        csv.push(rowData.join(','));
    });

    const blob = new Blob([csv.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'evidence_matrix.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}
