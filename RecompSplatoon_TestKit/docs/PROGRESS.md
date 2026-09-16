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
  - [x] Analyzer opcodes (`tools/shader_opcode_stats.py`, GPU-indépendant, produit md + json)
  - [x] Diff entre 2 dumps (`tools/shader_dump_diff.py`)
  - [x] Golden fixture runner + intégration `glslangValidator` optionnelle
  - [x] Harness build+run persistant (`tools/run_shader_tests.sh`)
  - [x] **Finding réel du translator** : `layout(binding=)` illégal en GLSL 4.10 strict (glslangValidator refuse ; drivers laxistes acceptent) — voir `docs/R700_GLSL_AUDIT.md §3`
  - [x] **Dump utilisateur légal reçu et vérifié** (`docs/DUMP_VERIFICATION.md`)
    - RPX SHA-256 : `45ecd1...` **STRICTEMENT IDENTIQUE** à la cible RebrewU
    - Region : PAL, Title ID `0005000010176A00`, title_version 16 (v1.0 launch)
    - Structure `{code, content, meta}` intacte, `Updates/` et `Saves/` non touchés
  - [x] Boot avec dump : progresse jusqu'à `GHS context created: 0x28000000` puis boucle infinie de dispatch à 0 à l'intérieur de `Gambit__start` (le contexte GL 4.1 n'existe pas dans ce conteneur ARM64 headless)
  - [ ] Capture réelle des shaders Splatoon — **REQUIRES WINDOWS/GPU VALIDATION**
        L'environnement actuel (Debian aarch64, dummy/llvmpipe) n'atteint pas
        `resolve_active_program`. La chaîne complète est prête, elle nécessite
        une box GPU x86-64 avec GL 4.1 core matériel.
  - [ ] Comptage opcodes rencontrés → priorité d'implémentation
  - [ ] Compléter les opcodes ALU/TEX manquants pour couvrir le VS+PS du render context initial
  - [ ] Décider #version 410+ext OU #version 420 pour le UBO binding
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

## Flow M5 clé-en-main (à exécuter sur box GPU + dump légal)

Toute l'infrastructure d'analyse est déjà en place et persistante dans
`/app/tools/`. La séquence exacte :

```bash
# 0. Prérequis : /app/vendor/rebrewu build_port/Gambit + content/ légal + GPU
cd /app/vendor/rebrewu
cp -r /path/to/legal/dump/content build_port/    # dump utilisateur

# 1. Capture des shaders réels avec fallback magenta DÉSACTIVÉ
mkdir -p /app/build/shader_dump_run1
RECOMP_SHADER_DUMP=/app/build/shader_dump_run1 \
  RECOMP_SHADER_NO_STUB=1 \
  ./build_port/Gambit

# 2. Rapport de fréquence + classification Supported/Partial/Missing
python3 /app/tools/shader_opcode_stats.py \
  /app/build/shader_dump_run1 \
  --out /app/docs/generated/R700_SPLATOON_OPCODE_STATS.md \
  --json /app/build/shader_dump_run1/stats.json

# 3. Golden tests sur les fixtures réelles (nécessite glslangValidator)
apt-get install -y glslang-tools           # si non présent
ln -sf /app/build/shader_dump_run1 /app/tests/shaders/fixtures  # OU cp
/app/tools/run_shader_tests.sh /app/tests/shaders/fixtures

# 4. À partir du rapport, implémenter UNIQUEMENT les opcodes "Missing" de la
#    section "Missing opcodes — implementation priority (highest count first)".
#    Rebuild : cmake --build /app/vendor/rebrewu/build_port

# 5. Re-capture après chaque itération et diff vs run précédent
mkdir -p /app/build/shader_dump_run2
RECOMP_SHADER_DUMP=/app/build/shader_dump_run2 RECOMP_SHADER_NO_STUB=1 \
  ./build_port/Gambit
python3 /app/tools/shader_dump_diff.py \
  /app/build/shader_dump_run1 \
  /app/build/shader_dump_run2 \
  --out /app/docs/generated/shader_diff.md

# 6. Une fois que le rapport ne montre plus d'opcodes "Missing" critiques
#    ET que run_shader_tests.sh passe avec glslangValidator,
#    supprimer RECOMP_SHADER_NO_STUB et observer un frame non-magenta.
#    Screenshot + logs = preuve M5.
```

Les fixtures capturées **restent dans `/app/build/`** et **ne sont jamais
committées** (`tests/shaders/.gitignore` + emplacement hors du tree docs).
