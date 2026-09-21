import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Hls from 'hls.js'
import Layout from '../Layout'

const API_URL = 'http://127.0.0.1:8000'

function VeureStream() {
  const { cameraId } = useParams()
  const navigate = useNavigate()

  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  const refreshTimeoutRef = useRef(null)

  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')
  const [streamUrl, setStreamUrl] = useState('')

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
    const tempsFinsRenovar = expiresAt - now - 60000
    const delay = Math.max(tempsFinsRenovar, 0)

    refreshTimeoutRef.current = setTimeout(async () => {
      try {
        setError('')
        setMissatge('Renovant token del stream...')

        const data = await obtenirTokenIStream()
        const hlsUrl = `${data.hls_url}?jwt=${encodeURIComponent(data.token)}`
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

    const carregarStreamInicial = async () => {
      try {
        setError('')
        setMissatge('Demanant token del stream...')

        const data = await obtenirTokenIStream()
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

  return (
    <Layout title={`Stream de la càmera ${cameraId}`}>
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        {missatge && <p className="muted">{missatge}</p>}

        <video
          ref={videoRef}
          controls
          autoPlay
          className="stream-video"
          style={{ marginTop: '12px' }}
        />

        <div className="btn-row">
          <button className="btn" onClick={() => navigate('/principal')}>
            Tornar al dashboard
          </button>
        </div>
      </div>
    </Layout>
  )
}

export default VeureStream
