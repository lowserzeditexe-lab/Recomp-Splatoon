# Recomp Splatoon — Kit de test (toolchain uniquement)

Ce kit contient **uniquement l'outillage** du projet : le recompiler
**RebrewU**, le **runtime/port** PC écrit à la main, le système de build,
les outils et la documentation.

> ⚠️ **Aucun contenu Nintendo n'est fourni.** Ce kit ne contient **pas** le
> jeu Splatoon : ni le RPX, ni les assets (`content/`), ni le code recompilé
> (`Gambit_part*.cpp`), ni le binaire compilé. Vous devez fournir **votre
> propre copie légalement dumpée** du jeu. La recompilation se fait **sur
> votre machine**, contre **votre** dump. Rien n'est jamais téléversé.
>
> C'est exactement le modèle des projets de recompilation statique publics
> (ex. *WiiCompiled* pour Mario Kart Wii) : *« Setup only ships the toolchain,
> the translation runs on your machine against your disc image. »*

---

## Ce que contient ce kit

| Dossier | Contenu |
|---|---|
| `vendor/rebrewu/src`, `include`, `cmake`, `tools`, `tests` | Le recompiler RebrewU (RPX → C++) |
| `vendor/rebrewu/third_party` | Dépendances open-source du recompiler |
| `vendor/rebrewu/port` | Runtime PC écrit à la main (shims Cafe OS, GX2→OpenGL, input, audio) |
| `tools/` | Outils Python d'analyse de shaders (R700) |
| `docs/` | Audit, architecture, compatibilité, build Windows, features manquantes |

## Ce qui a été RETIRÉ (à régénérer par le recompiler)

Ces fichiers sont **dérivés du binaire du jeu (RPX)** — ils sont générés
automatiquement par RebrewU et **ne doivent jamais être redistribués** :

- `vendor/rebrewu/Gambit/Gambit_part*.cpp`, `Gambit_data.cpp`, `Gambit.h`
- `vendor/rebrewu/port/loader/gambit_game_register.cpp`
- `vendor/rebrewu/port/os/gambit_plt_auto.cpp`
- `vendor/rebrewu/port/gambit_plt_stubs.cpp`

Vous les régénérez en lançant RebrewU sur **votre** RPX (étape 2 ci-dessous).

---

## Workflow de test (résumé)

```
[VOTRE dump légal] --(RebrewU)--> C++ recompilé --(CMake/compilateur)--> binaire natif
                                                     + VOTRE content/  --> test
```

### 1. Builder le recompiler RebrewU

```bash
cd vendor/rebrewu
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

Voir `vendor/rebrewu/README.md` pour les prérequis (CMake 3.22+, C++20, zlib)
et l'usage complet de la CLI.

### 2. Recompiler VOTRE RPX (fournissez votre propre dump)

Vérifiez d'abord le hash de votre RPX v1.0 (voir `port/README.md` §
« Verifying your RPX ») :

```bash
sha256sum Gambit.rpx
# doit commencer par 45ecd1ed81a97f46b1c8ae24820cd47fbc55399b50af09bf1f9050fe803308e5
```

Puis lancez la recompilation :

```bash
./vendor/rebrewu/build/rebrewu recompile --rpx /chemin/vers/VOTRE/Gambit.rpx --output vendor/rebrewu/Gambit
```

Ceci régénère `Gambit_part*.cpp` et les tables PLT/register retirées ci-dessus.

### 3. Builder le port PC

```bash
cmake -S vendor/rebrewu/port -B build_port -DCMAKE_BUILD_TYPE=Release
cmake --build build_port --parallel
```

Prérequis (SDL2, OpenGL, libcurl, zlib) et détails Windows (MSVC/vcpkg,
MinGW/MSYS2) / macOS : voir `vendor/rebrewu/port/README.md` § « Building ».

### 4. Fournir VOTRE contenu de jeu

Copiez le dossier `content/` de **votre** dump légal à côté du binaire produit :

```
build_port/Gambit          ← binaire compilé
build_port/content/        ← VOTRE /vol/content (assets du jeu, dumpés par vous)
```

Méthodes d'extraction légale (Dumpling, CDecrypt, disque…) : voir
`port/README.md` § « Extraction from a Wii U dump ».

### 5. Lancer le test

```bash
cd build_port && ./Gambit
```

Contrôles, variables d'environnement (`RBREW_FS_VERBOSE=1`) et dépannage :
`vendor/rebrewu/port/README.md`.

---

## État actuel (rappel)

Le premier frame **n'est pas encore visible** : le translator de shaders
AMD R700 → GLSL (`port/os/gx2/r700_to_glsl.cpp`) est en cours. Une fenêtre
noire au lancement est donc **le comportement attendu** à ce stade — le boot,
le FS et l'infra GX2 fonctionnent. Voir `docs/MISSING_FEATURES.md` et
`docs/PROGRESS.md`.

## Rappel légal

Le projet ne redistribue **jamais** de fichiers Nintendo (RPX, assets, code
recompilé, clés, tickets). Vous devez posséder et dumper vous-même une copie
légale du jeu. Ce kit ne fournit que l'outillage.
