# QiboDB Python Client — Tutorial & User Manual

This document is a step-by-step guide for using the **QiboDB Python client** (`client.py`) to upload and download:

- **Calibration bundles** (zipped from a calibration folder)
- **Experiment result bundles** (zipped from an experiment run folder)
- **“Best run” markers** (track which calibration/run pair is considered the best)

The client is a **thin HTTP wrapper** around a QiboDB server. It uses `requests` to call REST endpoints and stores optional defaults (server URL + token) in a local JSON config file.

---

## 1) What you need

### Python version
- Python 3.9+ is recommended.

### Dependencies
Install required libraries:

```bash
pip install requests tabulate
```

> `tabulate` is only used by the helper `print_table()` function; the rest of the client works without printing tables.

---

## 2) Get the client into your project

Place `client.py` somewhere importable (same folder as your script, or install it as part of your package).

Example project layout:

```
your_project/
  client.py
  run_upload.py
  data/
  calibrations/
```

Then import it:

```python
import client
```

---

## 3) Configure your server URL and token (recommended)

Most functions accept `server_url` and `api_token` directly, **but you can also persist defaults** so you don’t repeat them each call.

### 3.1 Persist defaults with `set_server()`

```python
import client

client.set_server(
    server_url="http://127.0.0.1:5050",
    api_token="YOUR_TOKEN_HERE"  # optional
)
```

What this does:
- Saves values to a config JSON file.
- Future calls can omit `server_url` and `api_token`.

### 3.2 Where the config is stored

The client looks for config files in this order (first readable wins):

1. Path pointed to by environment variable `QIBO_CLIENT_CONFIG`
2. `~/.qibo_client.json`
3. `./.qibo_client.json` (current working directory)

When writing config, it will:
- Write to `QIBO_CLIENT_CONFIG` if set
- Otherwise write to `~/.qibo_client.json`

Example config file:

```json
{
  "server_url": "http://127.0.0.1:5050",
  "api_token": "YOUR_TOKEN_HERE"
}
```

### 3.3 One-off overrides (no persistent config)

Every endpoint call supports:

- `server_url="..."`
- `api_token="..."`

Example:

```python
items = client.calibrations_list(server_url="http://example.com:5050", api_token="TOKEN")
```

---

## 4) Calibrations: upload, list, download

Calibrations are uploaded as a **ZIP archive** built from:

```
<calibrations_folder>/<hashID>/
```

### 4.1 Folder structure (required)

```
calibrations_folder/
  <hashID>/
    ... calibration files ...
```

- `hashID` is a string identifier (often a 40-character hash).

### 4.2 Upload one calibration folder: `calibrations_upload()`

```python
import client

resp = client.calibrations_upload(
    hashID="0123456789abcdef0123456789abcdef01234567",
    calibrations_folder="/path/to/calibrations_folder",
    notes="calibration params for telescope run 2026-02-02"
)

print(resp)
```

What happens:
1. Client checks that `<calibrations_folder>/<hashID>` exists and is a directory.
2. It zips the **contents of that folder recursively**.
3. Uploads to the server endpoint: `POST /calibrations/upload`
4. Returns the server’s JSON response.

Common errors:
- `FileNotFoundError`: the `<hashID>` folder doesn’t exist
- `NotADirectoryError`: path exists but isn’t a directory
- `requests.HTTPError`: server returned an error status (>= 400)

### 4.3 Upload all calibration subfolders: `upload_all_calibrations()`

This scans `calibrations_folder` and uploads **every subdirectory whose name is exactly 40 characters**.

```python
import client
client.upload_all_calibrations("/path/to/calibrations_folder")
```

Notes:
- It does **not** print a table by default (the print is commented out in the client).
- Only 40-character folder names are considered uploadable.

### 4.4 List recent calibrations: `calibrations_list()`

Returns metadata for the last 20 calibration uploads (newest first).

```python
import client

items = client.calibrations_list()
for it in items:
    print(it["hashID"], it["created_at"], it.get("notes"))
```

Returned item fields (typical):
- `id` (int)
- `hashID` (str)
- `notes` (str or None)
- `created_at` (str)
- `filename` (str)
- `size` (int) — stored ZIP size in bytes

### 4.5 Get the most recent calibration: `calibrations_get_latest()`

```python
import client

latest = client.calibrations_get_latest()
if latest:
    print("Latest:", latest["hashID"], latest["created_at"])
else:
    print("No calibrations exist on the server yet.")
```

