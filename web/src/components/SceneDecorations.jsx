import { useMemo, useEffect, useRef, useState } from 'react'

const base = import.meta.env.BASE_URL

const POOL = [
  'dino_1.png', 'dino_2.png', 'dino_3.png',
  'bush_1.png', 'bush_2.png', 'bush_3.png', 'bush_4.png',
]

// Slots along the bottom edge
const SLOTS = [
  { left: 0 },
  { right: 0 },
  { left: '8%' },
  { right: '8%' },
  { left: '18%' },
  { right: '18%' },
]

// Seeded LCG
function makeRand(seed) {
  let s = seed >>> 0
  return () => { s = (Math.imul(1664525, s) + 1013904223) >>> 0; return s / 0x100000000 }
}

function shuffle(arr, rand) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

export default function SceneDecorations({ seed = 1 }) {
  const items = useMemo(() => {
    const rand = makeRand(seed)
    const count = rand() > 0.4 ? 3 : 2
    const assets = shuffle(POOL, rand).slice(0, count)
    const slots  = shuffle(SLOTS, rand).slice(0, count)
    return assets.map((src, i) => ({
      src,
      slot: slots[i],
      size: 60 + Math.floor(rand() * 40),   // 60–100 px
      flip: rand() > 0.55,
    }))
  }, [seed])

  const [meteorStyle, setMeteorStyle] = useState(null)
  const [meteorFrame, setMeteorFrame] = useState(1)
  const timerRef  = useRef(null)
  const frameRef  = useRef(null)

  useEffect(() => {
    const DURATION = 2800
    const FRAMES   = 5

    function schedule() {
      timerRef.current = setTimeout(() => {
        setMeteorStyle({ top: `${Math.random() * 30 - 5}vh` })
        setMeteorFrame(1)

        let f = 1
        frameRef.current = setInterval(() => {
          f = Math.min(f + 1, FRAMES)
          setMeteorFrame(f)
          if (f === FRAMES) clearInterval(frameRef.current)
        }, DURATION / FRAMES)

        setTimeout(() => {
          clearInterval(frameRef.current)
          setMeteorStyle(null)
          setMeteorFrame(1)
          schedule()
        }, DURATION)
      }, 12000 + Math.random() * 18000)
    }
    schedule()
    return () => { clearTimeout(timerRef.current); clearInterval(frameRef.current) }
  }, [])

  return (
    <>
      {meteorStyle && (
        <img src={`${base}meteor_${meteorFrame}.png`} className="meteor" style={meteorStyle} alt="" />
      )}
      {items.map((item, i) => (
        <img
          key={i}
          src={`${base}${item.src}`}
          className="scene-deco"
          style={{
            bottom: 0,
            width: `min(${item.size}px, 12vw)`,
            ...(item.slot.left !== undefined ? { left: item.slot.left } : { right: item.slot.right }),
            transform: item.flip ? 'scaleX(-1)' : undefined,
          }}
          alt=""
        />
      ))}
    </>
  )
}
