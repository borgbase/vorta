# Slovak (sk) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Slovak translations.

## Register

Use formal plural **"vy"** (`Zadajte`, `Vyberte`) consistently throughout all translations.

## Slovak Style Rules

- **Capitalization:** Use Slovak sentence case for buttons, menu items, tabs, column headers, dialog titles, and parenthetical qualifiers (e.g., `(odporúčané)`, `(zastarané)`). Never copy English Title Case. Keep common nouns like `správca hesiel` lowercase mid-sentence.
- **Quotation marks:** Use Slovak typographic quotes `„…“` in prose. Keep ASCII `"..."` inside shell command examples (e.g., `echo "..."`).
- **Ellipses:** Use the Unicode ellipsis `…` (U+2026) on dialog-opening actions and progress messages (never ASCII `...`).
- **Plurals (Qt `numerus="yes"`):** Slovak uses 3 `<numerusform>` slots in this order:
  - `[0]` `n == 1` (e.g., `%n súbor`)
  - `[1]` `n ∈ 2..4` (e.g., `%n súbory`)
  - `[2]` `n == 0` or `n >= 5` (e.g., `%n súborov`)
- **Proper nouns (`Borg`, `Vorta`):** Always capitalize `Borg` and `Vorta` and decline them consistently in Slovak prose (`Borg` → `Borgu`, `Vorta` → `Vorty` / `aplikácia Vorta`, avoiding undeclined `borg heslo` or `pre Vorta`).
- **Progress messages:** Prefer impersonal verbal nouns (`Pripájanie…`, `Odpájanie…`, `Ukladanie…`, `Počítanie…`) for ongoing operations. Avoid 1st-person singular forms (`Spracovávam`, `Ukladám`, `Pripájam`, `Počítam`).
- **Avoid Bohemisms / Czechisms:** Do not use Czech forms or calques such as `inicializovat` (use `inicializovať`), `hodin` (use `hodiny`/`hodín`), `obdržal` (use `dostal`), `hlášky` (use `správy`/`hlásenia`), `kvôli` for cause/reason (use `pre`), or `žiaden` (prefer standard `žiadny`).
- **No parenthetical English glosses:** Do not append English words in parentheses such as `(mount)`, `(unmount)`, or `(hard link)` after standard Slovak terms.

## Terminology

| English | Slovak | Notes |
|---------|--------|-------|
| Repository | Repozitár | |
| Archive | Archív | |
| Backup (noun) | Záloha | |
| Backup (verb) | Zálohovať | |
| Prune | Vyčistiť / Vyčistenie | Autopruning: `Automatické vyčistenie`; forbid `Čistenie` / `Autočistenie` |
| Mount / Unmount | Pripojiť / Odpojiť | Filesystem mount/unmount; never add `(mount)` / `(unmount)` |
| Unlink (repository) | Zrušiť prepojenie | Distinct from filesystem `Unmount` (`Odpojiť`) and `Detach` (`Odpojiť od profilu`) |
| Detach (repository) | Odpojiť od profilu | Removes repo from current profile while keeping it for other profiles |
| Extract | Rozbaliť | Avoid `extrakcia` |
| Restore | Obnoviť | Restoring files/data or app state; distinct from `Refresh` (`Znovu načítať`) |
| Refresh | Znovu načítať | Reloading archive list/metadata; avoid conflating with `Restore` (`Obnoviť`) |
| Folder / Directory | Priečinok | Standard UI term (prefer `Priečinok` over `Adresár`) |
| Name (non-persons) | Názov | For repositories, archives, profiles, files; forbid `Meno` |
| Diff | Rozdiely / Porovnať | Noun: `Rozdiely`; action: `Porovnať` |
| Reset App | Obnoviť pôvodné nastavenia aplikácie | Forbid `Reštartovať aplikáciu` (which means restart, not reset) |
| Password / Passphrase | Heslo | Borg passphrase: `heslo Borgu` |
| Keychain / Password manager | Systémová kľúčenka / správca hesiel | Lowercase `správca hesiel` mid-sentence |
| System tray | Oznamovacia oblasť | |
| Profile | Profil | |
| Schedule | Plán | Avoid verb `Naplánovať` for the tab/noun label |
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
| 2026-04-19 | Prune | Vyčistiť / Vyčistenie | Matches existing `ArchiveTab` Slovak strings; forbids `Čistenie`/`Autočistenie` |
| 2026-04-19 | Logs (link) | záznamoch | Locative plural matching `Podrobnosti nájdete v %1.` |
| 2026-04-19 | Settings vs Misc | Nastavenia | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Zhutniť / Zhutňovanie | Distinct from data compression (`Kompresia`) |
| 2026-11-24 | Unmount / Unlink / Detach | Odpojiť / Zrušiť prepojenie / Odpojiť od profilu | Clear 3-way distinction between filesystem unmount, removing repo from Vorta, and detaching from one profile |
| 2026-11-24 | Restore vs Refresh | Obnoviť vs Znovu načítať | Prevents ambiguity between restoring backed-up data and reloading archive metadata |
| 2026-11-24 | Folder / Directory | Priečinok | Consistent modern Slovak UI terminology |
| 2026-11-24 | Name (non-persons) | Názov | Standard Slovak for inanimate objects; `Meno` is for persons |
| 2026-11-24 | Diff | Rozdiely / Porovnať | Natural Slovak noun/verb for archive comparison |
| 2026-11-24 | Reset App | Obnoviť pôvodné nastavenia aplikácie | Accurately conveys resetting app state/settings rather than restarting (`Reštartovať`) |
