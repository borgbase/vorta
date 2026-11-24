# Czech (cs) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Czech translations.

## Register

Use formal plural **"vy"** (`Zadejte`, `Vyberte`, `Zvolte`) consistently throughout all translations.

## Style Rules

- **Capitalization:** Use sentence case for buttons, menus, tabs, column headers, and dialog titles (`Přidat repozitář`, `Uložit`, `Plán`). Do not copy English Title Case. Keep parenthetical qualifiers lowercase (`(doporučeno)`, `(zastaralé)`, `(výchozí)`).
- **Quotation marks:** Use Czech typographic quotes `„…“` (U+201E / U+201C) in prose (`kartu „Text“`). Keep ASCII double quotes `"..."` inside shell command examples (`echo "..."`).
- **Ellipsis:** Always use Unicode ellipsis `…` (U+2026) in prose, progress messages, and dialog-opening actions (never ASCII `...`).
- **Qt plural forms (`numerus="yes"`):** Use Czech's 3-form slot order:
  - `[0]` `n == 1` (`%n soubor`)
  - `[1]` `n ∈ 2..4` (`%n soubory`)
  - `[2]` `n == 0` or `n >= 5` (`%n souborů`)
- **Grammatical gender of product names:**
  - `Borg` is **masculine inanimate** (`Borgu`, `nástroj Borg`, `Borg už běží`). Never treat it as neuter (`borg … spuštěné`) or use English-style noun adjuncts (`borg heslová fráze` → `heslová fráze Borgu`).
  - `Vorta` is **feminine** (`aplikace Vorta`, `Aplikace Vorta byla neočekávaně ukončena.`).
- **Verb mood:** Use the **infinitive** for buttons and actions (`Uložit`, `Přidat repozitář`, `Uvolnit prostor`, `Vyloučit soubory/složky`) and the formal **`vy` imperative** for prompts and instructions (`Zadejte heslovou frázi`, `Vyberte repozitář`, `Zvolte místní složku`).

## Terminology

| English | Czech | Notes |
|---------|-------|-------|
| Repository | Repozitář | |
| Archive | Archiv | |
| Backup (noun) | Záloha | |
| Backup (verb) | Zálohovat | |
| Prune | Prořezat | |
| Mount / Unmount | Připojit (mount) / Odpojit (unmount) | Or `Připojit` / `Odpojit` in concise labels; filesystem mount/unmount |
| Unlink | Zrušit propojení | Removes repository link from Vorta (distinct from `Unmount` and `Detach`) |
| Detach | Odpojit od profilu | Disconnects repository from current profile while keeping it for other profiles |
| Mount point | Přípojný bod | |
| Extract | Rozbalit | |
| Diff | Rozdíly / Porovnat | Noun `Rozdíly` (or `Výsledek porovnání`), verb `Porovnat` |
| Password / Passphrase | Heslo / Heslová fráze | Use `heslová fráze Borgu` (never `borg heslová fráze`) |
| Keychain / Password manager | Systémová klíčenka / Správce hesel | |
| System tray | Oznamovací oblast | |
| Profile | Profil | |
| Schedule | Plán | Noun for tab/section title (not `Naplánovat`) |
| Source | Zdroj | |
| Folder / Directory | Složka | Consistent user-facing term for both `Folder` and `Directory` |
| Path | Cesta | Avoid verbose `Popis umístění` |
| Exclude | Vyloučit | Never use `vynechat` |
| Raw | Text | Or `Surové`; avoid `Holé` |
| Metered network / connection | Síť s účtovanými daty / Připojení s účtovanými daty | Consistent terminology across UI and status messages |
| Full Disk Access | Plný přístup k disku | Matches macOS Czech system terminology |
| Reset App | Resetovat aplikaci | Never `Restartovat aplikaci` (Reset clears/resets app state, not a restart) |
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
| 2026-11-24 | Exclude | Vyloučit | Consistent with Borg exclusion semantics; forbid `vynechat` |
| 2026-11-24 | Unmount / Unlink / Detach | Odpojit / Zrušit propojení / Odpojit od profilu | Preserves the 3-way distinction between filesystem unmount, removing repo from Vorta, and detaching repo from a single profile |
| 2026-11-24 | Path | Cesta | Standard concise Czech UI term; avoids verbose `Popis umístění` |
| 2026-11-24 | Diff | Rozdíly / Porovnat | Natural Czech for archive comparison (`Porovnat` for action, `Rozdíly` for results) |
| 2026-11-24 | Raw | Text (or Surové) | Clearer tab label for multi-line pattern entry than literal `Holé` |
| 2026-11-24 | Metered network / connection | Síť s účtovanými daty / Připojení s účtovanými daty | Standard Czech networking term |
| 2026-11-24 | Full Disk Access | Plný přístup k disku | Matches official Czech macOS Privacy & Security setting name |
| 2026-11-24 | Folder / Directory | Složka | Standard desktop Czech term used consistently across Vorta |
| 2026-11-24 | Mount point | Přípojný bod | Standard Czech filesystem terminology |
| 2026-11-24 | Reset App | Resetovat aplikaci | Distinguishes resetting application state from restarting (`Restartovat`) |
