// Shared helpers for the ensemble evaluation phase (papers list + evaluation page).

const ENSEMBLE_DATA_URL = '/reviews/evaluation-data-ensemble.json';

// All ensemble ratings use a 7-point Likert scale.
const LIKERT_MAX = 7;

// Stage 3 rubric: concise, standardized, decision-relevant dimensions.
const ENSEMBLE_METRICS = [
    {
        key: 'accuracy_rigor',
        label: 'Accuracy / Rigor',
        question: "How accurate and technically rigorous is this review in evaluating the manuscript's main methods, results, and claims?",
        anchors: [
            '1 = Inaccurate — misreads the methods or results, or makes clearly wrong technical claims.',
            '4 = Mostly accurate — sound on the main points, but technical judgment is superficial in places.',
            '7 = Highly rigorous — technically correct throughout and probes methods, results, and claims in depth.'
        ]
    },
    {
        key: 'specificity',
        label: 'Specificity',
        question: "How specific and well supported are the review's comments and criticisms?",
        anchors: [
            "1 = Generic — vague impressions with no reference to the manuscript's content.",
            '4 = Mixed — some concrete, grounded points alongside unsupported generalities.',
            '7 = Highly specific — points to concrete sections, figures, or results and justifies each claim.'
        ]
    },
    {
        key: 'novelty',
        label: 'Novelty',
        question: "How well does the review assess the manuscript's originality and relation to prior work?",
        anchors: [
            '1 = Not assessed — originality and prior work are ignored or misjudged.',
            '4 = Partial — notes originality in general terms but engages little with prior work.',
            '7 = Thorough — situates the contribution against prior work and judges the novelty claim convincingly.'
        ]
    },
    {
        key: 'decisiveness',
        label: 'Decisiveness',
        question: 'How effectively does the review resolve ambiguity for the editor by providing a definitive and well-justified editorial recommendation?',
        anchors: [
            "1 = Evasive — no clear recommendation, or one unsupported by the review's content.",
            '4 = Somewhat clear — a recommendation is stated but only loosely justified.',
            '7 = Decisive — an unambiguous recommendation that follows directly from well-argued evidence.'
        ]
    },
    {
        key: 'overall_usefulness',
        label: 'Integrity / Usefulness',
        question: "How trustworthy and substantive is the review as a professional contribution to the evaluation of the manuscript's merit?",
        anchors: [
            '1 = Not usable — superficial or untrustworthy; adds nothing to the decision.',
            '4 = Moderately useful — a reasonable contribution with real gaps.',
            '7 = Exemplary — substantive, trustworthy, and would meaningfully shape the editorial decision.'
        ]
    }
];

const CONFIDENCE_TOOLTIP = `1 = Not at all confident.
4 = Moderately confident.
7 = Extremely confident.`;

// Stage 1 (pre-task) provisional recommendation options.
const RECOMMENDATION_OPTIONS = [
    { value: 'desk_reject', label: 'Desk-Reject' },
    { value: 'reject_from_peer_review', label: 'Reject from peer review' },
    { value: 'major_revision', label: 'Major Revision' }
];

const PRETASK_MAX_ITEMS = 3;

// The evaluator commits to one category before any evaluation, and the choice is final.
// The data file is the source of truth so it survives into processing; localStorage is
// only a cache of what the file already says.
const CATEGORY_STORAGE_KEY = 'ensembleCategory';
const EVALUATOR_STORAGE_KEY = 'ensembleEvaluator';
const CATEGORY_FIELD = 'evaluator_category';
const CATEGORY_AT_FIELD = 'evaluator_category_at';
const EVALUATOR_FIELD = 'evaluator_name';
const SEED_FIELD = 'display_seed';

// ---------------------------------------------------------------- ordering

