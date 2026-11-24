# Finnish (fi) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Finnish translations.

## Register

Use informal 2nd person singular **"sinä"** (`Anna`, `Valitse`, `Lisää`) consistently throughout all translations.

## Style Rules

- **Capitalization:** Use sentence case for UI labels, buttons, tabs, menus, column headers, and dialog titles — never copy English Title Case. Use lowercase inside parenthetical qualifiers (e.g., `(suositeltu)`, `(automaattinen, vanha)`, `(avain tallennetaan kotikansioon)`).
- **Case inflection around placeholders (`%1`, `%2`, `{}`):** Because injected `%1`/`%2` link strings and `{}` values are uninflected, attach a governing head noun or hyphenated compound so the sentence reads grammatically (e.g., `%1-palvelua`, `%2-välilehden`, `kohteessa {}`, `tietovarastoon {}`).
- **Imperative vs. passive voice:** Use 2nd-person singular imperative (`Valitse`, `Anna`, `Pura`) for user actions and prompts, and Finnish passive (`Ladataan…`, `Aloitetaan varmuuskopiointia…`, `Irrotetaan arkiston liitosta…`) for progress and status messages.
- **Punctuation:** Use the Unicode ellipsis `…` (U+2026) on dialog-opening actions and progress messages (never ASCII `...`). Write `HUOM.` with a period (never `HUOM:`).
- **Compounds with foreign/technical identifiers:** Join foreign or code identifiers to Finnish head nouns with a hyphen (e.g., `profile_export-vientitiedosto`, `SSH-avain`, `Borg-varmuuskopio`).
- **Borg encryption modes:** Keep Borg mode names (`Repokey`, `Keyfile`) verbatim; do not translate `Keyfile` to `Avaintiedosto`.

## Terminology

| English | Finnish | Notes |
|---------|---------|-------|
| Repository | Tietovarasto | |
| Archive | Arkisto | |
| Backup (artifact/noun) | Varmuuskopio | The resulting backup |
| Backup (process) | Varmuuskopiointi | The act/process of backing up (distinct from artifact `Varmuuskopio`) |
| Backup (verb) | Varmuuskopioida | |
| Folder / Directory | Kansio | Prefer `Kansio` over `Hakemisto` in UI prose |
| Prune | Karsi | Noun form: `Karsiminen` |
| Diff | Erot | Avoid `Eroavaisuudet` |
| Cancel | Peru | Question form: `Perutaanko` (avoid `Peruuta` / `Peruutetaanko`) |
| Rename | Nimeä uudelleen | Avoid `Uudelleennimeä` |
| Enter (prompt) | Anna | Consistent with `sinä` register (prefer over `Syötä`) |
| Consistency | Eheys | Forbid `Yhtenäisyys` |
| Mount / Unmount | Liitä / Irrota liitos | Distinct from `Unlink` and `Detach` |
| Unlink (repository) | Poista yhteys | Removes repository from Vorta; distinct from `Unmount` (`Irrota liitos`) and `Detach` (`Irrota profiilista`) |
| Detach (repository) | Irrota profiilista | Disconnects repository from current profile while keeping it for others |
| Extract | Pura | |
| Password / Passphrase | Salasana / Salauslause | |
| Keychain / Password manager | Järjestelmän avainnippu / Salasanojen hallintaohjelma | Avoid `salasanahallinnan sovellus` / `salasanahallintasovellus` |
| System tray | Ilmoitusalue | |
| Profile | Profiili | |
| Schedule | Ajastus | |
| Source | Lähde | |
| Exclude | Ohita / Poissulkeminen | Verb / noun |
| Shell Commands | Shell-komennot | Hyphenated foreign compound |
| Full Disk Access | Täysi levyn käyttöoikeus | macOS permission name; inflect naturally in prose (`täyden levyn käyttöoikeuden`, `täyttä levyn käyttöoikeutta`) |
| Metered network / connection | Käytön mukaan laskutettava verkko / yhteys | |
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
| 2026-11-24 | Backup (process vs artifact) | Varmuuskopiointi / Varmuuskopio | Distinguish the backup operation from the resulting backup artifact |
| 2026-11-24 | Folder / Directory | Kansio | Standard modern Finnish UI term; avoids mixing `Kansio` and `Hakemisto` |
| 2026-11-24 | Diff | Erot | Concise UI label consistent with `ArchiveTab`; avoids `Eroavaisuudet` |
| 2026-11-24 | Cancel | Peru | Standard Finnish UI button label; keeps `Perutaanko` consistent |
| 2026-11-24 | Rename | Nimeä uudelleen | Idiomatic Finnish verb phrase; avoids calque `Uudelleennimeä` |
| 2026-11-24 | Enter | Anna | Natural Finnish prompt verb consistent across dialogs |
| 2026-11-24 | Consistency | Eheys | Standard computing term for data integrity/consistency; forbids `Yhtenäisyys` |
| 2026-11-24 | Shell Commands | Shell-komennot | Follows Finnish hyphenated foreign compound rule |
| 2026-11-24 | Full Disk Access | Täysi levyn käyttöoikeus | Matches macOS Finnish localization and unifies `VortaApp` + `settings` |
| 2026-11-24 | Metered network / connection | Käytön mukaan laskutettava verkko / yhteys | Standard Finnish OS terminology for metered connections |
| 2026-11-24 | Unmount / Unlink / Detach | Irrota liitos / Poista yhteys / Irrota profiilista | Three-way distinction between filesystem unmount, removing a repo from Vorta, and detaching from one profile |
