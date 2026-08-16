/**
 * API client — fetch wrapper with token attachment.
 */

function getToken() { return localStorage.getItem("token"); }

async function request(method, path, { body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const t = getToken();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }
  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = new Error(data?.message || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export const get = (path, opts) => request("GET", path, opts);
export const post = (path, body, opts) => request("POST", path, { body, ...opts });

export const register = (firstName, lastName) =>
  post("/api/auth/register", { firstName, lastName }, { auth: false });

export const login = (firstName, lastName) =>
  post("/api/auth/login", { firstName, lastName }, { auth: false });

export const logActivity = (payload) => post("/api/activities", payload);

export const getLeaderboard = () => get("/api/leaderboard", { auth: false });

export const getDashboard = (userId) => get(`/api/users/${userId}/dashboard`);
