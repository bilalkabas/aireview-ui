// Main page JavaScript
let allPapers = [];
let filters = {
    evaluators: new Set(),
    areas: new Set(),
    keywords: new Set(),
    titleKeywords: new Set(),
    statuses: new Set()
};

// Save filters to localStorage
function saveFilters() {
    const filtersData = {
        evaluators: Array.from(filters.evaluators),
        areas: Array.from(filters.areas),
        keywords: Array.from(filters.keywords),
        titleKeywords: Array.from(filters.titleKeywords),
        statuses: Array.from(filters.statuses)
    };
    localStorage.setItem('reviewFilters', JSON.stringify(filtersData));
}

// Load filters from localStorage
function loadSavedFilters() {
    const saved = localStorage.getItem('reviewFilters');
    if (saved) {
        try {
            const filtersData = JSON.parse(saved);
            filters.evaluators = new Set(filtersData.evaluators || []);
            filters.areas = new Set(filtersData.areas || []);
            filters.keywords = new Set(filtersData.keywords || []);
            filters.titleKeywords = new Set(filtersData.titleKeywords || []);
            filters.statuses = new Set(filtersData.statuses || []);
            console.log('Loaded filters from localStorage:', filtersData);
        } catch (e) {
            console.error('Error loading filters:', e);
        }
    }
}

// Load papers data
async function loadPapers() {
    try {
        const response = await fetch('/reviews/evaluation-data-all-venues.json');
        allPapers = await response.json();
        loadSavedFilters();
        initializeFilters();
        renderPapers();
    } catch (error) {
        console.error('Error loading papers:', error);
        document.getElementById('papers-list').innerHTML = `
            <div class="empty-state">
                <h3>Error Loading Papers</h3>
                <p>Could not load evaluation data. Please make sure the file exists.</p>
            </div>
        `;
    }
}

// Initialize filter options
function initializeFilters() {
    const evaluators = new Set();
    const areas = new Set();
    const keywords = new Set();

    allPapers.forEach(paper => {
        paper.evaluators.forEach(e => evaluators.add(e));
        paper.primary_area.forEach(a => areas.add(a));
        paper.keywords.forEach(k => keywords.add(k));
    });

    renderCheckboxList('evaluator-list', Array.from(evaluators).sort(), 'evaluator');
    renderCheckboxList('area-list', Array.from(areas).sort(), 'area');
    renderCheckboxList('keyword-list', Array.from(keywords).sort(), 'keyword');

    // Restore status checkboxes
    document.querySelectorAll('.status-filter').forEach(input => {
        if (filters.statuses.has(input.value)) {
            input.checked = true;
        }
    });

    // Restore keyword tags
    renderSelectedKeywords();
    renderSelectedTitleKeywords();
}

// Render checkbox list
function renderCheckboxList(elementId, items, type) {
    const container = document.getElementById(elementId);
    const filterSet = filters[type + 's'];

    container.innerHTML = items.map(item => `
        <label>
            <input type="checkbox" class="${type}-filter" value="${item}" ${filterSet.has(item) ? 'checked' : ''}>
            ${item}
        </label>
    `).join('');

    // Add event listeners
    container.querySelectorAll('input').forEach(input => {
        input.addEventListener('change', () => {
            if (input.checked) {
                filters[type + 's'].add(input.value);
            } else {
                filters[type + 's'].delete(input.value);
            }
            saveFilters();
            renderPapers();
        });
    });
}

// Handle keyword search
document.getElementById('keyword-search').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.target.value.trim()) {
        const keyword = e.target.value.trim();
        filters.keywords.add(keyword);
        renderSelectedKeywords();
        e.target.value = '';
        saveFilters();
        renderPapers();
    }
});

// Handle title search
document.getElementById('title-search').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.target.value.trim()) {
        const keyword = e.target.value.trim();
        filters.titleKeywords.add(keyword);
        renderSelectedTitleKeywords();
        e.target.value = '';
        saveFilters();
        renderPapers();
    }
});

// Render selected keywords
function renderSelectedKeywords() {
    const container = document.getElementById('selected-keywords');
    container.innerHTML = Array.from(filters.keywords).map(kw => `
        <div class="keyword-tag">
            ${kw}
            <span class="remove" onclick="removeKeyword('${kw}')">×</span>
        </div>
    `).join('');
}

// Render selected title keywords
function renderSelectedTitleKeywords() {
    const container = document.getElementById('selected-title-keywords');
    container.innerHTML = Array.from(filters.titleKeywords).map(kw => `
        <div class="keyword-tag">
            ${kw}
            <span class="remove" onclick="removeTitleKeyword('${kw}')">×</span>
        </div>
    `).join('');
}

// Remove keyword
function removeKeyword(keyword) {
    filters.keywords.delete(keyword);
    renderSelectedKeywords();
    saveFilters();
    renderPapers();
}

// Remove title keyword
function removeTitleKeyword(keyword) {
    filters.titleKeywords.delete(keyword);
    renderSelectedTitleKeywords();
    saveFilters();
    renderPapers();
}

// Status filters
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

