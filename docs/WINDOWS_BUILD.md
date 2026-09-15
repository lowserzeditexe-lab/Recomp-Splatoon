# WINDOWS_BUILD — Recomp Splatoon

Cet environnement de développement est **Linux aarch64**. Ce document
consigne les instructions Windows validées par la documentation et le CMake
du dépôt, mais **non exécutées ici**. Toute vérification "run on Windows"
est marquée `NOT TESTED — WINDOWS REQUIRED`.

## Prérequis Windows

- Windows 10 21H2 ou Windows 11
- Visual Studio 2022 (workload "Desktop development with C++")
- CMake 3.20+ (celui livré avec VS2022 suffit)
- Git for Windows
- vcpkg (recommandé pour les dépendances)
- GPU + driver OpenGL 4.1 core

## 1. Cloner et préparer

```powershell
git clone https://github.com/ApfelTeeSaft/RebrewU.git
cd RebrewU
# Optionnel : audio backend
Invoke-WebRequest `
  -Uri https://raw.githubusercontent.com/mackron/miniaudio/master/miniaudio.h `
  -OutFile third_party\miniaudio.h
```

## 2. Installer les dépendances via vcpkg

```powershell
git clone https://github.com/microsoft/vcpkg.git C:\vcpkg
C:\vcpkg\bootstrap-vcpkg.bat
C:\vcpkg\vcpkg install `
    sdl2:x64-windows `
    curl:x64-windows `
    zlib:x64-windows `
    opengl:x64-windows
```

## 3. Build du recompiler RebrewU (racine)

```powershell
cmake -B build -G "Visual Studio 17 2022" -A x64 `
      -DREBREWU_BUILD_TESTS=ON
cmake --build build --config Release
```

Sortie attendue : `build\bin\Release\rebrewu.exe` (CLI).
`NOT TESTED — WINDOWS REQUIRED`

## 4. Vérifier son dump

```powershell
Get-FileHash .\Gambit.rpx -Algorithm SHA256
# Doit commencer par : 45ecd1ed81a97f46b1c8ae24820cd47fbc55399b50af09bf1f9050fe803308e5
```

## 5. Re-générer le C++ (optionnel — pré-générés déjà présents dans `Gambit/`)

```powershell
.\build\bin\Release\rebrewu.exe recompile `
    --rpx .\Gambit.rpx `
    --output .\Gambit
```

## 6. Build du port Splatoon (Gambit.exe)

```powershell
cmake -S port -B build_port `
      -DCMAKE_BUILD_TYPE=Release `
      -DCMAKE_TOOLCHAIN_FILE=C:\vcpkg\scripts\buildsystems\vcpkg.cmake `
      -DVCPKG_TARGET_TRIPLET=x64-windows
cmake --build build_port --config Release
```

Sortie attendue : `build_port\Release\Gambit.exe` (~150–200 MB debug info,
plus petit en Release strip).
`NOT TESTED — WINDOWS REQUIRED`

## 7. Runtime

```
Répertoire d'exécution/
├── Gambit.exe
├── SDL2.dll           (copier depuis vcpkg installed\x64-windows\bin)
├── libcurl.dll        (idem)
├── content\           (dump utilisateur, /vol/content)
│   ├── *.pack
│   ├── *.bfres
│   └── sound\
└── meta\              (optionnel)
    ├── meta.xml
    └── iconTex.tga
```

## 8. Variables d'environnement utiles

| Variable            | Effet                                             |
| ------------------- | ------------------------------------------------- |
| `RBREW_FS_VERBOSE=1`| Log chaque open/read/close FS                     |
| `SDL_VIDEODRIVER`   | `dummy` pour boot headless (dev only)             |

## 9. Éléments qui n'existeront QUE sous Windows/Mac/Linux réel

Éléments physiques ou d'API qui ne peuvent pas être validés dans un
conteneur headless :

- OpenGL 4.1 core context (GLX/EGL/WGL/CGL réel avec compositor)
- Vsync et frame pacing réels
- Input via SDL2 (clavier physique, souris raw input, gamepads USB)
- Audio réel (WASAPI / ALSA / CoreAudio)
- Gyro via DualSense/DualShock/Switch Pro (HID)
- Rendu visible du menu Splatoon
- Session multi-heure de gameplay
- Bench 60/120/144 FPS

Ces étapes doivent être bloquées comme `REQUIRES WINDOWS/GPU VALIDATION`
dans `PROGRESS.md`.
