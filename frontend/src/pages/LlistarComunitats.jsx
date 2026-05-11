import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API_URL = 'http://127.0.0.1:8000'

function LlistarComunitats() {
  const navigate = useNavigate()
  const [communities, setCommunities] = useState([])
  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')

  useEffect(() => {
    const carregarComunitats = async () => {
      try {
        setError('')
        setMissatge('Carregant comunitats...')

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
        setMissatge('')
      } catch (err) {
        setError(err.message)
        setMissatge('')
      }
    }

    carregarComunitats()
  }, [])

  return (
    <div style={{ padding: '30px', fontFamily: 'Arial' }}>
      <h1>Llista de comunitats</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p>{missatge}</p>}

      {communities.length === 0 && !error && <p>No hi ha comunitats.</p>}

      {communities.map((community) => (
        <div
          key={community.id}
          style={{
            border: '1px solid #ccc',
            borderRadius: '8px',
            padding: '15px',
            marginBottom: '15px'
          }}
        >
          <p><strong>ID:</strong> {community.id}</p>
          <p><strong>Nom:</strong> {community.name}</p>
          <p><strong>Líder:</strong> {community.leader_mail || 'Sense líder'}</p>

          <button onClick={() => navigate(`/admin/comunitats/${community.id}`)}>
            Administrar comunitat
          </button>
        </div>
      ))}

      <button onClick={() => navigate('/admin')}>
        Tornar al panell admin
      </button>
    </div>
  )
}

export default LlistarComunitats