// Filter papers
function filterPapers() {
    return allPapers.filter(paper => {
        // Evaluator filter
        if (filters.evaluators.size > 0) {
            const hasEvaluator = paper.evaluators.some(e => filters.evaluators.has(e));
            if (!hasEvaluator) return false;
        }

        // Area filter
        if (filters.areas.size > 0) {
            const hasArea = paper.primary_area.some(a => filters.areas.has(a));
            if (!hasArea) return false;
        }

        // Keyword filter
        if (filters.keywords.size > 0) {
            const hasKeyword = Array.from(filters.keywords).every(kw =>
                paper.keywords.some(k => k.toLowerCase().includes(kw.toLowerCase()))
            );
            if (!hasKeyword) return false;
        }

        // Title search
        if (filters.titleKeywords.size > 0) {
            const hasTitle = Array.from(filters.titleKeywords).every(kw =>
                paper.title.toLowerCase().includes(kw.toLowerCase())
            );
            if (!hasTitle) return false;
        }

        // Status filter
        if (filters.statuses.size > 0) {
            if (!filters.statuses.has(paper.status)) return false;
        }

        return true;
    });
}

// Calculate paper progress
function calculateProgress(paper) {
    if (!paper.reviews || paper.reviews.length === 0) return { completed: 0, total: 0 };

    let completed = 0;
    paper.reviews.forEach(review => {
        const metrics = review.metrics;
        const hasSource = metrics.source && (metrics.source === 'ai' || metrics.source === 'human' || metrics.source === '1' || metrics.source === '2');
        const hasAllMetrics = metrics.coverage > 0 && metrics.specificity > 0 &&
                             metrics.correctness > 0 && metrics.constructiveness > 0 &&
                             metrics.stance > 0 && hasSource;
        if (hasAllMetrics) completed++;
    });

    return { completed, total: paper.reviews.length };
}

// Create status badge HTML with circular progress
function createStatusBadge(status, completed, total) {
    const percentage = total > 0 ? (completed / total) * 100 : 0;
    const circumference = 2 * Math.PI * 8; // radius = 8
    const offset = circumference - (percentage / 100) * circumference;

    const statusLabel = status.replace('_', ' ');
    const statusText = status === 'not_started'
        ? statusLabel
        : `${statusLabel} (${completed} of ${total} reviews completed)`;

    return `
        <span class="status-badge status-${status}">
            <span class="status-circle">
                <svg viewBox="0 0 20 20">
                    <circle class="status-circle-bg" cx="10" cy="10" r="8"></circle>
                    <circle class="status-circle-progress" cx="10" cy="10" r="8"
                            stroke-dasharray="${circumference}"
                            stroke-dashoffset="${offset}"></circle>
                </svg>
            </span>
            <span>${statusText}</span>
        </span>
    `;
}

// Update statistics bar
function updateStatistics(papers) {
    const stats = {
        total: papers.length,
        completed: 0,
        in_progress: 0,
        not_started: 0
    };

    papers.forEach(paper => {
        if (paper.status === 'completed') {
            stats.completed++;
        } else if (paper.status === 'in_progress') {
            stats.in_progress++;
        } else {
            stats.not_started++;
        }
    });

    document.getElementById('total-results').textContent = stats.total;
    document.getElementById('completed-count').textContent = stats.completed;
    document.getElementById('in-progress-count').textContent = stats.in_progress;
    document.getElementById('not-started-count').textContent = stats.not_started;
}

// Render papers
function renderPapers() {
    const filteredPapers = filterPapers();
    const container = document.getElementById('papers-list');

    // Update statistics
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

    container.innerHTML = filteredPapers.map((paper, index) => {
        const progress = calculateProgress(paper);

        return `
            <div class="paper-card" onclick="openPaper(${allPapers.indexOf(paper)})">
                <div>
                    <h3 class="paper-title">${paper.title}</h3>
                    <ul class="paper-meta">
                        <li>${createStatusBadge(paper.status, progress.completed, progress.total)}</li>
                        <li><strong>Evaluators:</strong> ${paper.evaluators.join(', ')}</li>
                        <li><strong>Research areas:</strong> ${paper.primary_area.join(', ')}</li>
                    </ul>
                    <details class="abstract-section" onclick="event.stopPropagation()">
                        <summary>Abstract</summary>
                        <p>${paper.abstract || 'No abstract available'}</p>
                    </details>
                </div>
            </div>
        `;
    }).join('');
}

// Open paper evaluation page
function openPaper(paperIndex) {
    window.location.href = `evaluate.html?paper=${paperIndex}`;
}

// Initialize filter search functionality
function setupFilterSearch(searchId, listId) {
    const searchInput = document.getElementById(searchId);
    const list = document.getElementById(listId);

    searchInput.addEventListener('input', () => {
        const query = searchInput.value.toLowerCase();
        const labels = list.querySelectorAll('label');

        labels.forEach(label => {
            const text = label.textContent.toLowerCase();
            label.style.display = text.includes(query) ? 'block' : 'none';
        });
    });
}

// Setup filter searches
setupFilterSearch('evaluator-search', 'evaluator-list');
setupFilterSearch('area-search', 'area-list');

// Setup collapsible filter headers
function setupCollapsibleHeaders() {
    document.querySelectorAll('.filter-header.collapsible').forEach(header => {
        header.addEventListener('click', () => {
            const content = header.nextElementSibling;

            // Toggle collapsed class
            header.classList.toggle('collapsed');
            content.classList.toggle('collapsed');
        });
    });
}

// Initialize collapsible headers
setupCollapsibleHeaders();

// Load papers on page load
loadPapers();
