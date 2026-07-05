import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Hls from 'hls.js'

const API_URL = 'http://127.0.0.1:8000'

function VeureStreamAdmin() {
  const { cameraId } = useParams()
  const navigate = useNavigate()

  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  const refreshTimeoutRef = useRef(null)

  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')
  const [streamUrl, setStreamUrl] = useState('')
  const [tokenStream, setTokenStream] = useState('')
  const [expires, setExpires] = useState('')

  const obtenirTokenIStream = async () => {
    const tokenSessio = localStorage.getItem('token')

    const res = await fetch(`${API_URL}/api/cameras/${cameraId}/stream`, {
      headers: {
        Authorization: `Bearer ${tokenSessio}`
      }
    })

    const data = await res.json()

    if (!res.ok) {
      throw new Error(data.detail || 'No s’ha pogut obtenir el token del stream')
    }

    return data
  }

  const programarRenovacioToken = (expiresIso) => {
    if (!expiresIso) return

    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current)
    }

    const expiresAt = new Date(expiresIso).getTime()
    const now = Date.now()

    // Renovar 1 minut abans que caduqui
    const tempsFinsRenovar = expiresAt - now - 60000
    const delay = Math.max(tempsFinsRenovar, 0)

    refreshTimeoutRef.current = setTimeout(async () => {
      try {
        setError('')
        setMissatge('Renovant token del stream...')

        const data = await obtenirTokenIStream()

        setTokenStream(data.token)
        setExpires(data.expires || '')

        const hlsUrl = `${data.hls_url}?jwt=${encodeURIComponent(data.token)}`
        
        console.log('Resposta stream:', data)
        console.log('URL HLS final:', hlsUrl)

        setStreamUrl(hlsUrl)

        setMissatge('Token renovat correctament')

        programarRenovacioToken(data.expires)
      } catch (err) {
        setError(err.message)
        setMissatge('')
      }
    }, delay)
  }

  useEffect(() => {
    const usuariGuardat = localStorage.getItem('usuari')
    const tokenSessio = localStorage.getItem('token')

    if (!usuariGuardat || !tokenSessio) {
      navigate('/')
      return
    }

    const usuari = JSON.parse(usuariGuardat)

    if (usuari.role !== 'admin') {
      navigate('/principal')
      return
    }

    const carregarStreamInicial = async () => {
      try {
        setError('')
        setMissatge('Demanant token del stream...')

        const data = await obtenirTokenIStream()

        setTokenStream(data.token)
        setExpires(data.expires || '')

        const hlsUrl = `${data.hls_url}?jwt=${encodeURIComponent(data.token)}`
        setStreamUrl(hlsUrl)

        setMissatge('Token rebut. Carregant stream...')

        programarRenovacioToken(data.expires)
      } catch (err) {
        setError(err.message)
        setMissatge('')
      }
    }

    carregarStreamInicial()

    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current)
      }

      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
    }
  }, [cameraId, navigate])

  useEffect(() => {
    const video = videoRef.current
    if (!video || !streamUrl) return

    setError('')
    setMissatge('Carregant stream HLS...')

    if (hlsRef.current) {
      hlsRef.current.destroy()
      hlsRef.current = null
    }

    if (Hls.isSupported()) {
      const hls = new Hls()
      hlsRef.current = hls

      hls.loadSource(streamUrl)
      hls.attachMedia(video)

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setMissatge('Stream carregat correctament')
      })

      hls.on(Hls.Events.ERROR, (_, data) => {
        setError(`Error HLS: ${data?.details || 'No s’ha pogut carregar el stream'}`)
      })
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

    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current)
    }

    if (hlsRef.current) {
      hlsRef.current.destroy()
      hlsRef.current = null
    }

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

      {expires && (
        <p><strong>Caduca a:</strong> {expires}</p>
      )}

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