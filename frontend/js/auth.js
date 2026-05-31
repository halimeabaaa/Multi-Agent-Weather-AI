// Django API — tarayıcıdan erişilebilir adres (Docker: 8000)
const API_BASE = (() => {
    const host = window.location.hostname || 'localhost';
    if (host === 'localhost' || host === '127.0.0.1') {
        return 'http://localhost:8000';
    }
    return `http://${host}:8000`;
})();

function getAccessToken() {
    const token = localStorage.getItem('access');
    if (!token || token === 'undefined' || token === 'null') {
        return null;
    }
    return token;
}

function getRefreshToken() {
    const token = localStorage.getItem('refresh');
    if (!token || token === 'undefined' || token === 'null') {
        return null;
    }
    return token;
}

function setTokens(access, refresh) {
    if (access) {
        localStorage.setItem('access', access);
    }
    if (refresh) {
        localStorage.setItem('refresh', refresh);
    }
}

function clearTokens() {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
}

function isLoggedIn() {
    return Boolean(getAccessToken());
}

async function refreshAccessToken() {
    const refresh = getRefreshToken();
    if (!refresh) {
        return null;
    }

    const response = await fetch(`${API_BASE}/api/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
    });

    if (!response.ok) {
        return null;
    }

    const data = await response.json();
    setTokens(data.access, refresh);
    return data.access;
}

async function authFetch(url, options = {}) {
    let token = getAccessToken();
    const headers = {
        ...(options.headers || {}),
    };

    if (!headers['Content-Type'] && options.body) {
        headers['Content-Type'] = 'application/json';
    }

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    let response = await fetch(url, { ...options, headers });

    if (response.status === 401 && getRefreshToken()) {
        token = await refreshAccessToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
            response = await fetch(url, { ...options, headers });
        }
    }

    return response;
}

function redirectToLogin() {
    clearTokens();
    window.location.href = '/login.html';
}

function logout() {
    redirectToLogin();
}
