// Ensemble phase — evaluation page (Stage 1 pre-task + Stage 2 review evaluation)
let currentPaper = null;
let currentPaperIndex = -1;
let allPapers = [];
let filteredPaperIndices = [];
let currentFilteredIndex = -1;
let appConfig = null;
let activeTab = 'pretask';
const saveTimeouts = {};

// ---------------------------------------------------------------- config / data

async function loadConfig() {
    try {
        const response = await fetch('/config');
        appConfig = await response.json();
    } catch (error) {
        console.error('Error loading config:', error);
        appConfig = { showReviewerType: false, shuffleReviews: false, shuffleSeed: 42 };
    }
}

function loadFilters() {
    const saved = localStorage.getItem('ensembleReviewFilters');
    if (!saved) return null;
    try {
        const data = JSON.parse(saved);
        return {
            titleKeywords: new Set(data.titleKeywords || []),
            statuses: new Set(data.statuses || [])
        };
    } catch (e) {
        console.error('Error loading filters:', e);
        return null;
    }
}

// Keep paper-to-paper navigation in sync with the filters used on the list page.
function getFilteredPapers() {
    const filters = loadFilters();
    const category = getChosenCategory();

    const indices = [];
    allPapers.forEach((paper, index) => {
        // Evaluation is confined to the category the evaluator committed to.
        if (paper.category !== category) return;
        if (!filters) {
            indices.push(index);
            return;
        }

        if (filters.titleKeywords.size > 0) {
            const matchesTitle = Array.from(filters.titleKeywords).every(kw =>
                (paper.title || '').toLowerCase().includes(kw.toLowerCase())
            );
            if (!matchesTitle) return;
        }

        if (filters.statuses.size > 0 && !filters.statuses.has(computeStatus(paper))) return;

        indices.push(index);
    });

    return indices;
}

async function loadPapers() {
    try {
        await loadConfig();
        allPapers = await loadEnsemblePapers();
        syncCategoryFromPapers(allPapers);

        // The category is chosen on the list page and gates every evaluation.
        if (!getChosenCategory()) {
            window.location.replace('ensemble.html');
            return;
        }

        filteredPaperIndices = getFilteredPapers();

        const params = new URLSearchParams(window.location.search);
        currentPaperIndex = parseInt(params.get('paper'), 10);

        if (!(currentPaperIndex >= 0 && currentPaperIndex < allPapers.length)) {
            document.getElementById('paper-title').textContent = 'Paper not found';
            return;
        }

        if (allPapers[currentPaperIndex].category !== getChosenCategory()) {
            window.location.replace('ensemble.html');
            return;
        }

        currentPaper = allPapers[currentPaperIndex];
        currentFilteredIndex = filteredPaperIndices.indexOf(currentPaperIndex);

        renderPaper();
        setupResizer();
        updateNavigationButtons();
    } catch (error) {
        console.error('Error loading paper:', error);
        document.getElementById('paper-title').textContent = error.message || 'Error loading paper';
    }
}

async function persist() {
    currentPaper.status = computeStatus(currentPaper);
    allPapers[currentPaperIndex] = currentPaper;
    await saveEnsemblePapers(allPapers);
}

function scheduleSave(key) {
    if (saveTimeouts[key]) clearTimeout(saveTimeouts[key]);
    saveTimeouts[key] = setTimeout(async () => {
        saveTimeouts[key] = null;
        await persist();
    }, 600);
}

async function flushSave(key) {
    if (saveTimeouts[key]) {
        clearTimeout(saveTimeouts[key]);
        saveTimeouts[key] = null;
    }
    await persist();
}

// ---------------------------------------------------------------- page rendering

function renderPaper() {
    document.getElementById('paper-title').textContent = currentPaper.title;
    document.getElementById('paper-category').textContent = paperCategoryLabel(currentPaper);
    document.getElementById('paper-manuscript').textContent = currentPaper.manuscript_id || '—';
    document.getElementById('paper-abstract').textContent = currentPaper.abstract || 'No abstract available';

    if (currentPaper.url) setupPDFViewer(currentPaper.url);

    renderPretask();
    renderReviews();
    updateStatusDisplay();

    // Land on the stage the evaluator still has to work on.
    activateTab(isPretaskSubmitted(currentPaper) ? 'reviews' : 'pretask');
}

