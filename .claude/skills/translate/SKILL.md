---
name: translate
description: Manage Vorta translations using AI. Commands - /translate missing (report untranslated counts), /translate review <lang> (generate translations), /translate compile (build .qm files).
---

# Vorta Translation Skill

Manage translations for the Vorta backup application. This skill replaces the previous Transifex-based workflow with AI-powered translations.

## Commands

### `/translate missing`
Report the count of untranslated strings for each language.

### `/translate review <lang>`
Review and generate translations for a specific language (e.g., `de`, `es`, `fr`).

### `/translate compile`
Compile all .ts files to binary .qm format.

---

## File Locations

- **Source .ts files:** `src/vorta/i18n/ts/vorta.<lang>.ts`
- **Compiled .qm files:** `src/vorta/i18n/qm/vorta.<lang>.qm`

## Supported Languages

| Code | Language |
|------|----------|
| ar | Arabic (RTL) |
| cs | Czech |
| de | German |
| es | Spanish |
| fi | Finnish |
| fr | French |
| gl | Galician |
| it | Italian |
| nl | Dutch |
| ru | Russian |
| sk | Slovak |
| sv | Swedish |

---

## Command: `/translate missing`

1. Refresh the message set first, so the counts reflect the current code:
   ```bash
   make translations-from-source
   ```
   This runs `pylupdate6` over `src/vorta` and merges the extracted strings into
   **every** `vorta.*.ts` at once. Existing translations are preserved, new strings
   arrive as `type="unfinished"`, and strings that vanished from the code are kept as
   `type="vanished"`. It is idempotent — a second run is a no-op.
2. Read each .ts file in `src/vorta/i18n/ts/`
3. Count strings where `<translation>` has attribute `type="unfinished"` (untranslated/unreviewed), ignoring `type="vanished"` entries. Note that `type="unfinished"` occurs in two XML forms:
   - Empty self-closing tags: `<translation type="unfinished" />` or `<translation type="unfinished"/>`
   - Heuristic pre-filled tags produced by `pylupdate6` when strings move across contexts: `<translation type="unfinished">Suggested text</translation>`
4. Count total live `<message>` elements (again ignoring `vanished`)
5. Display a summary table:

```
Language    Untranslated    Total    Completion
de          12              450      97.3%
es          45              450      90.0%
...
```

---

## Command: `/translate review <lang>`

Generate and review translations for a specific language (`/translate translate <lang>` is an accepted alias).

### Step 1: Parse the .ts file

Read `src/vorta/i18n/ts/vorta.<lang>.ts` and identify:
- Untranslated or unreviewed strings: any `<message>` whose `<translation>` has `type="unfinished"`, including both empty `<translation type="unfinished" />` (`<translation type="unfinished"/>`) and heuristic pre-filled `<translation type="unfinished">Suggested text</translation>` (which must be verified against the new context and glossary before removing `type="unfinished"`)
- Existing translations for context

### Step 2: Load glossary and scan for consistency

**2a. Load glossary:** Read `glossaries/<lang>.md` (in this skill directory, e.g. `.agents/skills/translate/glossaries/<lang>.md`) if it exists. All terms and style rules in the glossary are mandatory — use them consistently.

**2b. Scan existing translations:** Before translating new strings, grep for key domain terms in already-translated strings to identify established conventions. Flag any conflicts with the glossary (e.g., a glossary says "Passwort" but existing translations use "Kennwort"), as well as register/orthography drift.

**2c. Resolve unknown terms:** If a source string contains a term not covered by the glossary, and the term is ambiguous or has multiple valid translations, ask the user which translation to use. Add the decision to the glossary file and its Decision Log.

### Step 3: Understand the .ts file format

```xml
<context>
    <name>AddProfileWindow</name>          <!-- UI component name -->
    <message>
        <location filename="views/profile.py" line="25"/>  <!-- Source location -->
        <source>Save</source>              <!-- English text to translate -->
        <translation>Speichern</translation>  <!-- Translated text -->
    </message>
</context>
```

The text to translate is always in `<source>`, and `<name>` is always the real
context — including for strings marked with `QT_TRANSLATE_NOOP` in the code, which
land under lowercase contexts like `messages`, `settings`, `utils` and `app`:

```xml
<context>
    <name>settings</name>
    <message>
        <location filename="../../store/settings.py" line="51"/>
        <source>Add Vorta to the systems autostart list</source>
        <translation type="unfinished"/>
    </message>
</context>
```

Older files used a `<source>settings</source>` + `<comment>actual text</comment>`
shape produced by `pylupdate5 -translate-function`. That shape is gone; if you ever
meet it in an archived file, the `<comment>` holds the text and the `<source>` holds
the context.

