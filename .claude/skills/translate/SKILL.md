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
3. Count strings with `<translation type="unfinished"/>` (untranslated), ignoring
   `type="vanished"` entries
4. Count total live `<message>` elements (again ignoring `vanished`)
5. Display a summary table:

```
Language    Untranslated    Total    Completion
de          12              450      97.3%
es          45              450      90.0%
...
```

---

## Command: `/translate translate <lang>`

Generate translations for a specific language.

### Step 1: Parse the .ts file

Read `src/vorta/i18n/ts/vorta.<lang>.ts` and identify:
- Untranslated strings: `<translation type="unfinished"/>`
- Existing translations for context

### Step 2: Load glossary and scan for consistency

**2a. Load glossary:** Read `.claude/skills/translate/glossaries/<lang>.md` if it exists. All terms in the glossary are mandatory — use them consistently.

**2b. Scan existing translations:** Before translating new strings, grep for key domain terms in already-translated strings to identify established conventions. Flag any conflicts with the glossary (e.g., a glossary says "Passwort" but existing translations use "Kennwort").

**2c. Resolve unknown terms:** If a source string contains a term not covered by the glossary, and the term is ambiguous or has multiple valid translations, ask the user which translation to use (via `AskUserQuestion`). Add the decision to the glossary file and its Decision Log.

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
   - **Buttons:** Title Case in English (Save, Cancel, Add Repository)
   - **Labels with colons:** Keep the colon (Repository:, Password:)
   - **Menu items:** Title Case
   - **Descriptions/tooltips:** Sentence case
   - **Technical terms:** Keep English for: Borg, BorgBackup, SSH, repository (or use locale-appropriate term)
   - **Placeholders:** Preserve `{variable}` and `%s` patterns exactly

### Step 5: Terminology check

Before writing translations, cross-check all generated translations against the glossary. Verify that no inconsistent terms slipped through (e.g., using "Kennwort" when the glossary specifies "Passwort"). Fix any violations before proceeding.

### Step 6: Update the .ts file

Replace `<translation type="unfinished"/>` with `<translation>Translated text</translation>`

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
- Preserve formatting placeholders (`{0}`, `%s`, `%d`, etc.)

### DON'T:
- Translate proper nouns: Borg, BorgBackup, Vorta, SSH, URL
- Change technical identifiers or paths
- Add or remove punctuation unnecessarily
- Translate placeholder text that's clearly an example (e.g., email@example.com)
- Translate based on code-internal names instead of actual UI labels (e.g., code says "Misc" but UI shows "Settings / About" — translate as "Settings")

### RTL Languages (Arabic):
- Text direction is handled by Qt automatically
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

Per-language glossaries live in `.claude/skills/translate/glossaries/<lang>.md`. These document agreed-upon translations for domain-specific and ambiguous terms. The terms in a glossary are **mandatory** — they must be used consistently in all translations for that language.

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