function updateStatusDisplay() {
    const progress = calculateProgress(currentPaper);
    const status = computeStatus(currentPaper);
    currentPaper.status = status;
    document.getElementById('paper-status').innerHTML =
        createStatusBadge(status, progress.completed, progress.total);

    const submitted = isPretaskSubmitted(currentPaper);
    document.getElementById('tab-pretask-state').textContent = submitted ? 'submitted' : 'required';
    document.getElementById('tab-reviews-state').textContent = submitted
        ? `${(currentPaper.reviews || []).filter(isReviewComplete).length} / ${(currentPaper.reviews || []).length} rated`
        : 'locked';
    document.getElementById('tab-reviews').classList.toggle('is-locked', !submitted);
}

function activateTab(tab) {
    closeAllTooltips();
    activeTab = tab;
    document.querySelectorAll('.stage-tab').forEach(button => {
        const isActive = button.dataset.tab === tab;
        button.classList.toggle('active', isActive);
        button.setAttribute('aria-selected', String(isActive));
    });
    document.getElementById('panel-pretask').classList.toggle('active', tab === 'pretask');
    document.getElementById('panel-reviews').classList.toggle('active', tab === 'reviews');
    document.getElementById('paper-panel').scrollTop = 0;

    // Measured once the panel is visible, so hidden elements don't report zero height.
    syncStageTabsOffset();
}

document.querySelectorAll('.stage-tab').forEach(button => {
    button.addEventListener('click', () => activateTab(button.dataset.tab));
});

// The tab bar is sticky; publish its height so sticky children can offset below it.
function syncStageTabsOffset() {
    const tabs = document.querySelector('.stage-tabs');
    if (!tabs) return;
    const height = Math.round(tabs.getBoundingClientRect().height);
    document.documentElement.style.setProperty('--stage-tabs-offset', `${height}px`);

    const reviewHeader = document.querySelector('#panel-reviews .review-header');
    if (reviewHeader) {
        const headerHeight = Math.round(reviewHeader.getBoundingClientRect().height);
        document.documentElement.style.setProperty('--review-header-offset', `${headerHeight}px`);
    }
}

window.addEventListener('resize', syncStageTabsOffset);

document.getElementById('go-to-pretask-btn').addEventListener('click', () => activateTab('pretask'));

// ---------------------------------------------------------------- shared widgets

function renderLikert(scaleId, value, options = {}) {
    const { disabled = false, lowLabel = '', highLabel = '' } = options;
    const buttons = [];
    for (let i = 1; i <= LIKERT_MAX; i++) {
        buttons.push(`
            <button type="button" class="likert-btn ${i === value ? 'selected' : ''}"
                    data-value="${i}" ${disabled ? 'disabled' : ''}>${i}</button>
        `);
    }
    // The end labels are only worth the space when they say more than the button numbers do.
    const caption = (lowLabel || highLabel)
        ? `<div class="likert-caption"><span>${escapeHtml(lowLabel)}</span><span>${escapeHtml(highLabel)}</span></div>`
        : '';
    return `
        <div class="likert" data-scale="${escapeHtml(scaleId)}">
            <div class="likert-buttons">${buttons.join('')}</div>
            ${caption}
        </div>
    `;
}

function tooltipMarkup(text) {
    return `<span class="info-icon">i</span><span class="tooltiptext">${escapeHtml(text)}</span>`;
}

// ---------------------------------------------------------------- stage 1: pre-task

