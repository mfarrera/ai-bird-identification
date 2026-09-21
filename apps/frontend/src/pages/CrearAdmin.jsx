import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../Layout'

const API_URL = 'http://127.0.0.1:8000'

function CrearAdmin() {
  const [mail, setMail] = useState('')
  const [password, setPassword] = useState('')
  const [missatge, setMissatge] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setMissatge('')
    setError('')

    try {
      const res = await fetch(`${API_URL}/api/users/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mail, password, role: 'admin' })
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Error en crear l’admin')

      setMissatge('Admin creat correctament')
      setMail('')
      setPassword('')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <Layout
      title="Crear admin"
      subtitle="Dona permisos d'administrador a un nou compte."
    >
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        {missatge && <div className="alert alert-success">{missatge}</div>}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Correu</label>
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

          <button className="btn btn-primary" type="submit">Crear admin</button>
        </form>

        <div className="btn-row">
          <button className="btn" onClick={() => navigate('/admin')}>Tornar</button>
        </div>
      </div>
    </Layout>
  )
}

export default CrearAdmin
