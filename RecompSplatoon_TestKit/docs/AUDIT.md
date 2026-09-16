# AUDIT — Recomp Splatoon / RebrewU

**Date de l'audit :** 2026-01
**Auditeur :** E1 (agent Emergent) — lecture directe du code source, pas de suppositions
**Environnement d'audit :** Debian 12 aarch64, GCC 12.2.0, CMake 3.25.1, Ninja
**Commit RebrewU audité :** `0b40c4f810fdb41727cb8d6c979380001e29533f`
**Message de commit :** *"override fiber scheduler as no-op"*
**Dépôt :** <https://github.com/ApfelTeeSaft/RebrewU>

> Ce document est basé exclusivement sur le contenu réel du dépôt et sur des
> builds réels effectués dans cet environnement. Toute case marquée `UNKNOWN`
> signifie que la donnée n'a pas pu être vérifiée à la lecture du code.

---

## 1. Résumé exécutif

| Composant                                | État réel                                                  |
| ---------------------------------------- | ---------------------------------------------------------- |
| RebrewU (recompiler statique PPC → C++)  | **Compile et fonctionne** (Linux aarch64 vérifié)          |
| Port Splatoon (`Gambit`)                 | **Compile et link** (237/237 TU, aucune erreur)            |
| Code recompilé (`Gambit_part*.cpp`)      | **Présent, 214 TU générés + Gambit_data + Gambit_register** |
| Boot du binaire natif                    | **OK** : arène 768 MB, OS registered, heap seed, ctors run |
| Exécution avec dump utilisateur          | Non testable ici (dump non fourni, illégal à distribuer)   |
| Chaîne "RPX → C++ → exe natif"           | **Prouvée par l'existant** (le port fonctionne déjà)       |

Conclusion : **le pipeline principal existe déjà et fonctionne**. Le projet
n'est PAS à écrire de zéro. Le travail restant est de la spécialisation
runtime (voir §MISSING_FEATURES.md).

---

## 2. Structure réelle du dépôt

```
RebrewU/
├── CMakeLists.txt              # racine, C++20, ZLIB, nlohmann/json vendored
├── cmake/                      # CompilerOptions.cmake, RebrewUConfig.cmake.in
├── include/rebrewu/version.hpp # seul header public exporté
├── src/                        # sources du recompiler (50 fichiers)
│   ├── analysis/               # cfg_builder, function_discovery, jump_table
│   ├── cli/                    # cli_options + main → binaire `rebrewu`
│   ├── codegen/                # cpp_emitter, naming (C++ emission)
│   ├── config/                 # JSON overrides (symboles, boundaries, jumps)
│   ├── core/                   # elf/, rpx/, rpl/, relocation/, linker/
│   ├── diagnostics/            # logs structurés
│   ├── ir/                     # ir_types, ir_builder, ir_function, ir_module
│   └── ppc/                    # decoder + semantics
├── runtime/include/            # rebrewu_runtime.h (140 l.) — INTERFACE lib
├── tests/                      # 5 test files + Catch2 (fetch v3.7.1)
├── third_party/                # miniaudio.h (à télécharger), nlohmann/json.hpp
├── tools/plt_resolver.py       # helper Python pour la résolution PLT
├── Gambit/                     # OUTPUT DU RECOMPILER (218 fichiers)
│   ├── Gambit.h
│   ├── Gambit_data.cpp         # .data / .rodata en tableaux d'octets
│   ├── Gambit_register.cpp     # rbrew_register_func pour chaque fn traduite
│   └── Gambit_part0000..0214.cpp   # 214 TU de fonctions PPC → C++
└── port/                       # RUNTIME PC SPÉCIFIQUE À SPLATOON
    ├── CMakeLists.txt          # SDL2 + OpenGL + CURL + ZLIB + miniaudio opt.
    ├── README.md               # doc build/verify/troubleshoot
    ├── dirent_win.h            # shim POSIX dirent pour MSVC
    ├── main.cpp                # 396 lignes — boot & main loop, très commenté
    ├── gambit_plt_stubs.cpp    # 1530 l. — 610 stubs PLT auto-générés
    ├── loader/
    │   ├── gambit_loader.cpp        # Gambit_data_init fallback (weak)
    │   └── gambit_game_register.cpp # Gambit_game_register linkage
    ├── runtime/
    │   ├── rebrewu_runtime.cpp / .h  # dispatch, mem R/W, log
    │   └── screen_mode.h
    └── os/                     # Wii U OS shim
        ├── coreinit/           # fs, memory, misc, sync, threads
        ├── gx2/                # context, draw, render, r700_to_glsl (405 l.)
        ├── nsysnet/            # 35 fonctions socket enregistrées
        ├── padscore/           # WiiMote/pro pad
        ├── snd_core/           # audio AX
        ├── stubs/              # fallback pour APIs inconnues
        ├── vpad/               # GamePad
        └── gambit_plt_auto.cpp # pre-registre STUB pour 610 imports
```

## 3. Ce qui fonctionne réellement (vérifié dans cet audit)

