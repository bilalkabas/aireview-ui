// Ensemble phase — papers list page
let allPapers = [];
const filters = {
    titleKeywords: new Set(),
    statuses: new Set()
};

const FILTERS_STORAGE_KEY = 'ensembleReviewFilters';

function saveFilters() {
    localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify({
        titleKeywords: Array.from(filters.titleKeywords),
        statuses: Array.from(filters.statuses)
    }));
}

function loadSavedFilters() {
    const saved = localStorage.getItem(FILTERS_STORAGE_KEY);
    if (!saved) return;
    try {
        const data = JSON.parse(saved);
        filters.titleKeywords = new Set(data.titleKeywords || []);
        filters.statuses = new Set(data.statuses || []);
    } catch (e) {
        console.error('Error loading filters:', e);
    }
}

async function loadPapers() {
    try {
        allPapers = await loadEnsemblePapers();
        loadSavedFilters();
        // The file, not the browser, decides whether a category is already committed.
        syncCategoryFromPapers(allPapers);
        // Nothing else is usable until the evaluator has committed to a category.
        await requireCategory();
        initializeFilters();
        renderPapers();
    } catch (error) {
        console.error('Error loading papers:', error);
        document.getElementById('papers-list').innerHTML = `
            <div class="empty-state">
                <h3>Error Loading Papers</h3>
                <p>${escapeHtml(error.message)}</p>
            </div>
        `;
    }
}

function initializeFilters() {
    document.getElementById('locked-category-name').textContent = categoryLabel(getChosenCategory());
    document.getElementById('locked-category-evaluator').textContent = getEvaluatorName();

    document.querySelectorAll('.status-filter').forEach(input => {
        if (filters.statuses.has(input.value)) input.checked = true;
    });

    renderSelectedTitleKeywords();
}

function availableCategories() {
    const categories = new Set();
    allPapers.forEach(paper => {
        if (paper.category) categories.add(paper.category);
    });
    return Array.from(categories).sort();
}

// Resolves once a category is stored; the gate cannot be dismissed any other way.
function requireCategory() {
    if (getChosenCategory()) return Promise.resolve();

    const gate = document.getElementById('category-gate');
    const options = document.getElementById('category-gate-options');
    const nameInput = document.getElementById('category-gate-name');
    const confirm = document.getElementById('category-gate-confirm');
    let selected = '';

    options.innerHTML = availableCategories().map(category => `
        <label class="radio-option">
            <input type="radio" name="ensemble-category" value="${escapeHtml(category)}">
            <span>${escapeHtml(categoryLabel(category))}</span>
        </label>
    `).join('');

    gate.hidden = false;
    nameInput.focus();

    // Both answers are required before anything can be committed.
    function refreshConfirm() {
        confirm.disabled = !(selected && nameInput.value.trim());
    }

    return new Promise(resolve => {
        nameInput.addEventListener('input', refreshConfirm);

        options.querySelectorAll('input').forEach(input => {
            input.addEventListener('change', () => {
                selected = input.value;
                refreshConfirm();
            });
        });

        confirm.addEventListener('click', async () => {
            const name = nameInput.value.trim();
            if (!selected || !name) return;

            const label = categoryLabel(selected);
            if (!window.confirm(`Start as "${name}" evaluating "${label}" papers?\n\nThis is final and cannot be changed later.`)) return;

            confirm.disabled = true;
            try {
                await commitCategory(allPapers, selected, name);
            } catch (error) {
                console.error('Error saving your details:', error);
                window.alert('Could not save your details. Check that the server is running, then try again.');
                refreshConfirm();
                return;
            }

            gate.hidden = true;
            resolve();
        });
    });
}

function renderCheckboxList(elementId, items, filterKey) {
    const container = document.getElementById(elementId);
    const filterSet = filters[filterKey];

    container.innerHTML = items.map(item => `
        <label>
            <input type="checkbox" value="${escapeHtml(item)}" ${filterSet.has(item) ? 'checked' : ''}>
            ${escapeHtml(item)}
        </label>
    `).join('');

    container.querySelectorAll('input').forEach(input => {
        input.addEventListener('change', () => {
            if (input.checked) {
                filterSet.add(input.value);
            } else {
                filterSet.delete(input.value);
            }
            saveFilters();
            renderPapers();
        });
    });
}

document.getElementById('title-search').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.target.value.trim()) {
        filters.titleKeywords.add(e.target.value.trim());
        renderSelectedTitleKeywords();
        e.target.value = '';
        saveFilters();
        renderPapers();
    }
});

