// Evaluation page JavaScript
let currentPaper = null;
let allPapers = [];
let filteredPaperIndices = [];
let currentFilteredIndex = -1;
let appConfig = null; // Will be loaded from server
const commentSaveTimeouts = {}; // Track pending saves for comment inputs

// Load configuration from server
async function loadConfig() {
    try {
        const response = await fetch('/config');
        appConfig = await response.json();
        console.log('Loaded config:', appConfig);
    } catch (error) {
        console.error('Error loading config:', error);
        // Use defaults if config fails to load
        appConfig = {
            showHarmonizedByDefault: true,
            defaultHarmonizationModel: 'gpt-4o-mini',
            enableModelDropdown: false,
            enableSplitView: false,
            showReviewerType: false,
            shuffleReviews: false,
            shuffleSeed: 42
        };
    }
}

// Load filters from localStorage
function loadFilters() {
    const saved = localStorage.getItem('reviewFilters');
    if (saved) {
        try {
            const filtersData = JSON.parse(saved);
            return {
                evaluators: new Set(filtersData.evaluators || []),
                areas: new Set(filtersData.areas || []),
                keywords: new Set(filtersData.keywords || []),
                titleKeywords: new Set(filtersData.titleKeywords || []),
                statuses: new Set(filtersData.statuses || [])
            };
        } catch (e) {
            console.error('Error loading filters:', e);
        }
    }
    return null;
}

// Filter papers based on saved filters
function getFilteredPapers() {
    const filters = loadFilters();
    if (!filters) {
        return allPapers.map((_, index) => index);
    }

    const indices = [];
    allPapers.forEach((paper, index) => {
        // Evaluator filter
        if (filters.evaluators.size > 0) {
            const hasEvaluator = paper.evaluators.some(e => filters.evaluators.has(e));
            if (!hasEvaluator) return;
        }

        // Area filter
        if (filters.areas.size > 0) {
            const hasArea = paper.primary_area.some(a => filters.areas.has(a));
            if (!hasArea) return;
        }

        // Keyword filter
        if (filters.keywords.size > 0) {
            const hasKeyword = Array.from(filters.keywords).every(kw =>
                paper.keywords.some(k => k.toLowerCase().includes(kw.toLowerCase()))
            );
            if (!hasKeyword) return;
        }

        // Title search
        if (filters.titleKeywords.size > 0) {
            const hasTitle = Array.from(filters.titleKeywords).every(kw =>
                paper.title.toLowerCase().includes(kw.toLowerCase())
            );
            if (!hasTitle) return;
        }

        // Status filter
        if (filters.statuses.size > 0) {
            if (!filters.statuses.has(paper.status)) return;
        }

        indices.push(index);
    });

    return indices;
}

// Metric tooltips
const METRIC_TOOLTIPS = {
    coverage: `1 = Very poor – touches on none or only 1 criterion, superficial.
2 = Poor – mentions 1–2 criteria, shallow engagement.
3 = Fair – addresses 2–3 criteria with some detail, but misses others.
4 = Good – engages with most criteria (3–4) with reasonable depth.
5 = Excellent – systematically covers all 4 criteria with depth and clarity.`,

    specificity: `1 = Very vague – generic comments with no concrete examples.
2 = Vague – occasional specifics but mostly general impressions.
3 = Mixed – some detailed points but also broad or unsupported claims.
4 = Specific – most comments grounded in manuscript details.
5 = Very specific – consistently detailed, citing precise sections.`,

    correctness: `1 = Very poor – contains clear factual errors or misinterpretations.
2 = Poor – several questionable or weakly grounded claims.
3 = Fair – mostly correct, with some minor inaccuracies.
4 = Good – accurate and logically sound with only small issues.
5 = Excellent – entirely factually/logically grounded, no errors.`,

    constructiveness: `1 = Not constructive – only complaints, no suggestions.
2 = Low – minimal guidance; suggestions are vague.
3 = Mixed – some useful suggestions, but incomplete.
4 = Constructive – clear, actionable recommendations for most issues.
5 = Highly constructive – specific, actionable guidance for all issues.`,

    stance: `1 = Very unbalanced (lenient) – overlooks major flaws, overly positive.
2 = Unbalanced (lenient) – underplays weaknesses.
3 = Balanced – tone proportional to strengths/weaknesses.
4 = Unbalanced (harsh) – exaggerates flaws.
5 = Very unbalanced (harsh) – dismissive or unfairly negative.`,

    source: `1 = AI-generated (e.g., GPT-4, Claude, etc.)
2 = Human-generated`
};

