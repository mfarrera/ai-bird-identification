import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Hls from 'hls.js'
import Layout from '../Layout'

function ProvaTokenStream() {
  const videoRef = useRef(null)
  const navigate = useNavigate()

  const [token, setToken] = useState('')
  const [usarToken, setUsarToken] = useState(false)
  const [cameraPath, setCameraPath] = useState('cam1')
  const [missatge, setMissatge] = useState('')
  const [urlActual, setUrlActual] = useState('')

  const baseUrl = `http://localhost:8888/${cameraPath}/index.m3u8`
  const videoUrl = usarToken && token
    ? `${baseUrl}?jwt=${encodeURIComponent(token)}`
    : baseUrl

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    setUrlActual(videoUrl)
    setMissatge('Carregant stream...')

    if (Hls.isSupported()) {
      const hls = new Hls()

      hls.loadSource(videoUrl)
      hls.attachMedia(video)

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setMissatge('Manifest HLS carregat')
      })

      hls.on(Hls.Events.ERROR, (_, data) => {
        setMissatge(`Error HLS: ${data?.details || 'No s’ha pogut carregar el stream'}`)
      })

      return () => {
        hls.destroy()
      }
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = videoUrl
      setMissatge('Carregant stream amb suport nadiu HLS')
    } else {
      setMissatge('Aquest navegador no suporta HLS')
    }
  }, [videoUrl])

  return (
    <Layout
      title="Prova de stream amb token"
      subtitle="Comprova manualment l'HLS d'una càmera amb o sense token JWT."
    >
      <div className="panel">
        <div className="field">
          <label>Path de la càmera</label>
          <input
            className="input"
            type="text"
            value={cameraPath}
            onChange={(e) => setCameraPath(e.target.value)}
            placeholder="cam1"
          />
        </div>

        <div className="field">
          <label>Token JWT</label>
          <textarea
            className="input wide"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Enganxa aquí el token"
            rows="5"
          />
        </div>

        <div className="btn-row">
          <button className="btn" onClick={() => setUsarToken(false)}>
            Provar sense token
          </button>
          <button className="btn btn-primary" onClick={() => setUsarToken(true)}>
            Provar amb token
          </button>
        </div>

        <p className="muted" style={{ marginTop: '16px' }}>
          <strong>URL actual:</strong> {urlActual}
        </p>
        <p className="muted"><strong>Estat:</strong> {missatge}</p>

        <video
          ref={videoRef}
          controls
          autoPlay
          className="stream-video"
          style={{ marginTop: '12px' }}
        />

        <div className="btn-row">
          <button className="btn" onClick={() => navigate('/admin')}>
            Tornar al panell admin
          </button>
        </div>
      </div>
    </Layout>
  )
}

export default ProvaTokenStream
