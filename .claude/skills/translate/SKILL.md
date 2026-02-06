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

1. Read each .ts file in `src/vorta/i18n/ts/`
2. Count strings with `<translation type="unfinished"/>` (untranslated)
3. Count total `<message>` elements
4. Display a summary table:

```
Language    Untranslated    Total    Completion
de          12              450      97.3%
es          45              450      90.0%
...
```

---

## Command: `/translate review <lang>`

Generate or review translations for a specific language.

### Step 1: Parse the .ts file

Read `src/vorta/i18n/ts/vorta.<lang>.ts` and identify:
- Untranslated strings: `<translation type="unfinished"/>`
- Existing translations for context

### Step 2: Understand the .ts file format

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

**Special case - comment-based strings:**
```xml
<message>
    <source>messages</source>
    <comment>Please unlock your system password manager</comment>  <!-- THIS is the text to translate -->
    <translation type="unfinished"/>
</message>
```
When `<source>` is `messages`, `settings`, or `app`, the actual translatable text is in `<comment>`.

### Step 3: Generate translations with context

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

### Step 4: Update the .ts file

Replace `<translation type="unfinished"/>` with `<translation>Translated text</translation>`

**Important XML rules:**
- Preserve exact XML structure and indentation
- Escape XML entities: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`
- Preserve newlines in multi-line strings
- Keep `type="unfinished"` attribute only for strings you cannot confidently translate

### Step 5: Show summary

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
- Use formal/polite form appropriate for the language (e.g., "Sie" in German)
- Preserve keyboard shortcuts (e.g., "&File" where & indicates Alt+F)
- Keep URLs unchanged
- Preserve formatting placeholders (`{0}`, `%s`, `%d`, etc.)

### DON'T:
- Translate proper nouns: Borg, BorgBackup, Vorta, SSH, URL
- Change technical identifiers or paths
- Add or remove punctuation unnecessarily
- Translate placeholder text that's clearly an example (e.g., email@example.com)

### RTL Languages (Arabic):
- Text direction is handled by Qt automatically
- Ensure no hardcoded LTR punctuation breaks the flow
- Test UI layout after translation

---

## Testing Translations

After updating translations:

1. Compile: `make translations-to-qm`
2. Run the app: `uv run vorta`
3. Go to **Misc** tab → **Language** dropdown
4. Select the language and restart the app
5. Verify translations appear correctly in the UI

---

## Workflow Example

```bash
# 1. Check translation status
/translate missing

# 2. Review and translate German
/translate review de

# 3. Compile translations
/translate compile

# 4. Test in app
uv run vorta
```

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
| Passphrase | Encryption password | Security credential |
| Profile | Backup configuration | Group of settings |
| Schedule | Backup timing | When to run backups |
| Source | Files to back up | Folders/files to include |
| Exclude | Files to skip | Patterns to ignore |

---

## Adding a New Language

1. Copy an existing .ts file as template:
   ```bash
   cp src/vorta/i18n/ts/vorta.de.ts src/vorta/i18n/ts/vorta.XX.ts
   ```

2. Update the language attribute in the new file:
   ```xml
   <TS version="2.1" language="XX">
   ```

3. Clear all translations (set to `type="unfinished"`)

4. Run `/translate review XX` to generate translations

5. Compile with `/translate compile`

6. Test in the application