// Load papers data
async function loadPapers() {
    try {
        // Load config first
        await loadConfig();

        const response = await fetch('/reviews/evaluation-data-all-venues.json');
        allPapers = await response.json();

        // Get filtered paper indices
        filteredPaperIndices = getFilteredPapers();

        // Get paper index from URL
        const params = new URLSearchParams(window.location.search);
        const paperIndex = parseInt(params.get('paper'));

        if (paperIndex >= 0 && paperIndex < allPapers.length) {
            currentPaper = allPapers[paperIndex];

            // Find position in filtered list
            currentFilteredIndex = filteredPaperIndices.indexOf(paperIndex);

            renderPaper();
            setupResizer();
            updateNavigationButtons();
        } else {
            document.getElementById('paper-title').textContent = 'Paper not found';
        }
    } catch (error) {
        console.error('Error loading papers:', error);
        document.getElementById('paper-title').textContent = 'Error loading paper';
    }
}

// Update navigation buttons state
function updateNavigationButtons() {
    const prevBtn = document.getElementById('prev-paper-btn');
    const nextBtn = document.getElementById('next-paper-btn');
    const positionSpan = document.getElementById('paper-position');

    // Update position text
    if (currentFilteredIndex >= 0) {
        positionSpan.textContent = `${currentFilteredIndex + 1} / ${filteredPaperIndices.length}`;
    } else {
        positionSpan.textContent = '1 / 1';
    }

    // Enable/disable buttons
    prevBtn.disabled = currentFilteredIndex <= 0;
    nextBtn.disabled = currentFilteredIndex >= filteredPaperIndices.length - 1;
}

// Navigate to previous paper
function navigateToPreviousPaper() {
    if (currentFilteredIndex > 0) {
        const newIndex = filteredPaperIndices[currentFilteredIndex - 1];
        navigateToPaper(newIndex);
    }
}

// Navigate to next paper
function navigateToNextPaper() {
    if (currentFilteredIndex < filteredPaperIndices.length - 1) {
        const newIndex = filteredPaperIndices[currentFilteredIndex + 1];
        navigateToPaper(newIndex);
    }
}

// Navigate to a specific paper
function navigateToPaper(paperIndex) {
    // Stop PDF loading
    const pdfViewer = document.getElementById('pdf-viewer');
    if (pdfViewer) {
        pdfViewer.src = 'about:blank';
    }

    // Update URL and reload
    window.location.href = `evaluate.html?paper=${paperIndex}`;
}

// Setup navigation button handlers
document.getElementById('prev-paper-btn').addEventListener('click', navigateToPreviousPaper);
document.getElementById('next-paper-btn').addEventListener('click', navigateToNextPaper);

// Setup toggle all reviews button
document.getElementById('toggle-all-reviews').addEventListener('click', toggleAllReviews);

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Left arrow or 'p' for previous
    if ((e.key === 'ArrowLeft' || e.key === 'p') && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const activeElement = document.activeElement;
        // Don't trigger if user is typing in an input
        if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA') {
            e.preventDefault();
            navigateToPreviousPaper();
        }
    }
    // Right arrow or 'n' for next
    if ((e.key === 'ArrowRight' || e.key === 'n') && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const activeElement = document.activeElement;
        // Don't trigger if user is typing in an input
        if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA') {
            e.preventDefault();
            navigateToNextPaper();
        }
    }
});

