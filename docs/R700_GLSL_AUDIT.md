# R700_GLSL_AUDIT — Audit du translator AMD R700 / Latte → GLSL 410 core

> **M5 blocker.** Ce document liste ce que `port/os/gx2/r700_to_glsl.cpp`
> (405 l., commit `0b40c4f`) supporte réellement, ce qui est partiel, ce
> qui manque, et ce qui est UNKNOWN — sans aucune supposition. Toute
> classification est justifiée par le code source ou son commentaire.

## 1. Résumé

- Un seul fichier : `port/os/gx2/r700_to_glsl.cpp` + `.h`.
- Approche : parse CF (Control Flow) puis émet GLSL 410 core en deux passes.
- Cible : shaders R700/Latte réellement utilisés par **Splatoon v1.0 launch**.
- Sortie : `#version 410 core` avec UBO 256×vec4, samplers 2D, `vs_out[8]`.
- Compilation host : `gx2_render.cpp::compile_translated_program` (glCreateShader + glShaderSource + glCompileShader + glLinkProgram).
- Fallback : shader stub magenta (`STUB_FRAG_SRC` — `color = vec4(1,0,1,1)`)
  si la traduction ou le lien échoue. **Ce fallback masque les erreurs**
  et devra être conditionné en mode debug (voir §7).

## 2. Ce qui EST supporté (dans le code)

### CF instructions (7 opcodes vus)
| Opcode  | Nom              | Statut  | Ligne        |
| ------- | ---------------- | :-----: | ------------ |
| 0x00    | CF_NOP           | ✅      | 69, 332      |
| 0x01    | CF_TEX           | ✅      | 70, 311      |
| 0x08-0x0B, 0x48-0x4B | CF_ALU (toutes variantes) | ✅ | 74-76, 296 |
| 0x27    | CF_EXPORT        | ✅      | 71, 324      |
| 0x28    | CF_EXPORT_DONE   | ✅      | 72, 324      |

### ALU OP2 (25 opcodes)
| Opcode | Nom            | GLSL émis                          |
| ------ | -------------- | ---------------------------------- |
| 0x00   | ADD            | `(A)+(B)`                          |
| 0x01/0x02 | MUL / MUL_IEEE | `(A)*(B)`                       |
| 0x03   | MAX            | `max(A,B)`                         |
| 0x04   | MIN            | `min(A,B)`                         |
| 0x08/0x10 | FRACT       | `fract(A)`                         |
| 0x09/0x11 | TRUNC       | `trunc(A)`                         |
| 0x0A/0x12 | CEIL        | `ceil(A)`                          |
| 0x0C/0x14 | FLOOR       | `floor(A)`                         |
| 0x19   | MOV            | `A`                                |
| 0x1B   | SETNE         | `((A)!=(B)?1.0:0.0)`               |
| 0x1C   | SETE          | `((A)==(B)?1.0:0.0)`               |
| 0x20   | PRED_SETGT     | `((A)>(B)?1.0:0.0)`                |
| 0x21   | PRED_SETGE     | `((A)>=(B)?1.0:0.0)`               |
| 0x50/0x51 | DOT4 (partiel — cf. §3) | `(A)*(B)` par composante |
| 0x61   | EXP_IEEE       | `exp2(A)`                          |
| 0x62/0x63 | LOG_CLAMPED/IEEE | `log2(max(abs(A),1e-30))`      |
| 0x66   | RECIP_IEEE     | `1.0/max(abs(A),1e-30)*sign(A+1e-30)` |
| 0x69   | RSQRT_IEEE     | `inversesqrt(max(abs(A),1e-30))`   |
| 0x6A   | SQRT_IEEE      | `sqrt(max(A,0.0))`                 |
| 0x6E   | SIN            | `sin(A*π)` — l'unité R700 divise le radian ; ici multiplié par π (voir §3) |
| 0x6F   | COS            | `cos(A*π)` — idem                  |

### ALU OP3 (4 opcodes)
| Opcode | Nom     | GLSL émis                    |
| ------ | ------- | ---------------------------- |
| 0x10/0x14 | MULADD | `(A)*(B)+(C)`             |
| 0x18   | CNDE    | `((A)==0.0?B:C)`             |
| 0x19   | CNDGT   | `((A)>0.0?B:C)`              |
| 0x1A   | CNDGE   | `((A)>=0.0?B:C)`             |