**Obsolete entries:** messages whose source string no longer exists in the code are
kept with `<translation type="vanished">`. Leave them alone — they are what lets a
future rewording recover its old translation. Do not count them as untranslated.


**Delegated `.tr()` helper convention:** Non-`QObject` UI and scheduler helper classes (`ArchiveDelete`, `ArchiveDiff`, `ArchiveExtract`, `ArchiveMaintenance`, `ArchiveMount`, `ArchiveRename`, `SchedulerExecution`, `SchedulerTimers`, etc.) define `def tr(self, *args, **kwargs): return translate(self.__class__.__name__, *args, **kwargs)` and call `self.tr(...)` (never `self.tab.tr(...)` or `self.scheduler.tr(...)`) so `pylupdate6`'s class-based `<context><name>` matches runtime lookup.
### Step 4: Generate translations with context

For each untranslated string, consider:

1. **UI Context** (`<name>` element):
   - `RepoTab`, `ArchiveTab`, `SourceTab` = main tabs
   - `AddRepoWindow`, `AddProfileWindow` = dialog windows
   - `MainWindow` = main application window

2. **Source Location** (`<location>` element):
   - Files in `views/` = UI text
   - Files in `borg/` = backup operation messages
   - Files in `store/` = settings descriptions

3. **Application Domain:**
   - Vorta is a backup GUI for BorgBackup
   - Key terms: repository, archive, backup, prune, mount, extract, passphrase

4. **Style Guide:**
   - **Capitalization:** English uses Title Case for buttons and menu items (`Save`, `Add Repository`), but **non-English languages must follow their own capitalization conventions** (typically sentence case for buttons, menus, tabs, column headers, dialog titles, and lowercase inside parenthetical qualifiers like `(recommended)`, `(legacy)`, plus German noun capitalization). Do not copy English Title Case into target languages.
   - **Labels with colons:** Keep the colon (`Repository:`, `Password:`) and follow target-language spacing rules (e.g., French requires a non-breaking space `\u00a0` before `:`, `?`, `!`, `;`).
   - **Descriptions/tooltips:** Sentence case; do not add or drop trailing periods relative to `<source>`, and preserve Unicode ellipses `…` (U+2026) on dialog-opening actions and progress messages (never replace `…` with ASCII `...`).
   - **Progress & status messages:** Keep voice consistent per language (typically impersonal nominal or passive forms — avoid mixing 1st-person progressive with impersonal forms, and never translate a status message like `Not running backup…` as an imperative command).
   - **Numeric boundaries:** Preserve exact inequality semantics (`at least N` means `>= N`, never "more than N"; `less than 65` means `<= 64`, never "max 65").
   - **Technical terms & proper nouns:** Keep proper nouns and Borg mode/CLI identifiers unchanged: `Borg`, `BorgBackup`, `Vorta`, `SSH`, `URL`, `macFUSE`, `GitHub` (prefer `GitHub` even if `<source>` writes `Github`), `BorgBase`, `Sparkle`, `KWallet`, `Repokey`, `Keyfile`, `umask 0277`, `rc 1`, `Wi-Fi` (prefer `Wi-Fi` over `Wifi`). Always capitalize `Borg` in prose even when `<source>` writes lowercase `borg`. For `repository` and other domain nouns, follow the per-language glossary.
   - **Qt Designer design-time placeholders:** `.ui` files contain sample/default strings overwritten at runtime (`Form`, `MainWindow`, `0.0`, `1.1.8`, `/usr/bin/borg`, `nyx2.local-2018-11-16T09:49:58 from November 16, 2018`). Keep technical/numeric placeholders verbatim; if translating `Form` or sample text, never confuse `Form` with `From`.
   - **Placeholders & syntax tokens:** Preserve all placeholder and syntax formats used in Vorta exactly:
     - **Qt plural (`numerus="yes"`):** `%n` inside `<numerusform>` elements matching the target language's Qt plural count and slot order:
       - 2 forms (`de`, `es`, `fi`, `fr`, `gl`, `it`, `nl`, `sv`): `[0]` singular (`n == 1`, or `0, 1` in `fr`), `[1]` plural.
       - 3 forms (`cs`, `sk`): `[0]` `n == 1`, `[1]` `n ∈ 2..4`, `[2]` `n == 0` or `n >= 5`.
       - 3 forms (`ru`): `[0]` `1, 21, 31…`, `[1]` `2–4, 22–24…`, `[2]` `0, 5–20, 25–30…`.
       - 6 forms (`ar`): `[0]` `n == 0`, `[1]` `n == 1`, `[2]` `n == 2`, `[3]` `3–10`, `[4]` `11–99`, `[5]` `100+`.
     - **Python printf:** `%s`, `%d`.
     - **Python `str.format` & archive-name template variables (`format_archive_name` in `src/vorta/utils.py`):** `{}`, `{0}`, `{1}`, `{size}`, `{path}`, `{repo_url}`, `{exit_code}`, `{method}`, `{hostname}`, `{fqdn}`, `{profile_id}`, `{profile_slug}`, `{now:%Y-%m-%d-%H%M%S}`, `{utc_now:...}`, `{user}` — NEVER translate variable names OR alter strftime format specifiers inside `{now:...}` (e.g., keep `%Y-%m-%d-%H%M%S` verbatim so archive names sort chronologically).
     - **Rich-text `format_richtext()` (`src/vorta/i18n/richtext.py`):** `%1`, `%2` (replaced in reverse numeric order with HTML `link()`, `bold()`, `italic()`, or `code()` spans — e.g., `italic('ssh')`, `italic(settings)`, `italic('borg create')`, `code('$repo_url, ...')`).
     - **Shell command examples (`ShellCommandsPage`):** Keep `$repo_url`, `$profile_name`, `$profile_slug`, `$returncode` verbatim AND keep ASCII double quotes `"..."` around `echo "..."` examples (never replace with typographic/curly quotes `‘…’` or single quotes `'...'`, which break shell syntax or variable expansion).
     - **Qt `QFileDialog` filters:** Keep ASCII `;;` separators and glob patterns verbatim (e.g., `JSON (*.json);;All files (*)` — never localize `;;` to `؛؛` or fullwidth characters).
   - **Link-text & rich-text grammar rule (`%1`/`%2` substitutions):** Standalone strings (`here`, `more`, `logs`, `documentation`, `Click here`, `Github`, `Full Disk Access`, `System Preferences > Security & Privacy`, `BorgBase`, `Settings`) are injected into `%1`/`%2` templates. Always check the surrounding `%1`/`%2` sentence in the same class/context (and cross-context references like `MainWindow::Settings`) so prepositions, articles, and grammatical case fit seamlessly without duplication (e.g., avoid `"från" + "här"` in Swedish or `"via" + "hier"` in Dutch). In case-inflected/agglutinative languages (`fi`, `cs`, `sk`, `ru`), attach a governing head noun or hyphenated compound when a nominative `%1`/`%2` token appears in an oblique case (e.g., `%1-palvelua`, `%2-välilehden`, `v nabídce %2`, `na karte %2`, `в разделе %2`).

