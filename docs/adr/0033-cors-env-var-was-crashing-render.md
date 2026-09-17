# 33. `CORS_ALLOW_ORIGINS` was crash-looping the Render deploy

Date: 2026-09-17

## Status

Accepted.

## Context

The user's first real Render deploy of `docs/adr/0031-*.md`'s image
crash-looped on boot:

```
pydantic_settings.exceptions.SettingsError: error parsing value for
field "cors_allow_origins" from source "EnvSettingsSource"
...
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

`Settings.cors_allow_origins` was typed `list[str]`. pydantic-settings
treats any `list`/`dict`/`tuple`-typed field as "complex" and
unconditionally JSON-decodes its env var **inside its own env-source
machinery** (`EnvSettingsSource.prepare_field_value` →
`decode_complex_value`) — before the value ever reaches this class's
own validators. A `mode="before"` `field_validator` cannot intercept or
recover from this; it never runs. `docs/DEPLOYMENT.md`'s own instructions
made this worse, not better: it told the user to leave `CORS_ALLOW_ORIGINS`
unset until a first deploy revealed the real Vercel URL, and an
empty/unset value hits this exact same crash (`json.loads("")` also
raises `JSONDecodeError`). The guide that was supposed to make this
deploy real walked the user straight into the one failure mode it never
tested for — because local verification (`docs/adr/0031-*.md`) ran the
container with env vars set directly, never through an empty or
plain-string value the way a person actually fills in a dashboard.

## Decision

`cors_allow_origins` is now typed `str`, not `list[str]` — removing it
from pydantic-settings' complex-type path entirely, so it is never
auto-JSON-decoded and can never crash boot regardless of what's in the
env var. A new `cors_allow_origins_list` property does the actual
parsing, by hand, accepting three real inputs:

- The originally-documented JSON array (`["https://a.com","https://b.com"]`) —
  kept working, not a breaking change for anyone who already used it.
- A plain comma-separated string (`https://a.com` or
  `https://a.com,https://b.com`) — what a person actually types into a
  host's env-var box, with no brackets or quotes to get wrong.
- Blank/unset — this field's own default (`http://localhost:3000` and
  its two Next.js fallback ports), not an empty allowlist that would
  silently block every real request with no explanation.

`coolblock_api.main`'s `CORSMiddleware` now reads
`cors_allow_origins_list`. Verified directly against all four real
inputs (bare URL, empty string, JSON array, comma-separated) plus the
existing local `.env`'s own `CORS_ALLOW_ORIGINS=*` — none crash, all
parse to the expected list.

## Consequences

- Nothing this app's own settings expose as `list[str]`-from-env can
  crash boot this way again, *if* the same fix is applied — this was
  the only such field today, but the pattern (declare as `str`, parse in
  a property) is the one to reuse if another list-shaped setting is
  added later.
- `docs/DEPLOYMENT.md` updated to recommend the plain form, and to say
  explicitly that leaving it unset is safe (falls back, doesn't crash),
  removing the sequencing trap the original wording created.
- This was found from a live failure, not local testing catching it
  first — `docs/adr/0031-*.md`'s "built and ran it locally" verification
  used env vars set directly in a `docker run` command, which never
  exercises the empty/malformed-string paths a real dashboard produces.
  Worth remembering next time: local verification of a config value
  needs to include the values a human would actually type, not just the
  values a script sets correctly.
