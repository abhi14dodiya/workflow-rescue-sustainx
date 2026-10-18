import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

// All geometry, lighting and surfaces are procedural. No external model or texture downloads.
export default function CrystalScene({ progress, selected, workflow, onSelect, onPositions, onReady, onUnavailable }) {
  const host = useRef(null);
  const latest = useRef({ progress, selected, workflow, onSelect, onPositions, onReady, onUnavailable });
  latest.current = { progress, selected, workflow, onSelect, onPositions, onReady, onUnavailable };

  useEffect(() => {
    const container = host.current;
    const canvas = document.createElement('canvas');
    let context;
    try { context = canvas.getContext('webgl2', { alpha: true, antialias: true, powerPreference: 'low-power' }); } catch { /* graceful SVG fallback */ }
    if (!context) { latest.current.onUnavailable(); return; }
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, context, alpha: true, antialias: true, powerPreference: 'low-power' });
    } catch { latest.current.onUnavailable(); return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, window.innerWidth < 760 ? 1.25 : 1.75));
    renderer.setClearColor(0x000000, 0);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.12;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    canvas.setAttribute('aria-hidden', 'true');
    canvas.dataset.scene = 'recovery-crystal';
    container.appendChild(canvas);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 80);
    camera.position.set(0, 2.2, 11.8);
    camera.lookAt(0, 0, 0);
    const room = new RoomEnvironment();
    const pmrem = new THREE.PMREMGenerator(renderer);
    const environment = pmrem.fromScene(room, 0.025);
    scene.environment = environment.texture;
    scene.environmentIntensity = 0.75;
    room.dispose();
    scene.add(new THREE.AmbientLight(0xd8d5ff, 0.8));
    const key = new THREE.DirectionalLight(0xffffff, 2.6); key.position.set(-4, 5, 6); scene.add(key);
    const fill = new THREE.PointLight(0x79eaff, 14, 20); fill.position.set(4, 1, 2); scene.add(fill);
    const warm = new THREE.PointLight(0xac80ff, 12, 15); warm.position.set(-4, -2, 3); scene.add(warm);

    const sculpture = new THREE.Group(); scene.add(sculpture);
    sculpture.rotation.set(-0.06, -0.4, -0.14);
    const glass = new THREE.MeshPhysicalMaterial({ color: 0x7b7fe5, metalness: 0.16, roughness: 0.12,
      transmission: 0.36, thickness: 1, ior: 1.45, clearcoat: 1, clearcoatRoughness: 0.06,
      attenuationColor: new THREE.Color(0x6963bd), attenuationDistance: 2, envMapIntensity: 1.15 });
    const darkGlass = new THREE.MeshPhysicalMaterial({ color: 0x242459, roughness: 0.12, metalness: 0.4,
      transmission: 0.12, thickness: 0.8, clearcoat: 1, envMapIntensity: 1.5 });
    const bright = new THREE.MeshStandardMaterial({ color: 0xd6dcff, metalness: 0.55, roughness: 0.2,
      emissive: 0x7875ff, emissiveIntensity: 0.35 });
    const champagne = new THREE.MeshStandardMaterial({ color: 0x98eaff, metalness: 0.7, roughness: 0.2 });
    const palette = [0x5ad4f0, 0xa58afb, 0x6b9bff];
    const semanticColor = (status, i) => status === 'verified' ? 0x52e3ad : ['blocked', 'review'].includes(status) ? 0xffbb57 : status === 'error' ? 0xff657e : palette[i];

    // An open orbital frame, rather than a tower. The three domains fit around the intent core.
    const core = new THREE.Mesh(new THREE.IcosahedronGeometry(0.74, 0), darkGlass);
    core.position.set(0, 0, 0); sculpture.add(core);
    const coreWire = new THREE.LineSegments(new THREE.EdgesGeometry(core.geometry), new THREE.LineBasicMaterial({ color: 0xcbb8ff, transparent: true, opacity: 0.7 }));
    core.add(coreWire);
    const inner = new THREE.Mesh(new THREE.OctahedronGeometry(0.36, 0), bright); core.add(inner);

    const rings = [];
    for (let i = 0; i < 2; i++) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(2.34 + i * 0.14, 0.013, 6, 110), i ? champagne : bright);
      ring.rotation.set(Math.PI / 2 + (i ? 0.15 : 0), 0.2, 0); sculpture.add(ring); rings.push(ring);
    }
    const markerPoints = [];
    for (let i = 0; i < 50; i++) {
      const angle = (i / 50) * Math.PI * 2;
      markerPoints.push(new THREE.Vector3(Math.cos(angle) * 2.72, -1.08, Math.sin(angle) * 2.72));
    }
    const track = new THREE.Points(new THREE.BufferGeometry().setFromPoints(markerPoints), new THREE.PointsMaterial({ color: 0x807be0, size: 0.028, transparent: true, opacity: 0.8 }));
    sculpture.add(track);
    const groups = []; const shells = []; const connectors = []; const packets = []; const dots = [];
    for (let i = 0; i < 3; i++) {
      const group = new THREE.Group();
      const shellMaterial = glass.clone(); shellMaterial.color.set(palette[i]);
      const shell = new THREE.Mesh(new RoundedBoxGeometry(1.46, 1.6, 0.76, 3, 0.13), shellMaterial);
      shell.userData.service = i; group.add(shell); shells.push(shell);
      const inset = new THREE.Mesh(new RoundedBoxGeometry(1.13, 1.23, 0.085, 2, 0.06), darkGlass);
      inset.position.z = -0.18; group.add(inset);
      // Each domain has a distinct physical symbol visible through the polished shell.
      if (i === 0) {
        const coin = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.07, 40), champagne);
        coin.rotation.x = Math.PI / 2; coin.position.z = 0.37; group.add(coin);
        const slit = new THREE.Mesh(new RoundedBoxGeometry(0.1, 0.32, 0.08, 2, 0.025), bright);
        slit.position.z = 0.425; group.add(slit);
      } else if (i === 1) {
        for (let j = 0; j < 4; j++) {
          const box = new THREE.Mesh(new RoundedBoxGeometry(0.25, 0.25, 0.2, 2, 0.035), j === 3 ? champagne : bright);
          box.position.set((j % 2 - 0.5) * 0.33, (Math.floor(j / 2) - 0.5) * 0.33, 0.38); group.add(box);
        }
      } else {
        for (let j = 0; j < 3; j++) {
          const line = new THREE.Mesh(new RoundedBoxGeometry(j === 2 ? 0.3 : 0.6, 0.06, 0.06, 2, 0.025), bright);
          line.position.set(j === 2 ? -0.15 : 0, 0.19 - j * 0.19, 0.43); group.add(line);
        }
      }
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.047, 10, 8), bright.clone()); dot.position.set(-0.46, 0.54, 0.41); group.add(dot); dots.push(dot);
      sculpture.add(group); groups.push(group);
      const geometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]);
      const line = new THREE.Line(geometry, new THREE.LineDashedMaterial({ color: palette[i], transparent: true, opacity: 0.55, dashSize: 3, gapSize: 0.08 })); sculpture.add(line); connectors.push(line);
      const packet = new THREE.Mesh(new THREE.SphereGeometry(0.052, 10, 8), bright.clone()); sculpture.add(packet); packets.push(packet);
    }

    let frame = 0, disposed = false, visible = false, dragging = false, startX = 0, totalMove = 0;
    let drag = 0, dragSmooth = 0, rotation = -0.4, smoothedProgress = 0, lastTime = 0, elapsed = 0, spread = 1;
    const targetColor = new THREE.Color();
    const resize = () => {
      const { width, height } = container.getBoundingClientRect();
      if (!width || !height) return;
      camera.aspect = width / height;
      camera.position.z = width < 450 ? 13.3 : 11.8;
      camera.updateProjectionMatrix(); renderer.setSize(width, height);
    };
    const animate = time => {
      frame = 0;
      if (disposed || !visible || document.hidden) return;
      const dt = Math.min((time - (lastTime || time)) / 1000, 0.05); lastTime = time; elapsed += dt;
      const state = latest.current;
      smoothedProgress = THREE.MathUtils.damp(smoothedProgress, state.progress, 5, dt);
      dragSmooth = THREE.MathUtils.damp(dragSmooth, drag, 5, dt);
      rotation = THREE.MathUtils.damp(rotation, -0.4 + smoothedProgress * 2.1 - state.selected * 0.22 + dragSmooth, 4, dt);
      sculpture.rotation.y = rotation;
      sculpture.rotation.x = -0.12 + smoothedProgress * 0.28;
      sculpture.rotation.z = -0.13 + Math.sin(elapsed * 0.22) * 0.025;
      const aligned = state.workflow.aligned;
      // Only audited workflow state changes the formation. Scrolling is camera rotation only.
      spread = THREE.MathUtils.damp(spread, aligned ? 0 : state.workflow.phase === 'replanning' ? 1.2 : 1, 3, dt);
      groups.forEach((group, i) => {
        const angle = (i / 3) * Math.PI * 2 + Math.PI / 6;
        const radius = 1.5 + spread * 0.53;
        group.position.set(Math.cos(angle) * radius, Math.sin(angle) * (1.3 + spread * 0.45), Math.sin(angle + 0.6) * 0.7);
        group.position.y += Math.sin(elapsed * 0.7 + i * 2) * 0.045;
        group.rotation.set(0.04 + i * 0.1, -0.28 + Math.cos(angle) * 0.38, Math.cos(angle) * 0.09 * spread);
        const status = state.workflow.nodes[i].status;
        const active = state.workflow.active === i && !['blocked', 'review', 'error'].includes(status);
        const scale = state.selected === i ? 1.055 + (active ? Math.sin(elapsed * 4) * 0.012 : 0) : 0.97;
        group.scale.lerp(new THREE.Vector3(scale, scale, scale), 0.065);
        targetColor.set(semanticColor(status, i));
        shells[i].material.color.lerp(targetColor, 0.09);
        shells[i].material.emissive.copy(targetColor);
        shells[i].material.emissiveIntensity = active ? 0.15 + Math.sin(elapsed * 4) * 0.06 : state.selected === i ? 0.08 : 0.02;
        dots[i].material.color.copy(targetColor); dots[i].material.emissive.copy(targetColor); dots[i].material.emissiveIntensity = active ? 1.5 : 0.5;
        connectors[i].material.color.copy(targetColor);
        connectors[i].material.dashSize = status === 'blocked' ? 0.09 : status === 'waiting' ? 0.15 : 3;
        connectors[i].material.opacity = status === 'waiting' ? 0.3 : 0.75;
        const positions = connectors[i].geometry.attributes.position;
        positions.setXYZ(0, 0, 0, 0); positions.setXYZ(1, group.position.x, group.position.y, group.position.z);
        positions.needsUpdate = true;
        connectors[i].computeLineDistances();
        packets[i].visible = active;
        packets[i].position.copy(group.position).multiplyScalar((elapsed * 0.65) % 1);
        packets[i].material.emissive.copy(targetColor);
      });
      core.rotation.y = elapsed * 0.16; core.rotation.z = elapsed * 0.06;
      rings[0].rotation.z = elapsed * 0.07;
      bright.emissive.set(aligned ? 0x52e3ad : ['replanning', 'review'].includes(state.workflow.phase) ? 0xd59742 : state.workflow.phase === 'error' ? 0xff657e : 0x7875ff);
      bright.emissiveIntensity = aligned ? 0.8 : 0.4;
      renderer.render(scene, camera);
      const { width, height } = container.getBoundingClientRect();
      const project = vector => { const point = vector.project(camera); return { x: (point.x + 1) * width / 2, y: (-point.y + 1) * height / 2 }; };
      latest.current.onPositions(groups.map((group, i) => project(group.localToWorld(i === 2 ? new THREE.Vector3(1.05, 0, 0.5) : new THREE.Vector3(0, -0.98, 0.5)))));
      // Exposes only visual state for browser QA; no business or credential data.
      canvas.dataset.rotation = rotation.toFixed(3);
      canvas.dataset.progress = smoothedProgress.toFixed(3);
      canvas.dataset.phase = state.workflow.phase;
      canvas.dataset.services = JSON.stringify(groups.map((group, i) => ({ ...project(group.getWorldPosition(new THREE.Vector3())), status: state.workflow.nodes[i].status })));
      frame = requestAnimationFrame(animate);
    };
    const wake = () => { if (!disposed && visible && !document.hidden && !frame) { lastTime = 0; frame = requestAnimationFrame(animate); } };
    const resizeObserver = new ResizeObserver(() => { resize(); wake(); }); resizeObserver.observe(container);
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (!visible) { cancelAnimationFrame(frame); frame = 0; }
      else wake();
    }, { rootMargin: '60px' }); observer.observe(container);
    const visibility = () => { if (document.hidden) { cancelAnimationFrame(frame); frame = 0; } else wake(); };
    document.addEventListener('visibilitychange', visibility);
    const raycaster = new THREE.Raycaster();
    const down = event => { if (event.pointerType === 'touch') return; dragging = true; startX = event.clientX; totalMove = 0; canvas.setPointerCapture(event.pointerId); };
    const move = event => { if (dragging) { const dx = event.clientX - startX; drag += dx * 0.007; totalMove += Math.abs(dx); startX = event.clientX; } };
    const up = event => {
      const wasDragging = dragging; dragging = false;
      if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
      if (wasDragging && totalMove > 5) return;
      const rect = canvas.getBoundingClientRect();
      const pointer = new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1);
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(shells);
      if (hits[0]) latest.current.onSelect(hits[0].object.userData.service);
    };
    const cancel = () => { dragging = false; };
    const lost = event => { event.preventDefault(); latest.current.onUnavailable(); };
    canvas.addEventListener('pointerdown', down); canvas.addEventListener('pointermove', move);
    canvas.addEventListener('pointerup', up); canvas.addEventListener('pointercancel', cancel);
    canvas.addEventListener('webglcontextlost', lost);
    resize(); latest.current.onReady();
    return () => {
      disposed = true; cancelAnimationFrame(frame); observer.disconnect(); resizeObserver.disconnect();
      document.removeEventListener('visibilitychange', visibility);
      canvas.removeEventListener('pointerdown', down); canvas.removeEventListener('pointermove', move);
      canvas.removeEventListener('pointerup', up); canvas.removeEventListener('pointercancel', cancel); canvas.removeEventListener('webglcontextlost', lost);
      const geometries = new Set(), materials = new Set();
      scene.traverse(object => { if (object.geometry) geometries.add(object.geometry); if (object.material) (Array.isArray(object.material) ? object.material : [object.material]).forEach(m => materials.add(m)); });
      geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose());
      glass.dispose(); environment.dispose(); pmrem.dispose(); renderer.dispose(); renderer.forceContextLoss();
      if (canvas.parentNode === container) container.removeChild(canvas);
    };
  }, []);

  return <div ref={host} className="webgl-host" />;
}