### Sources
| Range      | Signification                          | GLSL          |
| ---------- | -------------------------------------- | ------------- |
| 0-127      | GPR                                    | `r[N].chan`   |
| 128-159    | KCACHE0 (base = WORD0[31:24] × 16)     | `vc[kc0+(sel-128)].chan` |
| 160-191    | KCACHE1 (base = WORD1[9:2] × 16)       | `vc[kc1+(sel-160)].chan` |
| 248        | Const 0.0                              | `0.0`         |
| 249        | Const 1.0                              | `1.0`         |
| 253        | PV (previous vector)                   | `pv.chan`     |

### Fetch (TEX)
| Instruction | Statut       | Notes                                          |
| ----------- | :----------: | ---------------------------------------------- |
| SAMPLE 2D   | ✅ (basique) | `texture(texN, r[src].xy)`, `.xy` seulement    |

### Exports
| Type          | Cible GLSL      | Notes                              |
| ------------- | --------------- | ---------------------------------- |
| 0 = PIXEL     | `frag_color`    | uniquement en shader pixel         |
| 1 = POSITION  | `gl_Position`   | uniquement en shader vertex        |
| 2 = PARAMETER | `vs_out[base]`  | base ∈ 0..7 uniquement (varying array) |

## 3. Ce qui est PARTIEL

| Item                          | Détail                                                                                                    |
| ----------------------------- | --------------------------------------------------------------------------------------------------------- |
| DOT4 (0x50/0x51)              | Émis comme MUL par composante — le regroupement en `dot(vec4,vec4)` n'est **pas** fait. Résultat correct par slot mais suboptimal et potentiellement faux si le CF combine 4 slots comme un vrai DOT4. `NEEDS RESEARCH`. |
| SIN/COS (0x6E/0x6F)           | Multiplication par π appliquée en supposant que R700 utilise le "revolution" (0..1 = 0..2π/2). Le code multiplie par π (pas 2π) — à valider contre du shader concret. `NEEDS VALIDATION`. |
| RECIP (0x66)                  | Correction `sign(A+1e-30)` — hack pour éviter division par zéro ; pas identique à l'IEEE R700. |
| Source modifiers              | Seul le flag `neg` (bit 12/25 de WORD0) est appliqué. **`abs` et `rel` non gérés.** |
| Write masks / dst.chan        | Un seul `dst_ch` par instruction (WORD1[29:30]) ; multi-channel writes non testés. |
| KCACHE `kmode`                | Ignorés — on suppose toujours `LOCK_LOOP_INDEX` implicite en unités de vec4. |
| OP3 src2_neg                  | Ligne 195 : `s2_neg = false; // OP3 negation less common; skip for now`. |
| GPR array indexing            | GLSL 4.10 supporte l'accès dynamique aux tableaux **uniforme constant only** ; ici `r[]` local, borné 4..128 (l. 366-368). Aucun problème connu, mais non testé au-delà de 32 GPR. |
| Emission ordre EXPORT         | 1er EXPORT PIXEL → `frag_color` ; les suivants sont **silencieusement écrasés**. Splatoon peut faire du MRT. `NEEDS RESEARCH`. |
| CF fetch clause size          | Codé en dur 16 octets/slot (l. 242) — corrigé pour SAMPLE ; les autres formats (VTX, MEM_STREAM) ne sont pas traités. |

## 4. Ce qui MANQUE (visible dans le code)

### CF opcodes
- `CF_LOOP_START` / `CF_LOOP_END` / `CF_LOOP_CONTINUE` / `CF_LOOP_BREAK`
- `CF_JUMP` / `CF_ELSE` / `CF_POP` (structured control flow non-trivial)
- `CF_CALL_FS` (fetch shader) — géré ailleurs dans `gx2_draw.cpp` pour la partie fetch shader du vertex pipeline, pas ici.
- `CF_KCACHE_LOCK` / `CF_KCACHE_UNLOCK`
- `CF_ALU_PUSH_BEFORE` / `CF_ALU_POP_AFTER` / `CF_ALU_ELSE_AFTER`
- `CF_MEM_STREAM*` (transform feedback)

