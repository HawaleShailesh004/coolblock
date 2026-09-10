"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

/**
 * §9.7's scroll hero, the visual half: a stylized city block whose ground
 * plane heats and cools using this project's own real thermal-ramp tokens
 * (packages/ui/src/tokens.css §8.2 -- inferno family, not a rainbow ramp),
 * not an arbitrary color chosen for this page. Buildings stay a fixed,
 * neutral, semi-transparent gray -- deliberately echoing the real product's
 * own building layer (packages/map/src/layers/buildings.ts,
 * docs/adr/0025-*.md's fix) so the marketing hero and the actual app agree
 * on what a "building" looks like, not two different visual languages.
 *
 * `progress` (0-1) is owned by the scroll-driving parent (ScrollHeatHero) --
 * this component only renders it, so a `prefers-reduced-motion` or
 * low-end-device fallback can hold `progress` at a fixed value instead of
 * tying it to scroll, without this file needing to know why.
 */

const COOL = new THREE.Color("#4cc9c0"); // --cool: cooling delivered
const HOT_PEAK = new THREE.Color("#de4968"); // --t-60: the real inferno ramp's mid-hot tone
const BUILDING_COLOR = new THREE.Color("#1a1f26"); // --bg-2, matching the real buildings layer

const GRID_SIZE = 9;
const SPACING = 1.15;

interface Building {
  x: number;
  z: number;
  height: number;
}

function buildGrid(): Building[] {
  // A fixed, hand-seeded pattern (not Math.random()) so the scene is
  // identical on every load -- deterministic, matching this project's
  // general preference for reproducible-over-flashy.
  const buildings: Building[] = [];
  let seed = 7;
  const next = () => {
    seed = (seed * 48271) % 2147483647;
    return seed / 2147483647;
  };
  for (let i = 0; i < GRID_SIZE; i++) {
    for (let j = 0; j < GRID_SIZE; j++) {
      if (next() < 0.15) continue; // sparse gaps, like real streets/lots
      buildings.push({
        x: (i - GRID_SIZE / 2) * SPACING,
        z: (j - GRID_SIZE / 2) * SPACING,
        height: 0.3 + next() * 1.6,
      });
    }
  }
  return buildings;
}

function heatFactorAt(progress: number): number {
  // A triangle wave: 0 at progress=0, 1 at progress=0.5, 0 again at
  // progress=1 -- heats into the problem, cools into the solution
  // (COOLBLOCK-BUILD-PLAN.md §9.7's own framing).
  return progress <= 0.5 ? progress / 0.5 : (1 - progress) / 0.5;
}

function heatColorAt(progress: number): THREE.Color {
  return COOL.clone().lerp(HOT_PEAK, heatFactorAt(progress));
}

function Scene({ progress }: { progress: number }) {
  const buildings = useMemo(() => buildGrid(), []);
  const groundRef = useRef<THREE.Mesh>(null);
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    const mat = groundRef.current?.material as THREE.MeshStandardMaterial | undefined;
    if (mat) {
      const color = heatColorAt(progress);
      mat.color.copy(color);
      mat.emissive.copy(color);
      mat.emissiveIntensity = 0.2 + heatFactorAt(progress) * 0.5;
    }
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.03;
    }
  });

  return (
    <group ref={groupRef} rotation={[0, 0, 0]}>
      <mesh ref={groundRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
        <planeGeometry args={[GRID_SIZE * SPACING + 1, GRID_SIZE * SPACING + 1]} />
        <meshStandardMaterial color={COOL} roughness={0.9} />
      </mesh>
      {buildings.map((b, i) => (
        <mesh key={i} position={[b.x, b.height / 2, b.z]} castShadow>
          <boxGeometry args={[0.7, b.height, 0.7]} />
          <meshStandardMaterial color={BUILDING_COLOR} transparent opacity={0.55} />
        </mesh>
      ))}
      <ambientLight intensity={0.7} />
      <directionalLight position={[6, 10, 4]} intensity={1.1} />
    </group>
  );
}

export default function HeatBlockScene({ progress }: { progress: number }) {
  return (
    <Canvas camera={{ position: [7, 6, 7], fov: 40 }} dpr={[1, 1.5]} gl={{ antialias: true }}>
      <Scene progress={progress} />
    </Canvas>
  );
}