function renderSelectedTitleKeywords() {
    const container = document.getElementById('selected-title-keywords');
    container.innerHTML = Array.from(filters.titleKeywords).map(kw => `
        <div class="keyword-tag">
            ${escapeHtml(kw)}
            <span class="remove" data-keyword="${escapeHtml(kw)}">×</span>
        </div>
    `).join('');

    container.querySelectorAll('.remove').forEach(span => {
        span.addEventListener('click', () => {
            filters.titleKeywords.delete(span.dataset.keyword);
            renderSelectedTitleKeywords();
            saveFilters();
            renderPapers();
        });
    });
}

document.querySelectorAll('.status-filter').forEach(input => {
    input.addEventListener('change', () => {
        if (input.checked) {
            filters.statuses.add(input.value);
        } else {
            filters.statuses.delete(input.value);
        }
        saveFilters();
        renderPapers();
    });
});

function filterPapers() {
    return allPapers.filter(paper => {
        if (paper.category !== getChosenCategory()) return false;

        if (filters.titleKeywords.size > 0) {
            const matchesTitle = Array.from(filters.titleKeywords).every(kw =>
                (paper.title || '').toLowerCase().includes(kw.toLowerCase())
            );
            if (!matchesTitle) return false;
        }

        if (filters.statuses.size > 0 && !filters.statuses.has(computeStatus(paper))) {
            return false;
        }

        return true;
    });
}

function updateStatistics(papers) {
    const stats = { total: papers.length, completed: 0, in_progress: 0, not_started: 0 };

    papers.forEach(paper => {
        const status = computeStatus(paper);
        if (status === 'completed') stats.completed++;
        else if (status === 'in_progress') stats.in_progress++;
        else stats.not_started++;
    });

    document.getElementById('total-results').textContent = stats.total;
    document.getElementById('completed-count').textContent = stats.completed;
    document.getElementById('in-progress-count').textContent = stats.in_progress;
    document.getElementById('not-started-count').textContent = stats.not_started;
}

function renderPapers() {
    const filteredPapers = filterPapers();
    const container = document.getElementById('papers-list');

    updateStatistics(filteredPapers);

    if (filteredPapers.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No Papers Found</h3>
                <p>Try adjusting your filters to see more results.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = filteredPapers.map(paper => {
        const progress = calculateProgress(paper);
        const status = computeStatus(paper);
        const pretaskDone = isPretaskSubmitted(paper);

        return `
            <div class="paper-card" data-index="${allPapers.indexOf(paper)}">
                <div>
                    <h3 class="paper-title">${escapeHtml(paper.title)}</h3>
                    <ul class="paper-meta">
                        <li class="status-row">
                            ${createStatusBadge(status, progress.completed, progress.total)}
                            <span class="pretask-chip ${pretaskDone ? 'done' : 'pending'}">
                                Pre-task ${pretaskDone ? 'submitted' : 'pending'}
                            </span>
                        </li>
                        <li><strong>Category:</strong> ${escapeHtml(paperCategoryLabel(paper))}</li>
                        <li><strong>Manuscript:</strong> ${escapeHtml(paper.manuscript_id || '—')}</li>
                    </ul>
                    <details class="abstract-section">
                        <summary>Abstract</summary>
                        <p>${escapeHtml(paper.abstract || 'No abstract available')}</p>
                    </details>
                </div>
            </div>
        `;
    }).join('');

    container.querySelectorAll('.paper-card').forEach(card => {
        card.addEventListener('click', (event) => {
            // Let the abstract disclosure work without navigating away.
            if (event.target.closest('.abstract-section')) return;
            openPaper(parseInt(card.dataset.index, 10));
        });
    });
}

function openPaper(paperIndex) {
    window.location.href = `ensemble-evaluate.html?paper=${paperIndex}`;
}

function setupFilterSearch(searchId, listId) {
    const searchInput = document.getElementById(searchId);
    const list = document.getElementById(listId);

    searchInput.addEventListener('input', () => {
        const query = searchInput.value.toLowerCase();
        list.querySelectorAll('label').forEach(label => {
            label.style.display = label.textContent.toLowerCase().includes(query) ? 'block' : 'none';
        });
    });
}


function setupCollapsibleHeaders() {
    document.querySelectorAll('.filter-header.collapsible').forEach(header => {
        header.addEventListener('click', () => {
            header.classList.toggle('collapsed');
            header.nextElementSibling.classList.toggle('collapsed');
        });
    });
}

setupCollapsibleHeaders();
loadPapers();
