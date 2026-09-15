# Recomp Splatoon — Audit & Design Workspace

Ce dépôt Emergent contient l'**audit** et le **design technique** du
projet **Recomp Splatoon** — une recompilation statique native de
Splatoon Wii U vers un exécutable PC, basée sur
[RebrewU](https://github.com/ApfelTeeSaft/RebrewU).

## Nature du workspace

Cet environnement est un **conteneur Linux aarch64** utilisé pour :

- Cloner et **auditer** RebrewU + son port Splatoon existant (read-only).
- **Compiler** les composants portables du dépôt (validé Linux aarch64).
- Produire des **documents techniques** (audit, architecture,
  compatibilité, design des sous-systèmes).

Il ne produit **pas** de binaire Windows x64 : cette phase se fait sur
une machine Windows avec MSVC (voir `docs/WINDOWS_BUILD.md`).

## Ce qui a été vérifié dans cet audit

- `RebrewU @ 0b40c4f` : builde en Linux aarch64, CLI `rebrewu` fonctionne.
- Port Splatoon (`Gambit`) : **237/237 unités de traduction** compilent
  sans erreur ; binaire produit ; **le boot passe** (arène 768 MB, OS
  registered, data loaded, dimport re-patched, heap seedé 127 MB, ctors
  exécutés) jusqu'aux dispatch attendus à 0 (absence de dump utilisateur).
- L'existant est **beaucoup plus mûr** que ce que le README pouvait
  laisser croire : `Gambit_part*.cpp` (214 fichiers) est déjà recompilé
  et présent dans le dépôt, tous les shims OS de base sont écrits.

## Ce qui reste à faire

Voir `docs/MISSING_FEATURES.md` et `docs/PROGRESS.md`. En très bref :

- **P0** : compléter `port/os/gx2/r700_to_glsl.cpp` (shader translator R700
  → GLSL) pour obtenir le premier frame visible.
- **P1** : multi-thread réel, audio complet, save data.
- **P2** : renderer alternatifs, UI launcher, gyro, sensibilités configurables.
- **P3** : Pretendo (recherche protocole d'abord), save transfer Wii U↔PC,
  modding officiel, séparation stricte des environnements.

## Documents

Tous les fichiers sont dans `docs/` :

| Fichier                 | Contenu                                                       |
| ----------------------- | ------------------------------------------------------------- |
| `AUDIT.md`              | Audit détaillé du dépôt réel (build vérifiés, inventaire)     |
| `ARCHITECTURE.md`       | Architecture **réellement implémentée aujourd'hui**           |
| `TARGET_ARCHITECTURE.md`| Architecture **cible finale** (contrat, pas implémentation)   |
| `COMPATIBILITY.md`      | Versions du jeu et plateformes hôtes                          |
| `WINDOWS_BUILD.md`      | Instructions build Windows (non exécutées ici)                |
| `MISSING_FEATURES.md`   | Éléments absents ou incomplets, priorisés P0..P3              |
| `PROGRESS.md`           | Tracker milestones M0..M11 et checklist                       |
| `PRETENDO_DESIGN.md`    | Design de la couche compte/réseau (PNID, NEX, PRUDP)          |
| `SAVE_TRANSFER.md`      | Design du transfert de sauvegardes Wii U ↔ PC                 |
| `MODDING_DESIGN.md`     | Design du système de mods (VFS, hooks, memory patches)        |
| `ENVIRONMENTS.md`       | Politique Vanilla Online / Private Modded / Offline Dev       |

## Rappel légal

Le projet ne redistribue **jamais** :

- Le RPX ou tout fichier propriétaire de Nintendo.
- Les assets extraits d'un dump.
- Des clés ou tickets.
- Des liens vers des copies pirates.

L'utilisateur doit fournir lui-même une copie légalement acquise du jeu.

## Prochaine action concrète

Compléter le translator `r700_to_glsl.cpp` sur une machine Windows/Linux
avec GPU réel, puis vérifier l'apparition du premier frame contre un
dump utilisateur légitime. Voir `PROGRESS.md § "Prochaine action concrète"`.
