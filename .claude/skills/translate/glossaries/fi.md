# Finnish (fi) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Finnish translations.

## Register

Use informal 2nd person singular **"sinä"** (`Anna`, `Valitse`, `Lisää`) consistently throughout all translations.

## Terminology

| English | Finnish | Notes |
|---------|---------|-------|
| Repository | Tietovarasto | |
| Archive | Arkisto | |
| Backup (noun) | Varmuuskopio | |
| Backup (verb) | Varmuuskopioida | |
| Prune | Karsi | Noun form: `Karsiminen` |
| Mount / Unmount | Liitä / Irrota liitos | |
| Extract | Pura | |
| Password / Passphrase | Salasana / Salauslause | |
| Keychain / Password manager | Järjestelmän avainnippu / Salasanojen hallintaohjelma | |
| System tray | Ilmoitusalue | |
| Profile | Profiili | |
| Schedule | Ajastus | |
| Source | Lähde | |
| Exclude | Ohita / Poissulkeminen | Verb / noun |
| Settings (tab) | Asetukset | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Lokit | Link form in elative (`Katso lisätietoja %1.`): `lokeista` |
| Compact / Compaction | Tiivistä / Tiivistys | Distinct from Compression (`Pakkaus`) |
| Socket (Unix file type) | Vastake | Avoid `Pistoke` (physical electrical plug) |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository | Tietovarasto | Established term across `vorta.fi.ts` |
| 2026-04-19 | Prune | Karsi / Karsiminen | Matches existing `ArchiveTab` Finnish strings |
| 2026-04-19 | Logs (link) | lokeista | Elative plural matching `Katso lisätietoja %1.` |
| 2026-04-19 | Settings vs Misc | Asetukset | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Tiivistä / Tiivistys | Distinct from data compression (`Pakkaus` / `Pakkaa`) |
| 2026-11-12 | Socket | Vastake | Standard Finnish computing term for Unix-domain/network socket |