function renderPretask() {
    closeAllTooltips();
    const pretask = getPretask(currentPaper);
    const locked = pretask.submitted;
    const form = document.getElementById('pretask-form');
    const actions = document.getElementById('pretask-actions');

    const recommendationOptions = RECOMMENDATION_OPTIONS.map(option => `
        <label class="radio-option ${pretask.recommendation === option.value ? 'selected' : ''}">
            <input type="radio" name="provisional-recommendation" value="${option.value}"
                   ${pretask.recommendation === option.value ? 'checked' : ''} ${locked ? 'disabled' : ''}>
            <span>${escapeHtml(option.label)}</span>
        </label>
    `).join('');

    const textList = (field, placeholderPrefix) => pretask[field].map((text, idx) => `
        <textarea class="pretask-text" data-field="${field}" data-index="${idx}" rows="2"
                  placeholder="${escapeHtml(`${placeholderPrefix} ${idx + 1}${idx === 0 ? '' : ' (optional)'}`)}"
                  ${locked ? 'disabled' : ''}>${escapeHtml(text)}</textarea>
    `).join('');

    form.innerHTML = `
        ${locked ? `
            <div class="locked-banner">
                <strong>Pre-task submitted${pretask.submitted_at ? ` on ${escapeHtml(new Date(pretask.submitted_at).toLocaleString())}` : ''}.</strong>
                These answers are read-only.
            </div>
        ` : ''}

        <div class="pretask-block ${locked ? 'locked' : ''}">
            <h4 class="pretask-question">1. Provisional recommendation</h4>
            <div class="radio-group" id="recommendation-group">${recommendationOptions}</div>
        </div>

        <div class="pretask-block ${locked ? 'locked' : ''}">
            <h4 class="pretask-question tooltip">
                2. Confidence in that recommendation
                ${tooltipMarkup(CONFIDENCE_TOOLTIP)}
            </h4>
            ${renderLikert('confidence', pretask.confidence, {
                disabled: locked,
                lowLabel: '1 — Not at all confident',
                highLabel: 'Extremely confident — 7'
            })}
        </div>

        <div class="pretask-block ${locked ? 'locked' : ''}">
            <h4 class="pretask-question">3. Major concerns <span class="pretask-hint">(up to three; at least one required)</span></h4>
            <div class="pretask-fields">${textList('concerns', 'Concern')}</div>
        </div>

        <div class="pretask-block ${locked ? 'locked' : ''}">
            <h4 class="pretask-question">4. Major strengths <span class="pretask-hint">(up to three)</span></h4>
            <div class="pretask-fields">${textList('strengths', 'Strength')}</div>
        </div>
    `;

    if (locked) {
        actions.innerHTML = `
            <div class="pretask-actions locked">
                <span class="pretask-locked-note">Submitted — the reviews are unlocked in the Review Evaluation tab.</span>
                <button type="button" class="primary-button" id="go-to-reviews-btn">Go to Review Evaluation →</button>
            </div>
        `;
        document.getElementById('go-to-reviews-btn').addEventListener('click', () => activateTab('reviews'));
    } else {
        actions.innerHTML = `
            <div class="pretask-actions">
                <div class="pretask-warning">
                    <strong>Heads up:</strong> submitting locks these answers. You will still be able to read them,
                    but you cannot edit them afterwards. The AI and human reviews unlock as soon as you submit.
                </div>
                <div class="pretask-submit-row">
                    <button type="button" class="primary-button" id="pretask-submit-btn">Submit Pre-task</button>
                    <span class="pretask-missing" id="pretask-missing"></span>
                </div>
            </div>
        `;
        document.getElementById('pretask-submit-btn').addEventListener('click', submitPretask);
        setupPretaskInputs();
        updateSubmitState();
    }

    setupTooltips();
}

function setupPretaskInputs() {
    const pretask = getPretask(currentPaper);

    document.querySelectorAll('#recommendation-group input[type="radio"]').forEach(input => {
        input.addEventListener('change', async () => {
            pretask.recommendation = input.value;
            document.querySelectorAll('#recommendation-group .radio-option').forEach(label => {
                label.classList.toggle('selected', label.contains(input));
            });
            updateSubmitState();
            updateStatusDisplay();
            await flushSave('pretask');
        });
    });

    const confidenceScale = document.querySelector('.likert[data-scale="confidence"]');
    if (confidenceScale) {
        confidenceScale.querySelectorAll('.likert-btn').forEach(button => {
            button.addEventListener('click', async () => {
                const value = parseInt(button.dataset.value, 10);
                pretask.confidence = value;
                confidenceScale.querySelectorAll('.likert-btn').forEach(btn => {
                    btn.classList.toggle('selected', parseInt(btn.dataset.value, 10) === value);
                });
                updateSubmitState();
                updateStatusDisplay();
                await flushSave('pretask');
            });
        });
    }

    document.querySelectorAll('.pretask-text').forEach(textarea => {
        const field = textarea.dataset.field;
        const index = parseInt(textarea.dataset.index, 10);

        textarea.addEventListener('input', () => {
            pretask[field][index] = textarea.value;
            updateSubmitState();
            scheduleSave('pretask');
        });

        textarea.addEventListener('blur', async () => {
            pretask[field][index] = textarea.value;
            updateStatusDisplay();
            await flushSave('pretask');
        });
    });
}

