const base = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${base}/api${path}`, {
      ...options,
      signal: AbortSignal.timeout(12000),
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
  } catch {
    throw new Error('Our connection was interrupted. Please try again in a moment.');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check your details and try again.');
  }
  return data;
}

export const login = (username, password) => request('/auth/login', {
  method: 'POST', body: JSON.stringify({ username, password }),
});
export const getProfile = (token) => request('/auth/me', {
  headers: { Authorization: `Bearer ${token}` },
});