// Render paper information
function renderPaper() {
    // Paper info
    document.getElementById('paper-title').textContent = currentPaper.title;

    const progress = calculateProgress(currentPaper);
    document.getElementById('paper-status').innerHTML = createStatusBadge(currentPaper.status, progress.completed, progress.total);
    document.getElementById('paper-evaluators').textContent = currentPaper.evaluators.join(', ');
    document.getElementById('paper-areas').textContent = currentPaper.primary_area.join(', ');
    document.getElementById('paper-abstract').textContent = currentPaper.abstract || 'No abstract available';

    // PDF viewer
    if (currentPaper.url) {
        setupPDFViewer(currentPaper.url);
    }

    // Reviews
    renderReviews();
}

// Setup PDF viewer with fallback
function setupPDFViewer(pdfUrl) {
    const pdfViewer = document.getElementById('pdf-viewer');
    const pdfLinkIcon = document.getElementById('pdf-link-icon');
    const pdfFallback = document.getElementById('pdf-fallback');
    const pdfFallbackLink = document.getElementById('pdf-fallback-link');

    // Set links to original URL (for local paths, make them absolute)
    const absoluteUrl = pdfUrl.startsWith('pdfs/') ? '/' + pdfUrl : pdfUrl;
    pdfLinkIcon.href = absoluteUrl;
    pdfFallbackLink.href = absoluteUrl;

    // Determine if URL is local or remote
    let viewUrl;
    console.log('PDF URL from data:', JSON.stringify(pdfUrl));
    console.log('PDF URL type:', typeof pdfUrl);
    console.log('Starts with pdfs/:', pdfUrl.startsWith('pdfs/'));
    console.log('Starts with http:', pdfUrl.startsWith('http'));

    // Trim any whitespace
    const cleanUrl = pdfUrl.trim();

    if (cleanUrl.startsWith('pdfs/') || cleanUrl.startsWith('/pdfs/')) {
        // Local PDF - serve directly
        viewUrl = cleanUrl.startsWith('/') ? cleanUrl : '/' + cleanUrl;
        console.log('✓ Loading local PDF:', viewUrl);
    } else if (cleanUrl.startsWith('http://') || cleanUrl.startsWith('https://')) {
        // Remote PDF - use proxy to bypass CORS
        viewUrl = `/pdf-proxy?url=${encodeURIComponent(cleanUrl)}`;
        console.log('✓ Loading remote PDF via proxy');
    } else {
        // Assume it's a local path if it doesn't start with http
        viewUrl = cleanUrl.startsWith('/') ? cleanUrl : '/' + cleanUrl;
        console.log('✓ Loading as local PDF (fallback):', viewUrl);
    }

    // Show iframe, hide fallback initially
    pdfViewer.style.display = '';
    pdfFallback.style.display = 'none';

    // Load PDF with view parameters for fit to width
    // FitH = Fit Horizontally (width), navpanes=0 hides navigation panes
    pdfViewer.src = `${viewUrl}#view=FitH&navpanes=0&toolbar=1`;

    // Only show fallback on actual error
    pdfViewer.onerror = (e) => {
        console.error('PDF viewer error:', e);
        pdfViewer.style.display = 'none';
        pdfFallback.style.display = 'flex';
    };

    // Log when PDF loads successfully
    pdfViewer.onload = () => {
        console.log('PDF iframe loaded successfully with FitH view');
    };
}

// Calculate progress
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

// Seeded random number generator (for reproducible shuffling)
function seededRandom(seed) {
    let state = seed;
    return function() {
        state = (state * 1103515245 + 12345) & 0x7fffffff;
        return state / 0x7fffffff;
    };
}

// Shuffle array using Fisher-Yates algorithm with a seeded RNG
function shuffleWithSeed(array, seed) {
    const rng = seededRandom(seed);
    const shuffled = [...array]; // Create a copy

    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }

    return shuffled;
}

