# TARGET_ARCHITECTURE — Architecture cible finale (Recomp Splatoon)

> **Ce document décrit l'architecture *cible*, pas l'implémentation actuelle.**
>
> Pour l'implémentation réellement présente aujourd'hui, voir
> `ARCHITECTURE.md`. Pour la différence entre les deux, voir
> `MISSING_FEATURES.md`. Pour l'avancement, voir `PROGRESS.md`.
>
> Ce document sert de **contrat architectural**. Il ne doit pas être
> implémenté d'un bloc. La priorité immédiate reste **M5 — First Native
> Frame**. Cette cible existe uniquement pour éviter les mauvaises
> décisions de conception dès maintenant (couplages qu'on regretterait,
> hypothèses qu'on figerait par erreur).

---

## 1. Vue d'ensemble

```
                         Recomp Splatoon
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
   Recompiler             Game Runtime            Launcher
        │                      │                      │
        │          ┌───────────┼───────────┐          │
        │          │           │           │          │
        │       Graphics     Audio       Input      Settings
        │          │           │           │          │
        │          └───────────┼───────────┘          │
        │                      │                      │
        │                Save System                  │
        │                      │                      │
        │                Mod Runtime                  │
        │                      │                      │
        │             ┌────────┼─────────┐            │
        │             │        │         │            │
        │            VFS     Patches   Plugins        │
        │             │        │         │            │
        │             └────────┼─────────┘            │
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                        Network Runtime
                               │
                     ┌─────────┴─────────┐
                     │                   │
                   Offline            Pretendo
                                         │
                                  ┌──────┴──────┐
                                  │             │
                                 PNID          NEX
                                  │             │
                                  └──────┬──────┘
                                         │
                                  Game Services
```

Trois blocs de premier niveau :

- **Recompiler** — reste RebrewU, génère C++ + **métadonnées** (nouveau).
- **Game Runtime** — Cafe OS shim + Graphics + Audio + Input + Save + Mods.
- **Launcher** — application native Windows (profils, config, mods,
  Pretendo, diagnostics).

Le **Network Runtime** est une sous-couche transverse consommée par le
Game Runtime et pilotée par le Launcher.

---

## 2. Recompiler — métadonnées cibles

Le cœur RebrewU doit rester séparé du runtime Splatoon. En complément
du code C++ actuel, le recompiler doit produire :

```
generated/
├── symbols.json          # fn name/ID → adresse, taille, section
├── functions.json        # fonctions découvertes + CFG + jump tables
├── globals.json          # .data / .bss / .rodata globals adressables
├── sections.json         # ELF sections (base, taille, perms, hash)
├── relocations.json      # relocations résolues + résiduelles
└── version.json          # RPX hash, jeu, région, version, recompiler rev
```

Ces métadonnées serviront ensuite au :

- Debugging (symboles pour stack traces natives).
- Profiling (attribution fn recompilée ↔ fn PPC).
- Modding (hooks stables par symbole, pas par adresse absolue).
- Diagnostics (crash logs enrichis).
- Plugins (référencer une fonction sans hardcoder `0x02C6BCA4`).

> Ces générateurs **n'existent pas** aujourd'hui dans RebrewU. C'est une
> extension à discuter avec l'upstream ou à ajouter en couche annexe.

---

## 3. Version identity

Chaque build doit exposer, à l'exécution comme dans les logs :

```
Game            : Splatoon
Region          : NTSC-EN
Game Version    : v1.0 launch
RPX SHA-256     : 45ecd1…
Recompiler      : RebrewU <rev> (<git sha>)
Runtime         : Recomp Splatoon <semver>
Mod API         : <int>
```

Aucun de ces champs n'est optionnel. Ils permettent le refus de mods
incompatibles et la comparaison des rapports de bug.

---

## 4. Runtime — couches cibles

```
Game (recompiled C++)
        │
        ▼
┌───────────────────────────────────────────────────┐
│                Guest Memory                       │  ← arène, dispatch, R/W endian
├───────────────────────────────────────────────────┤
│         Cafe OS compatibility layer               │
│  ┌─────────┬──────────┬────────┬─────────────┐    │
│  │ Threads │  Sync    │  TLS   │  Message Q  │    │
│  │ (real)  │ (real)   │(real)  │   (real)    │    │
│  └─────────┴──────────┴────────┴─────────────┘    │
│  ┌─────────┬──────────┬────────┬─────────────┐    │
│  │  Fiber/ │ Timers   │   FS   │  Panic/log  │    │
│  │  sched  │          │        │             │    │
│  └─────────┴──────────┴────────┴─────────────┘    │
├───────────────────────────────────────────────────┤
│              GX2 compatibility layer              │  ← surfaces, buffers, draws
├───────────────────────────────────────────────────┤
│                  Graphics Backend                 │  ← OpenGL / Vulkan / D3D12 / Metal
├───────────────────────────────────────────────────┤
│  Audio (AX pool + mixer)    │  Input (SDL2/HID)   │
├───────────────────────────────────────────────────┤
│           Save / Filesystem VFS / Mod Runtime     │
└───────────────────────────────────────────────────┘
```

### 4.1 Bootstrap temporaire

Les 4 overrides fibers actuellement dans `port/main.cpp` (voir
`ARCHITECTURE.md §2`) sont marqués **TEMPORARY BOOTSTRAP**. Ils doivent
disparaître progressivement à mesure que :

- `OSThread` → `std::thread` est branché.
- `OSMutex` / `OSSemaphore` / `OSEvent` → primitives C++ standards.
- `OSFiber` / GHS scheduler → mapping réel (fibers hôtes ou pool de threads).
- `OSGetThreadSpecific` → vrai TLS.

Tant que ces couches ne sont pas complètes, les overrides restent —
**mais ne sont pas considérés comme l'architecture finale**.

---

## 5. Graphics — abstraction cible

Pour M5, on garde **strictement** le backend OpenGL existant.

Architecture cible ensuite :

```
Game GX2 calls (recompiled)
        │
        ▼
     GX2 layer          (port/os/gx2/*)  — sémantique GX2 host-agnostic
        │
        ▼
  Graphics Backend       (interface abstraite)
        │
   ┌────┼────┬────────┐
   ▼    ▼    ▼        ▼
OpenGL Vulkan D3D12  Metal
```

Règle : ne **pas** refactorer le renderer avant M5. Une fois le premier
frame stable, extraire l'interface `IGraphicsBackend` en gardant OpenGL
comme implémentation de référence, puis ajouter Vulkan/D3D12/Metal.

---

## 6. Stub management

Les **610 stubs PLT** actuels (`gambit_plt_auto.cpp`) doivent être
classifiés au fur et à mesure de la couverture réelle :

| Classe                    | Statut cible                  |
| ------------------------- | ----------------------------- |
| Required for boot         | implémentés (état actuel)     |
| Required for menu         | implémentés (M6)              |
| Required for gameplay     | implémentés (M8)              |
| Required for audio        | implémentés (M8)              |
| Required for save         | implémentés (M9)              |
| Required for networking   | implémentés (M11+)            |
| Harmless / no-op          | documentés, laissés en STUB   |
| Unknown                   | listés, à investiguer         |

Un compteur "610 stubs pré-enregistrés" **ne mesure pas** le niveau de
compatibilité. Le tableau ci-dessus, quand rempli, le mesurera.

---

## 7. Address / symbol database

Pour chaque adresse aujourd'hui hardcodée dans `port/main.cpp` (voir
`AUDIT.md §7`), une entrée doit exister dans une table :

