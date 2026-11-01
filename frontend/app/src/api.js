/**
 * HTTP client for the LegacyLift FastAPI backend.
 *
 * `npm run dev` and `npm run preview` on this machine leave VITE_API_URL empty.
 * Vite proxies `/api` and `/health` to http://127.0.0.1:8000. A hosted build
 * sets VITE_API_URL to the public API origin (no trailing slash, no `/api` suffix).
 */

function usesLocalProxy() {
  if (typeof window === 'undefined') return false
  const host = window.location.hostname
  return host === 'localhost' || host === '127.0.0.1' || host === '::1'
}

const apiUrl = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '')

function endpoint(path) {
  return `${apiUrl}${path}`
}

function detailMessage(data, fallback) {
  const detail = data && data.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'string' ? item : item.msg || JSON.stringify(item)))
      .join(' ')
  }
  return fallback
}

/** localStorage key agreed with the login routes. The login page writes it. */
export const tokenStorageKey = 'legacylift-token'

export function saveToken(token) {
  localStorage.setItem(tokenStorageKey, token)
}

export function clearToken() {
  localStorage.removeItem(tokenStorageKey)
}

function readToken() {
  try {
    return localStorage.getItem(tokenStorageKey) || ''
  } catch {
    return ''
  }
}

function withAuth(options) {
  const headers = { ...(options.headers || {}) }
  const token = readToken()
  if (token && !headers.Authorization && !headers.authorization) {
    headers.Authorization = `Bearer ${token}`
  }
  return { ...options, headers }
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(endpoint(path), withAuth(options))
  } catch {
    throw new Error('Cannot reach the LegacyLift backend. Check the API connection and try again.')
  }

  if (response.status === 204) return null
  const data = await response.json().catch(() => ({}))
  if (response.status === 401) clearToken()
  if (!response.ok) {
    if (response.status === 413) {
      throw new Error(`That upload is too large. The API rejects a request over 1.2 MB.`)
    }
    throw new Error(detailMessage(data, `Request failed (${response.status}).`))
  }
  return data
}

/**
 * True when `/health` and `/api` can be requested.
 * Dev and localhost preview use the Vite proxy. Hosted pages need VITE_API_URL.
 * Whether that backend is up is checkBackend(), not this flag.
 */
export const apiConfigured = import.meta.env.DEV || usesLocalProxy() || Boolean(apiUrl)

/** Probe FastAPI /health. Use this to enable Convert only when the API is up. */
export async function checkBackend() {
  try {
    const data = await request('/health', { method: 'GET', cache: 'no-store' })
    return data && (data.status === 'ok' || Boolean(data.message))
  } catch {
    return false
  }
}

/**
 * Batch-convert COBOL File objects through POST /api/convert.
 * Returns `{ download_id, files }`. Each file is
 * `{ source_name, python_name, program_name, python, notes }`.
 */
export async function convertFiles(files) {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  return request('/api/convert', { method: 'POST', body: form })
}

/**
 * Download one generated Python file from the API and save it in the browser.
 * `path` is a project run file or a batch conversion file. The bytes come from
 * that response, not from Python already held on the page.
 */
export async function downloadPythonFile(path, fileName) {
  let response
  try {
    response = await fetch(endpoint(path), withAuth({}))
  } catch {
    throw new Error('Cannot reach the LegacyLift backend. Check the API connection and try again.')
  }
  if (response.status === 401) {
    const data = await response.json().catch(() => ({}))
    failAuth(data)
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(detailMessage(data, `Request failed (${response.status}).`))
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export async function createProject(name) {
  return request('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
}

/** Ask the backend for a new project containing the longer COBOL example. */
export async function createDemoProject() {
  return request('/api/projects/demo', { method: 'POST' })
}

export async function uploadProjectFiles(projectId, files) {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  return request(`/api/projects/${projectId}/files`, { method: 'POST', body: form })
}

/**
 * Convert every .cbl/.cob program already stored on a project
 * (POST /api/projects/{id}/convert). Uses the same converter as /api/convert.
 */
export async function convertProject(projectId) {
  const data = await request(`/api/projects/${projectId}/convert`, { method: 'POST' })
  return data
}

/**
 * Count files and return COPY, CALL, and PERFORM Links
 * (POST /api/projects/{id}/analyze).
 */
export async function analyzeProject(projectId) {
  const data = await request(`/api/projects/${projectId}/analyze`, { method: 'POST' })
  return data
}

/**
 * Compare each program's COBOL and Python output
 * (POST /api/projects/{id}/verify).
 */
export async function verifyProject(projectId) {
  const data = await request(`/api/projects/${projectId}/verify`, { method: 'POST' })
  return data
}

/**
 * Ask Gemini to compare each converted program with its Python
 * (POST /api/projects/{id}/ai-review).
 * Returns `{ project_id, run_id, status, model, files }`.
 * `status` is `clear` or `concerns`. Each file has `matches` and `concerns`;
 * each finding is `{ cobol_lines, python_lines, detail }`.
 */
export async function reviewProject(projectId) {
  return request(`/api/projects/${projectId}/ai-review`, { method: 'POST' })
}

/** GET /api/projects. Newest first, with file counts and the last run, without file contents. */
export async function listProjects() {
  return request('/api/projects', { method: 'GET' })
}

/** DELETE /api/projects/{id}. Removes the project, its files, and its runs (204). */
export async function deleteProject(projectId) {
  return request(`/api/projects/${projectId}`, { method: 'DELETE' })
} 

export async function getProject(projectId) {
  return request(`/api/projects/${projectId}`, { method: 'GET' })
}

export async function  getRuns(projectId) {
  return request(`/api/projects/${projectId}/runs`, { method: 'GET' })
}

export async function getRun(projectId, runId) {
  return request(`/api/projects/${projectId}/runs/${runId}`, { method: 'GET' })
}

/** POST /api/auth/register. Returns the account without a password or hash. */
export async function register(email, password, displayName) {
  return request('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, display_name: displayName }),
  })
}

/**
 * POST /api/auth/login. Saves the token in localStorage.
 * Returns `{ token, token_type, expires_in }`.
 */
export async function login(email, password) {
  const data = await request('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (data?.token) saveToken(data.token)
  return data
}

/** Drop the saved token. The next request is logged out. */
export function logout() {
  clearToken()
}

/** GET /api/auth/me, using the saved token. */
export async function getMe() {
  return request('/api/auth/me', { method: 'GET' })
}