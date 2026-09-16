# COMPATIBILITY — Recomp Splatoon

## Versions du jeu

| Region | Version         | Title ID       | RPX SHA-256          | Statut port         | Boot | Menu | Graphics | Audio | Input | Save | Gameplay | Network |
| ------ | --------------- | -------------- | -------------------- | ------------------- | :--: | :--: | :------: | :---: | :---: | :--: | :------: | :-----: |
| NTSC-U | v1.0 launch     | WUP-AAZE       | `45ecd1ed81a97f46b1c8ae24820cd47fbc55399b50af09bf1f9050fe803308e5` | **Primary target** — code addresses match | ✅ | ❓ | ⚠️ WIP shaders | ⚠️ WIP | ❓ | ❌ | ❓ | ❌ |
| PAL    | v1.0 launch     | WUP-AAZP       | UNKNOWN              | Non testé            | ❓ | ❓ | ❓ | ❓ | ❓ | ❌ | ❓ | ❌ |
| NTSC-J | v1.0 launch    | WUP-AAZJ       | UNKNOWN              | Non testé            | ❓ | ❓ | ❓ | ❓ | ❓ | ❌ | ❓ | ❌ |
| Any    | v1.x update     | ANY            | ≠ 45ecd1...          | **Non supporté** — addresses change | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Any    | Pre-launch / Testfire | ANY      | ≠ 45ecd1...          | Non testé — utile pour RE via Splatoon-Decomp | ❓ | ❓ | ❓ | ❓ | ❓ | ❌ | ❓ | ❌ |

Légende : ✅ fonctionne, ⚠️ partiel, ❌ non implémenté, ❓ non testé dans cet audit
(pas de dump utilisateur), UNKNOWN = donnée non trouvée dans le code.

## Plateformes hôtes

| Hôte                   | Recompiler `rebrewu` | Port `Gambit`             |
| ---------------------- | -------------------- | ------------------------- |
| Windows 10/11 x64      | ✅ (README RebrewU)  | ✅ (README port, vcpkg)   |
| Windows MinGW-w64      | ✅ (implicite C++20) | ✅ (README port)          |
| Linux x86-64           | ✅ (README RebrewU)  | ✅ (README port)          |
| Linux **aarch64**      | ✅ **vérifié**       | ✅ **vérifié dans cet audit** |
| macOS 11+ (Intel)      | ✅ (README RebrewU)  | ✅ (README port)          |
| macOS Apple Silicon    | ✅ (implicite)       | ⚠️ Rosetta 2 ou MoltenVK/ANGLE — Metal natif non implémenté |

## GPU requis

- OpenGL 4.1 core profile (2011+).
- Vulkan, D3D12, Metal : non implémentés, prévus futur.

## Backends prévus mais non implémentés

- Renderer Vulkan
- Renderer D3D12
- Renderer Metal
- Threading multi-cœur (`OSThread` → `std::thread`)
- Save data (nn_save)
- Networking Pretendo/NEX/PRUDP

## Notes

- Toute compatibilité au-delà de la ligne "primary target" nécessite au
  minimum la re-génération du fichier de config JSON (adresses différentes)
  et la ré-exécution du recompiler sur le nouveau RPX.
- Les overrides fibers de `port/main.cpp` (0x02817C50, 0x02818D40/44,
  0x02C8706C) sont **spécifiques à v1.0 launch**. Ils devront être re-mesurés
  pour toute autre version.
