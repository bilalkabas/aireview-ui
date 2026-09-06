// A small guided tour: a dimmed overlay with a cut-out around the step's target
// and a card explaining it. No dependencies, no framework.

const TOUR_SEEN_PREFIX = 'ensembleTourSeen:';

function hasSeenTour(key) {
    return localStorage.getItem(TOUR_SEEN_PREFIX + key) === 'true';
}

function markTourSeen(key) {
    localStorage.setItem(TOUR_SEEN_PREFIX + key, 'true');
}

function startTour(key, steps, options = {}) {
    // Steps whose target is missing are dropped, so a tour never points at nothing.
    const usable = steps.filter(step => !step.target || document.querySelector(step.target));
    if (usable.length === 0) return;

    const overlay = document.createElement('div');
    overlay.className = 'tour-overlay';
    overlay.innerHTML = `
        <div class="tour-hole" hidden></div>
        <div class="tour-card" role="dialog" aria-modal="true" aria-labelledby="tour-title">
            <div class="tour-step-count"></div>
            <h3 id="tour-title" class="tour-title"></h3>
            <p class="tour-body"></p>
            <div class="tour-actions">
                <button type="button" class="tour-skip">Skip</button>
                <div class="tour-nav">
                    <button type="button" class="tour-back">Back</button>
                    <button type="button" class="tour-next primary-button">Next</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    document.body.classList.add('tour-open');

    const hole = overlay.querySelector('.tour-hole');
    const card = overlay.querySelector('.tour-card');
    const countEl = overlay.querySelector('.tour-step-count');
    const titleEl = overlay.querySelector('.tour-title');
    const bodyEl = overlay.querySelector('.tour-body');
    const backBtn = overlay.querySelector('.tour-back');
    const nextBtn = overlay.querySelector('.tour-next');
    const skipBtn = overlay.querySelector('.tour-skip');

    let index = 0;

    function finish() {
        markTourSeen(key);
        document.body.classList.remove('tour-open');
        overlay.remove();
        window.removeEventListener('resize', place);
        window.removeEventListener('scroll', place, true);
        document.removeEventListener('keydown', onKey);
        if (typeof options.onFinish === 'function') options.onFinish();
    }

    function place() {
        const step = usable[index];
        const target = step.target ? document.querySelector(step.target) : null;

        if (!target) {
            // A step with no anchor is centred, like a welcome panel.
            hole.hidden = true;
            card.style.top = '50%';
            card.style.left = '50%';
            card.style.transform = 'translate(-50%, -50%)';
            return;
        }

        const pad = 8;
        const margin = 16;
        const raw = target.getBoundingClientRect();

        // Clamp to the viewport so the highlight border stays visible for a target
        // taller or wider than the screen.
        const box = {
            top: Math.max(pad, raw.top - pad),
            left: Math.max(pad, raw.left - pad),
            bottom: Math.min(window.innerHeight - pad, raw.bottom + pad),
            right: Math.min(window.innerWidth - pad, raw.right + pad)
        };
        hole.hidden = false;
        hole.style.top = `${box.top}px`;
        hole.style.left = `${box.left}px`;
        hole.style.width = `${Math.max(0, box.right - box.left)}px`;
        hole.style.height = `${Math.max(0, box.bottom - box.top)}px`;

        card.style.transform = 'none';
        const { width: cw, height: ch } = card.getBoundingClientRect();
        const clamp = (v, lo, hi) => Math.max(lo, Math.min(v, hi));
        const midX = clamp(box.left + (box.right - box.left) / 2 - cw / 2, margin, window.innerWidth - margin - cw);
        const midY = clamp(box.top + (box.bottom - box.top) / 2 - ch / 2, margin, window.innerHeight - margin - ch);

        // Try each side in turn and take the first that clears the highlight, so the
        // card never covers what it is describing.
        const candidates = [
            { top: box.bottom + margin, left: midX, fits: box.bottom + margin + ch <= window.innerHeight - margin },
            { top: box.top - margin - ch, left: midX, fits: box.top - margin - ch >= margin },
            { top: midY, left: box.right + margin, fits: box.right + margin + cw <= window.innerWidth - margin },
            { top: midY, left: box.left - margin - cw, fits: box.left - margin - cw >= margin }
        ];
        const spot = candidates.find(c => c.fits)
            || { top: clamp(window.innerHeight - margin - ch, margin, window.innerHeight), left: midX };

        card.style.top = `${clamp(spot.top, margin, Math.max(margin, window.innerHeight - margin - ch))}px`;
        card.style.left = `${clamp(spot.left, margin, Math.max(margin, window.innerWidth - margin - cw))}px`;
    }

    function render() {
        const step = usable[index];
        countEl.textContent = `Step ${index + 1} of ${usable.length}`;
        titleEl.textContent = step.title;
        bodyEl.textContent = step.body;
        backBtn.hidden = index === 0;
        nextBtn.textContent = index === usable.length - 1 ? 'Got it' : 'Next';

        const target = step.target ? document.querySelector(step.target) : null;
        if (target) target.scrollIntoView({ block: 'center', behavior: 'smooth' });
        // Let the smooth scroll settle before measuring.
        setTimeout(place, target ? 320 : 0);
        place();
    }

    function onKey(event) {
        if (event.key === 'Escape') finish();
        else if (event.key === 'ArrowRight') nextBtn.click();
        else if (event.key === 'ArrowLeft' && index > 0) backBtn.click();
    }

    nextBtn.addEventListener('click', () => {
        if (index === usable.length - 1) return finish();
        index += 1;
        render();
    });
    backBtn.addEventListener('click', () => {
        if (index === 0) return;
        index -= 1;
        render();
    });
    skipBtn.addEventListener('click', finish);
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    document.addEventListener('keydown', onKey);

    render();
}
