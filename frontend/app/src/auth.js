import { createAuthClient } from '@neondatabase/auth'
import { BetterAuthReactAdapter } from '@neondatabase/auth/react/adapters'

// Public Neon Auth URL for this project. Set VITE_NEON_AUTH_URL to override it.
// An empty URL makes sign-in POST to this site, which answers 405.
const authUrl =
  import.meta.env.VITE_NEON_AUTH_URL ||
  'https://ep-jolly-tree-b5ygfgag.neonauth.c-7.us-east-2.aws.neon.tech/neondb/auth'

// credentials has to be on the adapter. This SDK only copies headers from the
// top-level fetchOptions into the auth client, so a cookie session would not
// be sent and authClient.token() would come back empty.
export const authClient = createAuthClient(authUrl, {
  fetchOptions: { credentials: 'include' },
  adapter: BetterAuthReactAdapter({
    fetchOptions: { credentials: 'include' },
  }),
})

/** JWT for the API. `token()` is missing on this SDK, so call the same `/token` route. */
export async function neonAccessToken() {
  if (typeof authClient.token === 'function') {
    const { data, error } = await authClient.token()
    if (error || !data?.token) return ''
    return data.token
  }
  const response = await fetch(`${authUrl}/token`, { credentials: 'include' })
  if (!response.ok) return ''
  const body = await response.json().catch(() => null)
  return body?.token || ''
}