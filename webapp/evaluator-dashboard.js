// Evaluator Dashboard JavaScript
let allPapers = [];
let selectedEvaluator = null;
let chart = null;
function getChartColors() {
    const styles = getComputedStyle(document.body);
    const readVar = (name, fallback) => {
        const value = styles.getPropertyValue(name);
        return value ? value.trim() || fallback : fallback;
    };

    return {
        bar: readVar('--chart-bar-color', 'rgba(54, 162, 235, 0.6)'),
        border: readVar('--chart-bar-border', 'rgba(54, 162, 235, 1)'),
        grid: readVar('--chart-grid-color', 'rgba(226, 232, 240, 0.25)'),
        text: readVar('--chart-text-color', '#2d3748'),
        tooltipBg: readVar('--color-tooltip-bg', '#333333')
    };
}

function applyChartTheme(chartInstance) {
    if (!chartInstance) {
        return;
    }

    const colors = getChartColors();
    const toColor = (value, fallback) => {
        if (typeof value === 'string' && value.trim()) {
            return value.trim();
        }
        return fallback;
    };

    const safe = {
        bar: toColor(colors.bar, 'rgba(54, 162, 235, 0.6)'),
        border: toColor(colors.border, 'rgba(54, 162, 235, 1)'),
        grid: toColor(colors.grid, 'rgba(226, 232, 240, 0.25)'),
        text: toColor(colors.text, '#2d3748'),
        tooltipBg: toColor(colors.tooltipBg, '#333333')
    };

    chartInstance.data.datasets.forEach((dataset) => {
        dataset.backgroundColor = safe.bar;
        dataset.borderColor = safe.border;
    });

    const { scales, plugins } = chartInstance.options;

    if (scales?.x?.ticks) {
        scales.x.ticks.color = safe.text;
    }

    if (scales?.y?.ticks) {
        scales.y.ticks.color = safe.text;
    }

    if (scales?.x?.grid) {
        scales.x.grid.color = safe.grid;
    }

    if (scales?.y?.grid) {
        scales.y.grid.color = safe.grid;
    }

    if (plugins?.legend?.labels) {
        plugins.legend.labels.color = safe.text;
    }

    if (plugins?.tooltip) {
        plugins.tooltip.backgroundColor = safe.tooltipBg;
        plugins.tooltip.titleColor = safe.text;
        plugins.tooltip.bodyColor = safe.text;
    }

    chartInstance.update('none');
}

// Load saved evaluator selection
function loadSavedEvaluator() {
    const saved = localStorage.getItem('selectedEvaluator');
    return saved || null;
}

// Save evaluator selection
function saveEvaluator(evaluator) {
    localStorage.setItem('selectedEvaluator', evaluator);
}

// Load papers data
async function loadPapers() {
    try {
        const response = await fetch('/reviews/evaluation-data-all-venues.json');
        allPapers = await response.json();

        // Initialize evaluator dropdown
        initializeEvaluatorDropdown();

        // Load saved evaluator and display if exists
        const savedEvaluator = loadSavedEvaluator();
        if (savedEvaluator) {
            document.getElementById('evaluator-selector').value = savedEvaluator;
            selectEvaluator(savedEvaluator);
        }
    } catch (error) {
        console.error('Error loading papers:', error);
        alert('Error loading papers data. Please check console for details.');
    }
}

// Initialize evaluator dropdown
function initializeEvaluatorDropdown() {
    const evaluators = new Set();

    allPapers.forEach(paper => {
        paper.evaluators.forEach(e => evaluators.add(e));
    });

    const sortedEvaluators = Array.from(evaluators).sort();
    const dropdown = document.getElementById('evaluator-selector');

    sortedEvaluators.forEach(evaluator => {
        const option = document.createElement('option');
        option.value = evaluator;
        option.textContent = evaluator;
        dropdown.appendChild(option);
    });

    // Add change event listener
    dropdown.addEventListener('change', (e) => {
        if (e.target.value) {
            selectEvaluator(e.target.value);
        } else {
            hideAllSections();
        }
    });
}

// Hide all dashboard sections
function hideAllSections() {
    document.getElementById('stats-section').style.display = 'none';
    document.getElementById('continue-section').style.display = 'none';
    document.getElementById('chart-section').style.display = 'none';
    document.getElementById('papers-section').style.display = 'none';
    document.getElementById('empty-state').style.display = 'block';
}

