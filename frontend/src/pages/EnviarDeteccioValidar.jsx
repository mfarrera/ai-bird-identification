import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API_URL = 'http://127.0.0.1:8000'

function EnviarDeteccioValidar() {
  const [detectionId, setDetectionId] = useState('')
  const [missatge, setMissatge] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setMissatge('')
    setError('')

    try {
      const res = await fetch(`${API_URL}/api/detections/${detectionId}/send-to-validate`, {
        method: 'POST'
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Error en enviar la detecció a validar')

      setMissatge('Detecció enviada a validació correctament')
      setDetectionId('')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div style={{ padding: '30px', textAlign: 'center' }}>
      <h1>Enviar detecció a validar</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p style={{ color: 'green' }}>{missatge}</p>}

      <form onSubmit={handleSubmit}>
        <input type="number" placeholder="ID detecció" value={detectionId} onChange={(e) => setDetectionId(e.target.value)} /><br /><br />
        <button type="submit">Enviar</button>
      </form>

      <br />
      <button onClick={() => navigate('/admin')}>Tornar</button>
    </div>
  )
}

export default EnviarDeteccioValidar