// mulberry32. Every operation is a 32-bit integer op (Math.imul, >>>, ^), so the
// sequence is identical on every platform and browser — no floating-point drift,
// no dependence on the host's Math.random.
function seededRandom(seed) {
    let state = seed >>> 0;
    return function () {
        state = (state + 0x6D2B79F5) >>> 0;
        let t = state;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

// Derives a distinct but reproducible seed per paper from the evaluator's seed.
function deriveSeed(seed, salt) {
    return (Math.imul(seed >>> 0, 0x9E3779B1) ^ Math.imul(salt + 1, 0x85EBCA6B)) >>> 0;
}

// Fisher-Yates, so the result depends only on the seed and the input order.
function seededShuffle(array, seed) {
    const rng = seededRandom(seed);
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

function getDisplaySeed(papers) {
    const value = (papers || []).map(paper => paper[SEED_FIELD]).find(v => Number.isInteger(v));
    return Number.isInteger(value) ? value : 0;
}

// ---------------------------------------------------------------- timing

// Start is the first activity in a stage; end is rewritten by every activity that
// could be the last one, so the final write is the real end.
function getTiming(paper) {
    if (!paper.timing || typeof paper.timing !== 'object') paper.timing = {};
    const timing = paper.timing;
    ['pretask_started_at', 'pretask_ended_at', 'evaluation_started_at', 'evaluation_ended_at']
        .forEach(key => { if (typeof timing[key] !== 'string') timing[key] = ''; });
    return timing;
}

function markStageStart(paper, stage) {
    const timing = getTiming(paper);
    const key = `${stage}_started_at`;
    if (!timing[key]) timing[key] = new Date().toISOString();
}

function markStageEnd(paper, stage) {
    getTiming(paper)[`${stage}_ended_at`] = new Date().toISOString();
}

function getChosenCategory() {
    return localStorage.getItem(CATEGORY_STORAGE_KEY) || '';
}

function getEvaluatorName() {
    return localStorage.getItem(EVALUATOR_STORAGE_KEY) || '';
}

// Reads the committed assignment out of the data file and refreshes the cache, so a
// cleared browser cannot silently hand the evaluator a second choice.
function syncCategoryFromPapers(papers) {
    const list = papers || [];
    const category = list.map(paper => paper[CATEGORY_FIELD]).find(Boolean) || '';
    const evaluator = list.map(paper => paper[EVALUATOR_FIELD]).find(Boolean) || '';

    if (category) {
        localStorage.setItem(CATEGORY_STORAGE_KEY, category);
    } else {
        localStorage.removeItem(CATEGORY_STORAGE_KEY);
    }

    if (evaluator) {
        localStorage.setItem(EVALUATOR_STORAGE_KEY, evaluator);
    } else {
        localStorage.removeItem(EVALUATOR_STORAGE_KEY);
    }

    return category;
}

// Stamps every paper so the assignment is a file-level fact, then persists it.
// `evaluators` is the schema's existing per-paper list and is filled to match.
async function commitCategory(papers, category, evaluatorName) {
    const timestamp = new Date().toISOString();
    const name = (evaluatorName || '').trim();
    // One seed per evaluator, drawn here and never again; it fixes the order of
    // both the paper list and the reviews within each paper.
    const seed = Math.floor(Math.random() * 0x7FFFFFFF);

    papers.forEach(paper => {
        paper[CATEGORY_FIELD] = category;
        paper[CATEGORY_AT_FIELD] = timestamp;
        paper[EVALUATOR_FIELD] = name;
        paper[SEED_FIELD] = seed;
        paper.evaluators = name ? [name] : [];
    });

    await saveEnsemblePapers(papers);
    localStorage.setItem(CATEGORY_STORAGE_KEY, category);
    localStorage.setItem(EVALUATOR_STORAGE_KEY, name);
}

// Category values come from the data file in mixed case ("image analysis"); only the
// display form is normalised, so filtering still matches the raw value.
function categoryLabel(value) {
    const text = (value || '').trim();
    if (!text) return '—';
    return text.charAt(0).toUpperCase() + text.slice(1);
}

// The descriptive form of a paper's category; the data file has carried it in
// primary_area and, in earlier revisions, in category_name.
function paperCategoryLabel(paper) {
    const area = Array.isArray(paper.primary_area) ? paper.primary_area[0] : paper.primary_area;
    return categoryLabel(area || paper.category_name || paper.category);
}

function escapeHtml(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Normalise (and create, if missing) the pre-task record stored on a paper.
function getPretask(paper) {
    if (!paper.pretask || typeof paper.pretask !== 'object') {
        paper.pretask = {};
    }
    const pretask = paper.pretask;

    if (typeof pretask.recommendation !== 'string') pretask.recommendation = '';
    if (typeof pretask.confidence !== 'number') pretask.confidence = parseInt(pretask.confidence, 10) || 0;
    if (!Array.isArray(pretask.concerns)) pretask.concerns = [];
    if (!Array.isArray(pretask.strengths)) pretask.strengths = [];
    while (pretask.concerns.length < PRETASK_MAX_ITEMS) pretask.concerns.push('');
    while (pretask.strengths.length < PRETASK_MAX_ITEMS) pretask.strengths.push('');
    pretask.concerns = pretask.concerns.slice(0, PRETASK_MAX_ITEMS);
    pretask.strengths = pretask.strengths.slice(0, PRETASK_MAX_ITEMS);
    if (typeof pretask.submitted !== 'boolean') pretask.submitted = false;
    if (typeof pretask.submitted_at !== 'string') pretask.submitted_at = '';

    return pretask;
}

function isPretaskSubmitted(paper) {
    return Boolean(paper && paper.pretask && paper.pretask.submitted);
}

// Everything the evaluator must supply before the pre-task can be submitted.
function getPretaskMissingFields(pretask) {
    const missing = [];
    if (!pretask.recommendation) missing.push('a provisional recommendation');
    if (!(pretask.confidence >= 1 && pretask.confidence <= LIKERT_MAX)) missing.push('a confidence rating');
    if (!pretask.concerns.some(item => item.trim())) missing.push('at least one major concern');
    return missing;
}

function isReviewComplete(review) {
    const metrics = (review && review.metrics) || {};
    const allRated = ENSEMBLE_METRICS.every(metric => {
        const value = metrics[metric.key];
        return typeof value === 'number' && value >= 1 && value <= LIKERT_MAX;
    });
    return allRated;
}

function hasAnyProgress(paper) {
    const pretask = getPretask(paper);
    const pretaskTouched = Boolean(
        pretask.recommendation ||
        pretask.confidence ||
        pretask.concerns.some(item => item.trim()) ||
        pretask.strengths.some(item => item.trim())
    );
    if (pretaskTouched) return true;

    return (paper.reviews || []).some(review => {
        const metrics = (review && review.metrics) || {};
        return ENSEMBLE_METRICS.some(metric => metrics[metric.key] > 0) ||
            Boolean(metrics.comment && metrics.comment.trim());
    });
}

// Progress counts the pre-task as one step alongside each review evaluation.
function calculateProgress(paper) {
    const reviews = paper.reviews || [];
    const total = reviews.length + 1;
    let completed = isPretaskSubmitted(paper) ? 1 : 0;
    reviews.forEach(review => {
        if (isReviewComplete(review)) completed++;
    });
    return { completed, total };
}

function computeStatus(paper) {
    const progress = calculateProgress(paper);
    if (progress.total > 0 && progress.completed === progress.total) return 'completed';
    if (progress.completed > 0 || hasAnyProgress(paper)) return 'in_progress';
    return 'not_started';
}

function createStatusBadge(status, completed, total) {
    const percentage = total > 0 ? (completed / total) * 100 : 0;
    const circumference = 2 * Math.PI * 8; // radius = 8
    const offset = circumference - (percentage / 100) * circumference;

    const statusLabel = status.replace('_', ' ');
    const statusText = status === 'not_started'
        ? statusLabel
        : `${statusLabel} (${completed} of ${total} steps completed)`;

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
            <span>${escapeHtml(statusText)}</span>
        </span>
    `;
}

function recommendationLabel(value) {
    const option = RECOMMENDATION_OPTIONS.find(item => item.value === value);
    return option ? option.label : '—';
}

// Fetch the ensemble dataset and fail loudly if the server is serving another phase's data.
async function loadEnsemblePapers() {
    const response = await fetch(ENSEMBLE_DATA_URL);
    if (!response.ok) {
        throw new Error(`Failed to load review data (HTTP ${response.status})`);
    }
    const papers = await response.json();
    if (!Array.isArray(papers)) {
        throw new Error('Review data is not a list of papers');
    }
    if (papers.length && !('category' in papers[0])) {
        throw new Error('The server is not serving the ensemble dataset. Start it with ./run_ensemble');
    }
    papers.forEach(paper => getPretask(paper));
    return papers;
}

async function saveEnsemblePapers(papers) {
    try {
        const response = await fetch('/save_evaluation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(papers)
        });
        if (!response.ok) {
            console.error('Failed to save evaluation');
            return false;
        }
        return true;
    } catch (error) {
        console.error('Error saving evaluation:', error);
        return false;
    }
}

// ---------------------------------------------------------------- results download

function resultsFileName() {
    const slug = value => (value || '')
        .trim().toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
    const parts = ['evaluation', slug(getEvaluatorName()), slug(getChosenCategory())].filter(Boolean);
    return `${parts.join('-')}.json`;
}

// Downloads whatever is currently on disk, so a pending autosave cannot be missed.
async function downloadResults(button) {
    const label = button ? button.querySelector('.download-json-label') : null;
    const original = label ? label.textContent : '';

    try {
        if (label) label.textContent = 'Preparing…';
        const response = await fetch(`${ENSEMBLE_DATA_URL}?t=${Date.now()}`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const url = URL.createObjectURL(await response.blob());
        const link = document.createElement('a');
        link.href = url;
        link.download = resultsFileName();
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        if (label) label.textContent = 'Saved';
    } catch (error) {
        console.error('Error downloading results:', error);
        window.alert('Could not download the results file. Check that the console is still running.');
    } finally {
        if (label) setTimeout(() => { label.textContent = original; }, 1200);
    }
}

function setupDownloadButton() {
    document.querySelectorAll('[data-download-json]').forEach(button => {
        button.addEventListener('click', () => downloadResults(button));
    });
}