// Select evaluator and display dashboard
function selectEvaluator(evaluator) {
    selectedEvaluator = evaluator;
    saveEvaluator(evaluator);

    // Filter papers for this evaluator
    const evaluatorPapers = allPapers.filter(paper =>
        paper.evaluators.includes(evaluator)
    );

    // Hide empty state and show sections
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('stats-section').style.display = 'block';
    document.getElementById('continue-section').style.display = 'block';
    document.getElementById('chart-section').style.display = 'block';
    document.getElementById('papers-section').style.display = 'block';

    // Update statistics (both sidebar and stats bar)
    updateStatistics(evaluatorPapers);
    updateStatsBar(evaluatorPapers);

    // Update chart
    updateChart(evaluatorPapers);

    // Update papers list
    updatePapersList(evaluatorPapers);
}

// Update statistics (sidebar)
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

    document.getElementById('total-papers').textContent = stats.total;
    document.getElementById('completed-papers').textContent = stats.completed;
    document.getElementById('in-progress-papers').textContent = stats.in_progress;
    document.getElementById('not-started-papers').textContent = stats.not_started;
}

// Update statistics bar (top of papers list)
function updateStatsBar(papers) {
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

    document.getElementById('evaluator-total-results').textContent = stats.total;
    document.getElementById('evaluator-completed-count').textContent = stats.completed;
    document.getElementById('evaluator-in-progress-count').textContent = stats.in_progress;
    document.getElementById('evaluator-not-started-count').textContent = stats.not_started;
}

// Update chart
function updateChart(papers) {
    // Count papers by research area
    const areaCounts = {};

    papers.forEach(paper => {
        paper.primary_area.forEach(area => {
            areaCounts[area] = (areaCounts[area] || 0) + 1;
        });
    });

    // Sort areas by count (descending)
    const sortedAreas = Object.entries(areaCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10); // Show top 10 areas

    const labels = sortedAreas.map(([area, count]) => {
        // Truncate long area names
        return area.length > 40 ? area.substring(0, 37) + '...' : area;
    });
    const data = sortedAreas.map(([area, count]) => count);

    // Destroy existing chart if it exists
    if (chart) {
        chart.destroy();
    }

    // Create new chart
    const ctx = document.getElementById('research-area-chart').getContext('2d');
    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Papers',
                data: data,
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0,
                        autoSkip: false,
                        callback: function(value) {
                            const label = this.getLabelForValue(value);
                            return label.length > 30 ? label.slice(0, 27) + '...' : label;
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            // Show full area name in tooltip
                            const index = context[0].dataIndex;
                            return sortedAreas[index][0];
                        }
                    }
                }
            }
        }
    });

    applyChartTheme(chart);
}

// Update papers list
function updatePapersList(papers) {
    const container = document.getElementById('evaluator-papers-list');

    if (papers.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No Papers Found</h3>
                <p>This evaluator has no assigned papers.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = papers.map((paper, index) => {
        const progress = calculateProgress(paper);
        const paperIndex = allPapers.indexOf(paper);

        return `
            <div class="paper-card" onclick="openPaper(${paperIndex})">
                <div>
                    <h3 class="paper-title">${paper.title}</h3>
                    <ul class="paper-meta">
                        <li>${createStatusBadge(paper.status, progress.completed, progress.total)}</li>
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

// Open paper evaluation page
function openPaper(paperIndex) {
    window.location.href = `evaluate.html?paper=${paperIndex}`;
}

// Continue Evaluation button handler
document.getElementById('continue-evaluation-btn').addEventListener('click', () => {
    if (!selectedEvaluator) {
        alert('Please select an evaluator first.');
        return;
    }

    // Set the evaluator filter in localStorage
    const filters = {
        evaluators: [selectedEvaluator],
        areas: [],
        keywords: [],
        titleKeywords: [],
        statuses: []
    };
    localStorage.setItem('reviewFilters', JSON.stringify(filters));

    // Navigate to main papers page
    window.location.href = 'index.html';
});

document.addEventListener('themechange', () => {
    if (chart) {
        applyChartTheme(chart);
    }
});

// Load papers on page load
loadPapers();
