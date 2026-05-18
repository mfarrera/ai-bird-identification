import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API_URL = 'http://127.0.0.1:8000'

function IniciSessio() {
  const [mail, setMail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')

    try {
      const res = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mail, password })
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error en iniciar sessió')
      }

      // Guardem el token de sessió
      localStorage.setItem('token', data.token)

      // Guardem la informació bàsica de l'usuari
      localStorage.setItem('usuari', JSON.stringify(data.user))

      // Redirecció segons rol
      if (data.user.role_id === 1) {
        navigate('/admin')
      } else {
        navigate('/principal')
      }
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div style={{ padding: '30px', fontFamily: 'Arial', textAlign: 'center' }}>
      <h1>Inici de sessió</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      <form onSubmit={handleLogin}>
        <div style={{ marginBottom: '10px' }}>
          <input
            type="email"
            placeholder="Correu electrònic"
            value={mail}
            onChange={(e) => setMail(e.target.value)}
          />
        </div>

        <div style={{ marginBottom: '10px' }}>
          <input
            type="password"
            placeholder="Contrasenya"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <button type="submit">Iniciar sessió</button>
      </form>

      <div style={{ marginTop: '30px' }}>
        <button onClick={() => navigate('/crear-usuari')}>
          Crear nou usuari
        </button>
      </div>
    </div>
  )
}

export default IniciSessio