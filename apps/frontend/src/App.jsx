import { BrowserRouter, Routes, Route } from 'react-router-dom'
import IniciSessio from './pages/IniciSessio'
import CrearUsuari from './pages/CrearUsuari'
import Principal from './pages/Principal'
import Admin from './pages/Admin'
import CrearAdmin from './pages/CrearAdmin.jsx'
import EliminarUsuari from './pages/EliminarUsuari'
import EliminarCamera from './pages/EliminarCamera'
import AfegirCamera from './pages/AfegirCamera'
import EnviarDeteccioValidar from './pages/EnviarDeteccioValidar'
import ProvaTokenStream from './pages/ProvaTokenStream'
import LlistarCameresAdmin from './pages/LlistarCameresAdmin'
import VeureStreamAdmin from './pages/VeureStreamAdmin'
import CrearComunitat from './pages/CrearComunitat'
import LlistarComunitats from './pages/LlistarComunitats'
import GestionarComunitat from './pages/GestionarComunitat'
import NotificacionsCameres from './pages/NotificacionsCameres'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<IniciSessio />} />
        <Route path="/crear-usuari" element={<CrearUsuari />} />
        <Route path="/principal" element={<Principal />} />

        <Route path="/admin" element={<Admin />} />
        <Route path="/admin/crear-usuari" element={<CrearUsuari />} />
        <Route path="/admin/crear-admin" element={<CrearAdmin />} />
        <Route path="/admin/eliminar-usuari" element={<EliminarUsuari />} />
        <Route path="/admin/eliminar-camera" element={<EliminarCamera />} />
        <Route path="/admin/afegir-camera" element={<AfegirCamera />} />
        <Route path="/admin/enviar-deteccio-validar" element={<EnviarDeteccioValidar />} />
        <Route path="/admin/prova-token-stream" element={<ProvaTokenStream />} />
        <Route path="/admin/cameres" element={<LlistarCameresAdmin />} />
        <Route path="/admin/camera/:cameraId/stream" element={<VeureStreamAdmin />} />
        <Route path="/admin/crear-comunitat" element={<CrearComunitat />} />
        <Route path="/admin/comunitats" element={<LlistarComunitats />} />
        <Route path="/admin/comunitats/:communityId" element={<GestionarComunitat />} />
        <Route path="/admin/notificacions-cameres" element={<NotificacionsCameres />}
/>
      </Routes>
    </BrowserRouter>
  )
}

export default App