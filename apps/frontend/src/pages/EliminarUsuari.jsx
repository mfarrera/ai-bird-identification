import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../Layout'

const API_URL = 'http://127.0.0.1:8000'

function EliminarUsuari() {
  const [userId, setUserId] = useState('')
  const [missatge, setMissatge] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleDelete = async (e) => {
    e.preventDefault()
    setMissatge('')
    setError('')

    try {
      const res = await fetch(`${API_URL}/api/users/${userId}`, {
        method: 'DELETE'
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Error en eliminar l’usuari')

      setMissatge('Usuari eliminat correctament')
      setUserId('')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <Layout title="Eliminar usuari" subtitle="Elimina un compte d'usuari pel seu ID.">
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        {missatge && <div className="alert alert-success">{missatge}</div>}

        <form onSubmit={handleDelete}>
          <div className="field">
            <label>ID usuari</label>
            <input
              className="input"
              type="number"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </div>

          <button className="btn btn-danger" type="submit">Eliminar</button>
        </form>

        <div className="btn-row">
          <button className="btn" onClick={() => navigate('/admin')}>Tornar</button>
        </div>
      </div>
    </Layout>
  )
}

export default EliminarUsuari
