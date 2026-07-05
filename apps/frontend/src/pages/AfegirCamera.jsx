import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

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
    <div style={{ padding: '30px', fontFamily: 'Arial' }}>
      <h1>Sol·licitar una càmera</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p style={{ color: 'green' }}>{missatge}</p>}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '15px' }}>
          <label>URL de la càmera</label>
          <br />
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="rtsp://..."
            style={{ width: '400px' }}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label>Latitud</label>
          <br />
          <input
            type="number"
            step="any"
            value={latitude}
            onChange={(e) => setLatitude(e.target.value)}
            placeholder="41.3851"
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label>Longitud</label>
          <br />
          <input
            type="number"
            step="any"
            value={longitude}
            onChange={(e) => setLongitude(e.target.value)}
            placeholder="2.1734"
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Enviant...' : 'Enviar sol·licitud'}
        </button>
      </form>

      <div style={{ marginTop: '20px' }}>
        <button onClick={() => navigate('/principal')}>
          Tornar
        </button>
      </div>
    </div>
  )
}

export default AfegirCamera