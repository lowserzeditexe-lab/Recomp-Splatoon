# ARCHITECTURE — Recomp Splatoon

Ce document décrit l'architecture **réellement présente** dans le dépôt RebrewU,
pas une architecture souhaitée. Toute divergence entre les deux est notée dans
`MISSING_FEATURES.md`.

---

## 1. Pipeline global

```
User-owned Splatoon RPX (v1.0 launch, SHA-256 45ecd1...)
                       │
                       ▼
           ┌──────────────────────┐
           │   RebrewU CLI        │  src/cli/main.cpp
           │   rebrewu recompile  │  bin/rebrewu
           └──────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   RPX Loader      RPL Loader     ELF Reader        src/core/{rpx,rpl,elf}
        │              │              │
        └──────────────┴──────────────┘
                       ▼
           Relocation Processor                     src/core/relocation
                       ▼
           Linker + Module Graph                    src/core/linker
                       ▼
           PPC Decoder + Semantics                  src/ppc/{decoder,semantics}
                       ▼
           IR Builder                               src/ir
                       ▼
   ┌─────────────┼─────────────┐
   ▼             ▼             ▼
  CFG    Function Discovery  Jump Tables            src/analysis
   └─────────────┴─────────────┘
                       ▼
           C++ Emitter                              src/codegen
                       ▼
       Gambit/  (Gambit_part*.cpp
                Gambit_data.cpp,
                Gambit_register.cpp,
                Gambit.h)
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
  MSVC / GCC / Clang           port/main.cpp + port/os/*
        │                             │
        └──────────────┬──────────────┘
                       ▼
                RecompSplatoon
                (binaire natif :
                 Linux ELF / Windows PE / macOS Mach-O)
```

## 2. Runtime PC (port/)

```
main()                                    port/main.cpp
  │
  ├─ alloc_arena(WIIU_MEM_SIZE)           mmap / VirtualAlloc (768 MB)
  ├─ calloc(dispatch_table, 0x0D000000>>2)  entrées 4-byte
  ├─ CPUState { mem, dispatch_table, r[32], f[32], cr, lr, ctr, xer, ... }
  │
  ├─ gambit_plt_auto_register(cpu)        pre-registre 610 stubs
  ├─ coreinit_memory_init(arena)          ajuste l'arène
  ├─ coreinit_*_register(cpu)             fs, threads, sync, misc
  ├─ gx2_*_register(cpu)                  context, draw
  ├─ snd_core_register(cpu)               audio
  ├─ vpad_register(cpu)                   GamePad
  ├─ padscore_register(cpu)               Pro Controller
  ├─ stubs_register(cpu)                  fallback
  ├─ nsysnet_register(cpu)                sockets
  ├─ Gambit_game_register(cpu)            toutes les fns recompilées
  │
  ├─ rbrew_register_func(0x02817C50, no-op)    ─┐
  ├─ rbrew_register_func(0x02818D40, no-op)     │  fiber scheduler
  ├─ rbrew_register_func(0x02818D44, no-op)     │  bypass
  ├─ rbrew_register_func(0x02C8706C, render+swap)─┘
  │
  ├─ Gambit_data_init(arena)              copie .data/.rodata
  ├─ coreinit_dimport_repatch(cpu)        re-écrit fn pointers
  ├─ heap pre-seed @ 0x101D2554           127 MB free list
  │
  ├─ Setup CPUState { r1=stack, r2=SDA2, r13=SDA }
  ├─ Run ctors table @ 0x101BFA54 via rbrew_dispatch
  ├─ Clear 0x101C98F0 (TLS allocator handle)
  ├─ rbrew_dispatch(cpu, 0x02000020)      GHS _start
  ├─ rbrew_dispatch(cpu, 0x02C6BCA4)      Gambit__start (renderer init)
  ├─ rbrew_dispatch(cpu, 0x02D05B78)      GX2Init (idempotent)
  └─ rbrew_dispatch(cpu, 0x02C83190)      Main game loop
```

