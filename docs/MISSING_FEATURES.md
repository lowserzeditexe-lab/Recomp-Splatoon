# MISSING_FEATURES — Recomp Splatoon

Liste des éléments **absents ou incomplets** dans l'état actuel du dépôt, avec
la priorité et l'endroit exact où intervenir. Aucun élément inventé : chaque
ligne se rattache à un fichier ou à une mention explicite du dépôt.

Légende : `P0` bloquant premier frame • `P1` bloquant menu/gameplay •
`P2` qualité • `P3` réseau/futur.

---

## P0 — Bloquants "premier pixel"

### R700 → GLSL shader translation

- **Fichier** : `port/os/gx2/r700_to_glsl.cpp` (405 lignes actuellement).
- **Statut** : partiel — README section "Project Status" ligne "🔄 In progress".
- **Symptôme observé** : "black window / nothing renders" (README §Troubleshooting).
- **Action** : compléter l'émulation des instructions ALU/FETCH/CF R700 encore
  manquantes, faire le mapping des samplers/constants et générer des shaders
  GLSL 4.1 core valides. `REQUIRES WINDOWS/GPU VALIDATION`.
- **Blocker level** : sans ceci, aucun pixel réel n'est rendu.

### Content directory manquant / dump utilisateur

- **Fichier** : `port/os/coreinit/coreinit_fs.cpp`.
- **Statut** : implémenté, mais dépend de `./content/` fourni par l'utilisateur.
- **Action** : documenter, pas coder. Le projet **ne doit pas** intégrer le
  dump.

## P1 — Bloquants gameplay long-terme

### Multi-threading réel

- **Fichier** : `port/os/coreinit/coreinit_threads.cpp` (243 l., stubs).
- **Statut** : ⏳ Planned. Le fiber scheduler est déjà bypassé via 4 overrides
  dans `port/main.cpp`, mais toute logique multi-cœur du jeu est court-circuitée.
- **Action** : mapper `OSThread` → `std::thread`, `OSMutex` → `std::mutex`,
  `OSEvent` → `std::condition_variable`, `OSSemaphore` → `std::counting_semaphore`.
  Remplacer progressivement les overrides `no-op` des fibers par un vrai
  scheduler quand le multi-thread guest est stable.

### Audio réel (voice pool AX + mixing)

- **Fichier** : `port/os/snd_core/snd_core.cpp` + `third_party/miniaudio.h`.
- **Statut** : 🔄 In progress. Compilé conditionnellement (`HAVE_MINIAUDIO`).
- **Action** : implémenter le voice pool AX (32 voix Wii U), le sample-rate
  converter, le mix bus master/music/SFX, brancher sur `ma_device_start`.

### Save data (`nn_save`)

- **Fichier** : à créer sous `port/os/nn_save/nn_save.cpp`.
- **Statut** : ⏳ Planned, aucun code présent.
- **Action** : mapper le titre save Wii U vers `./save/splatoon/<user>/` sur
  l'hôte. Format binaire à extraire côté RE, ne pas inventer.

## P2 — Qualité, features PC natives

### Renderer alternatifs (Vulkan / D3D12 / Metal)

- **Fichier** : nouveaux backends sous `port/os/gx2/backends/`.
- **Statut** : non implémenté.
- **Action** : abstraire d'abord l'interface renderer (facade sur
  `gx2_render.cpp`), puis ajouter backends. Faible priorité tant que OpenGL
  n'affiche pas correctement.

### Fenêtre TV + Fenêtre GamePad séparées

- **Fichier** : `port/os/gx2/gx2_context.cpp` (fenêtre unique actuellement),
  `port/runtime/screen_mode.h`.
- **Statut** : mode intégré uniquement (TV + GamePad dans la même fenêtre,
  bascule via Tab).
- **Action** : ajouter mode "deux fenêtres SDL2", conserver le mode intégré
  par défaut.

### UI de configuration native

- **Fichier** : n'existe pas.
- **Statut** : aucun launcher.
- **Action** : après stabilisation, ajouter un binaire séparé (petite UI
  Dear ImGui ou similaire, mêmes deps SDL2/GL) qui écrit un `config.json` lu
  par le port au boot.

### Sensibilités & deadzones configurables

- **Statut** : hard-coded dans le shim vpad.
- **Action** : lire un `config.json` (mouse_sensitivity, gyro_sensitivity,
  left/right stick deadzones, invert X/Y, response curve).

### Gyroscope (DualSense / DualShock / Switch Pro)

- **Statut** : le GamePad Wii U l'expose, mais l'input hôte n'est pas
  branché sur SDL2 sensor API.
- **Action** : brancher `SDL_GameControllerGetSensor(SDL_SENSOR_GYRO)` sur
  les valeurs guest exposées par vpad.

### Frame pacer, FPS uncap safe

- **Statut** : le loop tourne au rythme des `GX2SwapScanBuffers`. Pas de
  découplage `refresh rate ≠ game FPS`.
- **Action** : après stabilisation du rendu, analyser les dépendances
  gameplay/timing avant de déverrouiller.

## P3 — Réseau (research seulement pour l'instant)

### NEX / PRUDP / Pretendo

- **Fichier** : `port/os/nsysnet/nsysnet.cpp` (35 sockets stubs enregistrés).
- **Statut** : ⏳ Planned. Aucun protocole implémenté au-dessus de socket.
- **Action** :
  1. Étudier `nex-go` (Go, côté serveur) pour la sémantique protocole
     PRUDP v1 et RMC — **référence uniquement**.
  2. Décider (a) implémentation C++ native, (b) processus séparé Go relié
     via IPC, (c) portage du protocole. **N'écrire pas de code réseau tant
     que la position officielle de Pretendo sur les clients PC natifs pour
     Splatoon n'est pas vérifiée.**
  3. Marquer toute progression comme `EXPERIMENTAL / RESEARCH`.

## Éléments qui **NE seront pas** ajoutés dans ce dépôt

- Le RPX ou tout fichier issu du dump (`content/`, `meta/`).
- Textures, sons, shaders, symboles issus de l'extraction Nintendo.
- Redirections vers des copies pirates.
- Clés / tickets.
