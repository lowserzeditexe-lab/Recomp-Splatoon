# Dump verification report — user-provided legal Splatoon dump

**Date:** 2026-01
**Source:** user's Google Drive (private, not committed, not redistributed)
**Local working dir:** `/app/build/dump/extracted/Games/Splatoon/` (Games/ only)
**Updates/**, **Saves/** — extracted alongside but **not touched** for M5.

---

## Verification result

```
Game dump:
✓  present, structure {code, content, meta} intact

Version:
title_version = 16 (0x10) = v1.0 launch
sdk_version   = 21212
os_version    = 000500101000400A

Region:
PAL / EUR (region mask 0x00000004)
Locales in content/Message: EUde, EUen, EUes, EUfr, EUit
Font: BmpFont_EU.szs
Product code: WUP-P-AGMP        (internal / master code)
Title ID    : 0005000010176A00  (Splatoon PAL)

RPX:
Games/Splatoon/code/Gambit.rpx (8,847,168 bytes)
ELF32 big-endian, Cafe OS ABI 0xCA
Magic: 7F 45 4C 46 01 02 01 CA

SHA-256:
45ecd1ed81a97f46b1c8ae24820cd47fbc55399b50af09bf1f9050fe803308e5

Matches current RebrewU target:
YES — hash STRICTLY IDENTICAL to the target documented in port/README.md
      (RebrewU README lists WUP-AAZP/AAZE as retail SKUs; product_code WUP-P-AGMP
      is the internal master code, but the bytecode is identical → all hardcoded
      addresses in port/main.cpp remain valid: 0x02C6BCA4, 0x02C83190, 0x02C8706C,
      0x02817C50, 0x02818D40/44, 0x101C98A8, 0x101D2554, 0x101BFA54, 0x101DC020.)
```

## Files (all present, none committed)

```
/app/build/dump/dump.bin                                 (2.1 GB zip, source)
/app/build/dump/extracted/Games/Splatoon/code/Gambit.rpx (8.8 MB, verified)
/app/build/dump/extracted/Games/Splatoon/code/app.xml
/app/build/dump/extracted/Games/Splatoon/code/cos.xml
/app/build/dump/extracted/Games/Splatoon/code/title.fst
/app/build/dump/extracted/Games/Splatoon/code/title.tmd
/app/build/dump/extracted/Games/Splatoon/content/      (629 entries)
/app/build/dump/extracted/Games/Splatoon/meta/
```

`Updates/` and `Saves/` remained **isolated** (not symlinked, not merged).

## Boot test with dump — findings

```
Environment      : Debian 12 aarch64 (headless container, NO real GPU)
Video backend    : SDL_VIDEODRIVER=dummy  AND  LIBGL_ALWAYS_SOFTWARE=1 (llvmpipe)
                   → both produce the SAME behavior
Symlinks placed  : build_port/content -> extracted/Games/Splatoon/content
                   build_port/meta    -> extracted/Games/Splatoon/meta
Env vars         : RECOMP_SHADER_DUMP=/app/build/shader_dump_run1
                   RECOMP_SHADER_NO_STUB=1

Boot progression measured:
[gambit] Guest arena: … 768 MB
[gambit] OS modules registered
[gambit] Data sections loaded
[gambit] Dimport function pointers re-patched
[gambit] Heap pre-seeded: free=[0x20000008,0x27FFF008) 127 MB
[gambit] Ran 1111 static constructors           ← NEW vs. no-dump run
[gambit] GHS TLS allocator handle cleared
[gambit] Entering game entry point 0x02000020
[gambit] GHS context created: 0x28000000        ← NEW vs. no-dump run
                                                  (fn_02000020 GHS _start returned r3=0x28000000)

Then blocked inside Gambit__start (dispatch to 0x02C6BCA4):
  – Infinite loop of "unhandled dispatch to 0x00000000"
  – ctr = 0x020062B8 (a real text address)
  – lr  = 0x101FE310 (a real code location inside Gambit__start's chain)
  – r3/r12 cycle over 0x101C0BC8 .. 0x101C0C04 in 12-byte strides
    (walking a small table of ~5 entries, then wrapping)

Log messages NOT reached:
  – [gambit] Gambit__start done; render_ctx=…
  – [gambit] GX2 init confirmed
  – [gambit] ctx=… entering game main loop
  – Any [gx2_render]  or  [gx2_context]  message

Shader dumps produced: 0
Translator was NEVER invoked in this environment.
```

## Interpretation

- With **1111 ctors** actually running (up from 0 in the empty-content run),
  the dump is being read: the ctor table at `0x101BFA54` is now populated
  with valid function pointers (the guest `.rodata` came from `Gambit_data.cpp`
  + it now dispatches into recompiled code). The dispatch chain is real.
- `Gambit__start` starts calling into the render/GHS init chain. That chain
  eventually calls into a function table that contains **null entries** —
  those entries would normally be filled by GX2Init opening an OpenGL 4.1
  core context (`fn_02818190` writes the render context pointer to
  `0x101C98A8`). In this container GL is not available (dummy) or is a
  software rasterizer without a real window (llvmpipe), so the SDL/GL init
  either fails silently or produces null resource pointers that propagate.
- **Conclusion: the shader translation phase is unreachable in this
  container**, regardless of the dump correctness. The RPX is exactly the
  right one; the environment does not have the GPU stack required by the
  port to reach `resolve_active_program`.

## Consequences for M5

- M5 shader capture must be executed on a **real GPU host** (Windows x64
  with a recent driver, or Linux x86-64 with Mesa 22+ / NVIDIA / AMD, or
  Apple Silicon with MoltenVK/ANGLE bridge).
- All pipeline pieces are ready and persistent under `/app`:
  - `tools/shader_opcode_stats.py`
  - `tools/shader_dump_diff.py`
  - `tools/run_shader_tests.sh`
  - `tests/test_r700_to_glsl.cpp` (+ fixtures runner)
  - Translator instrumentation (`RECOMP_SHADER_DUMP`, `RECOMP_SHADER_NO_STUB`)
- Recipe to reproduce, once on a GPU host with **this exact dump**:

  ```bash
  cd /app/vendor/rebrewu/build_port
  ln -sfn /app/build/dump/extracted/Games/Splatoon/content ./content
  ln -sfn /app/build/dump/extracted/Games/Splatoon/meta    ./meta
  mkdir -p /app/build/shader_dump_run1
  RECOMP_SHADER_DUMP=/app/build/shader_dump_run1 \
    RECOMP_SHADER_NO_STUB=1 ./Gambit
  python3 /app/tools/shader_opcode_stats.py \
    /app/build/shader_dump_run1 \
    --out /app/docs/generated/R700_SPLATOON_OPCODE_STATS.md \
    --json /app/build/shader_dump_run1/stats.json
  ```

## What is NOT started (per user instructions)

- **Save Transfer** from `Saves/` — untouched, no code path added.
- **Updates/** — untouched, not merged with base game. If ever merged
  later, the merged RPX SHA-256 must be re-verified (updates change
  addresses and would break every hardcoded fibers override).

## Legal reminders

- **This dump is NEVER committed.** `/app/build/dump/` is not tracked and
  contains only user-provided data.
- No file from `content/`, `meta/`, `code/`, or the zip archive is copied
  into the RebrewU tree or into `/app/tests/shaders/fixtures/`.
- Only the SHA-256 hash and the structural facts above are recorded in
  documentation. No Nintendo asset content is quoted or reproduced.
