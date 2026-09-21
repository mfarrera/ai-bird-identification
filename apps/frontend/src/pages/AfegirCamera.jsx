import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../Layout'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

function AfegirCamera() {
  const navigate = useNavigate()

  const [url, setUrl] = useState('')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()

    setError('')
    setMissatge('')

    const token = localStorage.getItem('token')

    if (!token) {
      navigate('/')
      return
    }

    if (!url.trim() || latitude === '' || longitude === '') {
      setError('Has d’omplir tots els camps')
      return
    }

    try {
      setLoading(true)

      const res = await fetch(`${API_URL}/api/cameras/requests`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          url: url.trim(),
          latitude: Number(latitude),
          longitude: Number(longitude)
        })
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(
          data.detail || 'No s’ha pogut crear la sol·licitud'
        )
      }

      setMissatge(
        'Sol·licitud enviada correctament. Un administrador la revisarà.'
      )

      setUrl('')
      setLatitude('')
      setLongitude('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout
      title="Sol·licitar una càmera"
      subtitle="Envia les dades de la teva càmera perquè un administrador la validi."
    >
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        {missatge && <div className="alert alert-success">{missatge}</div>}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>URL de la càmera</label>
            <input
              className="input wide"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="rtsp://..."
            />
          </div>

          <div className="field">
            <label>Latitud</label>
            <input
              className="input"
              type="number"
              step="any"
              value={latitude}
              onChange={(e) => setLatitude(e.target.value)}
              placeholder="41.3851"
            />
          </div>

          <div className="field">
            <label>Longitud</label>
            <input
              className="input"
              type="number"
              step="any"
              value={longitude}
              onChange={(e) => setLongitude(e.target.value)}
              placeholder="2.1734"
            />
          </div>

          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? 'Enviant...' : 'Enviar sol·licitud'}
          </button>
        </form>

        <div className="btn-row">
          <button className="btn" onClick={() => navigate('/principal')}>Tornar</button>
        </div>
      </div>
    </Layout>
  )
}

export default AfegirCamera