function updateSubmitState() {
    const missingLabel = document.getElementById('pretask-missing');
    const submitButton = document.getElementById('pretask-submit-btn');
    if (!missingLabel || !submitButton) return;

    const missing = getPretaskMissingFields(getPretask(currentPaper));
    submitButton.disabled = missing.length > 0;
    missingLabel.textContent = missing.length ? `Still needed: ${missing.join(', ')}.` : '';
}

async function submitPretask() {
    const pretask = getPretask(currentPaper);
    if (getPretaskMissingFields(pretask).length > 0) return;

    const confirmed = confirm(
        'Submit your pre-task?\n\n' +
        'Your answers will be locked and cannot be edited afterwards, and the reviews will be unlocked.'
    );
    if (!confirmed) return;

    pretask.submitted = true;
    pretask.submitted_at = new Date().toISOString();

    await flushSave('pretask');

    renderPretask();
    renderReviews();
    updateStatusDisplay();
    activateTab('reviews');
}

// ---------------------------------------------------------------- stage 2: reviews

function seededRandom(seed) {
    let state = seed;
    return function () {
        state = (state * 1103515245 + 12345) & 0x7fffffff;
        return state / 0x7fffffff;
    };
}

function shuffleWithSeed(array, seed) {
    const rng = seededRandom(seed);
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

function renderReviews() {
    closeAllTooltips();
    const lock = document.getElementById('reviews-lock');
    const section = document.getElementById('reviews-section');
    const container = document.getElementById('reviews-list');

    // Review text is only put in the DOM once the pre-task has been submitted.
    if (!isPretaskSubmitted(currentPaper)) {
        container.innerHTML = '';
        section.hidden = true;
        lock.hidden = false;
        return;
    }

    lock.hidden = true;
    section.hidden = false;

    const reviews = currentPaper.reviews || [];
    if (reviews.length === 0) {
        container.innerHTML = '<p>No reviews available</p>';
        return;
    }

    // Present reviews in a per-paper shuffled order, but always store ratings
    // against the review's original index in the data file.
    let ordered = reviews.map((review, originalIndex) => ({ review, originalIndex }));
    if (appConfig && appConfig.shuffleReviews) {
        ordered = shuffleWithSeed(ordered, appConfig.shuffleSeed + currentPaperIndex);
    }

    container.innerHTML = ordered.map(({ review, originalIndex }, displayIndex) => {
        const html = review.text ? marked.parse(review.text) : 'No review text available';
        const reviewerType = (appConfig && appConfig.showReviewerType && review.reviewer)
            ? ` [${escapeHtml(review.reviewer)}]`
            : '';

        return `
        <details class="review-item" open data-review-index="${originalIndex}">
            <summary class="review-header">
                <span>Review #${displayIndex + 1}${reviewerType}</span>
            </summary>
            <div class="review-content">
                <div class="review-text">${html}</div>
                <div class="metrics-sidebar ensemble-metrics ${metricsCollapsed ? 'collapsed' : ''}">
                    <button type="button" class="metrics-toggle" title="${metricsCollapsed ? 'Show ratings' : 'Hide ratings'}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="9 18 15 12 9 6"></polyline>
                        </svg>
                        <span class="metrics-toggle-badge">${ratedCount(originalIndex)}/${ENSEMBLE_METRICS.length}</span>
                    </button>
                    <div class="metrics-body">
                        ${ENSEMBLE_METRICS.map(metric => renderMetric(metric, originalIndex)).join('')}
                        ${renderCommentField(originalIndex)}
                    </div>
                </div>
            </div>
        </details>
        `;
    }).join('');

    setupStarMetrics();
    setupCommentInputs();
    setupClearEvaluationButtons();
    setupMetricsToggles();
    setupTooltips();
}

// Collapsing the sidebar hands its width back to the review text; the choice is
// remembered so it applies to every review and every paper.
const METRICS_COLLAPSED_KEY = 'ensembleMetricsCollapsed';
let metricsCollapsed = localStorage.getItem(METRICS_COLLAPSED_KEY) === 'true';

function ratedCount(reviewIndex) {
    const metrics = (currentPaper.reviews[reviewIndex] || {}).metrics || {};
    return ENSEMBLE_METRICS.filter(metric => metrics[metric.key] > 0).length;
}

function setMetricsCollapsed(collapsed) {
    metricsCollapsed = collapsed;
    localStorage.setItem(METRICS_COLLAPSED_KEY, String(collapsed));
    closeAllTooltips();

    document.querySelectorAll('#panel-reviews .metrics-sidebar').forEach(sidebar => {
        sidebar.classList.toggle('collapsed', collapsed);
        const toggle = sidebar.querySelector('.metrics-toggle');
        if (toggle) toggle.title = collapsed ? 'Show ratings' : 'Hide ratings';
    });
}

function setupMetricsToggles() {
    document.querySelectorAll('.metrics-toggle').forEach(button => {
        button.addEventListener('click', (e) => {
            e.stopPropagation();
            setMetricsCollapsed(!metricsCollapsed);
        });
    });
}

function refreshMetricsBadges() {
    document.querySelectorAll('#panel-reviews .review-item').forEach(item => {
        const reviewIndex = parseInt(item.dataset.reviewIndex, 10);
        const badge = item.querySelector('.metrics-toggle-badge');
        if (badge) badge.textContent = `${ratedCount(reviewIndex)}/${ENSEMBLE_METRICS.length}`;
    });
}

function renderMetric(metric, reviewIndex) {
    const value = currentPaper.reviews[reviewIndex].metrics[metric.key] || 0;
    const tooltip = `${metric.question}\n\n${metric.anchors.join('\n')}`;

    return `
        <div class="metric-row">
            <div class="metric-label tooltip">
                ${escapeHtml(metric.label)}
                ${tooltipMarkup(tooltip)}
            </div>
            <div class="metric-stars" data-metric="${metric.key}" data-review="${reviewIndex}">
                ${Array.from({ length: LIKERT_MAX }, (_, i) => `
                    <span class="star ${i + 1 <= value ? 'filled' : ''}" data-value="${i + 1}">★</span>
                `).join('')}
            </div>
        </div>
    `;
}

function renderCommentField(reviewIndex) {
    return `
        <div class="metric-row comment-row">
            <div class="metric-label">Comment</div>
            <textarea class="metric-comment" data-review="${reviewIndex}" placeholder="Auto saved as you type."></textarea>
        </div>
        <div>
            <button type="button" class="clear-evaluation-btn" data-review="${reviewIndex}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                </svg>
                Clear Evaluation
            </button>
        </div>
    `;
}

function setupStarMetrics() {
    document.querySelectorAll('.metric-stars').forEach(container => {
        const metricKey = container.dataset.metric;
        const reviewIndex = parseInt(container.dataset.review, 10);
        const stars = container.querySelectorAll('.star');

        stars.forEach(star => {
            const value = parseInt(star.dataset.value, 10);

            star.addEventListener('mouseenter', () => {
                stars.forEach((s, i) => s.classList.toggle('hovered', i < value));
            });

            star.addEventListener('click', async () => {
                currentPaper.reviews[reviewIndex].metrics[metricKey] = value;
                stars.forEach((s, i) => {
                    s.classList.toggle('filled', i < value);
                    s.classList.remove('hovered');
                });
                updateStatusDisplay();
                refreshMetricsBadges();
                await persist();
            });
        });

        container.addEventListener('mouseleave', () => {
            stars.forEach(s => s.classList.remove('hovered'));
        });
    });
}

function setupCommentInputs() {
    document.querySelectorAll('.metric-comment').forEach(textarea => {
        const reviewIndex = parseInt(textarea.dataset.review, 10);
        const review = currentPaper.reviews[reviewIndex];
        if (!review) return;

        const metrics = review.metrics || (review.metrics = {});
        textarea.value = metrics.comment || '';

        textarea.addEventListener('input', () => {
            metrics.comment = textarea.value;
            scheduleSave(`comment-${reviewIndex}`);
        });

        textarea.addEventListener('blur', async () => {
            metrics.comment = textarea.value;
            await flushSave(`comment-${reviewIndex}`);
        });
    });
}

function setupClearEvaluationButtons() {
    document.querySelectorAll('.clear-evaluation-btn').forEach(button => {
        const reviewIndex = parseInt(button.dataset.review, 10);
        if (!currentPaper.reviews[reviewIndex]) return;

        button.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to clear all evaluation data for this review?')) return;

            const metrics = currentPaper.reviews[reviewIndex].metrics || {};
            ENSEMBLE_METRICS.forEach(metric => { metrics[metric.key] = 0; });
            metrics.comment = '';

            await persist();
            renderReviews();
            updateStatusDisplay();
        });
    });
}

