# ENVIRONMENTS — Séparation stricte Vanilla Online / Private Modded / Offline Dev

**Statut : DESIGN ONLY — non implémenté.**

Ce document définit la politique de séparation entre les trois modes
d'exécution de Recomp Splatoon. Objectif : **liberté maximale de modding
en local** + **protection stricte des services publics en ligne**.

## 1. Les trois modes

```
Recomp Splatoon
   ├── VANILLA ONLINE     (public online, Pretendo)
   ├── PRIVATE MODDED     (LAN / private / friend session)
   └── OFFLINE / DEV      (solo, tests, développement)
```

## 2. Sélection au lancement

Le launcher affiche explicitement le mode actif :

```
Select Game Mode

○ Vanilla Online
  Official-like online environment

○ Private Modded
  Mods, hacks and custom content

○ Offline / Development
  Full testing environment
```

Le mode ne peut pas être masqué. La bascule de mode force une
re-validation de la configuration.

## 3. Matrice de capabilities

Le champ `capabilities` de chaque mod (voir MODDING_DESIGN §3) sert à
autoriser ou refuser son activation dans chaque mode :

| Capability      | Offline / Dev | Private Modded | Vanilla Online              |
| --------------- | :-----------: | :------------: | :-------------------------: |
| `cosmetic`      | ✅            | ✅             | configurable (par défaut ✅) |
| `audio`         | ✅            | ✅             | configurable                |
| `graphics`      | ✅            | ✅             | configurable                |
| `ui`            | ✅            | ✅             | configurable                |
| `gameplay`      | ✅            | ✅             | ❌                          |
| `map`           | ✅            | ✅             | ❌ (service-dependent)      |
| `memory`        | ✅            | ✅             | ❌                          |
| `code`          | ✅            | ✅             | ❌                          |
| `plugin` natif  | ✅            | ✅             | ❌                          |
| `debug`         | ✅            | ✅             | ❌                          |
| `network`       | ⚠️            | ⚠️             | ❌                          |

Les cellules `configurable` sont réglées par la politique effective au
moment de l'implémentation, sur la base des règles réelles du service
public — pas sur des suppositions.

## 4. Validation à l'entrée en mode Vanilla Online

```
Switching to VANILLA ONLINE
Checking environment...

[✓] No gameplay mods
[✓] No memory patches
[✓] No unauthorized plugins
[✓] No code hooks
[✓] Content unchanged (SHA-256 == 45ecd1…)

Online mode ready
```

Si une incompatibilité est détectée :

```
ONLINE MODE BLOCKED

Incompatible mods:
- awesome.chaos-weapons (gameplay)
- author.debug-cam (debug)

Choose:
[ Disable incompatible mods ]
[ Switch to Private Modded ]
[ Cancel ]
```

Aucune désactivation silencieuse. L'utilisateur voit ce qui bloque.

## 5. Bascule Private → Public

Si l'utilisateur en Private Modded tente de se connecter au service
public Pretendo :

```
MODDED ENVIRONMENT

Your current configuration contains modifications
that may be incompatible with public online services.

For safety, public online mode requires a Vanilla
compatible profile.

[ Switch to Vanilla ]
[ Stay Offline ]
[ Cancel ]
```

## 6. Profil "Pretendo Vanilla" auto-créé

Le premier lancement du launcher crée un profil `pretendo-vanilla` :

- Aucun mod activé.
- `network_backend = pretendo`
- Utilisable en un clic pour retrouver un environnement propre après
  session Private Modded.

## 7. Isolation des saves par mode

```
userdata/profiles/<player>/
├── vanilla/         (save utilisée en Vanilla Online + Offline vanilla)
├── private_modded/  (save utilisée en Private Modded, isolée)
└── development/     (save utilisée en Offline / Dev, isolée)
```

Une partie modifiée ne peut pas corrompre la save vanilla.

## 8. Reset to Vanilla (bouton du launcher)

Effet :

- Désactive tous les mods.
- Vide `mods/enabled/` (bascule vers `disabled/`).
- Purge `mod_cache/`.
- Restaure `mods/profiles/vanilla.json` comme actif.
- **Ne touche pas** aux saves utilisateur.

## 9. Backends réseau et modes

```
Mode              →   Backend réseau autorisé
─────────────────────────────────────────────────
VANILLA ONLINE    →   PretendoBackend                (via profil vanilla)
PRIVATE MODDED    →   OfflineBackend | LANBackend | PrivateServerBackend
OFFLINE / DEV     →   OfflineBackend                 (uniquement)
```

Aucun mode ne peut basculer vers `PretendoBackend` sans passer par la
validation §4.

## 10. LAN / Private server / Custom backend

Le NetworkManager expose ces backends comme des enfants séparés (voir
`PRETENDO_DESIGN.md §2`). En Private Modded, une session LAN entre amis
peut :

- Charger cartes custom et modèles custom.
- Distribuer un `session manifest` (liste des mods requis + checksums).
- Refuser un joueur dont les checksums ne matchent pas.

Aucun contenu propriétaire Nintendo n'est distribué automatiquement.

## 11. UI du launcher — section Mode

```
─────────────────────────────────
GAME MODE

  Current : Private Modded
  Network : LAN

  Active mods : 4
  Warnings    : 0
  Conflicts   : 0

  [ Switch mode ]     [ Manage mods ]

─────────────────────────────────
```

## 12. Diagnostics

Chaque log de crash inclut :

```
Mode           : Private Modded
Network        : LAN
Loaded mods    :
  - hd.textures 1.4.0
  - author.better-ui 2.1.0
  - author.cam-tools 0.8.2
Content hash   : 45ecd1... (match)
Runtime        : Recomp Splatoon 0.1.0 (RebrewU 0b40c4f)
```

## 13. Politique finale

Le projet **n'empêche pas** le modding. Il empêche uniquement
l'utilisation accidentelle d'un environnement moddé contre un service
public — protection à la fois des serveurs publics et des utilisateurs
respectueux. Les libertés en local (Private, Offline) sont totales.
