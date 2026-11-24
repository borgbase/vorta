# Dutch (nl) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Dutch translations.

## Register

Use informal **"je/jij"** (`Voer`, `Kies`, `Je`) consistently throughout all translations.

## Terminology

| English | Dutch | Notes |
|---------|-------|-------|
| Repository | Repo / Repository | Matches existing `vorta.nl.ts` |
| Archive | Archief | |
| Backup (noun) | Back-up | With hyphen |
| Backup (verb) | Back-uppen | |
| Prune | Vernietigen / Opschonen | Context-dependent matching `ArchiveTab` |
| Mount / Unmount | Aankoppelen / Afkoppelen | |
| Extract | Uitpakken | |
| Password / Passphrase | Wachtwoord / Toegangszin | |
| Keychain / Password manager | Sleutelbeheerder van het systeem / Wachtwoordbeheerder | |
| System tray | Systeemvak | |
| Profile | Profiel | |
| Schedule | Tijdschema | |
| Source | Bron | |
| Exclude | Uitsluiten | |
| Settings (tab) | Instellingen | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Logboeken | Link form: `logboeken` |
| Compact / Compaction | Ruimte vrijmaken / Reporuimte vrijmaken | Distinct from Compression (`Compressie`) |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Backup | Back-up | Standard Dutch spelling with hyphen used across `vorta.nl.ts` |
| 2026-04-19 | Mount / Unmount | Aankoppelen / Afkoppelen | Established terminology in `ArchiveTab` in `vorta.nl.ts` |
| 2026-04-19 | System tray | Systeemvak | Standard Dutch desktop term used in `vorta.nl.ts` |
| 2026-04-19 | Settings vs Misc | Instellingen | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Ruimte vrijmaken / Reporuimte vrijmaken | Reclaims deleted segment space; avoids collision with data compression (`Compressie` / `Comprimeren`) |
