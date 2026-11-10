
import { useState } from 'react'
import logo from './assets/logo.svg'

const features = [
  {
    number: '01',
    icon: '◎',
    title: 'Servicio social',
    description:
      'Consulta información sobre requisitos, horas, documentación y procedimientos del servicio social.',
    tag: 'TRÁMITES ACADÉMICOS',
  },
  {
    number: '02',
    icon: '⌘',
    title: 'Residencias profesionales',
    description:
      'Conoce los procesos, requisitos y lineamientos para realizar tus residencias profesionales.',
    tag: 'DESARROLLO PROFESIONAL',
  },
  {
    number: '03',
    icon: '◇',
    title: 'Titulación',
    description:
      'Encuentra orientación sobre modalidades, requisitos y pasos necesarios para tu titulación.',
    tag: 'INFORMACIÓN ESCOLAR',
  },
]

function App() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <>
      <header className="navbar">
        <div className="nav-container">
          <a href="#" className="brand" aria-label="TecBot Académico">
            <img src={logo} alt="TecBot Académico" />
          </a>

          <button
            className="menu-toggle"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Abrir menú"
            aria-expanded={menuOpen}
          >
            <span></span>
            <span></span>
            <span></span>
          </button>

          <nav className={menuOpen ? 'nav-links active' : 'nav-links'}>
            <a href="#caracteristicas" onClick={() => setMenuOpen(false)}>
              Características
            </a>
            <a href="#procesos" onClick={() => setMenuOpen(false)}>
              Procesos
            </a>
            <a href="#recursos" onClick={() => setMenuOpen(false)}>
              Recursos
            </a>
          </nav>

          <a href="#caracteristicas" className="nav-button">
            Comenzar <span>↗</span>
          </a>
        </div>
      </header>

      <main>
        <section className="hero" id="procesos">
          <div className="hero-glow"></div>

          <div className="hero-content">
            <div className="hero-badge">
              <span className="status-dot"></span>
              ⚡ Demostración académica
            </div>

            <h1>
              Tu camino académico,
              <br />
              <span>más claro e inteligente.</span>
            </h1>

            <p className="hero-description">
              Conoce los procesos académicos de forma sencilla.
              Encuentra orientación sobre servicio social, residencias
              profesionales y titulación en un solo lugar.
            </p>

            <div className="hero-actions">
              <a href="#caracteristicas" className="btn-primary">
                Explorar plataforma <span>→</span>
              </a>
              <a href="#recursos" className="btn-secondary">
                Conocer más
              </a>
            </div>

            <div className="hero-note">
              <span className="note-line"></span>
              Información académica al alcance de todos
            </div>
          </div>

          <div className="hero-decoration" aria-hidden="true">
            <div className="orbit orbit-one"></div>
            <div className="orbit orbit-two"></div>
            <div className="orbit-center">
              <img src={logo} alt="" />
              <div className="orbit-caption">TEC<span>BOT</span></div>
              <div className="orbit-subtitle">ASISTENTE ACADÉMICO</div>
            </div>
            <span className="floating-dot dot-one"></span>
            <span className="floating-dot dot-two"></span>
            <span className="floating-dot dot-three"></span>
          </div>
        </section>

        <section className="features-section" id="caracteristicas">
          <div className="section-heading">
            <span className="section-label">¿QUÉ PUEDES CONSULTAR?</span>
            <h2>
              Información que te impulsa
              <span>.</span>
            </h2>
            <p>
              Encuentra orientación sobre los principales procesos de tu
              trayectoria académica.
            </p>
          </div>

          <div className="features-grid">
            {features.map((feature) => (
              <article className="feature-card" key={feature.number}>
                <div className="card-top">
                  <div className="feature-icon">{feature.icon}</div>
                  <span className="card-number">{feature.number}</span>
                </div>

                <span className="card-tag">{feature.tag}</span>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>

                <a href="#recursos" className="card-link">
                  Conocer más <span>→</span>
                </a>
              </article>
            ))}
          </div>
        </section>

        <section className="bottom-section" id="recursos">
          <div>
            <span className="section-label">TECBOT ACADÉMICO</span>
            <h2>Tu información académica, en un solo lugar.</h2>
            <p>
              Una demostración de cómo la tecnología puede facilitar el
              acceso a la información escolar.
            </p>
          </div>
          <a href="#top" className="btn-secondary">
            Volver al inicio ↑
          </a>
        </section>
      </main>

      <footer className="footer">
        <img src={logo} alt="TecBot Académico" />
        <p>© 2026 TecBot Académico. Proyecto académico.</p>
      </footer>
    </>
  )
}

export default App
