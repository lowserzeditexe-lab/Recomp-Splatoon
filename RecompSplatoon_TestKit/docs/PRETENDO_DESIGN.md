# PRETENDO_DESIGN — Design de l'intégration Pretendo (Recomp Splatoon)

**Statut : DESIGN ONLY — non implémenté. Aucun code réseau n'est écrit tant
que la position officielle de Pretendo sur les clients PC natifs pour
Splatoon Wii U n'a pas été vérifiée et documentée.**

Ce document décrit uniquement les couches à prévoir. Il ne fixe pas d'API
définitive : celles-ci seront figées à partir du protocole réel observé et
de la documentation officielle Pretendo à la date d'implémentation.

## Sources à ré-analyser avant tout code

- <https://developer.pretendo.network/overview/nex>
- <https://developer.pretendo.network/overview/prudp>
- <https://developer.pretendo.network/docs/nex-go>
- <https://github.com/PretendoNetwork/nex-go>
- <https://nintendo-wiki.pretendo.network/docs/>
- <https://pretendo.network/docs/install/wiiu>
- <https://pretendo.network/docs/install>

**Rappel :** NEX-Go est une bibliothèque **Go côté serveur**. Elle ne peut
pas être liée directement à un client C++. Elle sert uniquement de
référence protocole. Trois stratégies restent ouvertes : (a) implémentation
native C++, (b) processus séparé Go relié via IPC local, (c) portage
partiel du protocole. La décision doit être prise **après** l'audit
protocole détaillé, pas avant.

---

## 1. Séparation stricte des identités

```
PC User
  ├── Local Splatoon profile   (JSON local, aucune info sensible)
  └── Pretendo Network ID (PNID)
        ├── Account information
        ├── Authentication
        └── NEX credentials
              └── Game services
```

**Interdit** : confondre PNID avec NNID Nintendo ou avec un compte
Windows local. Un PNID est spécifique à Pretendo (documentation
officielle : les NNID d'origine ne fonctionnent pas sur Pretendo).

## 2. Couches à prévoir

```
NetworkManager
   ├── OfflineBackend                (Phase 1 — par défaut)
   ├── LANBackend                    (Phase 3 — Private sessions)
   ├── PrivateServerBackend          (Phase 3 — Private/custom server)
   └── PretendoBackend               (Phase 4+, EXPERIMENTAL)
        ├── PretendoAccountService
        │     ├── initialize()
        │     ├── login(pnid)
        │     ├── logout()
        │     ├── getProfile()
        │     ├── getNEXIdentity()
        │     ├── refreshSession()
        │     └── discoverGameServer()
        ├── PRUDPTransport            (v1 pour Wii U — à vérifier)
        ├── RMCLayer                  (Remote Method Call sérialisation)
        ├── CertificateManager
        │     ├── load(), validate(), expiration(), renewal()
        └── GameServiceClient         (Splatoon-specific)
```

Les noms définitifs doivent correspondre au protocole réel. Aucune API
"placeholder" ne doit être écrite.

## 3. États exposés au launcher

Éviter le booléen `online = true`. Distinguer :

- `Pretendo unavailable`
- `Pretendo reachable`
- `Account not authenticated`
- `Account authenticated`
- `NEX unavailable`
- `NEX ready`
- `Game service unavailable`
- `Game service available`

## 4. Profils et secrets

- `profiles/<slug>/pretendo.json` : uniquement les champs **non sensibles**
  (display name, PNID public, remember_login, last login timestamp).
- Secrets (mot de passe PNID, tokens NEX, private key certificat) stockés
  via :
  - **Windows** : DPAPI (`CryptProtectData`) ou Windows Credential Manager.
  - **Linux** : libsecret / kwallet (à décider selon le desktop cible).
  - **macOS** : Keychain (`SecItemAdd`).
- Aucun secret en clair dans le JSON, jamais.

## 5. Logging

- Autorisé : `NEX authentication: SUCCESS`, `PRUDP session established`,
  `Discovery: game server acquired`.
- **Interdit** : mot de passe, NEX password, tokens, session secrets,
  clés privées, contenu certificat, même en `DEBUG` ou `TRACE`.

## 6. Découverte du game server

Suivre strictement la chaîne réelle :

```
Account Server → Authentication Server → Game Server Discovery → Splatoon Server
```

Aucun IP/host ne doit être hardcodé. Toute adresse doit provenir de la
réponse de découverte.

## 7. Politique Offline/Online

- Le lancement du jeu ne doit **jamais** dépendre de Pretendo, sauf si
  le mode sélectionné l'exige (`Vanilla Online` — voir `ENVIRONMENTS.md`).
- Un échec Pretendo doit dégrader silencieusement vers "Offline" et
  proposer une retry manuelle.

## 8. Compatibilité avec Splatoon recompilé

Les appels réseau du jeu recompilé arrivent au niveau `nsysnet` (35
fonctions socket déjà stubées). Deux stratégies :

1. **API-level** : intercepter au niveau NEX (fonctions haut-niveau de
   la Wii U) et court-circuiter vers le client Pretendo natif.
2. **Socket-level** : router les sockets `nsysnet` vers un endpoint
   local qui parle PRUDP à la vraie infra Pretendo.

Le choix dépend du reverse engineering du code recompilé — à faire
**après** l'audit protocole.

## 9. Ce qui ne sera pas fait sans validation

- Aucun endpoint Pretendo n'est écrit dans le code sans avoir été
  documenté officiellement.
- Aucun format certificat n'est inventé.
- Aucun handshake PRUDP n'est deviné.
- La progression Pretendo reste marquée `EXPERIMENTAL / RESEARCH`
  jusqu'à validation.

## 10. Phasage

```
Phase 1  Offline (default)                       ← état actuel
Phase 2  Network abstraction (NetworkManager)
Phase 3  Account abstraction (empty impl.)
Phase 4  PNID authentication (protocol study)
Phase 5  NEX authentication
Phase 6  Game server discovery
Phase 7  Splatoon online services
Phase 8  Matchmaking / gameplay
```
