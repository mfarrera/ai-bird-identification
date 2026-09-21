import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthLayout from '../AuthLayout'

const API_URL = 'http://127.0.0.1:8000'

function CrearUsuari() {
  const [mail, setMail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')
  const navigate = useNavigate()

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')
    setMissatge('')

    try {
      const res = await fetch(`${API_URL}/api/users/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mail,
          password,
          role: 'user'
        })
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error en crear l’usuari')
      }

      setMissatge('Usuari creat correctament')
      setMail('')
      setPassword('')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <AuthLayout
      title="Crear usuari"
      subtitle="Registra't per començar a fer servir Aviari."
    >
      {error && <div className="alert alert-error">{error}</div>}
      {missatge && <div className="alert alert-success">{missatge}</div>}

      <form onSubmit={handleRegister}>
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

        <button className="btn btn-primary" type="submit">Crear usuari</button>
      </form>

      <div className="btn-row" style={{ justifyContent: 'center', marginTop: '18px' }}>
        <button className="btn" onClick={() => navigate('/')}>
          Tornar a inici de sessió
        </button>
      </div>
    </AuthLayout>
  )
}

export default CrearUsuari