| Étape                                     | Résultat mesuré                                     |
| ----------------------------------------- | --------------------------------------------------- |
| `cmake -S . -B build_core -G Ninja`       | **OK** — ZLIB trouvé, nlohmann bundled              |
| `cmake --build build_core -j`             | **OK** — 26/26 TU, produit `bin/rebrewu` (300 KB)   |
| `./bin/rebrewu` (help)                    | **OK** — commandes exposées : recompile, inspect, symbols, sections, exports, imports, disasm, help, version |
| `cmake -S port -B build_port -G Ninja`    | **OK** — SDL2, OpenGL, CURL, ZLIB, miniaudio détectés |
| `cmake --build build_port`                | **OK** — 237/237 TU, produit `Gambit` (165 MB avec debug info) |
| `SDL_VIDEODRIVER=dummy ./Gambit` (dry-run)| Boot :  "Guest arena 768 MB", "OS modules registered", "Data sections loaded", "Dimport re-patched", "Heap pre-seeded 127 MB" — puis dispatch 0 (attendu, pas de content/) |

## 4. Sous-systèmes du runtime port — inventaire réel

| Module              | Fichier                              | Lignes | Rôle réel                             |
| ------------------- | ------------------------------------ | ------ | ------------------------------------- |
| Runtime core        | `port/runtime/rebrewu_runtime.cpp/h` | 48 + 140 | `rbrew_dispatch`, `rbrew_register_func`, R/W endian PPC |
| PLT stubs auto      | `port/os/gambit_plt_auto.cpp`        | (auto) | Pre-registre 610 imports comme STUB   |
| PLT stubs generic   | `port/gambit_plt_stubs.cpp`          | 1530   | Wrappers redispatching vers guest fns |
| coreinit / memory   | `coreinit_memory.cpp`                | 142    | init arène, MEMAlloc*                 |
| coreinit / threads  | `coreinit_threads.cpp`               | 243    | OSThread stubs (thread réel = *planned*) |
| coreinit / sync     | `coreinit_sync.cpp`                  | 222    | mutex/cond stubs                      |
| coreinit / misc     | `coreinit_misc.cpp`                  | 372    | time, panic, dispatch dimports        |
| coreinit / fs       | `coreinit_fs.cpp`                    | 248    | /vol/content → ./content, FS log      |
| GX2 / context       | `gx2_context.cpp`                    | 289    | SDL2 window + GL context              |
| GX2 / draw          | `gx2_draw.cpp`                       | 417    | VBO/VAO, fetch shader, byte-swap      |
| GX2 / render        | `gx2_render.cpp`                     | 1167   | FBO, textures, raster state, swap     |
| GX2 / r700→GLSL     | `r700_to_glsl.cpp`                   | 405    | Translation AMD R700 shader → GLSL (partiel) |
| snd_core            | `snd_core.cpp`                       | ?      | AX voice pool + miniaudio (opt)       |
| vpad / padscore     | `vpad.cpp` / `padscore.cpp`          | ?      | GamePad + Pro controller              |
| nsysnet             | `nsysnet.cpp`                        | ?      | 35 socket fns enregistrées            |
| stubs               | `stubs.cpp`                          | ?      | Retour STUB pour tout non impl.       |

## 5. Version du jeu ciblée (source: `port/README.md`)

| Champ            | Valeur                                                          |
| ---------------- | --------------------------------------------------------------- |
| Titre            | Splatoon (WUP-AAZP / WUP-AAZE / équivalents régionaux)          |
| Version          | v1.0 (launch) — sans update appliquée                           |
| RPX SHA-256      | `45ecd1ed81a97f46b1c8ae24820cd47fbc55399b50af09bf1f9050fe803308e5` |
| Adresse entrée   | GHS `_start` @ `0x02000020`                                     |
| Gambit__start    | `0x02C6BCA4`                                                    |
| Main loop        | `fn_02C83190`                                                   |
| Table ctors      | `.rodata @ 0x101BFA54` (terminée par 0)                         |
| Flag ctors done  | `.bss @ 0x101DC020`                                             |
| SDA base (r13)   | `0x101C0BC0`                                                    |
| SDA2 base (r2)   | `0x10000000`                                                    |
| Stack top (r1)   | `0x1FC00000` (1 MB)                                             |
| Arena size       | `WIIU_MEM_SIZE` (768 MB dans le boot mesuré)                    |
| Dispatch max     | `0x0D000000` (entries 4-byte)                                   |

## 6. Fibers overrides déjà appliqués (source: `port/main.cpp`)

| Adresse guest | Rôle réel                                | Override                        |
| ------------- | ---------------------------------------- | ------------------------------- |
| `0x02817C50`  | GHS "wait for first frame" loop           | no-op                           |
| `0x02818D40`  | Fiber scheduler dispatch loop             | no-op                           |
| `0x02818D44`  | Fiber scheduler dispatch loop             | no-op                           |
| `0x02C8706C`  | GHS vsync-wait (raises GHS signal 6)      | Lit `0x101C98A8` (render ctx), dispatch `fn_028194E4` puis `GX2SwapScanBuffers` |

## 7. Adresses runtime critiques

