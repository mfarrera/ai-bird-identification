import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

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
    <div style={{ padding: '30px', textAlign: 'center' }}>
      <h1>Crear admin</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p style={{ color: 'green' }}>{missatge}</p>}

      <form onSubmit={handleSubmit}>
        <input type="email" placeholder="Correu" value={mail} onChange={(e) => setMail(e.target.value)} /><br /><br />
        <input type="password" placeholder="Contrasenya" value={password} onChange={(e) => setPassword(e.target.value)} /><br /><br />
        <button type="submit">Crear admin</button>
      </form>

      <br />
      <button onClick={() => navigate('/admin')}>Tornar</button>
    </div>
  )
}

export default CrearAdmin