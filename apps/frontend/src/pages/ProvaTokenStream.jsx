import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Hls from 'hls.js'

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
    <div style={{ padding: '30px', fontFamily: 'Arial' }}>
      <h1>Prova de stream amb token</h1>

      <div style={{ marginBottom: '15px' }}>
        <label>Path de la càmera:</label>
        <br />
        <input
          type="text"
          value={cameraPath}
          onChange={(e) => setCameraPath(e.target.value)}
          placeholder="cam1"
          style={{ width: '300px' }}
        />
      </div>

      <div style={{ marginBottom: '15px' }}>
        <label>Token JWT:</label>
        <br />
        <textarea
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="Enganxa aquí el token"
          rows="5"
          style={{ width: '100%', maxWidth: '800px' }}
        />
      </div>

      <div style={{ marginBottom: '20px' }}>
        <button onClick={() => setUsarToken(false)}>
          Provar sense token
        </button>

        <button onClick={() => setUsarToken(true)} style={{ marginLeft: '10px' }}>
          Provar amb token
        </button>
      </div>

      <p><strong>URL actual:</strong> {urlActual}</p>
      <p><strong>Estat:</strong> {missatge}</p>

      <video
        ref={videoRef}
        controls
        autoPlay
        width="900"
        style={{ backgroundColor: 'black', maxWidth: '100%' }}
      />

      <div style={{ marginTop: '20px' }}>
        <button onClick={() => navigate('/admin')}>
          Tornar al panell admin
        </button>
      </div>
    </div>
  )
}

export default ProvaTokenStream