function toggleAllReviews() {
    const reviewItems = document.querySelectorAll('.review-item');
    const toggleBtn = document.getElementById('toggle-all-reviews');
    const toggleText = toggleBtn.querySelector('span');
    const toggleIcon = toggleBtn.querySelector('svg polyline');

    if (reviewItems.length === 0) return;

    const anyOpen = Array.from(reviewItems).some(item => item.open);
    reviewItems.forEach(item => { item.open = !anyOpen; });

    toggleText.textContent = anyOpen ? 'Expand All' : 'Collapse All';
    toggleBtn.title = anyOpen ? 'Expand all reviews' : 'Collapse all reviews';
    toggleIcon.setAttribute('points', anyOpen ? '9 18 15 12 9 6' : '6 9 12 15 18 9');
}

document.getElementById('toggle-all-reviews').addEventListener('click', toggleAllReviews);

// ---------------------------------------------------------------- tooltips

// Tooltips are moved to <body> while open: the metrics sidebar is its own stacking
// context (sticky + z-index), so a tooltip left inside it paints beneath the sticky
// review header no matter how high its own z-index is.
const openTooltips = [];

function closeAllTooltips() {
    while (openTooltips.length) {
        const { host, text } = openTooltips.pop();
        text.classList.remove('visible');
        text.classList.remove('below');
        host.appendChild(text);
    }
    document.querySelectorAll('.tooltiptext.visible').forEach(tt => tt.classList.remove('visible'));
}

