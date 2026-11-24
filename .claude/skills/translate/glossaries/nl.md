# Dutch (nl) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Dutch translations.

## Register

Use informal **"je/jij"** (`Voer`, `Kies`, `Je`) consistently throughout all translations.

## Style Rules

- **Capitalization:** Use Dutch sentence case (never English Title Case) for buttons, menus, tabs, column headers, dialog titles, and lowercase inside parenthetical qualifiers (`(aanbevolen)`, `(standaard)`, `(verouderd)`).
- **Compounds (*Groene Boekje*):** Write Dutch compounds solid (`shellopdrachten`, `wifinetwerk`, `repowachtwoorden`, `back-uppen`). Use a hyphen only for `back-up-` compounds (`back-up- en repo-instellingen`), vowel collisions (`repo-url`, `repo-instellingen`, `repo-opslag`), and proper nouns/acronyms (`SSH-sleutel`, `Borg-toegangszin`).
- **Acronyms & technical names:** Keep `SSH` uppercase in prose (never lowercase `ssh`). Keep `Borg`, `BorgBackup`, `Vorta`, `URL`, `macFUSE`, `GitHub`, `BorgBase`, `Sparkle`, `KWallet`, `Repokey`, `Keyfile` unchanged.
- **Shell `echo` examples:** Keep ASCII double quotes `"..."` around `echo "..."` examples (never curly quotes `‘…’` or single quotes `'...'`, which break shell syntax or variable expansion).
- **Standard wording:** Use standard `Niets` (forbid colloquial `Niks`).
- **Verb mood:** Use infinitive for settings and checkboxes (e.g., `Repowachtwoorden opslaan in…`, `Vorta toevoegen aan…`), and imperative for direct user prompts and instructions (e.g., `Voer een profielnaam in.`, `Kies een externe repo`).

## Terminology

| English | Dutch | Notes |
|---------|-------|-------|
| Repository | Repo | Forbid `opslagruimte` |
| Archive | Archief | |
| Backup (noun) | Back-up | With hyphen |
| Backup (verb) | Back-uppen | |
| Deduplicated | Gededupliceerd | `Deduplicated Size:` → `Gededupliceerde grootte:` (never `Uitgepakt`) |
| Compressed | Gecomprimeerd | `Compressed Size:` → `Gecomprimeerde grootte:` (never `Ingepakt`) |
| Prune | Vernietigen | Unify across all strings; forbid `Opruimen` and `Automatisch verwijderen` |
| Mount | Aankoppelen | |
| Unmount | Afkoppelen | Forbid `Ontkoppelen` for unmount |
| Unlink | Ontkoppelen | Distinct from Unmount (`Afkoppelen`) and Detach (`Loskoppelen`) |
| Detach | Loskoppelen | Distinct from Unmount (`Afkoppelen`) and Unlink (`Ontkoppelen`) |
| Extract | Uitpakken | |
| Refresh | Vernieuwen | |
| Password / Passphrase | Wachtwoord / Toegangszin | |
| Keychain / Password manager | Sleutelbeheerder van het systeem / Wachtwoordbeheerder | |
| Return code / Exit code | Afsluitcode | Forbid `Terugkoppelingscode` / `terugkoppelcode` |
| Path | Pad | Avoid `lokale locatie` (`lokaal pad`) |
| System tray | Systeemvak | |
| Profile | Profiel | |
| Schedule | Tijdschema | |
| Source | Bron | |
| Exclude | Uitsluiten | |
| Settings (tab) | Instellingen | UI label is `Instellingen / Over`; code uses `misc` internally |
| Logs | Logboek / logboeken | Singular UI label `Logboek`; plural/link form `logboeken` |
| Compact / Compaction | Ruimte vrijmaken / Reporuimte vrijmaken | Distinct from Compression (`Compressie`) |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Backup | Back-up | Standard Dutch spelling with hyphen used across `vorta.nl.ts` |
| 2026-04-19 | Mount / Unmount | Aankoppelen / Afkoppelen | Established terminology in `ArchiveTab` in `vorta.nl.ts` |
| 2026-04-19 | System tray | Systeemvak | Standard Dutch desktop term used in `vorta.nl.ts` |
| 2026-04-19 | Settings vs Misc | Instellingen | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Ruimte vrijmaken / Reporuimte vrijmaken | Reclaims deleted segment space; avoids collision with data compression (`Compressie` / `Comprimeren`) |
| 2026-11-24 | Deduplicated / Compressed | Gededupliceerd / Gecomprimeerd | Fixes incorrect `Uitgepakt` / `Ingepakt` translations that meant extracted/packed |
| 2026-11-24 | Prune | Vernietigen | Unified across the catalog, replacing inconsistent `Opruimen` and `Automatisch verwijderen` |
| 2026-11-24 | Unmount / Unlink / Detach | Afkoppelen / Ontkoppelen / Loskoppelen | Clear 3-way distinction between filesystem unmount, profile repo unlink, and shared repo detach |
| 2026-11-24 | Return code / Exit code | Afsluitcode | Unified standard Dutch term, replacing `Terugkoppelingscode` / `terugkoppelcode` |
| 2026-11-24 | Repository | Repo | Consistent short term across Vorta; avoids ambiguous `opslagruimte` |
| 2026-11-24 | Path | Pad | Standard Dutch filesystem term; avoids pleonastic `lokale locatie` |
| 2026-11-24 | Refresh | Vernieuwen | Consistent Dutch UI verb across archive/repo refresh operations |
| 2026-11-24 | Logs | Logboek / logboeken | Singular `Logboek` for tab/action labels, plural `logboeken` for prose/links |