// Toggle all reviews open/closed
function toggleAllReviews() {
    const reviewItems = document.querySelectorAll('.review-item');
    const toggleBtn = document.getElementById('toggle-all-reviews');
    const toggleText = toggleBtn.querySelector('span');
    const toggleIcon = toggleBtn.querySelector('svg polyline');

    if (reviewItems.length === 0) return;

    // Check if any reviews are open
    const anyOpen = Array.from(reviewItems).some(item => item.open);

    if (anyOpen) {
        // Collapse all
        reviewItems.forEach(item => item.open = false);
        toggleText.textContent = 'Expand All';
        toggleBtn.title = 'Expand all reviews';
        // Rotate icon 180 degrees (pointing right)
        toggleIcon.setAttribute('points', '9 18 15 12 9 6');
    } else {
        // Expand all
        reviewItems.forEach(item => item.open = true);
        toggleText.textContent = 'Collapse All';
        toggleBtn.title = 'Collapse all reviews';
        // Reset icon to pointing down
        toggleIcon.setAttribute('points', '6 9 12 15 18 9');
    }
}

// Render reviews
function renderReviews() {
    const container = document.getElementById('reviews-list');

    if (!currentPaper.reviews || currentPaper.reviews.length === 0) {
        container.innerHTML = '<p>No reviews available</p>';
        return;
    }

    // Shuffle reviews if enabled
    let reviewsToRender = currentPaper.reviews;
    if (appConfig && appConfig.shuffleReviews) {
        // Get current paper index from URL
        const params = new URLSearchParams(window.location.search);
        const paperIndex = parseInt(params.get('paper')) || 0;

        // Create a unique seed for this paper by combining base seed with paper index
        const paperSeed = appConfig.shuffleSeed + paperIndex;

        // Create array of [review, originalIndex] pairs
        const reviewsWithIndices = currentPaper.reviews.map((review, idx) => ({
            review,
            originalIndex: idx
        }));

        // Shuffle the array
        const shuffled = shuffleWithSeed(reviewsWithIndices, paperSeed);
        reviewsToRender = shuffled.map(item => item.review);

        console.log('Reviews shuffled with seed:', paperSeed, '(base seed:', appConfig.shuffleSeed, '+ paper index:', paperIndex + ')');
    }

    container.innerHTML = reviewsToRender.map((review, index) => {
        // Check if harmonization data exists
        const hasHarmonization = review.harmonization && review.harmonization.length > 0;

        // Find default harmonization by model name
        let defaultHarmonizationIndex = 0;
        let defaultHarmonizationText = '';

        if (hasHarmonization && appConfig && appConfig.showHarmonizedByDefault) {
            const foundIndex = review.harmonization.findIndex(
                h => h.model === appConfig.defaultHarmonizationModel
            );
            if (foundIndex !== -1) {
                defaultHarmonizationIndex = foundIndex;
            }
            defaultHarmonizationText = review.harmonization[defaultHarmonizationIndex].text;
        }

        // Determine which text to show in main area
        const showHarmonized = hasHarmonization && appConfig && appConfig.showHarmonizedByDefault;
        const mainText = showHarmonized ? defaultHarmonizationText : review.text;
        const mainHtml = mainText ? marked.parse(mainText) : 'No review text available';

        // Original review text for split view
        const originalHtml = review.text ? marked.parse(review.text) : 'No review text available';

        // Build harmonization dropdown options
        let harmonizationDropdown = '';
        if (hasHarmonization && appConfig && appConfig.enableModelDropdown) {
            const options = review.harmonization.map((harm, harmIdx) =>
                `<option value="${harmIdx}" ${harmIdx === defaultHarmonizationIndex ? 'selected' : ''}>${harm.model}</option>`
            ).join('');
            harmonizationDropdown = `
                <select class="harmonization-select" data-review="${index}">
                    ${options}
                </select>
            `;
        }

        // Split view button
        let splitViewButton = '';
        if (hasHarmonization && appConfig && appConfig.enableSplitView) {
            splitViewButton = `
                <button class="split-view-btn" data-review="${index}" title="Toggle split view">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="7" height="18" rx="1"></rect>
                        <rect x="14" y="3" width="7" height="18" rx="1"></rect>
                    </svg>
                </button>
            `;
        }

        const reviewerType = (appConfig && appConfig.showReviewerType && review.reviewer) ? `[${review.reviewer}]` : '';

        return `
        <details class="review-item" open data-review-index="${index}">
            <summary class="review-header">
                <span>Review #${index + 1} ${reviewerType}</span>
                ${hasHarmonization && (harmonizationDropdown || splitViewButton) ? `
                    <div class="review-header-actions">
                        ${harmonizationDropdown}
                        ${splitViewButton}
                    </div>
                ` : ''}
            </summary>
            <div class="review-content">
                <div class="harmonization-text" style="display: none;"></div>
                <div class="review-text" data-original-text="${encodeURIComponent(originalHtml)}">${mainHtml}</div>
                <div class="original-review-text" style="display: none;">${originalHtml}</div>
                <div class="metrics-sidebar">
                    ${renderMetric('Coverage', 'coverage', index)}
                    ${renderMetric('Specificity', 'specificity', index)}
                    ${renderMetric('Correctness', 'correctness', index)}
                    ${renderMetric('Constructiveness', 'constructiveness', index)}
                    ${renderMetric('Stance', 'stance', index)}
                    ${renderSourceMetric('Source', 'source', index)}
                    ${renderCommentField(index)}
                </div>
            </div>
        </details>
        `;
    }).join('');

    // Setup star ratings
    setupStarRatings();

    // Setup comment inputs
    setupCommentInputs();

    // Setup clear evaluation buttons
    setupClearEvaluationButtons();

    // Setup split view and harmonization controls
    setupSplitViewControls();
}

