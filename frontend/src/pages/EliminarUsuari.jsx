import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API_URL = 'http://127.0.0.1:8000'

function EliminarUsuari() {
  const [userId, setUserId] = useState('')
  const [missatge, setMissatge] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleDelete = async (e) => {
    e.preventDefault()
    setMissatge('')
    setError('')

    try {
      const res = await fetch(`${API_URL}/api/users/${userId}`, {
        method: 'DELETE'
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Error en eliminar l’usuari')

      setMissatge('Usuari eliminat correctament')
      setUserId('')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div style={{ padding: '30px', textAlign: 'center' }}>
      <h1>Eliminar usuari</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p style={{ color: 'green' }}>{missatge}</p>}

      <form onSubmit={handleDelete}>
        <input type="number" placeholder="ID usuari" value={userId} onChange={(e) => setUserId(e.target.value)} /><br /><br />
        <button type="submit">Eliminar</button>
      </form>

      <br />
      <button onClick={() => navigate('/admin')}>Tornar</button>
    </div>
  )
}

export default EliminarUsuari