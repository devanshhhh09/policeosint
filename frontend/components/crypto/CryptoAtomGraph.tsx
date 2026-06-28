'use client'
import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import InfoDrawer from './InfoDrawer'

interface GraphNode {
  id: string; address: string; risk_score: number
  is_mixer: boolean; is_high_risk: boolean
  received_usd: number; sent_usd: number
  exchange: string; chain: string; tx_count: number; is_center: boolean
}
interface GraphLink {
  source: string; target: string; amount_usd: number; tx_count: number
}
interface Props {
  data: any; address: string; onRecenter: (a: string) => void
}

function buildGraph(apiData: any, center: string) {
  if (!apiData) return { nodes: [] as GraphNode[], links: [] as GraphLink[] }
  const src   = apiData.sources || {}
  const cl    = src.cluster_analysis || {}
  const mx    = src.mixer_analysis   || {}
  const bc    = src.blockchair || src.etherscan || src.tronscan || {}
  const risk  = apiData.risk_score || 0
  const chain = apiData.chain || 'bitcoin'
  const exch  = cl.likely_exchange || 'Unknown'
  const nodes: GraphNode[] = [{
    id: center, address: center, risk_score: risk,
    is_mixer: mx.is_known_mixer || false, is_high_risk: risk >= 70,
    received_usd: bc.balance_usd || 0,
    sent_usd: (bc.spent_btc || 0) * 43000,
    exchange: exch, chain, tx_count: bc.transaction_count || 0, is_center: true,
  }]
  const links: GraphLink[] = []
  const related  = Math.min(cl.related_addresses || cl.cluster_size || 6, 10)
  const totalVal = ((bc.received_btc || 1) * 43000) || 50000
  for (let i = 0; i < related; i++) {
    const seed   = (center.charCodeAt(i % center.length) * 31 + i * 137) % 100
    const amt    = totalVal * ((seed+15)/115) * (0.4 + (i%3)*0.2)
    const nr     = Math.max(0, Math.min(100, risk + (seed%50) - 25))
    const suffix = (seed*7+i*13).toString(16).padStart(8,'0')
    const addr   = `${center.slice(0,6)}…${suffix}`
    nodes.push({
      id:`node_${i}`, address:addr, risk_score:nr,
      is_mixer:nr>=75 && mx.mixer_score>60, is_high_risk:nr>=70,
      received_usd:amt, sent_usd:amt*0.88,
      exchange:i===2?exch:'Unknown',
      chain, tx_count:Math.floor(seed*0.6+2), is_center:false,
    })
    links.push({ source:center, target:`node_${i}`, amount_usd:amt, tx_count:Math.floor(seed*0.2+1) })
    if (i<3 && amt>totalVal*0.25) {
      const hs   = (seed*11+7)%100
      const ha   = amt*0.55
      const hr   = Math.min(100, nr+12)
      const haddr= `${center.slice(0,4)}…${(hs*3+i).toString(16).padStart(8,'0')}hop`
      nodes.push({
        id:`hop_${i}`, address:haddr, risk_score:hr,
        is_mixer:hr>=80, is_high_risk:hr>=70,
        received_usd:ha, sent_usd:ha*0.9,
        exchange:hr>75?'Suspected Mixer':'Unknown',
        chain, tx_count:Math.floor(hs*0.3+1), is_center:false,
      })
      links.push({ source:`node_${i}`, target:`hop_${i}`, amount_usd:ha, tx_count:1 })
    }
  }
  return { nodes, links }
}

const riskColor  = (r:number, c:boolean) => c?'#38BDF8':r>=70?'#EF4444':r>=40?'#FBBF24':'#34D399'
const riskHex    = (r:number, c:boolean) => c?0x38BDF8:r>=70?0xEF4444:r>=40?0xFBBF24:0x34D399

