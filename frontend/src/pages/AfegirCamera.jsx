import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API_URL = 'http://127.0.0.1:8000'

function AfegirCamera() {
  const [url, setUrl] = useState('')
  const [ownerId, setOwnerId] = useState('')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [missatge, setMissatge] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setMissatge('')
    setError('')

    try {
      const res = await fetch(`${API_URL}/api/cameras`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          owner_id: Number(ownerId),
          latitude: Number(latitude),
          longitude: Number(longitude)
        })
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Error en afegir la càmera')

      setMissatge('Càmera creada correctament')
      setUrl('')
      setOwnerId('')
      setLatitude('')
      setLongitude('')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div style={{ padding: '30px', textAlign: 'center' }}>
      <h1>Afegir càmera</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p style={{ color: 'green' }}>{missatge}</p>}

      <form onSubmit={handleSubmit}>
        <input type="text" placeholder="URL" value={url} onChange={(e) => setUrl(e.target.value)} /><br /><br />
        <input type="number" placeholder="ID propietari" value={ownerId} onChange={(e) => setOwnerId(e.target.value)} /><br /><br />
        <input type="number" step="any" placeholder="Latitud" value={latitude} onChange={(e) => setLatitude(e.target.value)} /><br /><br />
        <input type="number" step="any" placeholder="Longitud" value={longitude} onChange={(e) => setLongitude(e.target.value)} /><br /><br />
        <button type="submit">Afegir càmera</button>
      </form>

      <br />
      <button onClick={() => navigate('/admin')}>Tornar</button>
    </div>
  )
}

export default AfegirCamera