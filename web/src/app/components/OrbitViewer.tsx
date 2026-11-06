"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type OrbitalObject = {
  name: string;
  catalog_id: string;
  position_km: [number, number, number];
  velocity_km_s: [number, number, number];
};

type OrbitPayload = {
  product: string;
  generated_at_utc: string;
  propagated_at_utc: string;
  coordinate_frame: string;
  snapshot_age_hours: number | null;
  object_count: number;
  objects: OrbitalObject[];
  limitations?: string[];
};

const EARTH_RADIUS_KM = 6371;

function formatVector(values: number[], digits = 2) {
  return values.map((value) => value.toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  })).join(", ");
}

const EARTH_MU_KM3_S2 = 398600.4418;

function calculateOrbitalElements(position: number[], velocity: number[]) {
  const dot = (a: number[], b: number[]) =>
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

  const cross = (a: number[], b: number[]) => [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];

  const magnitude = (v: number[]) => Math.sqrt(dot(v, v));

  const r = magnitude(position);
  const speed = magnitude(velocity);

  if (!Number.isFinite(r) || r <= 0 || !Number.isFinite(speed)) {
    return null;
  }

  const hVector = cross(position, velocity);
  const h = magnitude(hVector);

  if (!Number.isFinite(h) || h <= 0) return null;

  const eccentricityVector = cross(velocity, hVector).map(
    (value, index) => value / EARTH_MU_KM3_S2 - position[index] / r,
  );
  const eccentricity = magnitude(eccentricityVector);

  const specificEnergy = (speed * speed) / 2 - EARTH_MU_KM3_S2 / r;
  const semiMajorAxis =
    Math.abs(specificEnergy) > 1e-12
      ? -EARTH_MU_KM3_S2 / (2 * specificEnergy)
      : null;

  const inclination = Math.acos(
    Math.max(-1, Math.min(1, hVector[2] / h)),
  ) * (180 / Math.PI);

  const periodMinutes =
    semiMajorAxis !== null && semiMajorAxis > 0 && eccentricity < 1
      ? (2 * Math.PI * Math.sqrt(
          Math.pow(semiMajorAxis, 3) / EARTH_MU_KM3_S2,
        )) / 60
      : null;

  return {
    altitudeKm: r - EARTH_RADIUS_KM,
    speedKmS: speed,
    semiMajorAxisKm: semiMajorAxis,
    eccentricity,
    inclinationDeg: inclination,
    periodMinutes,
  };
}

function formatMetric(value: number | null, digits = 2) {
  return value !== null && Number.isFinite(value)
    ? value.toLocaleString(undefined, {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      })
    : "Unavailable";
}


