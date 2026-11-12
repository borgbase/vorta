# Czech (cs) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Czech translations.

## Register

Use formal plural **"vy"** (`Zadejte`, `Vyberte`) consistently throughout all translations.

## Terminology

| English | Czech | Notes |
|---------|-------|-------|
| Repository | Repozitář | |
| Archive | Archiv | |
| Backup (noun) | Záloha | |
| Backup (verb) | Zálohovat | |
| Prune | Prořezat | |
| Mount / Unmount | Připojit (mount) / Odpojit (unmount) | Or `Připojit` / `Odpojit` in concise labels |
| Extract | Rozbalit | |
| Password / Passphrase | Heslo / Heslová fráze | |
| Keychain / Password manager | Systémová klíčenka / Správce hesel | |
| System tray | Oznamovací oblast | |
| Profile | Profil | |
| Schedule | Plán | |
| Source | Zdroj | |
| Exclude | Vyloučit | |
| Settings (tab) | Nastavení | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Záznamy | Link form in locative (`v %1`): `záznamech` |
| Compact / Compaction | Uvolnit prostor / Uvolňování prostoru | Distinct from Compression (`Komprese`) |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository | Repozitář | Standard Czech technical term used throughout `vorta.cs.ts` |
| 2026-04-19 | Prune | Prořezat | Matches existing `ArchiveTab` Czech translations |
| 2026-04-19 | Logs (link) | záznamech | Locative plural matching `Podrobnosti naleznete v %1.` |
| 2026-04-19 | Settings vs Misc | Nastavení | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Uvolnit prostor / Uvolňování prostoru | Describes freeing deleted segment space; distinct from data compression |
