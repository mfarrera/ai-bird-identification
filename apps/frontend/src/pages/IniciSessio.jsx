import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthLayout from '../AuthLayout'
import { guardarSessio } from '../session'

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

      guardarSessio(data.token, data.expires, data.user)

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
    <AuthLayout
      title="Inici de sessió"
      subtitle="Accedeix al teu compte per gestionar les teves càmeres."
    >
      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={handleLogin}>
        <div className="field">
          <label>Correu electrònic</label>
          <input
            className="input"
            type="email"
            value={mail}
            onChange={(e) => setMail(e.target.value)}
          />
        </div>

        <div className="field">
          <label>Contrasenya</label>
          <input
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <button className="btn btn-primary" type="submit">Iniciar sessió</button>
      </form>

      <div className="btn-row" style={{ justifyContent: 'center', marginTop: '18px' }}>
        <button className="btn" onClick={() => navigate('/crear-usuari')}>
          Crear nou usuari
        </button>
      </div>
    </AuthLayout>
  )
}

export default IniciSessio