### 4.6 Download and unzip a calibration: `calibrations_download()`

```python
import client

notes, filename, created_at, zip_bytes = client.calibrations_download(
    hashID="0123456789abcdef0123456789abcdef01234567",
    output_folder="/path/to/local_calibrations_cache"
)

print(notes, filename, created_at)
```

Download behavior:
- Target directory: `<output_folder>/<hashID>`
- If that directory **already exists**, the client **skips downloading** and returns:
  - `(None, "", "", b"")`

If it downloads:
1. Calls server endpoint: `POST /calibrations/download` with JSON `{"hashID": ...}`
2. Receives base64-encoded zip payload in JSON
3. Decodes it and unzips into `<output_folder>/<hashID>`

---

## 5) Results: upload, list, download

Experiment results are uploaded as a ZIP archive built from:

```
<data_folder>/<hashID>/<runID>/
```

### 5.1 Folder structure (required)

```
data_folder/
  <hashID>/
    <runID>/
      ... result files ...
```

- `hashID` is a group identifier (often 40 characters).
- `runID` identifies a specific run (in batch tools it expects 14 characters).

### 5.2 Upload one experiment run: `results_upload()`

```python
import client

resp = client.results_upload(
    hashID="0123456789abcdef0123456789abcdef01234567",
    runID="00000000000042",            # example runID (must be non-empty)
    data_folder="/path/to/data_folder",
    name="experiment_group",           # logical grouping label
    notes="benchmarking run 42"
)

print(resp)
```

What happens:
1. Client checks that `<data_folder>/<hashID>/<runID>` exists and is a directory.
2. It zips the directory recursively.
3. Uploads to `POST /results/upload`
4. Returns server JSON.

Required fields:
- `hashID` (non-empty)
- `runID` (non-empty)
- `data_folder` must exist and contain the run folder

### 5.3 Upload *all* experiment runs in a folder: `upload_all_experiment_runs()`

This batch uploader:
- Scans `data_folder` for subfolders with name length **40** → treated as `hashID`
- Inside each `hashID` folder, scans for run folders with name length **14**
- Extracts a numeric key from `runID` (first integer substring) and sorts runs by that number
- Uploads each run in ascending order

```python
import client

resp_list = client.upload_all_experiment_runs("/path/to/data_folder")

# Optional: show responses
for resp in resp_list:
    print(resp.get("hashID"), resp.get("run_id"), resp.get("created_at"), resp.get("status"))
```

Important details:
- If a `runID` folder name contains **no digits**, it is skipped.
- If a `runID` is fully numeric, it sorts by `int(runID)`.
- Otherwise it sorts by the first number found in the string (regex `\d+`).

### 5.4 List results for a hashID: `results_list()`

```python
import client

items = client.results_list(hashID="0123456789abcdef0123456789abcdef01234567")
for it in items:
    print(it["name"], it.get("run_id"), it["created_at"], it.get("notes"))
```

Returned item fields (typical):
- `name` (str)
- `run_id` (str or None)
- `notes` (str or None)
- `created_at` (str)

### 5.5 Download and unzip a result run: `results_download()`

```python
import client

notes, filename, created_at, run_id, zip_bytes = client.results_download(
    hashID="0123456789abcdef0123456789abcdef01234567",
    runID="00000000000042",
    name="experiment_group",      # must match the 'name' used at upload if server filters by it
    output_folder="/path/to/local_results_cache"
)

print(notes, filename, created_at, run_id)
```

Download behavior:
- Target directory: `<output_folder>/<hashID>/<runID>`
- If that directory **already exists**, the client **skips downloading** and returns:
  - `(None, "", "", None, b"")`

If it downloads:
1. Calls `POST /results/download` with JSON `{"hashID": ..., "name": ..., "runID": ...}`
2. Receives base64 ZIP in JSON
3. Decodes and unzips into `<output_folder>/<hashID>/<runID>`

---

## 6) Best runs: set and query

The “best run” feature lets you record which `(calibrationHashID, runID)` pair is currently considered the best.

### 6.1 Set the best run: `set_best_run()`

```python
import client

resp = client.set_best_run(
    calibrationHashID="0123456789abcdef0123456789abcdef01234567",
    runID="00000000000042"
)

print(resp)
```

Server endpoint: `POST /bestruns/set`

### 6.2 Get the latest best run: `get_best_run()`

```python
import client

cal_hash, run_id, created_at = client.get_best_run()
print("Best:", cal_hash, run_id, created_at)
```

Server endpoint: `GET /bestruns/get`