// Render metric
function renderMetric(label, key, reviewIndex) {
    const value = currentPaper.reviews[reviewIndex].metrics[key] || 0;

    return `
        <div class="metric-row">
            <div class="metric-label tooltip">
                ${label}
                <span class="info-icon">i</span>
                <span class="tooltiptext">${METRIC_TOOLTIPS[key]}</span>
            </div>
            <div class="metric-stars" data-metric="${key}" data-review="${reviewIndex}">
                ${[1, 2, 3, 4, 5].map(i => `
                    <span class="star ${i <= value ? 'filled' : ''}" data-value="${i}">★</span>
                `).join('')}
            </div>
        </div>
    `;
}

// Render source metric (AI vs Human)
function renderSourceMetric(label, key, reviewIndex) {
    const value = currentPaper.reviews[reviewIndex].metrics[key] || '';
    const isAI = value.toLowerCase().startsWith('ai') || value === '1';
    const isHuman = value === 'human' || value === '2';

    return `
        <div class="metric-row">
            <div class="metric-label tooltip">
                ${label}
                <span class="info-icon">i</span>
                <span class="tooltiptext">${METRIC_TOOLTIPS[key]}</span>
            </div>
            <div class="source-options" data-metric="${key}" data-review="${reviewIndex}">
                <button class="source-btn ${isAI ? 'selected' : ''}" data-value="ai">AI</button>
                <button class="source-btn ${isHuman ? 'selected' : ''}" data-value="human">Human</button>
            </div>
        </div>
    `;
}

// Render free-form comment input
function renderCommentField(reviewIndex) {
    return `
        <div class="metric-row comment-row">
            <div class="metric-label">
                Comment
            </div>
            <textarea class="metric-comment" data-review="${reviewIndex}" placeholder="Auto saved as you type."></textarea>
        </div>
        <div>
            <button class="clear-evaluation-btn" data-review="${reviewIndex}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                </svg>
                Clear Evaluation
            </button>
        </div>
    `;
}

