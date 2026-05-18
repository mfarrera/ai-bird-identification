import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API_URL = 'http://127.0.0.1:8000'

function CrearComunitat() {
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [searchEmail, setSearchEmail] = useState('')
  const [userResults, setUserResults] = useState([])
  const [leader, setLeader] = useState(null)
  const [members, setMembers] = useState([])
  const [cameras, setCameras] = useState([])
  const [selectedCameras, setSelectedCameras] = useState([])
  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [loadingCameras, setLoadingCameras] = useState(false)
  const [creating, setCreating] = useState(false)

  const getToken = () => localStorage.getItem('token')

  const buscarUsuaris = async () => {
    if (!searchEmail.trim()) {
      setUserResults([])
      return
    }

    try {
      setError('')
      setLoadingUsers(true)

      const res = await fetch(
        `${API_URL}/api/users/search?email=${encodeURIComponent(searchEmail)}`,
        {
          headers: {
            Authorization: `Bearer ${getToken()}`
          }
        }
      )

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error cercant usuaris')
      }

      setUserResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoadingUsers(false)
    }
  }

  const carregarCameres = async () => {
    try {
      setError('')
      setLoadingCameras(true)

      const res = await fetch(`${API_URL}/api/cameras`, {
        headers: {
          Authorization: `Bearer ${getToken()}`
        }
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error carregant les càmeres')
      }

      setCameras(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoadingCameras(false)
    }
  }

  const afegirMembre = (user) => {
    const exists = members.some((m) => m.id === user.id)
    if (!exists) {
      setMembers([...members, user])
    }
  }

  const eliminarMembre = (userId) => {
    setMembers(members.filter((m) => m.id !== userId))

    if (leader && leader.id === userId) {
      setLeader(null)
    }
  }

  const toggleCamera = (camera) => {
    const exists = selectedCameras.some((c) => c.id === camera.id)

    if (exists) {
      setSelectedCameras(selectedCameras.filter((c) => c.id !== camera.id))
    } else {
      setSelectedCameras([...selectedCameras, camera])
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setMissatge('')

    if (!name.trim()) {
      setError('Has d’introduir un nom de comunitat')
      return
    }

    if (!leader) {
      setError('Has de seleccionar un líder')
      return
    }

    try {
      setCreating(true)

      // 1. Crear comunitat
      const createRes = await fetch(`${API_URL}/api/communities`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`
        },
        body: JSON.stringify({
          name,
          leader_id: leader.id
        })
      })

      const createData = await createRes.json()

      if (!createRes.ok) {
        throw new Error(createData.detail || 'Error creant la comunitat')
      }

      const communityId = createData.community.id

      // 2. Afegir membres
      if (members.length > 0) {
        const membersRes = await fetch(`${API_URL}/api/communities/${communityId}/members`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`
          },
          body: JSON.stringify({
            user_ids: members.map((m) => m.id)
          })
        })

        const membersData = await membersRes.json()

        if (!membersRes.ok) {
          throw new Error(membersData.detail || 'Error afegint membres')
        }
      }

      // 3. Afegir càmeres
      if (selectedCameras.length > 0) {
        const camerasRes = await fetch(`${API_URL}/api/communities/${communityId}/cameras`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`
          },
          body: JSON.stringify({
            camera_ids: selectedCameras.map((c) => c.id)
          })
        })

        const camerasData = await camerasRes.json()

        if (!camerasRes.ok) {
          throw new Error(camerasData.detail || 'Error afegint càmeres')
        }
      }

      setMissatge('Comunitat creada correctament')
      setName('')
      setSearchEmail('')
      setUserResults([])
      setLeader(null)
      setMembers([])
      setSelectedCameras([])
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div style={{ padding: '30px', fontFamily: 'Arial' }}>
      <h1>Crear comunitat</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p style={{ color: 'green' }}>{missatge}</p>}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '20px' }}>
          <label>Nom de la comunitat</label>
          <br />
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ width: '350px' }}
          />
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label>Cercar usuaris per email</label>
          <br />
          <input
            type="text"
            value={searchEmail}
            onChange={(e) => setSearchEmail(e.target.value)}
            placeholder="Ex: gmail.com"
            style={{ width: '350px' }}
          />
          <button
            type="button"
            onClick={buscarUsuaris}
            style={{ marginLeft: '10px' }}
          >
            Cercar usuaris
          </button>
        </div>

        {loadingUsers && <p>Cercant usuaris...</p>}

        {userResults.length > 0 && (
          <div style={{ marginBottom: '25px' }}>
            <h3>Resultats d'usuaris</h3>

            {userResults.map((user) => (
              <div
                key={user.id}
                style={{
                  border: '1px solid #ccc',
                  padding: '10px',
                  marginBottom: '10px',
                  borderRadius: '6px'
                }}
              >
                <p><strong>{user.mail}</strong></p>
                <p>Rol: {user.role}</p>

                <button
                  type="button"
                  onClick={() => setLeader(user)}
                >
                  Fer líder
                </button>

                <button
                  type="button"
                  onClick={() => afegirMembre(user)}
                  style={{ marginLeft: '10px' }}
                >
                  Afegir membre
                </button>
              </div>
            ))}
          </div>
        )}

        <div style={{ marginBottom: '20px' }}>
          <h3>Líder seleccionat</h3>
          {leader ? <p>{leader.mail}</p> : <p>Cap líder seleccionat</p>}
        </div>

        <div style={{ marginBottom: '20px' }}>
          <h3>Membres seleccionats</h3>

          {members.length === 0 && <p>No hi ha membres seleccionats</p>}

          {members.map((member) => (
            <div key={member.id} style={{ marginBottom: '8px' }}>
              {member.mail}
              <button
                type="button"
                onClick={() => eliminarMembre(member.id)}
                style={{ marginLeft: '10px' }}
              >
                Eliminar
              </button>
            </div>
          ))}
        </div>

        <div style={{ marginBottom: '20px' }}>
          <h3>Càmeres</h3>

          <button type="button" onClick={carregarCameres}>
            Carregar càmeres
          </button>

          {loadingCameras && <p>Carregant càmeres...</p>}

          {cameras.length > 0 && (
            <div style={{ marginTop: '15px' }}>
              {cameras.map((camera) => {
                const checked = selectedCameras.some((c) => c.id === camera.id)

                return (
                  <div
                    key={camera.id}
                    style={{
                      border: '1px solid #ccc',
                      padding: '10px',
                      marginBottom: '10px',
                      borderRadius: '6px'
                    }}
                  >
                    <label>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleCamera(camera)}
                      />
                      <span style={{ marginLeft: '8px' }}>
                        Càmera {camera.id} - {camera.url}
                      </span>
                    </label>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <button type="submit" disabled={creating}>
          {creating ? 'Creant...' : 'Crear comunitat'}
        </button>
      </form>

      <div style={{ marginTop: '20px' }}>
        <button onClick={() => navigate('/admin')}>
          Tornar al panell admin
        </button>
      </div>
    </div>
  )
}

export default CrearComunitat