export default function OrbitViewer() {
  const hostRef = useRef<HTMLDivElement>(null);
  const markerObjectsRef = useRef<{ mesh: THREE.Mesh; item: OrbitalObject }[]>([]);
  const [payload, setPayload] = useState<OrbitPayload | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState("");
  const latestObjectsRef = useRef<OrbitalObject[]>([]);
  const [loading, setLoading] = useState(true);

  const selected = payload?.objects.find((item) => item.catalog_id === selectedId) ?? null;
  useEffect(() => {
    latestObjectsRef.current = payload?.objects ?? [];
  }, [payload]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadStates() {
      try {
        const response = await fetch("/api/orbits", {
          cache: "no-store",
          signal: controller.signal,
        });
        const responseBody = await response.text();
        let parsedBody: unknown = null;
        try {
          parsedBody = responseBody ? JSON.parse(responseBody) : null;
        } catch {
          parsedBody = null;
        }

        if (!response.ok) {
          const detail =
            typeof parsedBody === "object" &&
            parsedBody !== null &&
            "detail" in parsedBody &&
            typeof parsedBody.detail === "string"
              ? parsedBody.detail
              : "";

          if (response.status === 503 && detail) {
            throw new Error(
              `Fresh orbital data is currently unavailable. ${detail}`,
            );
          }

          throw new Error(
            detail || `Orbital API returned HTTP ${response.status}`,
          );
        }

        if (!parsedBody || typeof parsedBody !== "object") {
          throw new Error("Orbital API returned an invalid response.");
        }
        const result = parsedBody as OrbitPayload;

        if (
          !Array.isArray(result.objects) ||
          !result.objects.every((item) =>
            typeof item.name === "string" &&
            typeof item.catalog_id === "string" &&
            Array.isArray(item.position_km) &&
            item.position_km.length === 3 &&
            item.position_km.every(Number.isFinite) &&
            Array.isArray(item.velocity_km_s) &&
            item.velocity_km_s.length === 3 &&
            item.velocity_km_s.every(Number.isFinite)
          )
        ) {
          throw new Error("Orbital API returned an unexpected state-vector format.");
        }

        if (!controller.signal.aborted) {
          setPayload(result);
          setSelectedId((current) =>
            current && result.objects.some((item) => item.catalog_id === current)
              ? current
              : result.objects[0]?.catalog_id ?? null
          );
          setLoadError("");
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setLoadError(error instanceof Error ? error.message : "Could not load orbital states.");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadStates();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    let disposed = false;
    let frameId = 0;
    let renderer: THREE.WebGLRenderer;

    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      window.setTimeout(() => setLoadError("WebGL is unavailable in this browser."), 0);
      return;
    }

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(host.clientWidth || 640, host.clientHeight || 390);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.domElement.className = "orbit-canvas";
    renderer.domElement.setAttribute("aria-label", "Interactive three-dimensional Earth and satellite positions");
    host.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#07111c");

    const camera = new THREE.PerspectiveCamera(
      42,
      (host.clientWidth || 640) / (host.clientHeight || 390),
      0.01,
      1000,
    );
    camera.position.set(2.7, 1.65, 3.3);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.minDistance = 1.25;
    controls.maxDistance = 12;
    controls.target.set(0, 0, 0);

    scene.add(new THREE.AmbientLight(0x9bb8df, 2.0));
    const sunlight = new THREE.DirectionalLight(0xffffff, 3.1);
    sunlight.position.set(4, 3, 5);
    scene.add(sunlight);

    const earth = new THREE.Mesh(
      new THREE.SphereGeometry(1, 64, 48),
      new THREE.MeshStandardMaterial({
        color: 0x123a59,
        roughness: 0.92,
        metalness: 0.02,
      }),
    );
    scene.add(earth);

    const gridMaterial = new THREE.LineBasicMaterial({
      color: 0x36779b,
      transparent: true,
      opacity: 0.48,
    });
    const gridGroup = new THREE.Group();

    for (let latitude = -75; latitude <= 75; latitude += 15) {
      const points: THREE.Vector3[] = [];
      const phi = THREE.MathUtils.degToRad(latitude);
      for (let step = 0; step <= 180; step++) {
        const theta = (step / 180) * Math.PI * 2;
        points.push(new THREE.Vector3(
          Math.cos(phi) * Math.cos(theta) * 1.003,
          Math.sin(phi) * 1.003,
          Math.cos(phi) * Math.sin(theta) * 1.003,
        ));
      }
      gridGroup.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(points),
        gridMaterial,
      ));
    }

    for (let longitude = 0; longitude < 180; longitude += 15) {
      const points: THREE.Vector3[] = [];
      const theta = THREE.MathUtils.degToRad(longitude);
      for (let step = 0; step <= 180; step++) {
        const phi = (step / 180) * Math.PI * 2;
        points.push(new THREE.Vector3(
          1.003 * Math.cos(phi) * Math.cos(theta),
          1.003 * Math.sin(phi),
          1.003 * Math.cos(phi) * Math.sin(theta),
        ));
      }
      gridGroup.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(points),
        gridMaterial,
      ));
    }
    scene.add(gridGroup);

    const atmosphere = new THREE.Mesh(
      new THREE.SphereGeometry(1.035, 48, 32),
      new THREE.MeshBasicMaterial({
        color: 0x328ac4,
        transparent: true,
        opacity: 0.075,
        side: THREE.BackSide,
      }),
    );
    scene.add(atmosphere);

    const starsGeometry = new THREE.BufferGeometry();
    const starPositions: number[] = [];
    let seed = 8731;
    const random = () => {
      seed = (seed * 16807) % 2147483647;
      return (seed - 1) / 2147483646;
    };
    for (let i = 0; i < 650; i++) {
      const radius = 12 + random() * 24;
      const theta = random() * Math.PI * 2;
      const y = (random() * 2 - 1) * radius;
      const ring = Math.sqrt(Math.max(0, radius * radius - y * y));
      starPositions.push(Math.cos(theta) * ring, y, Math.sin(theta) * ring);
    }
    starsGeometry.setAttribute("position", new THREE.Float32BufferAttribute(starPositions, 3));
    const stars = new THREE.Points(
      starsGeometry,
      new THREE.PointsMaterial({ color: 0x91b9d7, size: 0.035, transparent: true, opacity: 0.8 }),
    );
    scene.add(stars);

    const markerGroup = new THREE.Group();
    scene.add(markerGroup);
    const markerEntries: { mesh: THREE.Mesh; item: OrbitalObject }[] = [];
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();

    function addMarkers(items: OrbitalObject[]) {
      markerGroup.clear();
      markerEntries.length = 0;

      const markerGeometry = new THREE.SphereGeometry(0.025, 12, 10);
      for (const item of items) {
        const position = new THREE.Vector3(
          item.position_km[0] / EARTH_RADIUS_KM,
          item.position_km[1] / EARTH_RADIUS_KM,
          item.position_km[2] / EARTH_RADIUS_KM,
        );
        if (!Number.isFinite(position.length()) || position.length() < 1) continue;

        const material = new THREE.MeshBasicMaterial({ color: 0x48d8f5 });
        const mesh = new THREE.Mesh(markerGeometry, material);
        mesh.position.copy(position);
        mesh.userData.catalogId = item.catalog_id;
        markerGroup.add(mesh);

        const halo = new THREE.Mesh(
          new THREE.SphereGeometry(0.043, 12, 10),
          new THREE.MeshBasicMaterial({
            color: 0x2cc8f1,
            transparent: true,
            opacity: 0.18,
          }),
        );
        halo.position.copy(position);
        markerGroup.add(halo);
        markerEntries.push({ mesh, item });
      }
      markerObjectsRef.current = markerEntries;
    }

    const handleOrbitData = (event: Event) => {
      const customEvent = event as CustomEvent<OrbitalObject[]>;
      if (Array.isArray(customEvent.detail)) addMarkers(customEvent.detail);
    };
    host.addEventListener("skytrace-orbits-loaded", handleOrbitData);
    addMarkers(latestObjectsRef.current);

    function handlePointerDown(event: PointerEvent) {
      if (event.button !== 0) return;
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(markerEntries.map((entry) => entry.mesh));
      if (hits.length) {
        const catalogId = hits[0].object.userData.catalogId;
        if (typeof catalogId === "string") {
          setSelectedId(catalogId);
        }
      }
    }

    const handleSelection = (event: Event) => {
      const customEvent = event as CustomEvent<string>;
      if (!customEvent.detail) return;

      const selectedEntry = markerEntries.find(
        (entry) => entry.item.catalog_id === customEvent.detail,
      );

      for (const entry of markerEntries) {
        const selectedMarker = entry.item.catalog_id === customEvent.detail;
        (entry.mesh.material as THREE.MeshBasicMaterial).color.set(
          selectedMarker ? 0xffffff : 0x48d8f5,
        );
        entry.mesh.scale.setScalar(selectedMarker ? 1.65 : 1);
      }

      // Rotate the camera toward the selected satellite so far-side
      // objects can be inspected without drawing them through the Earth.
      if (selectedEntry) {
        const direction = selectedEntry.mesh.position.clone().normalize();
        camera.position.copy(direction.multiplyScalar(4.2));
        controls.target.set(0, 0, 0);
        controls.update();
      }
    };

    renderer.domElement.addEventListener("pointerdown", handlePointerDown);
    host.addEventListener("skytrace-object-select", handleSelection);

    const resizeObserver = new ResizeObserver(() => {
      if (disposed) return;
      const width = host.clientWidth;
      const height = host.clientHeight;
      if (width <= 0 || height <= 0) return;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    });
    resizeObserver.observe(host);

    function animate() {
      if (disposed) return;
      controls.update();
      renderer.render(scene, camera);
      frameId = window.requestAnimationFrame(animate);
    }
    animate();

    return () => {
      disposed = true;
      window.cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      host.removeEventListener("skytrace-object-select", handleSelection);
      host.removeEventListener("skytrace-orbits-loaded", handleOrbitData);
      controls.dispose();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.Points) {
          object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach((material) => material.dispose());
        }
      });
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !selectedId) return;
    host.dispatchEvent(new CustomEvent("skytrace-object-select", { detail: selectedId }));
  }, [selectedId]);

  useEffect(() => {
    if (!payload) return;
    const host = hostRef.current;
    if (!host) return;

    // The scene is mounted once; markers are rendered from the validated API response.
    // Keep marker construction tied to the scene's lifecycle through the canvas event.
    host.dispatchEvent(new CustomEvent("skytrace-orbits-loaded", {
      detail: payload.objects,
    }));
  }, [payload]);

  return (
    <div className="orbit-viewer">
      <div className="orbit-viewer-stage" ref={hostRef}>
        {loading && <div className="orbit-overlay">Loading propagated orbital states…</div>}
        {!loading && loadError && (
          <div className="orbit-overlay orbit-overlay-error" role="alert">
            <strong>Orbital data unavailable</strong>
            <span>{loadError}</span>
            <button type="button" onClick={() => window.location.reload()}>Retry</button>
          </div>
        )}
        {!loading && !loadError && payload && payload.objects.length === 0 && (
          <div className="orbit-overlay">The API returned no orbital objects.</div>
        )}
        <div className="orbit-viewer-badge">
          <span className="status-dot" />
          {payload ? `${payload.object_count} API objects` : "Awaiting data"}
        </div>
        <div className="orbit-viewer-help">Drag to rotate · Select a satellite to focus it · Scroll to zoom</div>
      </div>

      <div className="orbit-object-detail">
        <div className="orbit-object-heading">
          <div>
            <span className="eyebrow">SELECTED OBJECT</span>
            <strong>{selected?.name ?? "No object selected"}</strong>
          </div>
          <span className="orbit-object-id">{selected?.catalog_id ?? "—"}</span>
        </div>
        {selected ? (
          <>
            <div className="orbit-vector-grid">
            <div>
              <span>Position · km (TEME)</span>
              <code>{formatVector(selected.position_km)}</code>
            </div>
            <div>
              <span>Velocity · km/s (TEME)</span>
              <code>{formatVector(selected.velocity_km_s, 4)}</code>
            </div>
          </div>
          {(() => {
            const elements = calculateOrbitalElements(
              selected.position_km,
              selected.velocity_km_s,
            );

            if (!elements) return null;

            return (
              <>
                <p className="muted-note">Derived two-body orbital estimates</p>
                <div className="orbit-vector-grid">
                  <div>
                    <span>Altitude ? km</span>
                    <code>{formatMetric(elements.altitudeKm)}</code>
                  </div>
                  <div>
                    <span>Speed ? km/s</span>
                    <code>{formatMetric(elements.speedKmS, 4)}</code>
                  </div>
                  <div>
                    <span>Semi-major axis ? km</span>
                    <code>{formatMetric(elements.semiMajorAxisKm)}</code>
                  </div>
                  <div>
                    <span>Eccentricity</span>
                    <code>{formatMetric(elements.eccentricity, 5)}</code>
                  </div>
                  <div>
                    <span>Inclination ? degrees</span>
                    <code>{formatMetric(elements.inclinationDeg)}</code>
                  </div>
                  <div>
                    <span>Period ? minutes</span>
                    <code>{formatMetric(elements.periodMinutes)}</code>
                  </div>
                </div>
              </>
            );
          })()}
          </>
        ) : (
          <p className="muted-note">{loadError || "Select an object below to inspect its state vector."}</p>
        )}
      </div>

      {payload && payload.objects.length > 0 && (
        <div className="orbit-object-list" aria-label="Select a satellite">
          {payload.objects.map((item) => (
            <button
              key={item.catalog_id}
              type="button"
              className={`orbit-object-chip ${selectedId === item.catalog_id ? "is-selected" : ""}`}
              onClick={() => setSelectedId(item.catalog_id)}
              title={`Select ${item.name} (${item.catalog_id})`}
            >
              {item.name || item.catalog_id}
            </button>
          ))}
        </div>
      )}

      <div className="orbit-data-foot">
        <span>Frame: {payload?.coordinate_frame ?? "TEME"}</span>
        <span>Propagated: {payload?.propagated_at_utc ? new Date(payload.propagated_at_utc).toISOString().replace("T", " ").replace(".000Z", " UTC") : "—"}</span>
        <span>Snapshot age: {payload?.snapshot_age_hours != null ? `${payload.snapshot_age_hours.toFixed(1)} h` : "—"}</span>
      </div>
    </div>
  );
}
