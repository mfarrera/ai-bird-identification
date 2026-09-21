function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div className="brand center">🪶 <span>Av<span className="brand-accent">ia</span>ri</span></div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
        {children}
      </div>
    </div>
  )
}

export default AuthLayout