function positionTooltip(host, text) {
    const rect = host.getBoundingClientRect();
    const margin = 8;
    const width = text.offsetWidth;
    const height = text.offsetHeight;

    // Keep the box inside the viewport rather than letting it run off the edge.
    const half = width / 2;
    const centre = Math.min(
        Math.max(rect.left + rect.width / 2, margin + half),
        Math.max(window.innerWidth - margin - half, margin + half)
    );

    // Flip below the icon when there is not enough room above it.
    const below = rect.top - 10 - height < margin;
    text.classList.toggle('below', below);
    text.style.left = `${centre}px`;
    text.style.top = below ? `${rect.bottom + 10}px` : `${rect.top - 10}px`;
    text.style.transform = below ? 'translate(-50%, 0)' : 'translate(-50%, -100%)';
}

function setupTooltips() {
    document.querySelectorAll('.tooltip').forEach(tooltip => {
        if (tooltip.dataset.tooltipReady === 'true') return;
        tooltip.dataset.tooltipReady = 'true';

        const tooltipText = tooltip.querySelector('.tooltiptext');
        if (!tooltipText) return;

        tooltip.addEventListener('click', (e) => {
            e.stopPropagation();

            const willOpen = !tooltipText.classList.contains('visible');
            closeAllTooltips();
            if (!willOpen) return;

            document.body.appendChild(tooltipText);
            openTooltips.push({ host: tooltip, text: tooltipText });
            tooltipText.classList.add('visible');
            positionTooltip(tooltip, tooltipText);
        });
    });
}

document.addEventListener('click', closeAllTooltips);
window.addEventListener('resize', closeAllTooltips);
// A sticky sidebar moves under the cursor while the page scrolls, so drop the tooltip.
document.addEventListener('scroll', closeAllTooltips, true);

// ---------------------------------------------------------------- PDF viewer

