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

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(endpoint(path), options)
  } catch {
    throw new Error('Cannot reach the LegacyLift backend. Check the API connection and try again.')
  }

  if (response.status === 204) return null
  const data = await response.json().catch(() => ({}))
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
    response = await fetch(endpoint(path))
  } catch {
    throw new Error('Cannot reach the LegacyLift backend. Check the API connection and try again.')
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