# Swedish (sv) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Swedish translations.

## Register

Use informal **"du"** (`Ange`, `Din`, `Lås upp`) consistently throughout all translations.

## Terminology

| English | Swedish | Notes |
|---------|---------|-------|
| Repository | Förråd | |
| Archive | Arkiv | |
| Backup (noun) | Säkerhetskopiering / Säkerhetskopia | Process / single backup |
| Backup (verb) | Säkerhetskopiera | |
| Prune | Beskär | |
| Mount / Unmount | Montera / Avmontera | |
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

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository | Förråd | Established Swedish term across `vorta.sv.ts` |
| 2026-04-19 | Prune | Beskär | Matches existing `ArchiveTab` Swedish translations |
| 2026-04-19 | Logs (link) | loggarna | Definite plural matching `Se %1 för detaljer.` |
| 2026-04-19 | Settings vs Misc | Inställningar | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Kompaktera / Kompaktering | Reclaims free repository segment space; avoids collision with Compression (`Komprimering`) |