function resolvePdfUrl(url) {
    const clean = (url || '').trim();
    if (!clean) return '';
    if (/^https?:\/\//i.test(clean)) return `/pdf-proxy?url=${encodeURIComponent(clean)}`;
    if (clean.startsWith('/pdfs/')) return clean;
    if (clean.startsWith('pdfs/')) return `/${clean}`;
    // Ensemble URLs are relative to the PDF root, e.g. "AI4TMI_pdfs/TMI-2025-2235.pdf"
    return `/pdfs/${clean.replace(/^\/+/, '')}`;
}

function setupPDFViewer(pdfUrl) {
    const pdfViewer = document.getElementById('pdf-viewer');
    const pdfLinkIcon = document.getElementById('pdf-link-icon');
    const pdfFallback = document.getElementById('pdf-fallback');
    const pdfFallbackLink = document.getElementById('pdf-fallback-link');

    const viewUrl = resolvePdfUrl(pdfUrl);
    pdfLinkIcon.href = viewUrl;
    pdfFallbackLink.href = viewUrl;

    pdfViewer.style.display = '';
    pdfFallback.style.display = 'none';
    pdfViewer.src = `${viewUrl}#view=FitH&navpanes=0&toolbar=1`;

    pdfViewer.onerror = () => {
        pdfViewer.style.display = 'none';
        pdfFallback.style.display = 'flex';
    };
}

// ---------------------------------------------------------------- navigation

function updateNavigationButtons() {
    const prevBtn = document.getElementById('prev-paper-btn');
    const nextBtn = document.getElementById('next-paper-btn');
    const positionSpan = document.getElementById('paper-position');

    positionSpan.textContent = currentFilteredIndex >= 0
        ? `${currentFilteredIndex + 1} / ${filteredPaperIndices.length}`
        : '1 / 1';

    prevBtn.disabled = currentFilteredIndex <= 0;
    nextBtn.disabled = currentFilteredIndex >= filteredPaperIndices.length - 1;
}

function navigateToPaper(paperIndex) {
    const pdfViewer = document.getElementById('pdf-viewer');
    if (pdfViewer) pdfViewer.src = 'about:blank';
    window.location.href = `ensemble-evaluate.html?paper=${paperIndex}`;
}

function navigateToPreviousPaper() {
    if (currentFilteredIndex > 0) navigateToPaper(filteredPaperIndices[currentFilteredIndex - 1]);
}

function navigateToNextPaper() {
    if (currentFilteredIndex < filteredPaperIndices.length - 1) {
        navigateToPaper(filteredPaperIndices[currentFilteredIndex + 1]);
    }
}

document.getElementById('prev-paper-btn').addEventListener('click', navigateToPreviousPaper);
document.getElementById('next-paper-btn').addEventListener('click', navigateToNextPaper);

document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    const activeElement = document.activeElement;
    if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) return;

    if (e.key === 'ArrowLeft' || e.key === 'p') {
        e.preventDefault();
        navigateToPreviousPaper();
    }
    if (e.key === 'ArrowRight' || e.key === 'n') {
        e.preventDefault();
        navigateToNextPaper();
    }
});

document.getElementById('back-button').addEventListener('click', (e) => {
    e.preventDefault();
    const pdfViewer = document.getElementById('pdf-viewer');
    if (pdfViewer) pdfViewer.remove();
    window.stop();
    window.location.href = 'ensemble.html';
});

window.addEventListener('beforeunload', () => {
    const pdfViewer = document.getElementById('pdf-viewer');
    if (pdfViewer) pdfViewer.src = 'about:blank';
});

// ---------------------------------------------------------------- panel resizer

function loadSavedPanelWidth() {
    const savedWidth = localStorage.getItem('panelWidth');
    if (!savedWidth) return;
    const percentage = parseFloat(savedWidth);
    if (percentage >= 30 && percentage <= 70) {
        document.getElementById('paper-panel').style.flex = `0 0 ${percentage}%`;
        document.getElementById('pdf-panel').style.flex = `0 0 ${100 - percentage}%`;
    }
}

function setupResizer() {
    const resizer = document.getElementById('resizer');
    const paperPanel = document.getElementById('paper-panel');
    const pdfPanel = document.getElementById('pdf-panel');
    const container = document.querySelector('.evaluation-content');
    let isResizing = false;
    let startX = 0;
    let startPaperWidth = 0;

    loadSavedPanelWidth();

    resizer.addEventListener('mousedown', (e) => {
        e.preventDefault();
        isResizing = true;
        startX = e.clientX;
        startPaperWidth = paperPanel.getBoundingClientRect().width;
        document.body.classList.add('resizing');
        resizer.classList.add('resizing');
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        e.preventDefault();

        const containerWidth = container.getBoundingClientRect().width;
        const newPercentage = ((startPaperWidth + (e.clientX - startX)) / containerWidth) * 100;

        if (newPercentage >= 30 && newPercentage <= 70) {
            paperPanel.style.flex = `0 0 ${newPercentage}%`;
            pdfPanel.style.flex = `0 0 ${100 - newPercentage}%`;
        }
    });

    document.addEventListener('mouseup', () => {
        if (!isResizing) return;
        isResizing = false;

        const containerWidth = container.getBoundingClientRect().width;
        const finalPercentage = (paperPanel.getBoundingClientRect().width / containerWidth) * 100;
        localStorage.setItem('panelWidth', finalPercentage.toString());

        document.body.classList.remove('resizing');
        resizer.classList.remove('resizing');
    });
}

loadPapers();
