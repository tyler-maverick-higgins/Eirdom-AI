# Platinum & Bramble — Validation Gate & Worldbuilder: Install & Use

This covers the three pieces that make up the gated Worldbuilder:

1. **`gate.py`** — the deterministic structural validator (no model, no network).
2. **`gate_loop.py`** — the standalone retry loop: generates a note with your
   local model, validates it, and retries until it passes. Run from a terminal.
3. **`worldbuilder_gated_function.py`** — the same loop wrapped as an Open WebUI
   *Function (Pipe)*, so "Worldbuilder (Gated)" appears as a model in the chat
   dropdown and the gate runs invisibly behind each message.

All three share one set of schemas. The standalone loop *imports* `gate.py`. The
Open WebUI Function *embeds a copy* of the validator (Open WebUI sandboxes
Functions and can't import files from disk). **If you change a template, update
the `SCHEMAS` dict in BOTH `gate.py` and `worldbuilder_gated_function.py`.**

---

## Part 1 — The standalone loop (`gate_loop.py`)

Use this first. It's easier to debug than the Open WebUI Function, and proves
your model + gate work together before you wire anything into the UI.

### Prerequisites

- **Python 3.9+** — check with `python --version`.
- **Ollama running** with your model pulled:
  ```
  ollama list
  ```
  If your model isn't listed, pull it (use your actual tag):
  ```
  ollama pull qwen3:30b-a3b
  ```
- `gate.py` and `gate_loop.py` in the **same folder** (e.g. `scripts/`).
- No third-party libraries are required — the loop uses Python's standard
  library for HTTP. (`requests` is optional and not needed here.)

### Configure

Open `gate_loop.py` and edit the two lines just under the imports:

```python
OLLAMA_URL = "http://localhost:11434"   # where Ollama is listening
MODEL_NAME = "qwen3:30b-a3b"            # your exact model tag from `ollama list`
```

### Run

```bash
# Generate a region note:
python gate_loop.py region "The Marsh of Knor"

# With guidance for the model:
python gate_loop.py npc "Old Hedda" --brief "the innkeeper's wary mother"

# Save to a file ONLY if it passes the gate:
python gate_loop.py settlement "Greywater" --out ./Greywater.md

# Allow more retries (default is 4):
python gate_loop.py faction "The Salt Wardens" --max-tries 6
```

### What you'll see

The loop prints progress to the terminal (`attempt 1/4: generating…`), then:

- **PASS** — the complete, valid note, followed by a **"CANON TO APPROVE"** list
  of every wikilink the model referenced. This is the human step the gate can't
  do: confirm the real links, reject or rename invented canon you don't want.
  With `--out`, the note is written to the file (only on pass).
- **FAIL** — if it couldn't pass within max tries, it prints the last attempt
  plus the remaining errors, and does **not** write the file.

### How it works (one paragraph)

The loop builds a system prompt that embeds the *exact* required sections and
allowed frontmatter keys for the note type (pulled straight from `gate.py`'s
schema, so the model is told precisely what the gate will check). It sends that
to the model, extracts the note from the reply (stripping any ```` ``` ```` fences
or chatter), and runs `gate.validate()`. On failure, it appends the model's
attempt plus the gate's exact error list back into the conversation and asks for
a corrected note — looping until the gate passes or `--max-tries` is hit.
Structure is enforced automatically; canon truth is surfaced for you to approve.

---

## Part 2 — The Open WebUI Function (`worldbuilder_gated_function.py`)

This makes a **"Worldbuilder (Gated)"** entry in your model dropdown. You (or
Irina) pick it and chat normally; the generate-validate-retry loop runs behind
each message.

### Install

1. Open Open WebUI in your browser and sign in as an **admin** (Functions are an
   admin feature).
2. Go to **Admin Panel → Functions** (in current builds:
   **Settings / Workspace → Functions**, depending on version).
3. Click **`+`** (New Function).
4. Paste the entire contents of `worldbuilder_gated_function.py` into the editor.
5. Give it a name (e.g. *Worldbuilder Gated*) and **Save**.
6. **Enable** the function with its toggle.

> If saving complains about `requests` or `pydantic`: both ship with Open WebUI's
> backend, so no install is normally needed. If your deployment is unusual, make
> sure the backend environment has them.

### Configure (Valves)

After saving, click the function's **gear / Valves** icon and set:

- **OLLAMA_URL** — `http://localhost:11434` (or wherever Ollama runs relative to
  the Open WebUI backend; if Open WebUI is in Docker, `localhost` may need to be
  `http://host.docker.internal:11434` or your host's LAN IP).
- **MODEL_NAME** — your exact tag, e.g. `qwen3:30b-a3b`.
- **MAX_TRIES** — default `4`.
- **TEMPERATURE** — default `0.4`.

Valves are editable in the UI, so you don't have to touch the code to retarget
the model.

### Use

In a new chat, pick **Worldbuilder (Gated)** from the model dropdown, then type a
request in `type: name` form:

```
region: The Marsh of Knor
```
```
npc: Old Hedda — the innkeeper's wary mother
```
```
settlement: Greywater - a fishing village on the cold river
```

(Use an em-dash `—` or ` - ` to add a brief after the name.) Anything that isn't
a recognized `type:` prompt gets a short help message listing the valid types.

The reply contains the validated note in a fenced ```` ```markdown ```` block,
a pass/attempts header, and — on success — the **"Canon to approve"** list. Copy
the note into your vault; review the canon list before you commit invented links.

### Docker note

If Open WebUI runs in Docker and Ollama runs on the host, `http://localhost`
inside the container points at the container, not your host. Use
`http://host.docker.internal:11434` (Docker Desktop) or the host's LAN IP, and
make sure Ollama is bound to `0.0.0.0` not just `127.0.0.1`.

---

## Part 3 — Keeping the two gates in sync

There are two copies of the validator schema on purpose (one importable, one
embedded for the sandbox). They are currently identical. When you change a
template:

1. Update the matching entry in `gate.py`'s `SCHEMAS` (and `TAG_REQUIRED_TYPES`
   / `ALWAYS_NONEMPTY_BY_TYPE` if relevant).
2. Paste the same change into `worldbuilder_gated_function.py`'s `SCHEMAS`.
3. Sanity check they match — a quick way:
   ```bash
   python - <<'PY'
   import gate, importlib.util
   s = importlib.util.spec_from_file_location("wbf", "worldbuilder_gated_function.py")
   m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
   print("IDENTICAL" if gate.SCHEMAS == m.SCHEMAS else "MISMATCH — fix before use")
   PY
   ```

---

## What the gate checks (both copies)

- Frontmatter is a **closed set** — only template-defined keys, no extras.
- **No `summary:` key in frontmatter** — the Summary is a body `## Summary`.
- All **required `##` sections** present (the Templater title artifact
  `## <% tp.file.title %>` is ignored; extra sections are allowed).
- `type:` correct and `name:` (or `session_number:`) non-empty.
- `created:` is **blank or a real past date** (YYYY-MM-DD) — never future, never
  fabricated.
- **Balanced `GM-ONLY:START/END`** sentinels.
- The `bible` type must carry a `campaign-bible` or `gm-prep` tag (guardrail
  against using the loose type for in-world canon).

Forward-reference wikilinks (to `proposed` entities or open `[[Folder/]]` stubs)
are **allowed** — link resolution is a separate soft check
(`python gate.py <dir> --check-links`), never a hard failure.

## What the gate does NOT check

Truth. Invented fiction has no ground truth, so the gate validates *structure*
only. Canon approval stays human — that's what the "Canon to approve" list is
for. Keep that step; it's the price of fiction generation, not a flaw to remove.
