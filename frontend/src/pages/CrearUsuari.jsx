import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

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
    <div style={{ padding: '30px', fontFamily: 'Arial', textAlign: 'center' }}>
      <h1>Crear usuari</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p style={{ color: 'green' }}>{missatge}</p>}

      <form onSubmit={handleRegister}>
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

        <button type="submit">Crear usuari</button>
      </form>

      <div style={{ marginTop: '20px' }}>
        <button onClick={() => navigate('/')}>
          Tornar a inici de sessió
        </button>
      </div>
    </div>
  )
}

export default CrearUsuari