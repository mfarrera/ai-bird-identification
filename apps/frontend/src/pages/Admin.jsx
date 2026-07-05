import { useNavigate } from 'react-router-dom'

function Admin() {
  const navigate = useNavigate()

  return (
    <div style={{ padding: '30px', fontFamily: 'Arial', textAlign: 'center' }}>
      <h1>Panell d'administració</h1>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '300px', margin: '30px auto' }}>
        <button onClick={() => navigate('/admin/crear-usuari')}>Crear usuari</button>
        <button onClick={() => navigate('/admin/crear-admin')}>Crear admin</button>
        <button onClick={() => navigate('/admin/eliminar-usuari')}>Eliminar usuari</button>
        <button onClick={() => navigate('/admin/eliminar-camera')}>Eliminar càmera</button>
        <button onClick={() => navigate('/admin/afegir-camera')}>Afegir càmera</button>
        <button onClick={() => navigate('/admin/enviar-deteccio-validar')}>Enviar detecció a validar</button>
        <button onClick={() => navigate('/admin/prova-token-stream')}>Provar stream amb token</button>
        <button onClick={() => navigate('/admin/cameres')}>Veure càmeres</button>
        <button onClick={() => navigate('/admin/crear-comunitat')}>Crear comunitat</button>
        <button onClick={() => navigate('/admin/comunitats')}>Veure comunitats</button>
        <button onClick={() => navigate('/admin/notificacions-cameres')}>Notificacions de càmeres</button>
      </div>

      <button onClick={() => navigate('/principal')}>Tornar</button>
    </div>
  )
}

export default Admin