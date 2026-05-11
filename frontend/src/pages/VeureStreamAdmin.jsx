import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Hls from 'hls.js'

const API_URL = 'http://127.0.0.1:8000'

function VeureStreamAdmin() {
  const { cameraId } = useParams()
  const navigate = useNavigate()
  const videoRef = useRef(null)

  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')
  const [streamUrl, setStreamUrl] = useState('')
  const [tokenStream, setTokenStream] = useState('')
  const [expires, setExpires] = useState('')

  useEffect(() => {
    const usuariGuardat = localStorage.getItem('usuari')
    const tokenSessio = localStorage.getItem('token')

    if (!usuariGuardat || !tokenSessio) {
      navigate('/')
      return
    }

    const usuari = JSON.parse(usuariGuardat)

    // Comprovació de frontend per UX.
    // La seguretat real la fa el backend amb el token de sessió.
    if (usuari.role !== 'admin') {
      navigate('/principal')
      return
    }

    const obtenirTokenIStream = async () => {
      try {
        setError('')
        setMissatge('Demanant token del stream...')

        const res = await fetch(`${API_URL}/api/cameras/${cameraId}/stream`, {
          headers: {
            Authorization: `Bearer ${tokenSessio}`
          }
        })

        const data = await res.json()

        if (!res.ok) {
          throw new Error(data.detail || 'No s’ha pogut obtenir el token del stream')
        }

        setTokenStream(data.token)
        setExpires(data.expires || '')

        // Fem servir la URL HLS retornada pel backend
        const hlsUrl = `${data.hls_url}?jwt=${encodeURIComponent(data.token)}`
        setStreamUrl(hlsUrl)

        setMissatge('Token rebut. Carregant stream...')
      } catch (err) {
        setError(err.message)
        setMissatge('')
      }
    }

    obtenirTokenIStream()
  }, [cameraId, navigate])

  useEffect(() => {
    const video = videoRef.current
    if (!video || !streamUrl) return

    setError('')
    setMissatge('Carregant stream HLS...')

    if (Hls.isSupported()) {
      const hls = new Hls()
      hls.loadSource(streamUrl)
      hls.attachMedia(video)

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setMissatge('Stream carregat correctament')
      })

      hls.on(Hls.Events.ERROR, (_, data) => {
        setError(`Error HLS: ${data?.details || 'No s’ha pogut carregar el stream'}`)
      })

      return () => {
        hls.destroy()
      }
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = streamUrl
      setMissatge('Carregant stream amb suport nadiu HLS')
    } else {
      setError('Aquest navegador no suporta HLS')
    }
  }, [streamUrl])

  const tancarSessio = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('usuari')
    navigate('/')
  }

  return (
    <div style={{ padding: '30px', fontFamily: 'Arial' }}>
      <h1>Stream de la càmera {cameraId}</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p>{missatge}</p>}

      {tokenStream && (
        <details style={{ marginBottom: '15px' }}>
          <summary>Veure token del stream</summary>
          <textarea
            value={tokenStream}
            readOnly
            rows="5"
            style={{ width: '100%', maxWidth: '900px', marginTop: '10px' }}
          />
        </details>
      )}

      {expires && <p><strong>Caduca a:</strong> {expires}</p>}

      <video
        ref={videoRef}
        controls
        autoPlay
        width="900"
        style={{ backgroundColor: 'black', maxWidth: '100%' }}
      />

      <div style={{ marginTop: '20px' }}>
        <button onClick={() => navigate('/admin/cameres')}>
          Tornar a la llista de càmeres
        </button>

        <button onClick={() => navigate('/admin')} style={{ marginLeft: '10px' }}>
          Tornar al panell admin
        </button>

        <button onClick={tancarSessio} style={{ marginLeft: '10px' }}>
          Tancar sessió
        </button>
      </div>
    </div>
  )
}

export default VeureStreamAdmin