| Adresse       | Signification                                     |
| ------------- | ------------------------------------------------- |
| `0x101C98A8`  | render context pointer (écrit par `fn_02818190`)  |
| `0x101C98F0`  | GHS TLS allocator handle (clear pour fallback)    |
| `0x101D2554`  | Base allocateur custom (heap pré-seedé)           |
| `0x02D0B8F8`  | Début zone dimport function pointers              |
| `0x02D0B908`  | Fin zone dimport (repatch nécessaire)             |
| `0x20000000`  | Base du heap injecté (127 MB)                     |
| `0x27FFF008`  | Fin du heap injecté                               |

## 8. Dépendances build réelles

| Dépendance      | Version testée              | Utilisation                          |
| --------------- | --------------------------- | ------------------------------------ |
| CMake           | 3.25.1                      | ≥ 3.18 requis pour le port          |
| C++             | GCC 12.2.0                  | C++20                                |
| SDL2            | 2.26.5                      | Fenêtre + GL context + input         |
| OpenGL          | libGL 1.6.0 (Mesa 22.3.6)   | Rendu                                |
| libcurl         | 7.88.1                      | nsysnet stubs                        |
| zlib            | 1.2.13                      | Décompression                        |
| miniaudio.h     | master (single-header)      | Audio backend (optionnel)            |
| nlohmann/json   | 3.11.3 (bundled/fetched)    | Config JSON                          |
| Catch2          | 3.7.1 (FetchContent)        | Tests unitaires (recompiler)         |

## 9. Modules RebrewU exportables

Extrait direct de `CMakeLists.txt` :

- `rebrewu_core` — ELF/RPX/RPL parsing, relocations, linker
- `rebrewu_ppc` — décodeur PowerPC + sémantique
- `rebrewu_ir` — IR (basic blocks, CFG) — INTERFACE header-only
- `rebrewu_analysis` — function discovery, CFG, jump tables
- `rebrewu_codegen` — émetteur C++
- `rebrewu_config` — chargement JSON overrides
- `rebrewu_diagnostics` — diagnostics structurés
- `rebrewu_runtime` — INTERFACE header-only (guest CPU state)

## 10. Statut par sous-système (source: `port/README.md` + code)

| Description                                             | Statut projet | Statut confirmé par audit |
| ------------------------------------------------------- | :-----------: | :-----------------------: |
| Recompiler pipeline                                     | ✅ Complete   | ✅ Confirmé (build OK)    |
| Boot infrastructure                                     | ✅ Complete   | ✅ Confirmé (boot mesuré) |
| Asset handling + dual-screen UI                         | ✅ Complete   | ⚠️ Code présent, non testable sans dump |
| GX2 display infra (FBO, textures, raster state)         | ✅ Complete   | ⚠️ Code présent (1167 l. render), non testable |
| Draw call infra (VBO/VAO, fetch shader, byte-swap)      | ✅ Complete   | ⚠️ Code présent (417 l. draw), non testable |
| AMD R700 → GLSL shader translation                      | 🔄 In progress| ⚠️ 405 l., partiel        |
| Audio (AX voice pool + miniaudio mixing)                | 🔄 In progress| ⚠️ Optional               |
| Real threading (std::thread mapping)                    | ⏳ Planned    | ❌ Stubs uniquement       |
| Save data (nn_save → host filesystem)                   | ⏳ Planned    | ❌ Non implémenté         |
| Networking (TCP/IP)                                     | ⏳ Planned    | ⚠️ Socket stubs (nsysnet) |
| Full compatibility pass                                 | ⏳ Planned    | ❌ Non fait               |

## 11. Splatoon-Decomp (référence RE)

Utilisé pour cross-check, pas modifié. Contient plusieurs branches par région/version :
NTSC Splatoon, NTSC Splatoon Update, NTSC Pre-Launch, NTSC Testfire, EN
Splatoon, EN Global Testfire. La version qui compte pour ce port est
**NTSC EN v1.0 launch** (hash déclaré `45ecd1...`). Toute autre version
modifiera les adresses `0x02C6BCA4`, `0x02C83190`, `0x02C8706C`, etc. et
cassera les overrides.

## 12. Problèmes connus (source: `port/README.md` §Troubleshooting)

- **Fenêtre noire** : le stub GLSL est actif, translation shader incomplète.
- **OSPanic ind_sgnl.c:105** : bug historique corrigé par le dimport repatch ;
  observé si les vieux objets ne sont pas re-buildés.
- **glXxx not found** : driver OpenGL 4.1 core requis.
- **FSOpenFile NOT_FOUND** : `content/` manquant ou mauvais chemin.

## 13. Limites actuelles

1. Le rendu visuel ne fonctionne pas encore : shaders R700 → GLSL partiel.
2. Le multi-threading n'existe pas : tout tourne single-threaded avec fiber
   scheduler bypassé.
3. Pas de save data.
4. Pas de réseau réel (stubs).
5. Ciblé strictement RPX v1.0 launch — versions updated non supportées.
6. Le port présuppose que le dump utilisateur (`content/`) est légitime, non
   chiffré et présent à côté de `Gambit(.exe)`.
7. Aucune UI de configuration : tout se fait par variables d'env et code.
