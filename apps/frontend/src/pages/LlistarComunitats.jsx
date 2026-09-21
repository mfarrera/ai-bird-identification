import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../Layout'

const API_URL = 'http://127.0.0.1:8000'

function LlistarComunitats() {
  const navigate = useNavigate()
  const [communities, setCommunities] = useState([])
  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')
  const [joiningId, setJoiningId] = useState(null)

  const carregarComunitats = async () => {
    try {
      setError('')

      const token = localStorage.getItem('token')

      const res = await fetch(`${API_URL}/api/communities`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error carregant comunitats')
      }

      setCommunities(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    carregarComunitats()
  }, [])

  const unirme = async (communityId) => {
    try {
      setError('')
      setMissatge('')
      setJoiningId(communityId)

      const token = localStorage.getItem('token')

      const res = await fetch(`${API_URL}/api/communities/${communityId}/members`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error unint-te a la comunitat')
      }

      setMissatge('T\'has unit a la comunitat correctament')
    } catch (err) {
      setError(err.message)
    } finally {
      setJoiningId(null)
    }
  }

  return (
    <Layout
      title="Llista de comunitats"
      subtitle="Comunitats creades a la plataforma."
    >
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        {missatge && <div className="alert alert-success">{missatge}</div>}

        <div className="btn-row">
          <button className="btn btn-primary" onClick={() => navigate('/crear-comunitat')}>
            + Crear comunitat
          </button>
        </div>

        {communities.length === 0 && !error && (
          <p className="muted">No hi ha comunitats.</p>
        )}

        <div className="entity-list">
          {communities.map((community) => (
            <div className="entity-card" key={community.id}>
              <p><strong>ID:</strong> {community.id}</p>
              <p><strong>Nom:</strong> {community.name}</p>
              <p><strong>Líder:</strong> {community.leader_mail || 'Sense líder'}</p>

              <div className="btn-row">
                <button
                  className="btn"
                  disabled={joiningId === community.id}
                  onClick={() => unirme(community.id)}
                >
                  {joiningId === community.id ? 'Unint-te...' : 'Unir-me'}
                </button>
                <button
                  className="btn btn-primary"
                  onClick={() => navigate(`/comunitats/${community.id}`)}
                >
                  Administrar comunitat
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="btn-row">
          <button className="btn" onClick={() => navigate('/principal')}>
            Tornar al dashboard
          </button>
        </div>
      </div>
    </Layout>
  )
}

export default LlistarComunitats