// Setup star ratings
function setupStarRatings() {
    document.querySelectorAll('.metric-stars').forEach(starsContainer => {
        const metricKey = starsContainer.dataset.metric;
        const reviewIndex = parseInt(starsContainer.dataset.review);
        const stars = starsContainer.querySelectorAll('.star');

        stars.forEach(star => {
            const value = parseInt(star.dataset.value);

            // Hover effect
            star.addEventListener('mouseenter', () => {
                stars.forEach((s, i) => {
                    s.classList.toggle('hovered', i < value);
                });
            });

            // Click to set rating
            star.addEventListener('click', async () => {
                currentPaper.reviews[reviewIndex].metrics[metricKey] = value;

                // Update UI
                stars.forEach((s, i) => {
                    s.classList.toggle('filled', i < value);
                    s.classList.remove('hovered');
                });

                // Update status
                updatePaperStatus();

                // Save to file
                await saveEvaluation();
            });
        });

        // Remove hover effect on mouse leave
        starsContainer.addEventListener('mouseleave', () => {
            stars.forEach(s => s.classList.remove('hovered'));
        });
    });

    // Setup source buttons
    setupSourceButtons();

    // Setup tooltip positioning
    setupTooltips();
}

// Setup handlers for evaluator comment inputs
function setupCommentInputs() {
    document.querySelectorAll('.metric-comment').forEach(textarea => {
        const reviewIndex = parseInt(textarea.dataset.review, 10);
        if (Number.isNaN(reviewIndex) || !currentPaper.reviews[reviewIndex]) {
            return;
        }

        const metrics = currentPaper.reviews[reviewIndex].metrics || {};
        textarea.value = metrics.comment || '';

        textarea.addEventListener('input', () => {
            metrics.comment = textarea.value;

            if (commentSaveTimeouts[reviewIndex]) {
                clearTimeout(commentSaveTimeouts[reviewIndex]);
            }

            commentSaveTimeouts[reviewIndex] = setTimeout(async () => {
                commentSaveTimeouts[reviewIndex] = null;
                await saveEvaluation();
            }, 600);
        });

        textarea.addEventListener('blur', async () => {
            if (commentSaveTimeouts[reviewIndex]) {
                clearTimeout(commentSaveTimeouts[reviewIndex]);
                commentSaveTimeouts[reviewIndex] = null;
            }

            metrics.comment = textarea.value;
            await saveEvaluation();
        });
    });
}

// Setup clear evaluation buttons
function setupClearEvaluationButtons() {
    document.querySelectorAll('.clear-evaluation-btn').forEach(button => {
        const reviewIndex = parseInt(button.dataset.review, 10);
        if (Number.isNaN(reviewIndex) || !currentPaper.reviews[reviewIndex]) {
            return;
        }

        button.addEventListener('click', async () => {
            // Confirm before clearing
            if (!confirm('Are you sure you want to clear all evaluation data for this review?')) {
                return;
            }

            const metrics = currentPaper.reviews[reviewIndex].metrics || {};

            // Clear all metrics
            metrics.coverage = 0;
            metrics.specificity = 0;
            metrics.correctness = 0;
            metrics.constructiveness = 0;
            metrics.stance = 0;
            metrics.source = '';
            metrics.comment = '';

            // Save and re-render
            await saveEvaluation();
            renderReviews();
        });
    });
}

// Setup source buttons (AI vs Human)
function setupSourceButtons() {
    document.querySelectorAll('.source-options').forEach(container => {
        const metricKey = container.dataset.metric;
        const reviewIndex = parseInt(container.dataset.review);
        const buttons = container.querySelectorAll('.source-btn');

        buttons.forEach(button => {
            button.addEventListener('click', async () => {
                const value = button.dataset.value;

                // Update data - store as string
                currentPaper.reviews[reviewIndex].metrics[metricKey] = value;

                // Update UI - remove selected from all, add to clicked
                buttons.forEach(btn => btn.classList.remove('selected'));
                button.classList.add('selected');

                // Update status
                updatePaperStatus();

                // Save to file
                await saveEvaluation();
            });
        });
    });
}