```
address    | symbol          | version         | purpose                  | source              | stability
0x02000020 | GHS _start      | v1.0 launch     | Entry point              | RPX header          | stable
0x02C6BCA4 | Gambit__start   | v1.0 launch     | Renderer init chain      | RE, gambit_loader   | stable
0x02C83190 | main game loop  | v1.0 launch     | Frame update loop        | RE, main.cpp        | stable
0x02817C50 | fiber wait      | v1.0 launch     | Bypass no-op             | RE                  | fragile
0x02818D40 | fiber sched     | v1.0 launch     | Bypass no-op             | RE                  | fragile
0x02818D44 | fiber sched     | v1.0 launch     | Bypass no-op             | RE                  | fragile
0x02C8706C | GHS vsync       | v1.0 launch     | Custom render dispatch   | RE, main.cpp        | fragile
0x101C98A8 | render_ctx_ptr  | v1.0 launch     | Render context pointer   | RE                  | stable
0x101C98F0 | TLS alloc handle| v1.0 launch     | Clear-for-fallback       | RE                  | stable
0x101D2554 | heap alloc base | v1.0 launch     | Custom allocator base    | RE                  | stable
0x101BFA54 | ctor table      | v1.0 launch     | Static ctors table       | RE                  | stable
0x101DC020 | ctors done flag | v1.0 launch     | GHS ctors barrier        | RE                  | stable
```

Objectif : produire cette table à partir des métadonnées §2, puis
référencer les adresses par symbole dans le code, avec vérification hash
au chargement.

Ne pas supprimer les adresses tant que la couche symboles n'est pas
disponible : elles restent nécessaires au runtime actuel.

---

## 8. Save system — architecture cible

```
                     Save Manager
                          │
      ┌───────────────────┼───────────────────┐
      │                   │                   │
      ▼                   ▼                   ▼
  PC store          Wii U SaveMii         LAN / FTP
      │              (SD, USB, folder)      (Wii U homebrew)
      │                   │                   │
      ▼                   ▼                   ▼
 userdata/         Import / Export       Direct transfer
  profiles/*
```

