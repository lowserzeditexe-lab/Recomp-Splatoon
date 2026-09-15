# PROGRESS — Recomp Splatoon

Statut au 2026-01, basé sur l'audit réel du dépôt RebrewU @ `0b40c4f`.

## Milestones

- [x] **M0 — Repository audit** (docs/AUDIT.md, ARCHITECTURE.md, COMPATIBILITY.md, WINDOWS_BUILD.md, MISSING_FEATURES.md)
- [x] **M1 — RebrewU build** (Linux aarch64 vérifié, `bin/rebrewu` produit)
- [x] **M2 — Splatoon port build** (237/237 TU, `Gambit` binaire produit)
- [x] **M3 — Static recompilation** (déjà présent : 214 `Gambit_part*.cpp`)
- [x] **M4 — Runtime initialization** (boot mesuré : arène 768 MB, OS registered, heap seed, ctors run, entry dispatch)
- [ ] **M5 — First native frame** — BLOCKED par shaders R700→GLSL partiels (P0)
  - [x] Audit détaillé du translator (`docs/R700_GLSL_AUDIT.md`, 10 sections)
  - [x] Tests unitaires GPU-independent (`tests/test_r700_to_glsl.cpp`, 21 asserts, OK)
  - [x] Instrumentation opt-in : `RECOMP_SHADER_DUMP=<dir>` + `RECOMP_SHADER_NO_STUB=1` (safe, no effect if unset)
  - [ ] Capture réelle des shaders Splatoon (nécessite dump utilisateur légal)
  - [ ] Comptage opcodes rencontrés → priorité d'implémentation
  - [ ] Compléter les opcodes ALU/TEX manquants pour couvrir le VS+PS du render context initial
  - [ ] Validation GLSL sur GPU réel (`REQUIRES WINDOWS/GPU VALIDATION`)
  - [ ] Preuve : framebuffer présenté avec pixels non-magenta-stub
- [ ] **M6 — Splatoon main menu** — nécessite M5 + `content/` utilisateur
- [ ] **M7 — Input** — code présent (vpad, padscore), non testable sans dump
- [ ] **M8 — Playable offline** — nécessite M5..M7 + audio complet
- [ ] **M9 — Stability** — nécessite multi-thread réel + save data
- [ ] **M10 — Network research** — étude Pretendo/NEX/PRUDP (docs à produire)
- [ ] **M11 — Pretendo Account** (PNID, NEX identity, launcher status)
- [ ] **M12 — Pretendo Online** (game server discovery, Splatoon services)
- [ ] **M13 — Wii U ↔ PC Save Transfer** (SaveMii import/export, SD, LAN)
- [ ] **M14 — Modding** (VFS, manifest, load order, shader overrides)
- [ ] **M15 — Environment Separation** (Vanilla / Private Modded / Dev)
- [ ] **M16 — Private Modded Sessions** (LAN, custom maps, session manifest)
- [ ] **M17 — Native Windows Launcher** (UI complète)

## Trackers détaillés

- [x] Repository audit
- [x] RebrewU build (Linux aarch64)
- [x] Splatoon port build (Linux aarch64)
- [ ] RebrewU build (Windows x64) — `NOT TESTED — WINDOWS REQUIRED`
- [ ] Splatoon port build (Windows x64) — `NOT TESTED — WINDOWS REQUIRED`
- [ ] RPX verification tool (`recomp_verify` — non implémenté)
- [x] RPX analysis (rebrewu CLI disponible)
- [x] Static recompilation (déjà générée dans `Gambit/`)
- [x] Generated C++ compilation (GCC 12 aarch64 OK)
- [x] Runtime initialization (boot mesuré)
- [x] Memory arena (mmap/VirtualAlloc, 768 MB)
- [x] Filesystem shim (`/vol/content` → `./content`)
- [x] Window (SDL2) — code présent, non testable headless
- [ ] First frame — BLOCKED
- [x] GX2 display infrastructure — code présent (FBO, textures, raster state)
- [x] GX2 draw call infrastructure — code présent (VBO/VAO, fetch shader, byte-swap)
- [ ] Shaders R700 → GLSL — WIP (`port/os/gx2/r700_to_glsl.cpp`)
- [ ] Menu — nécessite frame + content
- [ ] Audio réel — miniaudio branché, mixing WIP
- [x] Input (VPAD/GamePad shim) — code présent
- [ ] Controller profiles (config JSON) — non implémenté
- [ ] Gyro (SDL2 SENSOR_GYRO) — non branché
- [ ] Save data (`nn_save`) — non implémenté
- [ ] Gameplay — dépend de tout ce qui précède
- [ ] Performance (FPS, frame time, 1% low overlay) — non implémenté
- [ ] Network research (NEX, PRUDP) — non commencé
- [ ] Pretendo Account layer — non implémenté (voir docs/PRETENDO_DESIGN.md)
- [ ] Save transfer Wii U ↔ PC — non implémenté (voir docs/SAVE_TRANSFER.md)
- [ ] Modding VFS + manifest — non implémenté (voir docs/MODDING_DESIGN.md)
- [ ] Environment separation (Vanilla / Private Modded / Dev) — non implémenté (voir docs/ENVIRONMENTS.md)

## Ce qui a été vérifié dans cet environnement

```
Host          : Debian 12 aarch64
Toolchain     : GCC 12.2.0, CMake 3.25.1, Ninja
RebrewU CLI   : bin/rebrewu (300 KB, help/recompile/inspect/... OK)
Port binaire  : build_port/Gambit (~165 MB Release+dbginfo)
Boot mesuré   : arène 768 MB, OS registered, data loaded,
                dimport re-patched, heap seeded 127 MB
```

## Prochaine action concrète

Une seule tâche à la fois. La prochaine est **M5** :

1. Reproduire un environnement Windows x64 ou Linux x86-64 avec GPU réel.
2. Compléter `port/os/gx2/r700_to_glsl.cpp` (instructions ALU/FETCH/CF R700
   manquantes, mapping samplers/constants, GLSL 4.1 core valide).
3. Fournir un `content/` légal.
4. Vérifier l'apparition du premier frame.