## 3. Modèle mémoire

- Une seule arène linéaire allouée à la première adresse virtuelle libre
  (`mmap MAP_ANONYMOUS` POSIX / `VirtualAlloc` Windows).
- Adresses guest = offsets dans l'arène, gamme complète Wii U (`0x00000000` –
  `0x2FFFFFFF` etc.). L'arène est indexée directement par l'adresse guest.
- Accès mémoire via helpers `rbrew_read32 / rbrew_write32 / read16 / write16 /
  read8 / write8` (byte-swap big-endian → host little-endian intégré).
- Stack guest : `0x1FBFFFFF` → `0x1FC00000` (1 MB, `r1 = 0x1FC00000 - 8`).
- SDA anchor (`r13`) : `0x101C0BC0` ; SDA2 (`r2`) : `0x10000000`.
- Heap OS custom seedé @ `0x101D2554` avec free list @ `0x20000000..0x27FFF008`.

## 4. Dispatch table

- Tableau `HostFunc dispatch_table[0x0D000000 >> 2]` (13 M entrées, 104 MB
  virtual sur x64).
- `rbrew_dispatch(cpu, addr)` = `dispatch_table[addr >> 2](cpu)`.
- Chaque fonction PPC traduite est enregistrée par `Gambit_register.cpp`.
- Chaque import Wii U est enregistré par les shims OS (`coreinit_*`, `gx2_*`,
  `vpad`, …) ou reste STUB via `gambit_plt_auto_register`.

## 5. Graphics stack

```
Game GX2 calls (recompiled)
        │
        ▼
port/os/gx2/gx2_context.cpp   (SDL2 window, GL context)
port/os/gx2/gx2_draw.cpp      (VBO/VAO, fetch shader, byte-swap)
port/os/gx2/gx2_render.cpp    (FBO, textures, raster state, swap)
port/os/gx2/r700_to_glsl.cpp  (AMD R700 → GLSL translator — WIP)
        │
        ▼
OpenGL 4.1 core profile
        │
        ▼
Host GPU (via Mesa/NVIDIA/AMD/Intel driver)
```

## 6. Audio stack

```
snd_core AX calls (recompiled) → port/os/snd_core/snd_core.cpp
                                   │
                                   ▼
              miniaudio (single-header, si HAVE_MINIAUDIO)
                                   │
                                   ▼
       WASAPI (Windows) / ALSA (Linux) / CoreAudio (macOS)
```

## 7. Input stack

- `port/os/vpad/vpad.cpp` : GamePad Wii U (stick gauche = SDL2 gamepad stick
  gauche ; touchpad = clic souris en Gamepad View ; Tab = toggle vue).
- `port/os/padscore/padscore.cpp` : Wii Remote / Pro Controller.
- Contrôles actuels (README) :
  - Move : Left stick
  - Camera : Mouse (TV) / right stick
  - Jump : A
  - Special/shoot : RT
  - Switch view : Tab
  - Touch : mouse click en Gamepad View

## 8. Filesystem mapping

```
Guest path                   Host path
--------------------------   -------------------------------
/vol/content/*               ./content/*        (à côté de Gambit)
/vol/meta/*                  ./meta/*
```

Logs contrôlés par `RBREW_FS_VERBOSE=1`.

## 9. Threading & fibers

**État actuel** : single-thread. Le scheduler fiber GHS de Splatoon est
court-circuité par 4 overrides (voir AUDIT §6). Il n'existe pas encore de
mapping `OSThread → std::thread`.

## 10. Version identity de l'environnement

```
RecompSplatoon (workspace)  : forked from RebrewU @ 0b40c4f
RebrewU version.hpp         : 0.1.0
Splatoon target             : NTSC EN v1.0 launch (SHA-256 45ecd1...)
Runtime interface           : rebrewu_runtime.h (140 l.)
```