Fonctionnalités attendues (détail : `SAVE_TRANSFER.md`) :

- Profile mapping (Wii U user ↔ PC / PNID).
- Backup automatique avant toute écriture destructive.
- Restore par sélection d'horodatage.
- Validation structurelle + hash SHA-256 avant/après.

---

## 9. Account / Pretendo — architecture cible

```
Launcher
   │
   ▼
Pretendo Account          ← PretendoAccountService
   │
   ▼
PNID                      ← identifiant Pretendo distinct des NNID/NEX
   │
   ▼
NEX Session               ← RMC over PRUDP
   │
   ▼
Game Services             ← découverte via Account Server
```

Détail dans `PRETENDO_DESIGN.md`. Rappels clés :

- PNID ≠ NNID ≠ compte Windows local.
- Les credentials NEX ne se confondent jamais avec les credentials PNID.
- Aucune adresse de game server n'est hardcodée : elle vient de la
  découverte.
- NEX-Go est une bibliothèque Go **côté serveur** — référence protocole
  uniquement, ce n'est **pas** un client C++.

---

## 10. Mod Runtime — architecture cible

```
Game file access
    │
    ▼
Virtual File System
    │
    ├── Mod Overrides    (priorités, load order, conflicts)
    ├── Patch layer      (shader overrides, small data patches)
    └── Original content

Execution hooks
    │
    ├── Code hooks       (dispatch_table entries)
    ├── Memory patches   (signature-guarded)
    └── Plugins          (native DLL/SO, permissions-aware)

Metadata inputs
    │
    ├── symbols.json     (recompiler-generated)
    ├── functions.json
    └── memory_map.json
```

Le système de modding utilise :

- Le **VFS** (intégré au `coreinit_fs`) pour tous les assets.
- La **dispatch table** existante pour les hooks — pas de trampoline
  natif à écrire.
- Les **métadonnées** §2 pour éviter les adresses brutes fragiles.

Détail complet : `MODDING_DESIGN.md`.

---

## 11. Environnements — architecture cible

```
                    Recomp Splatoon
                          │
      ┌───────────────────┼───────────────────┐
      │                   │                   │
      ▼                   ▼                   ▼
 VANILLA ONLINE     PRIVATE MODDED       OFFLINE / DEV
      │                   │                   │
   Pretendo         LAN / Private        Offline only
   validated         server / Local
   env
```

Ces environnements sont **techniquement séparables** :

- Isolation des saves (`userdata/profiles/<player>/{vanilla,private_modded,development}/`).
- Isolation des mods actifs (profils de mods).
- Isolation du backend réseau autorisé.
- Validation stricte à l'entrée en Vanilla Online (voir `ENVIRONMENTS.md §4`).

Un lobby privé sur un service public **n'autorise pas automatiquement**
les modifications : la politique du service prévaut.

---

## 12. Launcher — architecture cible

Application native Windows (pas web) avec sections :

- Profiles
- Graphics
- Display
- Input
- Gyro
- Audio
- Save Data
- Mods
- Pretendo
- Diagnostics
- Logs

**Le launcher n'est pas prioritaire** avant :

1. First Frame (M5)
2. Main Menu (M6)
3. Offline Playability (M8)
4. Stability (M9)

Tant que ces jalons ne sont pas atteints, l'expérience utilisateur passe
par la ligne de commande + variables d'environnement + fichier JSON de
config minimal.

---

## 13. Priorité d'exécution — M5 → M17

```
M5   First Native Frame
 ↓
M6   Main Menu
 ↓
M7   PC Input (clavier, souris, gamepads, gyro basique)
 ↓
M8   Offline Playable (audio réel, gameplay stable)
 ↓
M9   Stability / Threading réel / Save data
 ↓
M10  Pretendo Research (protocole PRUDP, RMC, NEX documentés)
 ↓
M11  Pretendo Account (PNID, NEX identity, launcher status)
 ↓
M12  Pretendo Online (game server discovery, Splatoon services)
 ↓
M13  Wii U ↔ PC Save Transfer (SaveMii import/export, SD, LAN)
 ↓
M14  Modding (VFS, manifest, load order, shader overrides)
 ↓
M15  Environment Separation (Vanilla / Private Modded / Dev, validation)
 ↓
M16  Private Modded Sessions (LAN, custom maps, session manifests)
 ↓
M17  Native Windows Launcher (UI complète)
```

**Cette cible n'est pas à implémenter maintenant.** Elle sert
uniquement à ne pas prendre de mauvaises décisions au niveau M5–M8 qui
rendraient impossibles les jalons M10+.

Chaque milestone ci-dessus reste à valider individuellement dans
`PROGRESS.md`. Aucune case n'est cochée à l'avance.