### 6.3 List the last N best runs: `get_best_n_runs(n)`

```python
import client

items = client.get_best_n_runs(5)
for cal_hash, run_id, created_at in items:
    print(cal_hash, run_id, created_at)
```

Server endpoint: `GET /bestruns/list?limit=n`

---

## 7) Helper utilities in the client

### 7.1 `unzip_bytes_to_folder(zip_bytes, target_folder)`
Unzips in-memory ZIP bytes into a destination folder.

This is used internally by `calibrations_download()` and `results_download()`.

### 7.2 `print_table(data)`
Pretty-prints a list of dicts using `tabulate`.

```python
import client
client.print_table([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
```

### 7.3 `test()`
Sanity check to confirm imports work:

```python
import client
client.test()  # prints: "import works!"
```

---

## 8) End-to-end workflow examples

### Example A — Upload calibration, upload run, mark best

```python
import client

client.set_server("http://127.0.0.1:5050", api_token="TOKEN")

cal_hash = "0123456789abcdef0123456789abcdef01234567"
run_id = "00000000000042"

client.calibrations_upload(cal_hash, "/data/calibrations", notes="v1 calibration")
client.results_upload(cal_hash, run_id, "/data/experiments", notes="run 42", name="experiment_group")

client.set_best_run(calibrationHashID=cal_hash, runID=run_id)
print("Best run set.")
```

### Example B — Pull latest calibration and its best run, then download both

```python
import client

latest = client.calibrations_get_latest()
if not latest:
    raise SystemExit("No calibrations exist on the server.")

cal_hash = latest["hashID"]

best_cal_hash, best_run_id, best_time = client.get_best_run()

# Download calibration
client.calibrations_download(best_cal_hash, output_folder="./cache/calibrations")

# Download result run
client.results_download(best_cal_hash, best_run_id, name="experiment_group", output_folder="./cache/results")

print("Downloaded calibration + best run data.")
```

---

## 9) Troubleshooting

### 9.1 “Upload failed (401/403)”
Likely authentication:
- Ensure `api_token` is correct
- Ensure the server expects a `Bearer` token
- If using `set_server()`, confirm `~/.qibo_client.json` contains the token you intended

### 9.2 “FileNotFoundError: ... folder not found”
For uploads:
- Calibration upload expects `<calibrations_folder>/<hashID>`
- Results upload expects `<data_folder>/<hashID>/<runID>`

### 9.3 Downloads silently skip
This is by design:
- If the target folder already exists locally, downloads return empty placeholders:
  - calibrations: `(None, "", "", b"")`
  - results: `(None, "", "", None, b"")`

Delete the local target folder if you want to force a fresh download.

### 9.4 Timeouts
The client uses timeouts up to:
- 60s for best-run endpoints
- 120s for list/latest
- 300s for upload/download

If you routinely hit timeouts, check server load, network latency, and archive size.

---

## 10) API endpoints used by the client

These are hard-coded in the client:

**Calibrations**
- `POST /calibrations/upload`
- `GET  /calibrations/list`
- `POST /calibrations/download`
- `GET  /calibrations/latest`

**Results**
- `POST /results/upload`
- `GET  /results/list?hashID=...`
- `POST /results/download`

**Best runs**
- `POST /bestruns/set`
- `GET  /bestruns/get`
- `GET  /bestruns/list?limit=n`

---

## Appendix: Quick reference

### Configuration
- `set_server(server_url, api_token=None)`
- Env var: `QIBO_CLIENT_CONFIG`
- Default config path: `~/.qibo_client.json`

### Calibrations
- `calibrations_upload(hashID, calibrations_folder, notes="...", server_url=None, api_token=None)`
- `upload_all_calibrations(calibrations_folder)`
- `calibrations_list(server_url=None, api_token=None)`
- `calibrations_download(hashID, output_folder, server_url=None, api_token=None)`
- `calibrations_get_latest(server_url=None, api_token=None)`

### Results
- `results_upload(hashID, runID, data_folder, name="experiment_group", notes="...", server_url=None, api_token=None)`
- `upload_all_experiment_runs(data_folder)`
- `results_list(hashID, server_url=None, api_token=None)`
- `results_download(hashID, runID, output_folder, name="experiment_group", server_url=None, api_token=None)`

### Best runs
- `set_best_run(calibrationHashID, runID, server_url=None, api_token=None)`
- `get_best_run(server_url=None, api_token=None)`
- `get_best_n_runs(n, server_url=None, api_token=None)`