### Step 5: Terminology and QA check

Before writing translations, cross-check all generated translations against the glossary and run these quality checks:
- No glossary violations (e.g., using "Kennwort" when the glossary specifies "Passwort")
- No untranslated live strings left without `type="unfinished"` (including stray English words like `Level`, `auto`, `default`, `Key` inside translated strings)
- No broken placeholders, altered `{now:...}` formats, localized `;;` filter separators, or curly quotes in shell `echo "..."` examples
- No stray leading/trailing whitespace or mismatched trailing colons/periods/ellipses compared to `<source>`
Fix any violations before proceeding.

### Step 6: Update the .ts file

Replace `<translation type="unfinished" />` (and verified `<translation type="unfinished">Suggested text</translation>`) with `<translation>Translated text</translation>`

**Important XML rules:**
- Preserve exact XML structure and indentation
- Escape XML entities: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`
- Preserve newlines in multi-line strings
- Keep `type="unfinished"` attribute only for strings you cannot confidently translate

### Step 7: Show summary

After making changes, display:
- Number of strings translated
- Any strings skipped (with reasons)
- Suggest running `/translate compile` to build .qm files

---

## Command: `/translate compile`

Compile .ts source files to binary .qm format:

```bash
make translations-to-qm
```

Or manually:
```bash
for f in src/vorta/i18n/ts/vorta.*.ts; do
    lrelease "$f" -qm "src/vorta/i18n/qm/$(basename "$f" .ts).qm"
