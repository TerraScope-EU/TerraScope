import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="TerraScope — High-End Neural Mesh", layout="wide")

st.markdown("""
<style>
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 0.6rem; max-width: 1600px; }
  canvas { border-radius: 14px; box-shadow: 0 14px 60px rgba(0,12,10,0.8); display:block; }
  .meta { color: #9eead7; opacity: 0.92; }
</style>
""", unsafe_allow_html=True)

HTML = """
<div style="width:100%; height:620px; overflow:hidden; background:#000;">
  <canvas id="terra_canvas" style="width:100%; height:620px;"></canvas>
</div>

<script>
// ---------------------------
// TerraScope High-End — JS
// ---------------------------

function RNG(seed = 1337){
  let s = seed >>> 0;
  return function() {
    s ^= s << 13; s ^= s >>> 17; s ^= s << 5;
    return ((s >>> 0) / 4294967295);
  };
}

function euPath(n=2200){
  const p = [];
  for(let i=0;i<n;i++){
    const θ = i/n * Math.PI*2;
    const r = 5.12 + 2.48*Math.cos(θ) + 1.62*Math.cos(2*θ) + 0.94*Math.sin(3*θ)
            -1.30*Math.cos(4*θ) + 0.78*Math.cos(6*θ) + 1.12*Math.pow(Math.cos(5*θ),3)
            +1.02*Math.exp(-32*(θ-1.05)**2)-0.68*Math.exp(-48*(θ+1.32)**2)
            +0.38*Math.tanh(3*θ)+0.36*Math.sin(8*θ);
    const x = 0.5 + 0.0618*(r*Math.cos(θ) + 0.46*Math.sin(7*θ));
    const y = 0.5 + 0.0618*(r*Math.sin(θ) + 1.12*Math.tanh(3*θ) + 0.32*Math.sin(9*θ));
    p.push({x,y});
  }
  return p;
}

const canvas = document.getElementById('terra_canvas');
const ctx = canvas.getContext('2d', { alpha: false });
let dpr = window.devicePixelRatio || 1;
let W = 0, H = 0;

function fitCanvas(){
  const r = canvas.getBoundingClientRect();
  W = Math.max(600, Math.floor(r.width));
  H = Math.max(300, Math.floor(r.height));
  canvas.width = Math.floor(W * dpr);
  canvas.height = Math.floor(H * dpr);
  canvas.style.width = W + 'px';
  canvas.style.height = H + 'px';
  ctx.setTransform(dpr,0,0,dpr,0,0);
}
fitCanvas();
window.addEventListener('resize', ()=>{ clearTimeout(window._fit); window._fit = setTimeout(fitCanvas,120); });

function pointInPoly(px, py, poly){
  let inside=false;
  for(let i=0,j=poly.length-1;i<poly.length;j=i++){
    const a = poly[i], b = poly[j];
    if(((a.y>py)!=(b.y>py)) && (px < (b.x-a.x)*(py-a.y)/(b.y-a.y+1e-12)+a.x)) inside=!inside;
  }
  return inside;
}

const rnd = RNG(987654321);
const boundary = euPath(2400);
const NODES = [];
(function genNodes(){
  const attempts = 4500;
  for(let i=0;i<attempts && NODES.length < 420;i++){
    const bx = Math.pow(rnd(), 0.9)*0.78 + 0.11;
    const by = Math.pow(rnd(), 1.15)*0.78 + 0.11;
    const x = Math.min(0.94, Math.max(0.06, bx + (rnd()-0.5)*0.06));
    const y = Math.min(0.94, Math.max(0.06, by + (rnd()-0.5)*0.06));
    if(pointInPoly(x,y,boundary)){
      NODES.push({
        x,y,
        phase: rnd()*Math.PI*2,
        radius: 1.6 + rnd()*1.8,
        bio: rnd()
      });
    }
  }
})();

// =================== GERADE LINIEN ===================
const EDGES = [];
(function linkNodes(){
  const maxNeighbors = 6;
  for(let i=0;i<NODES.length;i++){
    const a = NODES[i];
    const list = [];
    for(let j=0;j<NODES.length;j++){
      if(i===j) continue;
      const b = NODES[j];
      const dx = a.x - b.x, dy = a.y - b.y;
      const d2 = dx*dx + dy*dy;
      if(d2 < 0.06 && d2 > 0.0035) list.push({j,d2});
    }
    list.sort((p,q)=>p.d2-q.d2);
    for(let k=0;k<Math.min(maxNeighbors, list.length); k++){
      const j = list[k].j;
      const key = [Math.min(i,j), Math.max(i,j)].join('-');
      if(!EDGES.some(e => e.key === key)){
        EDGES.push({
          a: i, b: j, key,
          strength: 0.28 + rnd()*0.7
          // KEINE curvature mehr → gerade Linien
        });
      }
    }
  }
})();
// ================================================================

const DEEP_NODES = [];
for(let i=0;i<Math.min(220, Math.floor(NODES.length*0.5)); i++){
  const n = NODES[Math.floor(rnd()*NODES.length)];
  DEEP_NODES.push({
    x: n.x + (rnd()-0.5)*0.02,
    y: n.y + (rnd()-0.5)*0.02,
    phase: rnd()*Math.PI*2,
    radius: 1.0 + rnd()*1.0
  });
}
const DEEP_EDGES = [];
for(let i=0;i<DEEP_NODES.length;i++){
  const a = DEEP_NODES[i];
  for(let j=i+1;j<DEEP_NODES.length;j++){
    const b = DEEP_NODES[j];
    const dx=a.x-b.x, dy=a.y-b.y;
    const d2 = dx*dx + dy*dy;
    if(d2 < 0.045 && d2 > 0.0018 && rnd() < 0.26){
      DEEP_EDGES.push({a:i,b:j,str:0.22 + rnd()*0.5});
    }
  }
}

const PULSES = [];
function spawnPulseOnEdge(edgeIndex, deep=false){
  const e = deep ? DEEP_EDGES[edgeIndex] : EDGES[edgeIndex];
  if(!e) return;
  const from = (deep ? DEEP_NODES : NODES)[e.a];
  const to   = (deep ? DEEP_NODES : NODES)[e.b];
  const speed = (0.0025 + rnd()*0.0045) * (deep ? 0.6 : 1.0);
  PULSES.push({
    fromIdx: e.a, toIdx: e.b,
    from, to,
    t: 0, speed,
    layerDeep: deep,
    life: 1.0,
    hue: 170 + Math.floor(rnd()*40)
  });
}

function tickSpawn(t){
  const pcount = PULSES.length;
  const baseline = 0.28;
  if(rnd() < baseline * (1 + Math.min(pcount/40, 2))*0.6){
    const eidx = Math.floor(rnd()*EDGES.length);
    if(eidx < EDGES.length) spawnPulseOnEdge(eidx, false);
  }
  if(rnd() < 0.14){
    const eidx = Math.floor(rnd()*DEEP_EDGES.length);
    if(eidx < DEEP_EDGES.length) spawnPulseOnEdge(eidx, true);
  }
}

let lastTime = 0;
let heartbeatTimer = 0;
const HEARTBEAT_INTERVAL = 8000;
let heartbeatActive = false;

function renderFrame(tms){
  const t = tms * 0.001;
  const dt = Math.min(0.05, (tms - lastTime)/1000 || 0.016);
  lastTime = tms;

  const newDpr = window.devicePixelRatio || 1;
  if(newDpr !== dpr){ dpr = newDpr; fitCanvas(); }

  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, '#00161a'); g.addColorStop(1, '#000204');
  ctx.fillStyle = g; ctx.fillRect(0,0,W,H);

  ctx.globalAlpha = 0.12;
  ctx.fillStyle = 'rgba(0,8,12,1)';
  const fogShift = Math.sin(t * 0.12) * 30;
  ctx.fillRect(-40 + fogShift, -20, W+120, H+40);
  ctx.globalAlpha = 1.0;

  // DEEP EDGES – gerade, dick, langsam
  ctx.lineCap = 'round';
  for(let e of DEEP_EDGES){
    const A = DEEP_NODES[e.a], B = DEEP_NODES[e.b];
    const ax = A.x*W, ay = A.y*H, bx = B.x*W, by = B.y*H;
    ctx.lineWidth = 2.6 * e.str;
    ctx.strokeStyle = 'rgba(0,160,140,0.055)';
    ctx.beginPath(); ctx.moveTo(ax,ay); ctx.lineTo(bx,by); ctx.stroke();
    ctx.lineWidth = 0.9 * e.str;
    ctx.strokeStyle = 'rgba(0,210,180,0.12)';
    ctx.beginPath(); ctx.moveTo(ax,ay); ctx.lineTo(bx,by); ctx.stroke();
  }

  // SURFACE EDGES – gerade Linien, mehrschichtig
  for(let e of EDGES){
    const A = NODES[e.a], B = NODES[e.b];
    const ax = A.x*W, ay = A.y*H, bx = B.x*W, by = B.y*H;

    ctx.lineWidth = 1.2 * e.strength;
    ctx.strokeStyle = 'rgba(26,170,150,0.035)';
    ctx.beginPath(); ctx.moveTo(ax,ay); ctx.lineTo(bx,by); ctx.stroke();

    ctx.lineWidth = 0.9 * e.strength;
    ctx.strokeStyle = 'rgba(80,230,200,0.065)';
    ctx.beginPath(); ctx.moveTo(ax,ay); ctx.lineTo(bx,by); ctx.stroke();

    ctx.lineWidth = 0.5 * (0.6 + e.strength*0.8);
    ctx.strokeStyle = 'rgba(120,255,220,0.12)';
    ctx.beginPath(); ctx.moveTo(ax,ay); ctx.lineTo(bx,by); ctx.stroke();
  }

  tickSpawn(t);
  heartbeatTimer += dt * 1000;
  if(heartbeatTimer > HEARTBEAT_INTERVAL){
    heartbeatTimer = 0;
    for(let k=0;k<14;k++){
      const idx = Math.floor(rnd()*EDGES.length);
      spawnPulseOnEdge(idx, false);
    }
  }

  // PULSES – laufen jetzt auf GERADEN Linien
  for(let i = PULSES.length - 1; i >= 0; i--){
    const p = PULSES[i];
    p.t += p.speed * (1 + Math.min(PULSES.length/60, 1.5));
    if(p.t > 1.01 || p.life <= 0){ PULSES.splice(i,1); continue; }

    const x = p.from.x + (p.to.x - p.from.x) * p.t;
    const y = p.from.y + (p.to.y - p.from.y) * p.t;
    const screenX = x * W, screenY = y * H;

    const headSize = (p.layerDeep ? 2.0 : 2.8) * (0.8 + 0.6*(1 - Math.abs(0.5 - p.t)));
    const tailCount = 6;
    for(let s=0;s<tailCount;s++){
      const tt = p.t - s * 0.038;
      if(tt < 0) break;
      const kk = 1 - tt;
      const tx = p.from.x + (p.to.x - p.from.x) * tt;
      const ty = p.from.y + (p.to.y - p.from.y) * tt;
      const alpha = 0.34 * (1 - s / tailCount) * kk * (p.layerDeep ? 0.9 : 1.0);
      const size = headSize * (1 - s / (tailCount + 1)) * (p.layerDeep ? 0.6 : 1.0);

      ctx.globalCompositeOperation = 'lighter';
      ctx.beginPath();
      const col = `hsla(${p.hue}, 88%, ${p.layerDeep ? 55 : 62}%, ${alpha})`;
      const grad = ctx.createRadialGradient(screenX, screenY, 0, screenX, screenY, size*1.4);
      grad.addColorStop(0, col);
      grad.addColorStop(1, 'transparent');
      ctx.fillStyle = grad;
      ctx.arc(tx*W, ty*H, size*0.9, 0, Math.PI*2);
      ctx.fill();
      ctx.globalCompositeOperation = 'source-over';
    }
    p.life -= 0.0012;
  }

  // NODES
  for(let n of NODES){
    const b = 0.78 + 0.32*Math.sin(t*1.42 + n.phase);
    const sx = n.x * W, sy = n.y * H;
    ctx.globalCompositeOperation = 'lighter';
    const grad = ctx.createRadialGradient(sx, sy, 0, sx, sy, n.radius * 1.6 * b);
    grad.addColorStop(0, 'rgba(16,200,170,0.12)');
    grad.addColorStop(1, 'transparent');
    ctx.fillStyle = grad;
    ctx.beginPath(); ctx.arc(sx, sy, n.radius * 1.6 * b, 0, Math.PI*2); ctx.fill();
    ctx.globalCompositeOperation = 'source-over';

    ctx.beginPath();
    ctx.fillStyle = `rgba(120,255,220,${0.9 - n.bio*0.4})`;
    ctx.arc(sx, sy, n.radius * 0.9 * b, 0, Math.PI*2);
    ctx.fill();
  }

  requestAnimationFrame(renderFrame);
}

requestAnimationFrame(renderFrame);
</script>
"""

components.html(HTML, height=620)

st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)
st.markdown("""
<h1 style='font-size:48px; font-weight:700; margin:0;
  background:linear-gradient(90deg,#9ef0d6,#00c7a3);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>TerraScope — High-End Neural Mesh</h1>
""", unsafe_allow_html=True)

st.write("**TerraScope offers a European, autonomous alternative to traditional EO infrastructures, combining high-resolution optics, local analytics, and resilient terrestrial networking to support science, policy, agriculture, and crisis management.")

st.markdown("---")
c1, c2, c3 = st.columns(3)
with c1: st.subheader("Direkte Synapsen"); st.write("Gerade Linien = klare Kommunikationswege.")
with c2: st.subheader("Organische Dynamik"); st.write("Pulse, Glow und Herzschlag bleiben voll erhalten.")
with c3: st.subheader("High-End Performance"); st.write("Schneller, cleaner, skalierbar – ready für 2025.")

st.caption("© TerraScope — 2025 | Gerade. Klar. Lebendig.")
