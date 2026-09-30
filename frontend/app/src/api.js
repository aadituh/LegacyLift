/**
 * HTTP client for the LegacyLift FastAPI backend.
 *
 * Local Vite (`npm run dev`) leaves VITE_API_URL empty and proxies `/api`
 * (and `/health`) to http://127.0.0.1:8000. Hosted builds set VITE_API_URL
 * to the public API origin (no trailing slash, no `/api` suffix).
 */

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

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(endpoint(path), options)
  } catch {
    throw new Error('Cannot reach the LegacyLift backend. Check the API connection and try again.')
  }

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(detailMessage(data, `Request failed (${response.status}).`))
  }
  return data
}

/** True when a hosted API URL is configured. Live readiness still uses checkBackend(). */
export const apiConfigured = import.meta.env.DEV || Boolean(apiUrl)

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
 * Returns the `files` array: { source_name, python_name, program_name, python, notes }.
 */
export async function convertFiles(files) {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  const data = await request('/api/convert', { method: 'POST', body: form })
  return data.files
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

export async function getProject(projectId) {
  return request(`/api/projects/${projectId}`, { method: 'GET' })
}
