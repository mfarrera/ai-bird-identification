import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../Layout'

const API_URL = 'http://127.0.0.1:8000'

function PujarVideo() {
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [resultat, setResultat] = useState(null)
  const [pujant, setPujant] = useState(false)
  const navigate = useNavigate()

  const handleUpload = async (e) => {
    e.preventDefault()
    setError('')
    setResultat(null)

    if (!file) {
      setError('Selecciona un vídeo primer')
      return
    }

    const token = localStorage.getItem('token')

    if (!token) {
      setError('Has d\'iniciar sessió primer')
      navigate('/')
      return
    }

    setPujant(true)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(`${API_URL}/api/user_upload_video`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error pujant el vídeo')
      }

      setResultat(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setPujant(false)
    }
  }

  return (
    <Layout
      title="Pujar vídeo d'ocell"
      subtitle="Puja un vídeo perquè el sistema detecti i identifiqui l'ocell."
    >
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleUpload}>
          <div className="field">
            <label>Vídeo</label>
            <input
              type="file"
              accept="video/*"
              onChange={(e) => setFile(e.target.files[0])}
            />
          </div>

          <button className="btn btn-primary" type="submit" disabled={pujant}>
            {pujant ? 'Pujant...' : 'Pujar vídeo'}
          </button>
        </form>

        {resultat && (
          <div style={{ marginTop: '20px' }}>
            <p className="muted">
              Detecció creada (id {resultat.detection.id}, estat{' '}
              {resultat.detection.status})
            </p>
            <video
              src={resultat.detection.url}
              controls
              className="preview-media"
            />
          </div>
        )}
      </div>
    </Layout>
  )
}

export default PujarVideo