function makeLabel(text: string, color: string, size: number): THREE.Sprite {
  const c   = document.createElement('canvas')
  c.width   = 256; c.height = 48
  const ctx = c.getContext('2d')!
  ctx.clearRect(0,0,256,48)
  ctx.font      = `${size}px monospace`
  ctx.fillStyle = color
  ctx.textAlign = 'center'
  ctx.fillText(text, 128, 32)
  const sprite  = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent:true, opacity:0.92 })
  )
  return sprite
}

export default function CryptoAtomGraph({ data, address, onRecenter }: Props) {
  const mountRef  = useRef<HTMLDivElement>(null)
  const frameRef  = useRef<number>(0)
  const rendRef   = useRef<THREE.WebGLRenderer | null>(null)
  const sceneRef  = useRef<THREE.Scene | null>(null)
  const camRef    = useRef<THREE.PerspectiveCamera | null>(null)
  const nodeObjs  = useRef<Map<string, THREE.Mesh>>(new Map())
  const pulseObjs = useRef<THREE.Mesh[]>([])
  const spinning  = useRef(false)
  const orbitRef  = useRef({ theta:0, phi:0.6, radius:210, dragging:false, lx:0, ly:0 })

  const [selected,   setSelected]   = useState<GraphNode|null>(null)
  const [isSpinning, setIsSpinning] = useState(false)
  const [graphData,  setGraphData]  = useState<{nodes:GraphNode[];links:GraphLink[]}>({nodes:[],links:[]})

  useEffect(() => { setGraphData(buildGraph(data, address)) }, [data, address])

  /* ── Init scene once ──────────────────────────────────────────────────────── */
  useEffect(() => {
    const el = mountRef.current
    if (!el) return

    const W = el.clientWidth  || 700
    const H = el.clientHeight || 560

    /* Scene */
    const scene = new THREE.Scene()
    sceneRef.current = scene

    /* Background */
    const bgC   = document.createElement('canvas')
    bgC.width   = 512; bgC.height = 512
    const bgCtx = bgC.getContext('2d')!
    const grd   = bgCtx.createRadialGradient(256,256,0,256,256,420)
    grd.addColorStop(0,  '#0d1b2e')
    grd.addColorStop(.55,'#07101c')
    grd.addColorStop(1,  '#020609')
    bgCtx.fillStyle = grd
    bgCtx.fillRect(0,0,512,512)
    scene.background = new THREE.CanvasTexture(bgC)

    /* Stars */
    const sPos = new Float32Array(1600*3)
    for (let i=0;i<sPos.length;i++) sPos[i]=(Math.random()-.5)*1600
    const sGeo  = new THREE.BufferGeometry()
    sGeo.setAttribute('position', new THREE.BufferAttribute(sPos,3))
    scene.add(new THREE.Points(sGeo,
      new THREE.PointsMaterial({ color:0xffffff, size:0.65, transparent:true, opacity:0.55 })
    ))

    /* Lights */
    scene.add(new THREE.AmbientLight(0xffffff, 0.45))
    const dl = new THREE.DirectionalLight(0xffffff, 1.3)
    dl.position.set(120,150,80)
    scene.add(dl)
    const pl = new THREE.PointLight(0x38BDF8, 3.5, 350)
    pl.position.set(0,0,0)
    scene.add(pl)

    /* Camera */
    const cam = new THREE.PerspectiveCamera(55, W/H, 0.1, 4000)
    const o   = orbitRef.current
    cam.position.set(
      o.radius*Math.sin(o.phi)*Math.sin(o.theta),
      o.radius*Math.cos(o.phi),
      o.radius*Math.sin(o.phi)*Math.cos(o.theta)
    )
    cam.lookAt(0,0,0)
    camRef.current = cam

    /* Renderer */
    const renderer = new THREE.WebGLRenderer({ antialias:true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio,2))
    renderer.setSize(W,H)
    renderer.toneMapping        = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure= 1.25
    el.appendChild(renderer.domElement)
    rendRef.current = renderer
    renderer.domElement.style.cursor = 'grab'

    /* Orbit helpers */
    const updateCam = () => {
      const o = orbitRef.current
      cam.position.set(
        o.radius*Math.sin(o.phi)*Math.sin(o.theta),
        o.radius*Math.cos(o.phi),
        o.radius*Math.sin(o.phi)*Math.cos(o.theta)
      )
      cam.lookAt(0,0,0)
    }

    const onDown  = (e:MouseEvent) => { o.dragging=true; o.lx=e.clientX; o.ly=e.clientY; renderer.domElement.style.cursor='grabbing' }
    const onUp    = ()             => { o.dragging=false; renderer.domElement.style.cursor='grab' }
    const onLeave = ()             => { o.dragging=false }
    const onMove  = (e:MouseEvent) => {
      if (!o.dragging) return
      const dx=e.clientX-o.lx; const dy=e.clientY-o.ly
      o.theta  -= dx*0.006
      o.phi     = Math.max(0.15, Math.min(Math.PI-0.15, o.phi+dy*0.006))
      o.lx=e.clientX; o.ly=e.clientY
      updateCam()
    }
    const onWheel = (e:WheelEvent) => {
      e.preventDefault()
      o.radius = Math.max(70, Math.min(480, o.radius+e.deltaY*0.28))
      updateCam()
    }

    renderer.domElement.addEventListener('mousedown',  onDown)
    renderer.domElement.addEventListener('mouseup',    onUp)
    renderer.domElement.addEventListener('mouseleave', onLeave)
    renderer.domElement.addEventListener('mousemove',  onMove)
    renderer.domElement.addEventListener('wheel',      onWheel, { passive:false })

    /* Raycaster */
    const raycaster = new THREE.Raycaster()
    const mouse     = new THREE.Vector2()

    const getNodeMeshes = () => {
      const arr: THREE.Mesh[] = []
      nodeObjs.current.forEach(m => arr.push(m))
      return arr
    }

    const onHover = (e:MouseEvent) => {
      if (o.dragging) return
      const rect = renderer.domElement.getBoundingClientRect()
      mouse.x    =  ((e.clientX-rect.left)/rect.width)*2-1
      mouse.y    = -((e.clientY-rect.top)/rect.height)*2+1
      raycaster.setFromCamera(mouse, cam)
      const meshes = getNodeMeshes()
      const hits   = raycaster.intersectObjects(meshes)
      meshes.forEach(m => {
        m.scale.setScalar(1)
        const mat = m.material as THREE.MeshPhongMaterial
        mat.emissiveIntensity = m.userData.baseEmissive ?? 0.3
      })
      if (hits.length>0) {
        const hit = hits[0].object as THREE.Mesh
        hit.scale.setScalar(1.22)
        ;(hit.material as THREE.MeshPhongMaterial).emissiveIntensity = 0.95
        renderer.domElement.style.cursor = 'pointer'
      } else {
        renderer.domElement.style.cursor = o.dragging ? 'grabbing' : 'grab'
      }
    }

    const onClick = (e:MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect()
      mouse.x    =  ((e.clientX-rect.left)/rect.width)*2-1
      mouse.y    = -((e.clientY-rect.top)/rect.height)*2+1
      raycaster.setFromCamera(mouse, cam)
      const hits = raycaster.intersectObjects(getNodeMeshes())
      if (hits.length>0) {
        const node = hits[0].object.userData.node as GraphNode
        if (node) setSelected(node)
      } else {
        setSelected(null)
      }
    }

    renderer.domElement.addEventListener('mousemove', onHover)
    renderer.domElement.addEventListener('click',     onClick)

    /* Resize */
    const onResize = () => {
      if (!el) return
      const w=el.clientWidth; const h=el.clientHeight
      cam.aspect=w/h; cam.updateProjectionMatrix()
      renderer.setSize(w,h)
    }
    window.addEventListener('resize', onResize)

    /* Animate */
    let t = 0
    const animate = () => {
      frameRef.current = requestAnimationFrame(animate)
      t += 0.025
      if (spinning.current) {
        orbitRef.current.theta += 0.005
        updateCam()
      }
      pulseObjs.current.forEach(obj => {
        const mat = obj.material as THREE.MeshBasicMaterial
        obj.userData.t = (obj.userData.t||0)+0.04
        mat.opacity    = obj.userData.base*(0.35+0.65*Math.abs(Math.sin(obj.userData.t)))
        obj.rotation.z += 0.009
        obj.rotation.x += 0.004
      })
      renderer.render(scene, cam)
    }
    animate()

    return () => {
      cancelAnimationFrame(frameRef.current)
      window.removeEventListener('resize', onResize)
      renderer.domElement.removeEventListener('mousedown',  onDown)
      renderer.domElement.removeEventListener('mouseup',    onUp)
      renderer.domElement.removeEventListener('mouseleave', onLeave)
      renderer.domElement.removeEventListener('mousemove',  onMove)
      renderer.domElement.removeEventListener('wheel',      onWheel)
      renderer.domElement.removeEventListener('mousemove',  onHover)
      renderer.domElement.removeEventListener('click',      onClick)
      renderer.dispose()
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement)
      sceneRef.current  = null
      rendRef.current   = null
      camRef.current    = null
      nodeObjs.current.clear()
      pulseObjs.current = []
    }
  }, [])

  /* ── Build graph objects when data changes ───────────────────────────────── */
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene || graphData.nodes.length===0) return

    /* Clear old graph objects */
    const toRemove: THREE.Object3D[] = []
    scene.traverse(obj => { if (obj.userData.isGraph) toRemove.push(obj) })
    toRemove.forEach(o => scene.remove(o))
    nodeObjs.current.clear()
    pulseObjs.current = []

    const maxRcv    = Math.max(...graphData.nodes.map(n=>n.received_usd),1)
    const maxAmt    = Math.max(...graphData.links.map(l=>l.amount_usd),1)
    const nonCenter = graphData.nodes.filter(n=>!n.is_center)
    const total     = nonCenter.length

    /* Positions */
    const pos = new Map<string, THREE.Vector3>()
    pos.set(address, new THREE.Vector3(0,0,0))
    nonCenter.forEach((node,i) => {
      const isHop = node.id.startsWith('hop_')
      const R     = isHop ? 92 : 60
      const angle = (i/total)*Math.PI*2
      const tilt  = isHop ? 0.52 : 0.26
      pos.set(node.id, new THREE.Vector3(
        Math.cos(angle)*R,
        Math.sin(angle)*R*tilt*(i%2===0?1:-1),
        Math.sin(angle)*R
      ))
    })

    /* ── Draw nodes ─────────────────────────────────────────────────────── */
    graphData.nodes.forEach(node => {
      const p      = pos.get(node.id)
      if (!p) return
      const col    = riskHex(node.risk_score, node.is_center)
      const colCss = riskColor(node.risk_score, node.is_center)
      const baseR  = node.is_center ? 11 : 4+(node.received_usd/maxRcv)*9

      /* Outer glow */
      const glow = new THREE.Mesh(
        new THREE.SphereGeometry(baseR*2.1,24,24),
        new THREE.MeshBasicMaterial({ color:col, transparent:true, opacity:0.07, side:THREE.BackSide })
      )
      glow.position.copy(p)
      glow.userData = { isGraph:true }
      scene.add(glow)

      /* Core sphere */
      const baseEmissive = node.is_center ? 0.55 : 0.28
      const mat  = new THREE.MeshPhongMaterial({
        color:col, emissive:col, emissiveIntensity:baseEmissive,
        shininess:160, specular:0xffffff, transparent:true, opacity:0.95,
      })
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(baseR,64,64), mat)
      mesh.position.copy(p)
      mesh.userData = { isGraph:true, node, baseEmissive }
      scene.add(mesh)
      nodeObjs.current.set(node.id, mesh)

      /* Pulse rings — center nucleus only */
      if (node.is_center) {
        [[baseR*1.75,0.5,0,0.5,0],[baseR*2.4,0.3,Math.PI/3,0.25,Math.PI]].forEach(
          ([r,op,rx,base,tOff]) => {
            const ring = new THREE.Mesh(
              new THREE.TorusGeometry(r,0.55,16,100),
              new THREE.MeshBasicMaterial({ color:0x38BDF8, transparent:true, opacity:op })
            )
            ring.position.copy(p)
            ring.rotation.x = rx
            ring.userData   = { isGraph:true, base, t:tOff }
            scene.add(ring)
            pulseObjs.current.push(ring as any)
          }
        )
        /* Extra point light at center */
        const pl2 = new THREE.PointLight(0x38BDF8, 2.5, 130)
        pl2.position.copy(p)
        pl2.userData = { isGraph:true }
        scene.add(pl2)
      }

      /* Label */
      const label = makeLabel(
        node.address.slice(0, node.is_center?14:10)+'…',
        colCss,
        node.is_center ? 18 : 13
      )
      label.scale.set(30,7,1)
      label.position.copy(p)
      label.position.y += baseR+8
      label.userData = { isGraph:true }
      scene.add(label)
    })

    /* ── Draw cones / links ─────────────────────────────────────────────── */
    graphData.links.forEach(link => {
      const sp = pos.get(link.source)
      const tp = pos.get(link.target)
      if (!sp || !tp) return

      const sn   = graphData.nodes.find(n=>n.id===link.source)!
      const tn   = graphData.nodes.find(n=>n.id===link.target)!
      const sCol = riskHex(sn.risk_score, sn.is_center)
      const tCol = riskHex(tn.risk_score, false)
      const dir  = new THREE.Vector3().subVectors(tp, sp)
      const len  = dir.length()
      const mid  = new THREE.Vector3().addVectors(sp,tp).multiplyScalar(0.5)
      const cR   = sn.is_center ? 3.5+(tn.received_usd/maxRcv)*3.5 : 1.5+(link.amount_usd/maxAmt)*3

      /* Cone body */
      const cone = new THREE.Mesh(
        new THREE.CylinderGeometry(0.2, cR, len*0.82, 32, 1, true),
        new THREE.MeshPhongMaterial({
          color:sCol, emissive:sCol, emissiveIntensity:0.22,
          transparent:true, opacity:0.48,
          shininess:90, side:THREE.DoubleSide, specular:0xffffff,
        })
      )
      cone.position.copy(mid)
      cone.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), dir.clone().normalize())
      cone.userData = { isGraph:true }
      scene.add(cone)

      /* Glow axis line */
      const lineGeo = new THREE.BufferGeometry().setFromPoints([sp.clone(),tp.clone()])
      const line    = new THREE.Line(lineGeo,
        new THREE.LineBasicMaterial({ color:sCol, transparent:true, opacity:0.35 })
      )
      line.userData = { isGraph:true }
      scene.add(line)

      /* Arrow tip */
      const norm = dir.clone().normalize()
      const aN   = 4+cR*0.65
      const arrow = new THREE.Mesh(
        new THREE.ConeGeometry(cR*0.55, aN, 16),
        new THREE.MeshPhongMaterial({
          color:tCol, emissive:tCol, emissiveIntensity:0.5, transparent:true, opacity:0.9,
        })
      )
      arrow.position.copy(tp).addScaledVector(norm, -aN*0.55)
      arrow.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), norm)
      arrow.userData = { isGraph:true }
      scene.add(arrow)

      /* Amount label */
      const amtLabel = makeLabel(`$${(link.amount_usd/1000).toFixed(1)}K`, '#94A3B8', 11)
      amtLabel.scale.set(18,4,1)
      amtLabel.position.copy(mid)
      amtLabel.position.y += 4
      amtLabel.userData = { isGraph:true }
      scene.add(amtLabel)
    })

  }, [graphData, address])

  /* Controls */
  const toggleSpin = () => { spinning.current=!spinning.current; setIsSpinning(spinning.current) }
  const resetCamera = () => {
    orbitRef.current.theta=0; orbitRef.current.phi=0.6; orbitRef.current.radius=210
    const o=orbitRef.current; const cam=camRef.current
    if (!cam) return
    cam.position.set(
      o.radius*Math.sin(o.phi)*Math.sin(o.theta),
      o.radius*Math.cos(o.phi),
      o.radius*Math.sin(o.phi)*Math.cos(o.theta)
    )
    cam.lookAt(0,0,0)
  }

  return (
    <div className="relative w-full rounded-2xl overflow-hidden border border-gray-800 bg-gray-950"
      style={{ height:560 }}>

      <div ref={mountRef} className="w-full h-full" />

      {/* Scanlines */}
      <div className="absolute inset-0 pointer-events-none"
        style={{ background:'repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,0.03) 3px,rgba(0,0,0,0.03) 4px)' }} />

      {/* HUD top-left */}
      <div className="absolute top-3 left-3 bg-black/70 backdrop-blur-md rounded-xl
                      px-3 py-2 border border-gray-700/60 font-mono pointer-events-none">
        <div className="text-[10px] text-sky-400 font-bold mb-1 tracking-widest">CRYPTO TRACE</div>
        <div className="text-[9px] text-gray-400">NODES <span className="text-white font-bold ml-1">{graphData.nodes.length}</span></div>
        <div className="text-[9px] text-gray-400">LINKS <span className="text-white font-bold ml-1">{graphData.links.length}</span></div>
        <div className="text-[9px] text-gray-500 uppercase mt-0.5">{data?.chain||'BTC'}</div>
      </div>

      {/* Controls hint top-right */}
      <div className="absolute top-3 right-3 bg-black/70 backdrop-blur-md rounded-xl
                      px-3 py-2 border border-gray-700/60 font-mono pointer-events-none text-[9px] text-gray-400 space-y-0.5">
        <div><span className="text-sky-400">DRAG</span> Rotate</div>
        <div><span className="text-sky-400">SCROLL</span> Zoom</div>
        <div><span className="text-sky-400">CLICK</span> Inspect</div>
      </div>

      {/* Control buttons bottom-right */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2">
        <button onClick={toggleSpin}
          className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold
                      border backdrop-blur-md transition-all ${
            isSpinning ? 'bg-sky-600/80 border-sky-500 text-white'
              : 'bg-black/70 border-gray-700 text-gray-300 hover:border-sky-500 hover:text-white'
          }`}>
          <i className={`ti ti-rotate-clockwise ${isSpinning?'animate-spin':''}`} />
          {isSpinning?'Stop spin':'Auto spin'}
        </button>
        <button onClick={resetCamera}
          className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold
                     bg-black/70 border border-gray-700 text-gray-300 backdrop-blur-md
                     hover:border-sky-500 hover:text-white transition-all">
          <i className="ti ti-focus-centered" />Reset view
        </button>
      </div>

      {/* Legend bottom-left */}
      <div className="absolute bottom-4 left-4 bg-black/70 backdrop-blur-md
                      rounded-xl p-3 border border-gray-700/60 pointer-events-none">
        <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-2 font-mono">Legend</div>
        {[['#38BDF8','Center nucleus'],['#34D399','Clean'],['#FBBF24','Suspicious'],['#EF4444','High risk']].map(([c,l])=>(
          <div key={l} className="flex items-center gap-2 mb-1">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background:c, boxShadow:`0 0 5px ${c}` }} />
            <span className="text-[9px] text-gray-300 font-mono">{l}</span>
          </div>
        ))}
        <div className="pt-1.5 border-t border-gray-700/60 mt-1">
          <div className="text-[9px] text-gray-500">Large cone = High value</div>
          <div className="text-[9px] text-gray-500">Small cone = Low value</div>
        </div>
      </div>

      <InfoDrawer
        node={selected}
        onClose={() => setSelected(null)}
        onRecenter={(addr) => { onRecenter(addr); setSelected(null) }}
      />
    </div>
  )
}
