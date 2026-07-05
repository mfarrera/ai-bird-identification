import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

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
    <div style={{ padding: '30px', fontFamily: 'Arial' }}>
      <h1>Notificacions de càmeres</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p style={{ color: 'green' }}>{missatge}</p>}

      {cameras.length === 0 && (
        <p>No hi ha sol·licituds pendents.</p>
      )}

      {cameras.map((camera) => (
        <div
          key={camera.id}
          style={{
            border: '1px solid #ccc',
            borderRadius: '8px',
            padding: '15px',
            marginBottom: '15px'
          }}
        >
          <p><strong>ID:</strong> {camera.id}</p>
          <p><strong>Usuari:</strong> {camera.owner_mail}</p>
          <p><strong>URL:</strong> {camera.url}</p>
          <p>
            <strong>Localització:</strong>{' '}
            {camera.latitude}, {camera.longitude}
          </p>
          <p><strong>Estat:</strong> {camera.camera_status}</p>

          <button
            disabled={loadingCameraId === camera.id}
            onClick={() => enviarDecisio(camera.id, 'accepted')}
          >
            Acceptar
          </button>

          <div style={{ marginTop: '12px' }}>
            <textarea
              rows="3"
              value={rejectionReasons[camera.id] || ''}
              onChange={(e) =>
                setRejectionReasons((current) => ({
                  ...current,
                  [camera.id]: e.target.value
                }))
              }
              placeholder="Motiu de denegació"
              style={{ width: '100%', maxWidth: '600px' }}
            />
          </div>

          <button
            disabled={loadingCameraId === camera.id}
            onClick={() => enviarDecisio(camera.id, 'denied')}
            style={{ marginTop: '8px' }}
          >
            Denegar
          </button>
        </div>
      ))}

      <button onClick={() => navigate('/admin')}>
        Tornar al panell admin
      </button>
    </div>
  )
}

export default NotificacionsCameres