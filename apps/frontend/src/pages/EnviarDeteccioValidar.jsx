import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../Layout'

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
    <Layout
      title="Enviar detecció a validar"
      subtitle="Força l'enviament d'una detecció a la fase de validació."
    >
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        {missatge && <div className="alert alert-success">{missatge}</div>}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>ID detecció</label>
            <input
              className="input"
              type="number"
              value={detectionId}
              onChange={(e) => setDetectionId(e.target.value)}
            />
          </div>

          <button className="btn btn-primary" type="submit">Enviar</button>
        </form>

        <div className="btn-row">
          <button className="btn" onClick={() => navigate('/admin')}>Tornar</button>
        </div>
      </div>
    </Layout>
  )
}

export default EnviarDeteccioValidar
