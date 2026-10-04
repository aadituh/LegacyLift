import { useEffect, useMemo, useRef } from 'react'

function seeded(index, salt = 1) {
  const value = Math.sin(index * 127.1 + salt * 311.7) * 43758.5453
  return value - Math.floor(value)
}

export default function BackgroundFx() {
  const rootRef = useRef(null)

  const particles = useMemo(
    () =>
      Array.from({ length: 42 }, (_, index) => ({
        id: `p-${index}`,
        left: `${(seeded(index, 2) * 100).toFixed(2)}%`,
        top: `${(seeded(index, 3) * 100).toFixed(2)}%`,
        delay: `${(-seeded(index, 4) * 14).toFixed(2)}s`,
        duration: `${(8 + seeded(index, 5) * 1).toFixed(2)}s`,
        size: `${(1 + seeded(index, 6) * 2.4).toFixed(2)}px`,
        drift: `${(-30 + seeded(index, 7) * 60).toFixed(0)}px`,
      })),
    [],
  )

  const nodes = useMemo(
    () =>
      Array.from({ length: 16 }, (_, index) => ({
        id: `n-${index}`,
        left: `${(8 + seeded(index, 8) * 84).toFixed(2)}%`,
        top: `${(10 + seeded(index, 9) * 78).toFixed(2)}%`,
        delay: `${(-seeded(index, 10) * 7).toFixed(2)}s`,
      })),
    [],
  )

  useEffect(() => {
    const root = rootRef.current
    if (!root) return undefined

    let frame = 0

    const handlePointerMove = (event) => {
      if (frame) return

      frame = window.requestAnimationFrame(() => {
        const x = event.clientX / window.innerWidth - 0.5
        const y = event.clientY / window.innerHeight - 0.5
        root.style.setProperty('--mx', `${(x * 24).toFixed(2)}px`)
        root.style.setProperty('--my', `${(y * 20).toFixed(2)}px`)
        root.style.setProperty('--mx-soft', `${(x * 10).toFixed(2)}px`)
        root.style.setProperty('--my-soft', `${(y * 8).toFixed(2)}px`)
        frame = 0
      })
    }

    window.addEventListener('pointermove', handlePointerMove, { passive: true })

    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      if (frame) window.cancelAnimationFrame(frame)
    }
  }, [])

  return (
    <div className="tech-background" ref={rootRef} aria-hidden="true">
      <div className="tech-background__base" />
      <div className="tech-background__glow glow-one" />
      <div className="tech-background__glow glow-two" />
      <div className="tech-background__glow glow-three" />

      <div className="tech-grid tech-grid--fine" />
      <div className="tech-grid tech-grid--major" />
      <div className="tech-scanline" />
      <div className="tech-horizon" />

      <div className="tech-orbit orbit-one">
        <span />
      </div>
      <div className="tech-orbit orbit-two">
        <span />
      </div>
      <div className="tech-orbit orbit-three">
        <span />
      </div>

      <div className="tech-network">
        {nodes.map((node) => (
          <span
            className="tech-node"
            key={node.id}
            style={{ left: node.left, top: node.top, animationDelay: node.delay }}
          />
        ))}
      </div>

      <div className="tech-particles">
        {particles.map((particle) => (
          <span
            className="tech-particle"
            key={particle.id}
            style={{
              left: particle.left,
              top: particle.top,
              width: particle.size,
              height: particle.size,
              animationDelay: particle.delay,
              animationDuration: particle.duration,
              '--particle-drift': particle.drift,
            }}
          />
        ))}
      </div>

      <div className="tech-beam beam-one" />
      <div className="tech-beam beam-two" />
      <div className="tech-beam beam-three" />

      <div className="tech-corner corner-top-left" />
      <div className="tech-corner corner-top-right" />
      <div className="tech-corner corner-bottom-left" />
      <div className="tech-corner corner-bottom-right" />

      <div className="tech-background__vignette" />
    </div>
  )
}
