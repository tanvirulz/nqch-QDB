# QIBO DB Server (Flask + SQLAlchemy) & Python Client

Store **calibrations** and **results** as zipped blobs in a SQLAlchemy-backed database (SQLite by default).  
Includes a Python client with convenience helpers and persistent client config.

## Requirements
- Python **3.10+**
- [Poetry](https://python-poetry.org/docs/#installation)

---

## Install & Run

> **Where to run `poetry`?**  
> If your `pyproject.toml` is in the **project root** (as in the zip I provided), run the commands **from the project root** (don’t `cd server`).  
> If you moved `pyproject.toml` inside `server/`, then run them from `server/`.

### 1) Install
```bash
poetry install
```

### 2) Start the server
```bash
poetry run qibodb-server --host 0.0.0.0 --port 5050 --api-token secret-token
```

**Environment variables (optional):**
```bash
# choose DB location/engine
export QIBO_DB_URI="sqlite:///qibo.db"

# set token via env instead of CLI
export QIBO_API_TOKEN="secret-token"

# turn on SQLAlchemy/Flask debug
export QIBO_DEBUG=1
```

**Token persistence:**  
If you pass `--api-token ...`, the server writes it to `~/.qibo_server.json` so you don’t have to set it every time.

---

## API (server)

All endpoints require the header `Authorization: Bearer <token>` if a token is configured.

### Health
- `GET /health` → `{"status":"ok"}`

### Calibrations
- `POST /calibrations/upload` (alias: `POST /upload`)  
  **form fields:** `hashID`, `notes`  
  **file:** `archive` (zip)  
  **returns:** `{"status":"ok","id":<int>,"created_at":"<ts>"}`

- `GET /calibrations/list`  
  **returns:** `{"items":[{id,hashID,notes,created_at,filename,size}]}`

- `GET /calibrations/latest`  
  **returns:** `{"hashID": "...", "notes": "...", "created_at": "..."}` (404 if none)

- `POST /calibrations/download`  
  **json/form:** `{"hashID":"..."}`  
  **returns:** `{"notes": "...", "filename": "...", "data_b64": "..."}`

### Results
- `POST /results/upload`  
  **form fields:** `hashID`, `name`, `notes`  
  **file:** `archive` (zip)  
  **returns:** `{"status":"ok","id":<int>,"created_at":"<ts>"}`

- `POST /results/download`  
  **json/form:** `{"hashID":"...","name":"..."}`  
  **returns:** `{"notes": "...", "filename": "...", "data_b64": "..."}` (latest match)

---

## Python Client

### Persistent client config
The client stores defaults in `~/.qibo_client.json` (or `QIBO_CLIENT_CONFIG` path).

```python
from client.client import set_server

# Save defaults so you can omit server_url/api_token later
set_server("http://127.0.0.1:5050", api_token="secret-token")
```

### Functions

```python
from typing import List, Tuple, Dict, Any, Optional
from client.client import (
    set_server,
    calibrations_upload,      
    calibrations_list,
    calibrations_download,
    calibrations_get_latest,
    results_upload,
    results_download,
)
```

#### set_server(server_url: str, api_token: Optional[str] = None) -> None
Persist default server URL and optional API token to the client config.

#### calibrations_upload(hashID: str, notes: str, files: List[str], server_url: Optional[str] = None, api_token: Optional[str] = None) -> dict
Create an in-memory **ZIP** from `files` and upload it as a **calibration**.

```python
resp = calibrations_upload(
    hashID="abc123",
    notes="first batch",
    files=["/path/a.txt", "/path/b.txt"]   # list-based!
)
```

**Returns** a JSON dict like:
```python
{"status":"ok","id":1,"created_at":"2025-09-11 12:34:56"}
```

#### calibrations_list(server_url: Optional[str] = None, api_token: Optional[str] = None) -> List[Dict[str, Any]]
Fetch metadata for all calibration uploads (newest first).

```python
items = calibrations_list()
```

#### calibrations_download(hashID: str, server_url: Optional[str] = None, api_token: Optional[str] = None) -> Tuple[Optional[str], str, bytes]
Download the **latest calibration zip** for `hashID`. Returns `(notes, filename, data_bytes)`.

```python
notes, fname, zip_bytes = calibrations_download("abc123")
```

#### calibrations_get_latest(server_url: Optional[str] = None, api_token: Optional[str] = None) -> Dict[str, Any]
Get metadata for the most recent calibration overall.

```python
latest = calibrations_get_latest()
# {"hashID": "...", "notes": "...", "created_at": "..."}  or {}
```

#### results_upload(hashID: str, name: str, notes: str, files: List[str], server_url: Optional[str] = None, api_token: Optional[str] = None) -> dict
Create an in-memory **ZIP** from `files` and upload to the **results** table.

```python
resp = results_upload(
    hashID="abc123",
    name="daily-check",
    notes="passed",
    files=["/tmp/out.csv"]
)
```

#### results_download(hashID: str, name: str, server_url: Optional[str] = None, api_token: Optional[str] = None) -> Tuple[Optional[str], str, bytes]
Download the **latest results zip** matching both `hashID` and `name`. Returns `(notes, filename, data_bytes)`.

```python
notes, fname, zip_bytes = results_download("abc123", "daily-check")
```

---

## Unpacking a ZIP returned by the client

```python
import os, io, zipfile

def unpack(foldername: str, zipdata: bytes) -> None:
    os.makedirs(foldername, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zipdata)) as zf:
        zf.extractall(foldername)

# Example:
notes, fname, data = calibrations_download("abc123")
unpack("./calib_abc123", data)
```

---

## cURL examples

```bash
# Upload a calibration
curl -X POST "http://127.0.0.1:5050/calibrations/upload"   -H "Authorization: Bearer secret-token"   -F "hashID=abc123"   -F "notes=first batch"   -F "archive=@/path/bundle.zip"

# Latest calibration meta
curl -X GET "http://127.0.0.1:5050/calibrations/latest"   -H "Authorization: Bearer secret-token"

# Download latest calibration for a hashID
curl -X POST "http://127.0.0.1:5050/calibrations/download"   -H "Authorization: Bearer secret-token"   -H "Content-Type: application/json"   -d '{"hashID":"abc123"}'
```

---

## Notes & Tips
- For large files, adjust `QIBO_MAX_UPLOAD_BYTES` on the server (defaults to **500MB**).
- SQLite is the default DB; switch to Postgres/MySQL by setting `QIBO_DB_URI` to a valid SQLAlchemy URI.
- Consider adding auth + rate limiting if you expose this server on a public network.

---

## License
MIT (or your choice).
