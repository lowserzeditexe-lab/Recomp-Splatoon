# PRD — Recomp Splatoon Audit & Design Workspace

## Original problem statement
Créer **Recomp Splatoon** : recompilation statique native de Splatoon Wii U
(RPX/RPL PowerPC v1.0 launch) vers un exécutable PC (Windows x64 cible,
Linux/macOS possibles), en s'appuyant sur RebrewU. Livrable final :
`RecompSplatoon.exe`. Interdiction stricte de redistribuer tout fichier
propriétaire Nintendo.

Précision utilisateur (2e message) : **pas de dashboard web**. Le livrable
principal est le moteur natif ; le workspace Emergent doit servir à
auditer, comprendre, préparer le code — pas à recréer un SaaS.

## Environnement
- Conteneur Debian 12 aarch64, GCC 12.2.0, CMake 3.25.1, Ninja
- Impossible ici : produire un `.exe` Windows, tester GPU réel, tester
  contrôleurs physiques, tester audio réel, tester gameplay long.
- Possible ici : cloner RebrewU (fait), builder recompiler + port sur
  Linux aarch64 (fait), écrire docs (fait).

## User personas
- **Joueur** : possède un dump légal de Splatoon Wii U, veut jouer sur PC
  Windows sans émulateur.
- **Développeur / RE** : contribue au recompiler, au runtime, aux shaders,
  aux shims OS.
- **Modder** : crée des mods (assets, shaders, gameplay, plugins) via
  l'API officielle du projet.
- **Joueur privé / LAN** : joue avec des amis en environnement modifié
  isolé du réseau public.

## Core requirements (static)
1. Le projet **ne redistribue jamais** de fichiers Nintendo.
2. La chaîne technique est `RPX → RebrewU → C++ → MSVC/GCC → exe natif`.
3. Le runtime PC fournit Cafe OS shim, GX2 → OpenGL, input, audio, FS.
4. Pas d'émulateur, pas de Cemu, pas de clone, pas de remake.
5. Priorité : correctness > stabilité > perf. "Ça devrait marcher" interdit.
6. Chaque hypothèse est documentée, chaque test-terrain est marqué
   `NOT TESTED — WINDOWS REQUIRED` ou `REQUIRES WINDOWS/GPU VALIDATION`.

## What's been implemented (2026-01-15)
- **Clone RebrewU @ 0b40c4f** dans `/app/vendor/rebrewu/` (persistant).
- **Build recompiler** : `bin/rebrewu` fonctionne (v0.1.0), CLI vérifiée.
- **Build port Splatoon** : 237/237 TU compilent sans erreur, binaire
  `Gambit` produit (165 MB). **Boot mesuré** jusqu'à l'entry dispatch —
  seul le contenu utilisateur manque.
- **Documentation d'audit complète** dans `/app/docs/` :
  `AUDIT.md`, `ARCHITECTURE.md`, `COMPATIBILITY.md`, `WINDOWS_BUILD.md`,
  `MISSING_FEATURES.md`, `PROGRESS.md`.
- **Documents de design** pour les nouvelles sections utilisateur :
  `PRETENDO_DESIGN.md`, `SAVE_TRANSFER.md`, `MODDING_DESIGN.md`,
  `ENVIRONMENTS.md`.
- **README** du workspace pointant vers `docs/`.
- **Aucune modification** du code RebrewU — respect de la règle "ne pas
  toucher au recompiler sans nécessité".

## Prioritized backlog

### P0 — Premier pixel
- Compléter `port/os/gx2/r700_to_glsl.cpp` (translator R700 → GLSL).
  Nécessite GPU réel pour valider.

### P1 — Menu / gameplay
- Multi-threading réel (`OSThread` → `std::thread`).
- Audio complet (voice pool AX + mixer miniaudio).
- Save data (`nn_save` → host filesystem).

### P2 — PC-native features
- UI launcher native Windows (config JSON + boutons).
- Renderer alternatifs (Vulkan / D3D12 / Metal).
- Gyro via SDL2 SENSOR_GYRO.
- Sensibilités et deadzones configurables.
- Frame pacer découplé (refresh rate ≠ FPS).
- Fenêtre TV / Fenêtre GamePad séparées.

### P3 — Écosystème
- **Pretendo** : d'abord protocole (docs), puis PretendoAccountService,
  puis PRUDP, puis game server discovery, puis Splatoon services.
- **Save transfer Wii U ↔ PC** : SaveMii reader/writer, profile mapping,
  auto-backup, LAN Wii U FTP.
- **Modding** : VirtualFileSystem, manifest, load order, conflict
  detection, code hooks via `dispatch_table`, memory patches vérifiés.
- **Environnements** : Vanilla Online / Private Modded / Offline Dev,
  matrice de capabilities, validation stricte à l'entrée en Online.

## Next tasks (concrete, ordered)
1. Sur machine Windows/Linux avec GPU : compléter le shader translator.
2. Valider le premier frame contre un dump utilisateur légal.
3. Implémenter le VirtualFileSystem dans `coreinit_fs.cpp` (base du modding).
4. Étudier PRUDP v1 en détail (spec Pretendo) → publier `docs/PRUDP_STUDY.md`.
5. Ne pas commencer Pretendo tant que 1–3 ne sont pas verts.

## Ce qui reste MOCKED ou NON IMPLÉMENTÉ
- **Multi-threading** : bypass via 4 overrides fibers (main.cpp).
- **Save system** : aucune implémentation.
- **Pretendo, NEX, PRUDP** : aucune implémentation, uniquement DESIGN.
- **Save transfer Wii U↔PC** : aucune implémentation, uniquement DESIGN.
- **Modding, VFS, hooks** : aucune implémentation, uniquement DESIGN.
- **Environnements Vanilla/Private/Dev** : aucune UI, uniquement DESIGN.
- **UI launcher native** : n'existe pas encore.
- **First frame** : bloqué par shader translator incomplet.
