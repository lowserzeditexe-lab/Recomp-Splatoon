# MODDING_DESIGN — Design du système de mods

**Statut : DESIGN ONLY — non implémenté.** L'architecture doit s'intégrer
au runtime existant (`port/`) et respecter la nature "static recompilation"
du binaire : les adresses Wii U ne correspondent PAS aux adresses x64 —
tout mod code-level doit passer par le pipeline RebrewU / symboles générés.

## 1. Principes

1. Le modding est une fonctionnalité de première classe, pas un hack.
2. Les fichiers originaux du jeu (fournis par l'utilisateur) ne sont
   **jamais** écrasés.
3. Un mod peut être activé/désactivé sans réinstallation.
4. Chaque mod déclare ses **capabilities** (cosmetic / gameplay / map /
   audio / graphics / memory / code / plugin / network / debug).
5. Séparation stricte entre environnements — voir `ENVIRONMENTS.md`.

## 2. Structure disque

```
mods/
├── enabled/
│   └── example.mod/
│       ├── mod.json
│       ├── assets/
│       ├── patches/
│       ├── shaders/
│       ├── plugins/
│       └── README.md
├── disabled/
├── profiles/
│   ├── vanilla.json
│   ├── graphics_enhanced.json
│   └── competitive.json
└── cache/
    ├── shaders/
    ├── textures/
    ├── generated/
    └── metadata/
```

## 3. Manifest (`mod.json`)

Version schema versionnée. Exemple minimal :

```json
{
  "schema": 1,
  "id": "author.mod-name",
  "name": "Mod Name",
  "version": "1.0.0",
  "author": "Author",
  "description": "…",
  "game_version": "splatoon-v1.0-launch",
  "recomp_version": ">=0.1.0",
  "mod_api": 1,
  "capabilities": ["cosmetic", "graphics"],
  "network_policy": "cosmetic_online_ok",
  "priority": 100,
  "dependencies": [],
  "conflicts": []
}
```

`network_policy` ∈ { `offline_only`, `private_ok`, `cosmetic_online_ok`,
`public_online_ok` }.

## 4. Architecture d'exécution

```
Game file access (via /vol/content, coreinit_fs)
        ↓
VirtualFileSystem (nouveau, intégré au runtime)
        ↓
  ┌─── Mod Override 1
  ├─── Mod Override 2 (priorité plus élevée)
  ├─── Patch layer
  └─── Original content (./content)
        ↓
Game recompiled code
```

**Point d'insertion réel** : `port/os/coreinit/coreinit_fs.cpp` doit
consulter le VFS avant de lire `./content/`. C'est le SEUL endroit à
modifier dans le runtime pour l'override d'assets.

## 5. Types de mods et points d'intégration

| Type          | Point d'intégration                                                | Complexité |
| ------------- | ------------------------------------------------------------------ | ---------- |
| Texture       | VFS override `/vol/content/**/*.bfres,*.gtx`                       | Facile     |
| Model         | idem, format `.bfres`                                              | Moyen      |
| Audio         | idem, formats `.bfstm / .bfwav / .bfsar`                           | Moyen      |
| UI            | idem `/vol/content/**/*.arc`                                       | Moyen      |
| Shader        | Hook dans `r700_to_glsl.cpp` (surcharge du GLSL généré)            | Difficile  |
| Custom Map    | VFS + éventuellement patch tables jeu                              | Très diff. |
| Memory patch  | Écriture dans l'arène guest à des adresses vérifiées               | Difficile  |
| Code hook     | Remplacement d'entrée dans `dispatch_table` via `rbrew_register_func` | Difficile  |
| Plugin natif  | DLL/SO chargée par le runtime, appel dans `main.cpp` boucle        | Très diff. |

## 6. Code hooks — mécanisme spécifique à la recompilation

Les mods ne doivent PAS supposer qu'ils peuvent patcher directement la
mémoire x64 du processus. Le "code" du jeu vit dans la
`dispatch_table[addr >> 2]` — une table de pointeurs de fonctions C++
générées par le codegen.

**Hook stable** : remplacer l'entrée `dispatch_table[func_addr >> 2]` par
un handler du mod qui peut appeler l'original via un pointeur sauvegardé.

```
before:  dispatch_table[X] = &Gambit_fn_X
after:   dispatch_table[X] = &mod_handler_X
         (mod_handler_X sauvegarde &Gambit_fn_X et peut le rappeler)
```

Ce mécanisme utilise l'API existante `rbrew_register_func` — aucune API
nouvelle n'est nécessaire côté runtime.

## 7. Memory patches — protection anti-mauvaise-version

Un memory patch doit fournir :

```json
{
  "target_address": "0xXXXXXXXX",
  "expected_bytes": "AA BB CC DD",
  "replacement_bytes": "EE FF 00 11",
  "game_version": "splatoon-v1.0-launch",
  "game_rpx_sha256": "45ecd1..."
}
```

Avant application : lire les bytes actuels, comparer à `expected_bytes`.
Refuser silencieusement si mismatch. Ne pas appliquer sur une autre
version que celle déclarée.

## 8. Symbol map généré par le recompiler

Pour rendre les hooks stables entre versions, prévoir la génération
(par RebrewU) de :

```
build/symbols/
├── functions.json    (fn_XXXXXXXX → adresse, taille, section)
├── memory_map.json   (segments, SDA, ctors, etc.)
└── symbols.json      (agrégat exportable pour les mods)
```

**Cette génération n'existe pas encore dans RebrewU** — c'est une
extension à discuter avec l'upstream. En attendant, les hooks travaillent
avec des adresses absolues + hash de version.

## 9. Load order et conflicts

- Chaque mod déclare une `priority` (int, plus grand = appliqué en dernier).
- Un conflit VFS (deux mods sur le même fichier) est **explicite** :
  affichage user, choix manuel. Pas de sélection silencieuse.
- Un conflit `conflicts: [...]` bloque l'activation.

## 10. Vanilla / Safe / Developer

- **Vanilla profile** : aucun mod activé.
- **Safe mode** : si le dernier lancement a crashé, désactive
  automatiquement les mods et propose une réactivation manuelle.
- **Developer mode** : ouvre console, symbol viewer, memory viewer,
  frame overlay. Aucun code de production ne dépend de ce mode.

## 11. Sécurité

- Un plugin natif (DLL/SO) est du code arbitraire. Prompt utilisateur
  explicite avant chargement, permissions listées.
- Les mods "cosmetic only" ne devraient PAS pouvoir charger de plugin
  natif — validation du manifest par le mod loader.
- Aucune installation de mod ne s'exécute automatiquement au boot sans
  activation explicite dans le manifest utilisateur.

## 12. Phasage

```
Phase 1  Virtual File System (integré à coreinit_fs)
Phase 2  Asset overrides (textures, audio, UI)
Phase 3  Mod manifest + manager
Phase 4  Load order + conflict detection
Phase 5  Shader overrides
Phase 6  Code hooks (via dispatch_table)
Phase 7  Memory patches (avec vérif signature)
Phase 8  Plugin API (limitée, versioned)
Phase 9  Developer tools (console, viewers)
Phase 10 Policies online/private (voir ENVIRONMENTS.md)
```

## 13. Rappels légaux

- Aucun mod distribuant du contenu propriétaire Nintendo (assets extraits
  du RPX/dump) ne doit être hébergé dans un canal officiel du projet.
- Le mod loader travaille sur le contenu que l'utilisateur possède déjà.
