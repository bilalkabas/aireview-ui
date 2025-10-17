(function () {
  const STORAGE_KEY = 'reviewTheme';
  const MEDIA_QUERY = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function readStoredPreference() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'dark' || stored === 'light') {
      return stored;
    }
    return null;
  }

  function systemPreference() {
    if (MEDIA_QUERY && typeof MEDIA_QUERY.matches === 'boolean') {
      return MEDIA_QUERY.matches ? 'dark' : 'light';
    }
    return 'light';
  }

  function resolveInitialTheme() {
    return readStoredPreference() || systemPreference();
  }

  function applyTheme(theme, { persist = false } = {}) {
    const isDark = theme === 'dark';
    document.body.classList.toggle('theme-dark', isDark);
    document.body.setAttribute('data-theme', theme);

    updateToggleButtons(isDark);

    if (persist) {
      localStorage.setItem(STORAGE_KEY, theme);
    }

    document.dispatchEvent(
      new CustomEvent('themechange', {
        detail: { theme, isDark },
      }),
    );
  }

  function updateToggleButtons(isDark) {
    const nextActionLabel = isDark ? 'Switch to light theme' : 'Switch to dark theme';
    const icon = isDark ? '🌙' : '☀️';
    const label = isDark ? 'Dark' : 'Light';

    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      button.classList.toggle('is-dark', isDark);
      button.setAttribute('aria-pressed', String(isDark));
      button.setAttribute('aria-label', nextActionLabel);
      button.setAttribute('title', nextActionLabel);

      const iconSpan = button.querySelector('.theme-toggle-icon');
      if (iconSpan) {
        iconSpan.textContent = icon;
      }

      const labelSpan = button.querySelector('.theme-toggle-label');
      if (labelSpan) {
        labelSpan.textContent = label;
      }
    });
  }

  function toggleTheme() {
    const isCurrentlyDark = document.body.classList.contains('theme-dark');
    const nextTheme = isCurrentlyDark ? 'light' : 'dark';
    applyTheme(nextTheme, { persist: true });
  }

  function handleSystemChange(event) {
    if (readStoredPreference()) {
      // Respect explicit user preference.
      return;
    }
    applyTheme(event.matches ? 'dark' : 'light');
  }

  function initialise() {
    const initialTheme = resolveInitialTheme();
    applyTheme(initialTheme);

    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      button.addEventListener('click', toggleTheme);
    });

    if (MEDIA_QUERY && typeof MEDIA_QUERY.addEventListener === 'function') {
      MEDIA_QUERY.addEventListener('change', handleSystemChange);
    } else if (MEDIA_QUERY && typeof MEDIA_QUERY.addListener === 'function') {
      // Fallback for older browsers.
      MEDIA_QUERY.addListener(handleSystemChange);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialise);
  } else {
    initialise();
  }
})();