// Setup dynamic tooltip positioning
function setupTooltips() {
    document.querySelectorAll('.tooltip').forEach(tooltip => {
        const tooltipText = tooltip.querySelector('.tooltiptext');
        let isOpen = false;

        tooltip.addEventListener('click', (e) => {
            e.stopPropagation();

            // Close all other tooltips
            document.querySelectorAll('.tooltiptext').forEach(tt => {
                if (tt !== tooltipText) {
                    tt.classList.remove('visible');
                }
            });

            // Toggle current tooltip
            isOpen = !isOpen;

            if (isOpen) {
                const rect = tooltip.getBoundingClientRect();

                // Position tooltip above the element
                tooltipText.style.left = `${rect.left + rect.width / 2}px`;
                tooltipText.style.top = `${rect.top - 10}px`;
                tooltipText.style.transform = 'translate(-50%, -100%)';
                tooltipText.classList.add('visible');
            } else {
                tooltipText.classList.remove('visible');
            }
        });
    });

    // Close tooltips when clicking outside
    document.addEventListener('click', () => {
        document.querySelectorAll('.tooltiptext').forEach(tt => {
            tt.classList.remove('visible');
        });
    });
}

// Update paper status based on review completion
function updatePaperStatus() {
    const progress = calculateProgress(currentPaper);

    if (progress.completed === 0) {
        currentPaper.status = 'not_started';
    } else if (progress.completed < progress.total) {
        currentPaper.status = 'in_progress';
    } else {
        currentPaper.status = 'completed';
    }

    // Update status display
    document.getElementById('paper-status').innerHTML = createStatusBadge(currentPaper.status, progress.completed, progress.total);
}

// Save evaluation to file
async function saveEvaluation() {
    try {
        // Update the paper in allPapers array
        const params = new URLSearchParams(window.location.search);
        const paperIndex = parseInt(params.get('paper'));
        allPapers[paperIndex] = currentPaper;

        // Send to server
        const response = await fetch('/save_evaluation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(allPapers)
        });

        if (!response.ok) {
            console.error('Failed to save evaluation');
        }
    } catch (error) {
        console.error('Error saving evaluation:', error);
    }
}

// Load saved panel width from localStorage
function loadSavedPanelWidth() {
    const savedWidth = localStorage.getItem('panelWidth');
    if (savedWidth) {
        const percentage = parseFloat(savedWidth);
        if (percentage >= 30 && percentage <= 70) {
            const paperPanel = document.getElementById('paper-panel');
            const pdfPanel = document.getElementById('pdf-panel');
            paperPanel.style.flex = `0 0 ${percentage}%`;
            pdfPanel.style.flex = `0 0 ${100 - percentage}%`;
            console.log('Loaded saved panel width:', percentage + '%');
        }
    }
}

// Save panel width to localStorage
function savePanelWidth(percentage) {
    localStorage.setItem('panelWidth', percentage.toString());
}

// Setup resizer for panels
function setupResizer() {
    const resizer = document.getElementById('resizer');
    const paperPanel = document.getElementById('paper-panel');
    const pdfPanel = document.getElementById('pdf-panel');
    const container = document.querySelector('.evaluation-content');
    let isResizing = false;
    let startX = 0;
    let startPaperWidth = 0;

    // Load saved width on setup
    loadSavedPanelWidth();

    resizer.addEventListener('mousedown', (e) => {
        e.preventDefault();
        e.stopPropagation();

        isResizing = true;
        startX = e.clientX;

        // Get current width of paper panel
        startPaperWidth = paperPanel.getBoundingClientRect().width;

        // Add resizing class to body and resizer for visual feedback
        document.body.classList.add('resizing');
        resizer.classList.add('resizing');
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;

        e.preventDefault();
        e.stopPropagation();

        // Calculate the delta from start position
        const deltaX = e.clientX - startX;
        const containerWidth = container.getBoundingClientRect().width;

        // Calculate new width for paper panel
        const newPaperWidth = startPaperWidth + deltaX;
        const newPercentage = (newPaperWidth / containerWidth) * 100;

        // Allow resize between 30% and 70%
        if (newPercentage >= 30 && newPercentage <= 70) {
            paperPanel.style.flex = `0 0 ${newPercentage}%`;
            pdfPanel.style.flex = `0 0 ${100 - newPercentage}%`;
        }
    });

    document.addEventListener('mouseup', (e) => {
        if (!isResizing) return;

        e.preventDefault();
        e.stopPropagation();

        isResizing = false;

        // Save the final width to localStorage
        const containerWidth = container.getBoundingClientRect().width;
        const currentPaperWidth = paperPanel.getBoundingClientRect().width;
        const finalPercentage = (currentPaperWidth / containerWidth) * 100;
        savePanelWidth(finalPercentage);

        // Remove resizing classes
        document.body.classList.remove('resizing');
        resizer.classList.remove('resizing');
    });
}

