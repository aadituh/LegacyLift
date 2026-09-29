// Vite proxies /api to port 8000 during local development.
const apiUrl = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '')

export const backendIsReady = import.meta.env.DEV || Boolean(apiUrl)

export async function convertFiles(files) {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }

  let response
  try {
    response = await fetch(`${apiUrl}/api/convert`, {
      method: 'POST',
      body: form,
    })
  } catch {
    throw new Error('Cannot reach the backend. Check that it is running and the API URL is correct.')
  }

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : `Conversion failed (${response.status}).`)
  }
  return data.files
}