done
```

---

## Translation Quality Guidelines

### DO:
- Maintain consistency with existing translations in the same file
- Use formal/informal tone based on the target language's conventions
- Preserve keyboard shortcuts (e.g., "&File" where & indicates Alt+F)
- Keep URLs unchanged
- Preserve all formatting placeholders (`%n`, `%s`, `%d`, `%1`, `%2`, `{}`, `{0}`, `{1}`, `{size}`, `{path}`, `{repo_url}`, `{exit_code}`, `{method}`, `{hostname}`, `{profile_slug}`, `{now:...}`, `$repo_url`, `$profile_name`, `$profile_slug`, `$returncode`) and ensure standalone link-text strings (`here`, `more`, `logs`, `documentation`, etc.) grammatically fit their surrounding `%1`/`%2` sentences

### DON'T:
- Translate proper nouns or Borg/CLI identifiers: `Borg`, `BorgBackup`, `Vorta`, `SSH`, `URL`, `macFUSE`, `GitHub`, `BorgBase`, `Sparkle`, `KWallet`, `Repokey`, `Keyfile`, `umask 0277`, `rc 1`
- Change technical identifiers, paths, strftime specifiers (`{now:%Y-%m-%d-%H%M%S}`), `QFileDialog` `;;` separators, or ASCII `"..."` quotes in shell `echo` examples
- Copy English Title Case into non-English UI labels, buttons, or parenthetical qualifiers
- Add or remove punctuation unnecessarily (preserve `…`, colons, and matching trailing periods)
- Translate placeholder text that's clearly a literal syntax example (e.g., `email@example.com`, or Borg `--keep-within` unit suffixes `24H, 1d, 52w, 12m, 1y` where `H`, `d`, `w`, `m`, `y` are literal CLI tokens)
- Translate based on code-internal names instead of actual UI labels (e.g., code says "Misc" but UI shows "Settings / About" — translate as "Settings")

### RTL Languages (Arabic):
- Text direction is handled by Qt automatically
- Use Arabic punctuation (`،`, `؟`) in prose, but keep ASCII `,`, `;`, `;;`, `"..."` inside CLI/code/`QFileDialog` syntax tokens
- Add a space between Arabic prefixes (`لـ`) and Latin tokens (`لـ Ed25519`), and avoid spaces before colons (`مفتاح SSH:`)
- Use Western Arabic digits (`0–9`) consistently
- Ensure no hardcoded LTR punctuation breaks the flow
- Test UI layout after translation

---

## Testing Translations

After updating translations:

1. Compile: `make translations-to-qm`
2. Run the app in the target language: `LANG=de_DE uv run vorta --foreground`
   (there is no in-app language picker; the locale comes from `LANG`, else the system)
3. Verify translations appear correctly in the UI

---

## Workflow Example

```bash
# 1. Pull new strings out of the code into every .ts file
make translations-from-source

# 2. Check translation status
/translate missing

# 3. Review and translate German
/translate review de

# 4. Compile translations
/translate compile

# 5. Test in app
uv run vorta
```

Step 1 is what keeps the .ts files in sync with the code — run it after any change
that adds, removes or rewords a `self.tr()`, `QT_TRANSLATE_NOOP()` or `.ui` string.
There is no `vorta.en.ts` any more; extraction writes straight into the locale files.

---

## Glossary of Common Terms

Maintain consistency with these translations:

| English | Context | Notes |
|---------|---------|-------|
| Repository | Borg repo | Often kept as "Repository" in many languages |
| Archive | Backup snapshot | Time-based backup point |
| Backup | Action/noun | The backup operation |
| Prune | Delete old archives | Technical term |
| Mount | Make archive browsable | Filesystem operation |
| Extract | Restore files | Copy files from archive |
| Passphrase | Password to unlock the borg key | Security credential |
| Profile | Backup configuration | Group of settings |
| Schedule | Backup timing | When to run backups |
| Source | Files to back up | Folders/files to include |
| Exclude | Files to skip | Patterns to ignore |

## Per-Language Glossaries

Per-language glossaries live in `glossaries/<lang>.md` (`.agents/skills/translate/glossaries/<lang>.md`). These document agreed-upon translations for domain-specific and ambiguous terms, as well as language-specific style rules (register, capitalization, punctuation, compound words, and plural slots). The terms in a glossary are **mandatory** — they must be used consistently in all translations for that language.

Each glossary contains:
- A **Terminology** table mapping English terms to the agreed translation
- A **Decision Log** recording when and why each term was chosen

Create a new glossary when a language is first reviewed. Update it whenever a new term decision is made.

---

## Adding a New Language

1. Create an empty catalog with the right language attribute:
   ```bash
   printf '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n<TS version="2.1" language="XX">\n</TS>\n' \
       > src/vorta/i18n/ts/vorta.XX.ts
   ```

2. Fill it with the current message set:
   ```bash
   make translations-from-source
   ```
   Every message arrives as `type="unfinished"`. Do not copy another locale's file as
   a template — that carries its translations over under the wrong language.

3. Add the language to the Supported Languages table above. Nothing else needs
   registering — `init_translations()` picks the catalog up from `i18n/qm/` by locale.

4. Run `/translate review XX` to generate translations

5. Compile with `/translate compile`

6. Test in the application
