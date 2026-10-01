# Test the live read API

## 1. Provision the trial key

From this repository in PowerShell:

```powershell
python .\skills\voidhub-cp-coach\scripts\setup_access.py
```

This prints only the token file path and SHA-256 digest. On Windows, the dedicated
credentials directory grants access to the current user and SYSTEM, with parent
inheritance removed. On POSIX the directory/file modes are 0700/0600. The raw
key stays in the user's private application-data directory, outside this repo.
Running again reuses the existing key; `--rotate` explicitly replaces it.

Append the digest to `COACH_API_KEY_HASHES` in VoidHub's hosting variables (keep
other installation digests), then restart all web workers. The server requires
working Redis, correctly trusted HTTPS termination and actual client IPs. A
push alone does not enable the API. Remove the old digest when rotating.

## 2. Load the secret without displaying it

```powershell
$credentialPath = Join-Path $env:LOCALAPPDATA 'VoidHubCoach\credentials\trial.token'
$env:VOIDHUB_COACH_API_KEY = [IO.File]::ReadAllText($credentialPath).Trim()
```

Never run Get-Content on the secret without assigning its output. Never paste
the secret in chat, GitHub or request examples. Redact Authorization in proxy/APM.

## 3. Search and fetch a real statement

```powershell
python .\skills\voidhub-cp-coach\scripts\archive_client.py search --state-dir .\voidhub-coach-data --limit 5 --output .\voidhub-coach-data\search.json
$search = Get-Content .\voidhub-coach-data\search.json -Raw | ConvertFrom-Json
$problemId = $search.items[0].id
python .\skills\voidhub-cp-coach\scripts\archive_client.py problem --state-dir .\voidhub-coach-data --id $problemId --output .\voidhub-coach-data\problem.json
```

An empty search is a real result; do not run the second command without a
returned ID. Inspect public problem.json and open its canonical URL. Compare
contest/name, formulas, image references, resource limits and sample line breaks.
API error 503/api_disabled means the server digest is not enabled, not that the
skill can fabricate a substitute. 401 means key rejection. 429 requires waiting.

## Optional requests example

For your own Python environment with requests installed:

```python
import os
import requests

req = requests.post(
    'https://voidhub.co/api/coach/v1/search',
    headers={'Authorization': 'Bearer ' + os.environ['VOIDHUB_COACH_API_KEY']},
    json={'difficulty_min': 900, 'difficulty_max': 1300, 'limit': 5},
    timeout=(5, 15),
    allow_redirects=False,
)
if req.status_code != 200:
    raise RuntimeError(f'API returned {req.status_code}; retry-after={req.headers.get("Retry-After")}')
data = req.json()
print(data)  # Public metadata only; never print request headers.
```

Use the skill's bundled client for bounded download/schema validation and pacing.
