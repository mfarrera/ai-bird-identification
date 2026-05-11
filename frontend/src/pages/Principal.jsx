function Principal() {
  const usuari = JSON.parse(localStorage.getItem('usuari'))

  return (
    <div style={{ padding: '30px', fontFamily: 'Arial', textAlign: 'center' }}>
      <h1>Pàgina principal</h1>
      {usuari && <p>Benvingut/da, {usuari.mail}</p>}
      <button>Afegir càmera</button>
    </div>
  )
}

export default Principal