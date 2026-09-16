"use client";

import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { Suspense, useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

/**
 * The homepage's 3D neighborhood -- real data only, exported by
 * scripts/export_landing_scene.py: Edison-Eastlake's measured surface
 * temperature as the ground, its 2,844 real building footprints at their
 * real heights (no vertical exaggeration), every public-land tree site the
 * default plan could pick, and the sites the $20,000 plan actually picks.
 *
 * `story` runs 0 -> 3 as the visitor scrolls (ScrollStory owns it):
 *   0-1  the heat, whole neighborhood
 *   1-2  every public place a tree could go fades in
 *   2-3  the camera moves in and the chosen sites rise in rank order
 */

export interface SceneData {
  frame: { width_m: number; depth_m: number };
  buildings: number[][]; // [height, x0, z0, x1, z1, ...]
  possible_sites: [number, number, number][]; // [x, z, trees]
  chosen_sites: { rank: number; trees: number; xz: [number, number] }[];
}

const ASPHALT = "#1d1f22";
const BUILDING = "#8a8f96";
const POSSIBLE = "#15171a"; // ink: a pale marker disappeared into the hot end of the ramp
const CANOPY = "#4cc9c0"; // --cool: what the plan picks

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const smooth = (v: number) => {
  const t = clamp01(v);
  return t * t * (3 - 2 * t);
};

function buildBuildingGeometry(buildings: number[][]): THREE.BufferGeometry | null {
  const parts: THREE.BufferGeometry[] = [];
  for (const b of buildings) {
    const [height, ...flat] = b;
    if (flat.length < 6) continue;
    const shape = new THREE.Shape();
    // Shape lives in XY; after rotating -90° about X, shape-Y becomes -Z, so
    // pass -z to land each footprint exactly where scene.json put it.
    shape.moveTo(flat[0]!, -flat[1]!);
    for (let i = 2; i < flat.length; i += 2) shape.lineTo(flat[i]!, -flat[i + 1]!);
    const geom = new THREE.ExtrudeGeometry(shape, { depth: height, bevelEnabled: false });
    geom.rotateX(-Math.PI / 2);
    parts.push(geom);
  }
  if (parts.length === 0) return null;
  const merged = mergeGeometries(parts, false);
  parts.forEach((p) => p.dispose());
  return merged;
}

function Neighborhood({ data, story, reducedMotion }: { data: SceneData; story: number; reducedMotion: boolean }) {
  // Texture settings ride in as props (`map-colorSpace`) rather than being
  // assigned onto the loaded texture: useLoader caches and shares it, so
  // mutating it here would reach into a value this component doesn't own.
  const heat = useLoader(THREE.TextureLoader, "/landing/heat.png");

  const buildingGeometry = useMemo(() => buildBuildingGeometry(data.buildings), [data.buildings]);
  const possibleRef = useRef<THREE.InstancedMesh>(null);
  const chosenRef = useRef<THREE.InstancedMesh>(null);
  const heatMaterial = useRef<THREE.MeshBasicMaterial>(null);
  const possibleMaterial = useRef<THREE.MeshBasicMaterial>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const displayed = useRef(story);

  const focus = useMemo(() => {
    const n = data.chosen_sites.length || 1;
    const x = data.chosen_sites.reduce((s, c) => s + c.xz[0], 0) / n;
    const z = data.chosen_sites.reduce((s, c) => s + c.xz[1], 0) / n;
    return new THREE.Vector3(x, 0, z);
  }, [data.chosen_sites]);

  useEffect(() => {
    const mesh = possibleRef.current;
    if (!mesh) return;
    data.possible_sites.forEach(([x, z], i) => {
      dummy.position.set(x, 1.5, z);
      dummy.rotation.set(-Math.PI / 2, 0, 0);
      dummy.scale.setScalar(1);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
    });
    mesh.instanceMatrix.needsUpdate = true;
  }, [data.possible_sites, dummy]);

  const wide = useMemo(() => new THREE.Vector3(1650, 1550, 2050), []);
  // Close enough that the chosen sites are unmistakable, far enough that
  // they are still sites *in a neighborhood* rather than abstract columns.
  const close = useMemo(() => focus.clone().add(new THREE.Vector3(950, 1000, 1250)), [focus]);
  const lookTarget = useMemo(() => new THREE.Vector3(), []);

  // `state.camera`, not useThree()'s: the frame callback drives the camera
  // every frame, which is a mutation of something render must not own.
  useFrame(({ camera, clock }, delta) => {
    // Ease toward the scroll position instead of snapping, unless the
    // visitor asked for reduced motion -- then every state is immediate.
    displayed.current = reducedMotion ? story : THREE.MathUtils.damp(displayed.current, story, 6, delta);
    const s = displayed.current;

    const zoom = smooth((s - 2) / 0.9);
    camera.position.lerpVectors(wide, close, zoom);
    if (!reducedMotion) {
      const drift = clock.elapsedTime * 0.02;
      camera.position.x += Math.sin(drift) * 90 * (1 - zoom);
      camera.position.z += Math.cos(drift) * 60 * (1 - zoom);
    }
    lookTarget.set(0, 0, 0).lerp(focus, zoom);
    camera.lookAt(lookTarget);

    if (heatMaterial.current) heatMaterial.current.opacity = 1 - 0.28 * smooth(s - 1) - 0.22 * smooth(s - 2);
    if (possibleMaterial.current) possibleMaterial.current.opacity = 0.9 * smooth(s - 1) * (1 - 0.65 * smooth(s - 2));

    const chosen = chosenRef.current;
    if (chosen) {
      data.chosen_sites.forEach((site, i) => {
        // Sites rise one after another in the order the optimizer picked them.
        const rise = smooth((s - 2 - i * 0.07) / 0.35);
        const height = (60 + site.trees * 9) * Math.max(rise, 0.0001);
        dummy.position.set(site.xz[0], height / 2, site.xz[1]);
        dummy.rotation.set(0, 0, 0);
        // Width rises with height, so an unpicked site is genuinely absent
        // rather than a flat disc sitting there giving away the ending.
        dummy.scale.set(rise, height, rise);
        dummy.updateMatrix();
        chosen.setMatrixAt(i, dummy.matrix);
      });
      chosen.instanceMatrix.needsUpdate = true;
    }
  });

  return (
    <>
      <color attach="background" args={[ASPHALT]} />
      <fog attach="fog" args={[ASPHALT, 2600, 5200]} />
      <ambientLight intensity={1.1} />
      <directionalLight position={[-900, 1400, 600]} intensity={1.4} />

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
        <planeGeometry args={[data.frame.width_m, data.frame.depth_m]} />
        <meshBasicMaterial
          ref={heatMaterial}
          map={heat}
          map-colorSpace={THREE.SRGBColorSpace}
          map-anisotropy={4}
          transparent
          toneMapped={false}
        />
      </mesh>

      {buildingGeometry && (
        <mesh geometry={buildingGeometry}>
          <meshLambertMaterial color={BUILDING} transparent opacity={0.5} />
        </mesh>
      )}

      <instancedMesh ref={possibleRef} args={[undefined, undefined, data.possible_sites.length]}>
        <circleGeometry args={[19, 12]} />
        <meshBasicMaterial ref={possibleMaterial} color={POSSIBLE} transparent opacity={0} depthWrite={false} />
      </instancedMesh>

      <instancedMesh ref={chosenRef} args={[undefined, undefined, data.chosen_sites.length]}>
        <cylinderGeometry args={[16, 16, 1, 14]} />
        <meshBasicMaterial color={CANOPY} toneMapped={false} />
      </instancedMesh>
    </>
  );
}

export default function NeighborhoodScene({
  data,
  story,
  reducedMotion,
  active,
}: {
  data: SceneData;
  story: number;
  reducedMotion: boolean;
  active: boolean;
}) {
  return (
    <Canvas
      camera={{ position: [1650, 1550, 2050], fov: 34, near: 10, far: 9000 }}
      dpr={[1, 1.75]}
      gl={{ antialias: true }}
      frameloop={active ? "always" : "never"}
      aria-hidden
    >
      <Suspense fallback={null}>
        <Neighborhood data={data} story={story} reducedMotion={reducedMotion} />
      </Suspense>
    </Canvas>
  );
}