// Setup split view and harmonization controls
function setupSplitViewControls() {
    // Handle split view button clicks
    document.querySelectorAll('.split-view-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent details toggle
            const reviewIndex = parseInt(button.dataset.review);
            toggleSplitView(reviewIndex);
        });
    });

    // Handle harmonization model selection
    document.querySelectorAll('.harmonization-select').forEach(select => {
        select.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent details toggle
        });

        select.addEventListener('change', (e) => {
            const reviewIndex = parseInt(select.dataset.review);
            const harmonizationIndex = parseInt(select.value);
            updateMainText(reviewIndex, harmonizationIndex);
        });
    });
}

// Toggle split view for a review
function toggleSplitView(reviewIndex) {
    const reviewItem = document.querySelector(`.review-item[data-review-index="${reviewIndex}"]`);
    if (!reviewItem) return;

    const reviewContent = reviewItem.querySelector('.review-content');
    const splitViewBtn = reviewItem.querySelector('.split-view-btn');
    const reviewText = reviewItem.querySelector('.review-text');
    const originalText = reviewItem.querySelector('.original-review-text');
    const harmonizationText = reviewItem.querySelector('.harmonization-text');

    const isSplitView = reviewContent.classList.contains('split-view');

    if (!isSplitView) {
        // Entering split view: show original on left, current harmonized on right
        const currentHarmonizedHtml = reviewText.innerHTML;
        const originalHtml = originalText.innerHTML;

        reviewText.innerHTML = originalHtml;
        harmonizationText.innerHTML = currentHarmonizedHtml;

        reviewContent.classList.add('split-view');
        splitViewBtn.classList.add('active');
    } else {
        // Exiting split view: restore harmonized text to main area
        const harmonizedHtml = harmonizationText.innerHTML;
        reviewText.innerHTML = harmonizedHtml;

        reviewContent.classList.remove('split-view');
        splitViewBtn.classList.remove('active');
    }
}

// Update main text when dropdown changes
function updateMainText(reviewIndex, harmonizationIndex) {
    const review = currentPaper.reviews[reviewIndex];
    if (!review || !review.harmonization || !review.harmonization[harmonizationIndex]) {
        return;
    }

    const harmonization = review.harmonization[harmonizationIndex];
    const reviewItem = document.querySelector(`.review-item[data-review-index="${reviewIndex}"]`);
    if (!reviewItem) return;

    const reviewText = reviewItem.querySelector('.review-text');
    const reviewContent = reviewItem.querySelector('.review-content');
    const harmonizationText = reviewItem.querySelector('.harmonization-text');

    // Convert markdown to HTML
    const harmonizedHtml = harmonization.text ? marked.parse(harmonization.text) : 'No harmonized text available';

    if (reviewContent.classList.contains('split-view')) {
        // In split view: update the right panel
        harmonizationText.innerHTML = harmonizedHtml;
    } else {
        // Not in split view: update the main text
        reviewText.innerHTML = harmonizedHtml;
    }
}

// Handle back button - abort PDF loading for instant navigation
document.getElementById('back-button').addEventListener('click', (e) => {
    e.preventDefault();

    // Stop all pending requests including PDF
    const pdfViewer = document.getElementById('pdf-viewer');
    if (pdfViewer) {
        // Remove iframe from DOM to cancel request
        pdfViewer.remove();
    }

    // Stop any other pending requests
    window.stop();

    // Navigate immediately
    window.location.href = 'index.html';
});

// Also clean up on page unload
window.addEventListener('beforeunload', () => {
    const pdfViewer = document.getElementById('pdf-viewer');
    if (pdfViewer) {
        pdfViewer.src = 'about:blank';
    }
});

// Load paper on page load
loadPapers();
