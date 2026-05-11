import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API_URL = 'http://127.0.0.1:8000'

function EliminarCamera() {
  const [cameraId, setCameraId] = useState('')
  const [missatge, setMissatge] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleDelete = async (e) => {
    e.preventDefault()
    setMissatge('')
    setError('')

    try {
      const res = await fetch(`${API_URL}/api/cameras/${cameraId}`, {
        method: 'DELETE'
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Error en eliminar la càmera')

      setMissatge('Càmera eliminada correctament')
      setCameraId('')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div style={{ padding: '30px', textAlign: 'center' }}>
      <h1>Eliminar càmera</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p style={{ color: 'green' }}>{missatge}</p>}

      <form onSubmit={handleDelete}>
        <input type="number" placeholder="ID càmera" value={cameraId} onChange={(e) => setCameraId(e.target.value)} /><br /><br />
        <button type="submit">Eliminar</button>
      </form>

      <br />
      <button onClick={() => navigate('/admin')}>Tornar</button>
    </div>
  )
}

export default EliminarCamera