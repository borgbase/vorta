# Swedish (sv) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Swedish translations.

## Register

Use informal **"du"** (`Ange`, `Din`, `Lås upp`) consistently throughout all translations.

## Style Rules

- **Capitalization:** Use sentence case for buttons, menus, tabs, column headers, and dialog titles. Use lowercase inside parenthetical qualifiers, e.g. `(rekommenderas)`, `(äldre)`, `(standard)`, `(rekommenderas, nyckeln lagras i förrådet)`.
- **Compounds and hyphenation:** Follow Swedish closed-compound rules (*sammanskrivning*): `arkivnamn`, `förrådsnamn`, `profilnamn`, `förrådslösenord`. Hyphenate compounds with acronyms or proper nouns: `SSH-nyckel`, `Borg-lösenfras`, `Vorta-version`, `Wi-Fi-nätverk`.
- **Quotation marks:** Use consistent straight double quotes (`"..."`) in prose, and always keep ASCII double quotes `"..."` inside shell command examples (`echo "..."`).
- **macOS UI terms:** Use official macOS Swedish UI terminology: `Fullständig skivåtkomst`, `Systeminställningar > Säkerhet och integritet`.
- **Punctuation:** Preserve Unicode ellipses `…` (U+2026) on dialog-opening actions and progress messages, and match `<source>` trailing periods (do not add or drop trailing periods).

## Terminology

| English | Swedish | Notes |
|---------|---------|-------|
| Repository | Förråd | |
| Archive | Arkiv | |
| Backup (noun) | Säkerhetskopiering / Säkerhetskopia | Process / single backup |
| Backup (verb) | Säkerhetskopiera | |
| Prune | Beskär | |
| Mount / Unmount | Montera / Avmontera | Distinct from Unlink (`Koppla bort`) and Detach (`Koppla från`) |
| Unlink | Koppla bort | Remove repository link completely; distinct from Unmount (`Avmontera`) and Detach (`Koppla från`) |
| Detach | Koppla från | Detach repository from current profile only; distinct from Unlink (`Koppla bort`) and Unmount (`Avmontera`) |
| Extract | Extrahera | |
| Password / Passphrase | Lösenord / Lösenfras | |
| Keychain / Password manager | Systemets nyckelring / Lösenordshanterare | |
| System tray | Systemfältet | |
| Profile | Profil | |
| Schedule | Schema | |
| Source | Källa | |
| Exclude | Exkludera | |
| Settings (tab) | Inställningar | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Loggar | Link form (definite plural): `loggarna` |
| Compact / Compaction | Kompaktera / Kompaktering | Distinct from Compression (`Komprimering`) |
| Consistency / Consistency check | Konsistens / Konsistenskontroll | Never `konsekvenskontroll` |
| Public key | Offentlig nyckel | Never `publik nyckel` |
| Metered network / connection | Databegränsat nätverk / Databegränsad anslutning | |
| Preview | Förhandsgranskning | Never `Förhandsvisning` |
| Diff | Jämför / Jämförelse | Action button (`Jämför`) / noun (`Jämförelse`) |
| Full Disk Access | Fullständig skivåtkomst | Official macOS Swedish UI term; never `fullständig diskåtkomst` |
| Return code / Exit code | Returkod | Never `avslutningskod` |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository | Förråd | Established Swedish term across `vorta.sv.ts` |
| 2026-04-19 | Prune | Beskär | Matches existing `ArchiveTab` Swedish translations |
| 2026-04-19 | Logs (link) | loggarna | Definite plural matching `Se %1 för mer information.` |
| 2026-04-19 | Settings vs Misc | Inställningar | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Kompaktera / Kompaktering | Reclaims free repository segment space; avoids collision with Compression (`Komprimering`) |
| 2026-11-24 | Consistency / Consistency check | Konsistens / Konsistenskontroll | Standard Swedish technical term; avoids `konsekvenskontroll` |
| 2026-11-24 | Public key | Offentlig nyckel | Standard Swedish cryptography term; avoids anglicism `publik nyckel` |
| 2026-11-24 | Unmount / Unlink / Detach | Avmontera / Koppla bort / Koppla från | Preserves 3-way distinction between filesystem unmount, repo unlink, and profile detach |
| 2026-11-24 | Metered network / connection | Databegränsat nätverk / Databegränsad anslutning | Consistent, idiomatic Swedish across `NetworksPage` and `messages` |
| 2026-11-24 | Preview | Förhandsgranskning | Standard Swedish UI term; avoids `Förhandsvisning` |
| 2026-11-24 | Diff | Jämför / Jämförelse | Localizes English jargon `Diff` consistently with "Compare two archives" |
| 2026-11-24 | Full Disk Access | Fullständig skivåtkomst | Matches official macOS Swedish System Settings label |
| 2026-11-24 | Return code / Exit code | Returkod | Matches `LogPage` column header and avoids `avslutningskod` |
