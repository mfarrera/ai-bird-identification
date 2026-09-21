import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../Layout'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

function NotificacionsCameres() {
  const navigate = useNavigate()

  const [cameras, setCameras] = useState([])
  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')
  const [rejectionReasons, setRejectionReasons] = useState({})
  const [loadingCameraId, setLoadingCameraId] = useState(null)

  const token = localStorage.getItem('token')

  const carregarPendents = useCallback(async () => {
    try {
      setError('')

      const res = await fetch(`${API_URL}/api/admin/camera-requests`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(
          data.detail || 'No s’han pogut carregar les sol·licituds'
        )
      }

      setCameras(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message)
    }
  }, [token])

  useEffect(() => {
    if (!token) {
      navigate('/')
      return
    }

    carregarPendents()
  }, [carregarPendents, navigate, token])

  const enviarDecisio = async (cameraId, decision) => {
    try {
      setError('')
      setMissatge('')
      setLoadingCameraId(cameraId)

      const rejectionReason = rejectionReasons[cameraId] || ''

      if (decision === 'denied' && !rejectionReason.trim()) {
        throw new Error('Has d’indicar el motiu de denegació')
      }

      const res = await fetch(
        `${API_URL}/api/admin/cameras/${cameraId}/decision`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            decision,
            rejection_reason:
              decision === 'denied' ? rejectionReason.trim() : null
          })
        }
      )

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'No s’ha pogut revisar la càmera')
      }

      setMissatge(
        decision === 'accepted'
          ? 'Càmera acceptada. S’enviaran les credencials per correu.'
          : 'Càmera denegada. S’avisarà l’usuari per correu.'
      )

      setCameras((current) =>
        current.filter((camera) => camera.id !== cameraId)
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setLoadingCameraId(null)
    }
  }

  return (
    <Layout
      title="Notificacions de càmeres"
      subtitle="Sol·licituds de càmeres pendents de revisió."
    >
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        {missatge && <div className="alert alert-success">{missatge}</div>}

        {cameras.length === 0 && (
          <p className="muted">No hi ha sol·licituds pendents.</p>
        )}

        <div className="entity-list">
          {cameras.map((camera) => (
            <div className="entity-card" key={camera.id}>
              <p><strong>ID:</strong> {camera.id}</p>
              <p><strong>Usuari:</strong> {camera.owner_mail}</p>
              <p><strong>URL:</strong> {camera.url}</p>
              <p>
                <strong>Localització:</strong> {camera.latitude}, {camera.longitude}
              </p>
              <p>
                <strong>Estat:</strong>{' '}
                <span className="status-pill status-pending">{camera.camera_status}</span>
              </p>

              <div className="field" style={{ marginTop: '12px' }}>
                <label>Motiu de denegació</label>
                <textarea
                  className="input wide"
                  rows="3"
                  value={rejectionReasons[camera.id] || ''}
                  onChange={(e) =>
                    setRejectionReasons((current) => ({
                      ...current,
                      [camera.id]: e.target.value
                    }))
                  }
                  placeholder="Motiu de denegació"
                />
              </div>

              <div className="btn-row">
                <button
                  className="btn btn-primary"
                  disabled={loadingCameraId === camera.id}
                  onClick={() => enviarDecisio(camera.id, 'accepted')}
                >
                  Acceptar
                </button>
                <button
                  className="btn btn-danger"
                  disabled={loadingCameraId === camera.id}
                  onClick={() => enviarDecisio(camera.id, 'denied')}
                >
                  Denegar
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="btn-row">
          <button className="btn" onClick={() => navigate('/admin')}>
            Tornar al panell admin
          </button>
        </div>
      </div>
    </Layout>
  )
}

export default NotificacionsCameres