### ALU opcodes non implémentés (default = `0.0/*op2=0xXX*/`)
Tout ce qui n'est pas dans la liste §2 tombe dans `default`. Cela inclut
au moins (opcodes R700 documentés publiquement mais **non vus dans le
switch actuel**) :
- 0x05..0x07 : SETE/SETGT/SETGE (int)
- 0x0D..0x0F : ASHR / LSHR / LSHL
- 0x15..0x18 : MULHI, MULLO int
- 0x1A       : NOP
- 0x1D..0x1F : SETNE_INT / etc.
- 0x22..0x26 : PRED_SETNE/SETE/SETE_PUSH/SET_INV/SET_CLR
- 0x30..0x4F : conversion FLT_TO_INT, INT_TO_FLT, MOVA, etc.
- 0x52..0x60 : CUBE, MAX4, DOT4_IEEE variant, GROUP_BARRIER, GROUP_SEQ_BEGIN/END
- 0x64/0x65  : LOG_IEEE clamped/unclamped variants
- 0x67/0x68  : RECIP_UINT, RECIPSQRT_CLAMPED, RECIPSQRT_FF
- 0x6B..0x6D : SIN_D2, COS_D2 (autres normalisations)
- 0x70..0xFF : diverses instructions int/uint/spécialisées
- 0x100+     : OP3-only range

### OP3 opcodes non implémentés
Le code n'inclut que `0x10, 0x14, 0x18, 0x19, 0x1A`. Manquent :
- 0x11..0x13 : MULADD_M2/M4/D2 (scaling variants)
- 0x15..0x17 : MULADD_IEEE variants
- 0x1B..0x1D : CNDE_INT / CNDGT_INT / CNDGE_INT
- 0x50..0x7F : BFE, BFI, BFM, LDS_IDX_OP, etc.

### TEX opcodes non implémentés
Seul `SAMPLE 2D` avec `.xy` UV. Manquent :
- `SAMPLE_L` (mip level explicit)
- `SAMPLE_LB` (LOD bias)
- `SAMPLE_G` (gradient) — ombres, mip control
- `SAMPLE_C` (compare, PCF)
- `LD` (load, non-filtered)
- `GATHER4`
- `SET_TEXTURE_OFFSETS`
- 1D, 3D, CUBE, 2D_ARRAY, CUBE_ARRAY — actuellement forcé `sampler2D` uniquement
- `MEGA_FETCH_COUNT` / `MEGA_FETCH_SEMANTIC_ID` (constant fetch → uniform)

### Source features non implémentés
- `abs()` modifier (bit dans WORD1)
- `rel` (relative addressing via ARL/MOVA)
- Literal constants (sel = 250-252 : LITERAL_X/Y/Z encodé après les slots)
- CFILE / CBUF (sel = 192..255 hors LITERAL)

### Output side
- Depth export (`CF_EXPORT` type 0 avec base=61) → `gl_FragDepth`
- Stencil / mask exports
- Multiple render targets (MRT) — un seul export PIXEL retenu (voir §3)
- Point size (`vs_out` slot spécial)

### Précision et flags
- `clamp` (bit 31 WORD1) implémenté ; mais **`omod` (output modifier ×2/×4/÷2)
  non géré** (bits WORD1[26:27]).
- `update_exec_mask`, `update_pred` : ignorés.

## 5. Ce qui reste UNKNOWN (à mesurer sur Splatoon réel)

- Fréquence réelle de chaque opcode dans les shaders Splatoon v1.0.
- Nombre total de paires (VS, PS) à traduire pour atteindre M5 (premier frame).
- Utilisation ou non d'instructions integer / bitwise.
- Utilisation de gs (geometry shader) — le pipeline actuel ne le prévoit pas.
- Utilisation de MRT en Splatoon.
- Types de samplers réellement utilisés (2D, cube, array).
- Format des fetch shaders (partiellement géré par `gx2_draw.cpp`, hors scope ici).

**Ces mesures nécessitent** :

1. Un dump utilisateur légal (`content/`).
2. L'exécution du port jusqu'à l'appel `resolve_active_program`.
3. Capture de chaque `(vs_bytecode, ps_bytecode)` avant `r700_to_glsl`.
4. Comptage des opcodes / instructions / types de texture rencontrés.

L'infrastructure de capture est ajoutée en §7.

## 6. Test / validation actuelle

- **Aucun test unitaire** ne cible `r700_to_glsl.cpp` (les 5 tests
  `tests/test_*.cpp` couvrent le recompiler, pas le translator).
