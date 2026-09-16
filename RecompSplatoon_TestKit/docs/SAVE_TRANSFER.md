# SAVE_TRANSFER — Design du transfert de sauvegardes Wii U ↔ PC

**Statut : DESIGN ONLY — non implémenté.** Les formats exacts (SaveMii,
common data, per-user data, encryption si applicable) doivent être
extraits du reverse engineering réel des sauvegardes Splatoon Wii U et de
SaveMii, pas devinés.

## Sources à ré-analyser

- <https://pretendo.network/docs/install/wiiu>
- <https://github.com/Xpl0itU/savemii>
- <https://github.com/Ryuzaki-MrL/savemii>
- <https://pretendo.network/docs/network-dumps>

## 1. Objectif utilisateur

```
1. Backup Splatoon sur Wii U (SaveMii)
2. Insérer la SD dans le PC
3. Ouvrir Recomp Splatoon Launcher
4. "Import Wii U Save"
5. Sélectionner Splatoon
6. Sélectionner profil Wii U + profil PC/PNID
7. Confirmer
8. Lancer le jeu
```

## 2. Architecture

```
SaveTransfer
   ├── Detector
   │    ├── SDCardDetector
   │    ├── FolderDetector
   │    └── FTPDetector          (Phase 8)
   ├── SaveMiiReader             (format saveMii)
   ├── SaveMiiWriter             (export PC → SaveMii)
   ├── Validator
   │    ├── Structure
   │    ├── TitleID
   │    ├── Version
   │    └── Integrity (SHA-256)
   ├── ProfileMapper             (Wii U user ↔ PC/PNID)
   ├── BackupManager             (auto-backup avant destruction)
   └── VersioningStore           (metadata versionnée)
```

## 3. Emplacement SaveMii (source : projet SaveMii)

```
sd:/wiiu/backups/<TitleID>/<slot>/
   ├── saveMiiMeta.json
   ├── 80000001/       (per-user data, ID Wii U)
   ├── 80000002/
   └── common/
```

## 4. Structure locale PC

```
userdata/
├── profiles/
│   ├── player1/
│   │   ├── account/
│   │   │   ├── local.json           (nom, PNID public, prefs)
│   │   │   └── pretendo.secret     (DPAPI/libsecret/Keychain)
│   │   └── splatoon/
│   │       ├── save/                (données jeu, format à déterminer)
│   │       ├── save.meta.json
│   │       └── save.sha256
│   └── player2/...
└── backups/
    └── 2026-01-15_14-30/
        └── splatoon/
```

## 5. Import Wii U → PC (workflow)

```
User selects source
  ├── SD card auto-detect (/wiiu/backups)
  ├── Folder browse
  └── FTP (Phase 8 — Wii U homebrew LAN)
        ↓
SaveMiiReader
        ↓
Detect Splatoon (Title ID) — Title ID à déterminer par RE, pas hardcodé
        ↓
List Wii U profiles + common data
        ↓
User selects Wii U profile → PC/PNID profile mapping
        ↓
Validate structure + integrity
        ↓
Auto-backup existing PC save (BackupManager)
        ↓
Transform format Wii U → format Recomp
        ↓
Write PC save + save.meta.json + save.sha256
        ↓
Verify (re-read + hash)
        ↓
Done
```

## 6. Export PC → Wii U

Symétrique. Regénère la structure SaveMii `wiiu/backups/<TitleID>/<slot>/`
avec `saveMiiMeta.json`, `80000001/`, `common/`. **Ne pas** écrire
directement dans la NAND Wii U — passer par SaveMii sur la console.

## 7. Métadonnées versionnées (`save.meta.json`)

```json
{
  "schema_version": 1,
  "game": "Splatoon",
  "region": "NTSC-U",
  "source": "WiiU",
  "source_title_id": "<hex>",
  "source_profile_id": "<hex>",
  "target_profile": "player1",
  "target_pnid": "<optional>",
  "imported_at": "2026-01-15T14:30:00Z",
  "recomp_version": "0.1.0",
  "sha256": "<hex>",
  "size_bytes": 0,
  "file_count": 0
}
```

Valeurs réelles calculées, aucune valeur inventée.

## 8. Validation stricte avant écriture

```
[✓] Save structure valid
[✓] Splatoon detected
[✓] Profile data detected
[✓] Common data detected
[✓] Backup metadata valid
```

Échecs possibles :

- Invalid save structure
- Unknown Title ID
- Missing required files
- Unsupported save version
- Corrupted backup (SHA-256 mismatch)

En cas d'échec critique : refus de l'import, aucune écriture partielle.

## 9. Backup automatique avant écriture

Toute opération destructive doit :

1. Créer un snapshot dans `userdata/backups/<timestamp>/`.
2. Vérifier le snapshot (re-read + hash).
3. Seulement ensuite procéder à l'import.
4. En cas d'échec de l'import, restaurer automatiquement le snapshot.

## 10. Ce qui ne sera jamais tenté

- Copier des données de compte **côté serveur** Nintendo — non
  transférables par cette méthode (voir doc Pretendo).
- Écriture directe dans la NAND Wii U depuis le PC.
- Deviner le Title ID Splatoon sans preuve du RE ou du dump.
- Chiffrement custom : si la sauvegarde Wii U est chiffrée, le
  déchiffrement doit passer par un mécanisme légal (SaveMii sur console
  ou clés fournies par l'utilisateur), pas par un algorithme inventé.

## 11. Phasage

```
Phase 1  Gestion PC save (metadata + backup)
Phase 2  Détection SaveMii (SD card, folder)
Phase 3  Import SaveMii → PC (read + transform)
Phase 4  Profile mapping (Wii U user → PC profile / PNID)
Phase 5  Validation stricte
Phase 6  Export PC → SaveMii
Phase 7  Workflow SD complet + drag & drop
Phase 8  Transfert LAN direct (Wii U homebrew FTP)
Phase 9  Intégration Pretendo profile
```
