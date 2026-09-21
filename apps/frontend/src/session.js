const API_URL = 'http://127.0.0.1:8000'

let refreshTimeoutId = null

// Marge amb què renovem abans de caducar. Prou gran perquè, encara
// que l'usuari tingui la pestanya en segon pla i el navegador retardi
// els timers, hi hagi marge de sobra per intentar-ho.
const MARGE_RENOVACIO_MS = 5 * 60 * 1000

export function guardarSessio(token, expiresIso, usuari) {
  localStorage.setItem('token', token)
  localStorage.setItem('tokenExpires', expiresIso)
  if (usuari) {
    localStorage.setItem('usuari', JSON.stringify(usuari))
  }
  programarRenovacioSessio()
}

export function netejarSessio() {
  if (refreshTimeoutId) {
    clearTimeout(refreshTimeoutId)
    refreshTimeoutId = null
  }
  localStorage.removeItem('token')
  localStorage.removeItem('tokenExpires')
  localStorage.removeItem('usuari')
}

export function programarRenovacioSessio() {
  if (refreshTimeoutId) {
    clearTimeout(refreshTimeoutId)
    refreshTimeoutId = null
  }

  const expiresIso = localStorage.getItem('tokenExpires')
  const token = localStorage.getItem('token')

  if (!expiresIso || !token) return

  const expiresAt = new Date(expiresIso).getTime()
  const delay = Math.max(expiresAt - Date.now() - MARGE_RENOVACIO_MS, 0)

  refreshTimeoutId = setTimeout(renovarSessio, delay)
}

async function renovarSessio() {
  const tokenActual = localStorage.getItem('token')
  if (!tokenActual) return

  try {
    const res = await fetch(`${API_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${tokenActual}`
      }
    })

    if (!res.ok) {
      // El token ja no es recuperable (per exemple, l'usuari ha estat
      // massa temps sense obrir cap pagina): tanquem sessio netament
      // en lloc de deixar l'app en un estat d'error permanent.
      netejarSessio()
      window.location.href = '/'
      return
    }

    const data = await res.json()
    localStorage.setItem('token', data.token)
    localStorage.setItem('tokenExpires', data.expires)

    programarRenovacioSessio()
  } catch (err) {
    // Error de xarxa puntual (per exemple el backend reiniciant-se):
    // ho reintentem en un minut en lloc de tancar la sessio de cop.
    refreshTimeoutId = setTimeout(renovarSessio, 60000)
  }
}