- **Aucun harness GLSL** ne vérifie que la sortie compile réellement — la
  compilation se fait au premier draw call runtime (via SDL2+GL context).
- Fallback silencieux vers stub magenta si échec.

## 7. Instrumentation à ajouter (safe, non-intrusive)

Deux additions minimales, ne changeant **aucun comportement par défaut**,
activées uniquement par variables d'environnement :

### 7.1 Shader dump — `RECOMP_SHADER_DUMP=<dir>`

Quand cette variable est définie :

- Chaque bytecode R700 (VS et PS) est écrit en `<dir>/shader_NNNN_vs.r700`
  et `<dir>/shader_NNNN_ps.r700` (avec numérotation croissante par paire).
- La sortie GLSL est écrite en `<dir>/shader_NNNN_vs.glsl` et
  `<dir>/shader_NNNN_ps.glsl`.
- Le log de compilation GL est écrit en `<dir>/shader_NNNN.log`.

Cela permet de collecter, sur une machine avec dump + GPU, les shaders
réels de Splatoon pour :

- Mesurer la couverture d'opcodes.
- Rejouer hors ligne sur un translator amélioré.
- Comparer visuellement les logs de compilation.

### 7.2 Stub magenta désactivable — `RECOMP_SHADER_NO_STUB=1`

Quand cette variable est définie, un échec de traduction ou de lien ne
retombe **pas** sur le stub magenta : le program cache stocke `0` et le
draw call est skippé (avec un log). Utile pour identifier immédiatement
quel shader casse.

Ces deux additions n'introduisent **aucune API nouvelle** (variables d'env
uniquement) et n'ont **aucun effet** quand elles ne sont pas définies.

## 8. Test unitaire minimal ajouté

`tests/test_r700_to_glsl.cpp` (nouveau) — vérifie sans GPU :

1. `r700_to_glsl` renvoie un `char*` non nul pour un bytecode valide.
2. La sortie contient `#version 410 core`.
3. La sortie contient `layout(std140, binding=0)` en VS / `binding=1` en PS.
4. Un shader vide (0 CF utile → juste EXPORT_DONE) produit une main().
5. Un opcode non supporté produit un commentaire `/*op2=0xXX*/` sans crash.

**Ce test ne valide pas la compilation GLSL** — celle-ci exige un GPU
réel avec contexte OpenGL 4.1 core. Sur Windows / Linux + GPU :
`RECOMP_SHADER_DUMP` produit les fichiers et le harness peut être
étendu avec `glslangValidator` si présent.

## 9. Priorité d'implémentation pour M5

Chemin minimal pour "premier frame" :

1. **Confirmer** que le VS + PS du render context initial produisent bien
   des instructions couvertes par §2.
2. **Implémenter les manquants critiques** identifiés par la capture
   §7.1 (ordre exact = fréquence d'apparition).
3. **Corriger DOT4** si un vrai `DOT4` clause apparaît (regrouper 4
   slots en `dot(vec4,vec4)`).
4. **Gérer les samplers non-2D** si présents.
5. **Ne pas** implémenter les 200+ opcodes R700 documentés publiquement
   qui ne seront pas rencontrés — c'est du temps perdu tant que la
   couverture réelle n'est pas mesurée.

## 10. Statut par catégorie

| Catégorie       | Statut  | Preuve                           |
| --------------- | :-----: | -------------------------------- |
| CF core         | Partiel | 5/plusieurs dizaines documentées |
| ALU OP2         | Partiel | ~20 / ~150+                      |
| ALU OP3         | Partiel | 4 / ~30                          |
| TEX fetch       | Basique | 1 / ~10                          |
| KCACHE          | Basique | 2 banks, no relative/lock modes  |
| Constants       | Basique | 0.0, 1.0, PV ; pas de LITERAL    |
| Source modifiers| Basique | neg only                         |
| Write modifiers | Partiel | clamp only ; pas d'omod          |
| Exports         | Basique | POSITION, PIXEL, PARAMETER ; pas de depth/MRT |
| Control flow    | Absent  | pas de loop, if, else, break, continue |
| Integer ops     | Absent  | shifts / bitwise / int math      |
| GS pipeline     | Absent  | non prévu par r700_to_glsl.cpp   |
