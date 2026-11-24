# Slovak (sk) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Slovak translations.

## Register

Use formal plural **"vy"** (`Zadajte`, `Vyberte`) consistently throughout all translations.

## Terminology

| English | Slovak | Notes |
|---------|--------|-------|
| Repository | Repozitár | |
| Archive | Archív | |
| Backup (noun) | Záloha | |
| Backup (verb) | Zálohovať | |
| Prune | Vyčistiť | |
| Mount / Unmount | Pripojiť / Odpojiť | |
| Extract | Rozbaliť | |
| Password / Passphrase | Heslo | |
| Keychain / Password manager | Systémová kľúčenka / Správca hesiel | |
| System tray | Oznamovacia oblasť | |
| Profile | Profil | |
| Schedule | Plán | |
| Source | Zdroj | |
| Exclude | Vylúčiť | |
| Settings (tab) | Nastavenia | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Záznamy | Link form in locative (`v %1`): `záznamoch` |
| Compact / Compaction | Zhutniť / Zhutňovanie | Distinct from Compression (`Kompresia`) |
| Preset | Predvoľba | Plural: `Predvoľby`; avoid `Profily` which collides with backup profiles |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository | Repozitár | Standard Slovak technical term used throughout `vorta.sk.ts` |
| 2026-04-19 | Prune | Vyčistiť | Matches existing `ArchiveTab` Slovak strings |
| 2026-04-19 | Logs (link) | záznamoch | Locative plural matching `Podrobnosti nájdete v %1.` |
| 2026-04-19 | Settings vs Misc | Nastavenia | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Zhutniť / Zhutňovanie | Distinct from data compression (`Kompresia`) |
