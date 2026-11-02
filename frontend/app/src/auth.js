import { createAuthClient } from '@neondatabase/auth'
import { BetterAuthReactAdapter } from '@neondatabase/auth/react/adapters'

// Public Neon Auth URL for this project. Set VITE_NEON_AUTH_URL to override it.
// An empty URL makes sign-in POST to this site, which answers 405.
const authUrl =
  import.meta.env.VITE_NEON_AUTH_URL ||
  'https://ep-jolly-tree-b5ygfgag.neonauth.c-7.us-east-2.aws.neon.tech/neondb/auth'

// credentials has to be on the adapter. This SDK only copies headers from the
// top-level fetchOptions into the auth client, so a cookie session would not
// be sent and the API would save the project with no owner.
export const authClient = createAuthClient(authUrl, {
  fetchOptions: { credentials: 'include' },
  adapter: BetterAuthReactAdapter({
    fetchOptions: { credentials: 'include' },
  }),
})

let cachedJwt = ''
let cachedJwtExp = 0

function isJwt(value) {
  return typeof value === 'string' && value.split('.').length === 3
}

function jwtFromBody(data) {
  if (isJwt(data?.token)) return data.token
  if (isJwt(data?.session?.token)) return data.session.token
  if (isJwt(data?.session?.access_token)) return data.session.access_token
  return ''
}

function jwtExpiry(token) {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = payload + '='.repeat((4 - (payload.length % 4)) % 4)
    const claims = JSON.parse(atob(padded))
    return typeof claims.exp === 'number' ? claims.exp * 1000 : 0
  } catch {
    return 0
  }
}

/** Drop the JWT kept for API calls. Sign-out and a new sign-in both need this. */
export function clearNeonAccessToken() {
  cachedJwt = ''
  cachedJwtExp = 0
}

/**
 * JWT for the signed-in Neon account.
 *
 * `authClient.token()` is served from the session cache once `useSession` has
 * run, and that cache body has no `token` field, so a project request went out
 * with no Authorization header and was saved with a null owner. A forced
 * session read copies `set-auth-jwt` onto the session; `/token` is the backup.
 */
export async function neonAccessToken() {
  const now = Date.now()
  if (cachedJwt && now < cachedJwtExp - 30_000) return cachedJwt

  let token = ''
  try {
    let headerToken = ''
    const { data, error } = await authClient.getSession({
      fetchOptions: {
        headers: { 'X-Force-Fetch': '1' },
        onSuccess(ctx) {
          const header = ctx?.response?.headers?.get?.('set-auth-jwt')
          if (isJwt(header)) headerToken = header
        },
      },
    })
    if (!error) token = headerToken || jwtFromBody(data)
  } catch {
    token = ''
  }

  if (!token && typeof authClient.token === 'function') {
    try {
      const { data, error } = await authClient.token()
      if (!error) token = jwtFromBody(data)
    } catch {
      token = ''
    }
  }

  if (!token) {
    try {
      const response = await fetch(`${authUrl}/token`, { credentials: 'include' })
      if (response.ok) {
        const body = await response.json().catch(() => null)
        token = jwtFromBody(body)
      }
    } catch {
      token = ''
    }
  }

  if (!token) return ''
  cachedJwt = token
  cachedJwtExp = jwtExpiry(token) || now + 60_000
  return token
}
