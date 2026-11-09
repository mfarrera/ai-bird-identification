import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../Layout'

const API_URL = 'http://127.0.0.1:8000'

function Principal() {
  const navigate = useNavigate()
  const usuari = JSON.parse(localStorage.getItem('usuari') || 'null')
  const [cameres, setCameres] = useState([])
  const [carregant, setCarregant] = useState(true)
  const [error, setError] = useState('')

  const [mesVistes, setMesVistes] = useState([])
  const [carregantMesVistes, setCarregantMesVistes] = useState(true)

  const [stats, setStats] = useState(null)
  const [carregantStats, setCarregantStats] = useState(true)

  const [miniatures, setMiniatures] = useState({})

  useEffect(() => {
    if (!usuari) {
      navigate('/')
      return
    }

    fetch(`${API_URL}/api/cameras`)
      .then((res) => res.json())
      .then((data) => {
        const meves = data.filter((c) => c.owner_id === usuari.id)
        setCameres(meves)
      })
      .catch(() => setError('No s\'han pogut carregar les càmeres'))
      .finally(() => setCarregant(false))

    const token = localStorage.getItem('token')
    fetch(`${API_URL}/api/users/me/cameras/most-viewed`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setMesVistes(Array.isArray(data) ? data : []))
      .catch(() => setMesVistes([]))
      .finally(() => setCarregantMesVistes(false))

    fetch(`${API_URL}/api/users/me/detections/stats`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setStats(data))
      .catch(() => setStats(null))
      .finally(() => setCarregantStats(false))
  }, [])

  useEffect(() => {
    const token = localStorage.getItem('token')
    const ids = new Set([
      ...cameres.map((c) => c.id),
      ...mesVistes.map((c) => c.id)
    ])

    ids.forEach((id) => {
      fetch(`${API_URL}/api/cameras/${id}/detections?limit=1`, {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then((res) => (res.ok ? res.json() : []))
        .then((data) => {
          if (Array.isArray(data) && data.length > 0 && data[0].url) {
            setMiniatures((prev) => ({ ...prev, [id]: data[0].url }))
          }
        })
        .catch(() => {})
    })
  }, [cameres, mesVistes])

  return (
    <Layout
      title={`Bon dia${usuari ? `, ${usuari.mail}` : ''} 🌤️`}
      subtitle="Resum de les teves càmeres i deteccions."
    >
      <div className="stats">
        <div className="stat-card">
          <div className="label">Càmeres actives</div>
          <div className="value">{carregant ? '…' : cameres.length}</div>
        </div>
        <div className="stat-card">
          <div className="label">Deteccions avui</div>
          <div className="value">
            {carregantStats ? '…' : (stats ? stats.detections_today : '—')}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Espècies identificades</div>
          <div className="value">
            {carregantStats ? '…' : (stats ? stats.species_identified : '—')}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">En procés</div>
          <div className="value">
            {carregantStats ? '…' : (stats ? stats.in_progress : '—')}
          </div>
        </div>
      </div>

      {!carregantMesVistes && mesVistes.length > 0 && (
        <div className="panel">
          <h2>Càmeres més vistes</h2>
          <div className="entity-list">
            {mesVistes.map((c) => (
              <div className="entity-row" key={c.id}>
                {miniatures[c.id] ? (
                  <img src={miniatures[c.id]} alt="" className="thumb-img" />
                ) : (
                  <span className="thumb">🎥</span>
                )}
                <div className="entity-info">
                  <div className="title">Càmera #{c.id}</div>
                  <div className="meta">{c.url}</div>
                </div>
                <span className="badge">{c.views} {c.views === 1 ? 'visualització' : 'visualitzacions'}</span>
                <button
                  className="btn btn-primary"
                  style={{ marginLeft: '10px' }}
                  onClick={() => navigate(`/camera/${c.id}/stream`)}
                >
                  Veure
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel">
        <h2>Les teves càmeres</h2>

        {error && <div className="alert alert-error">{error}</div>}

        {!carregant && cameres.length === 0 && !error && (
          <p className="muted">Encara no tens cap càmera registrada.</p>
        )}

        <div className="entity-list">
          {cameres.map((c) => (
            <div className="entity-row" key={c.id}>
              {miniatures[c.id] ? (
                <img src={miniatures[c.id]} alt="" className="thumb-img" />
              ) : (
                <span className="thumb">🎥</span>
              )}
              <div className="entity-info">
                <div className="title">Càmera #{c.id}</div>
                <div className="meta">{c.url}</div>
              </div>
              <button className="btn" onClick={() => navigate(`/camera/${c.id}/stream`)}>
                Veure
              </button>
            </div>
          ))}
        </div>

        <div className="btn-row">
          <button
            className="btn btn-primary"
            onClick={() => navigate('/admin/afegir-camera')}
          >
            + Sol·licitar càmera
          </button>
        </div>
      </div>
    </Layout>
  )
}

export default Principal
