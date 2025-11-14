# QiboDB Client API (Run ID Version)

The **QiboDB Client** is a lightweight Python interface for interacting with the QiboDB server.  
This version uses **runID** instead of experimentID.

---

## 🧭 Overview

Each record in QiboDB contains:

- `hashID` — identifier linking related results  
- `name` — name for a specific result/dataset  
- `runID` — optional run identifier  
- `notes` — optional metadata  
- A binary archive (ZIP) containing data files  

The client library handles communication, authentication, ZIP creation, and decoding.

---

## ⚙️ Installation

Install dependencies:

```bash
pip install requests
```

Ensure the `client/` directory is importable in your Python project.

---

## 🔑 Authentication

The server requires an API token. You may set it:

### Option 1 — Pass explicitly  
```python
results_upload(..., api_token="your_token")
```

### Option 2 — Environment variable
```bash
export QIBODB_API_TOKEN="your_token"
```

---

## 🌍 Server URL Configuration

Either pass a server URL:

```python
results_list("abc123", server_url="https://your.server")
```

Or set it globally:

```bash
export QIBODB_SERVER_URL="https://your.server"
```

---

## 🧩 Client API

### 1. `results_upload()`

Uploads a ZIP archive containing the provided files.

```python
from client.client import results_upload

results_upload(
    hashID="abc123",
    name="run1",
    notes="baseline measurement",
    runID="run_001",                 # optional
    files=["output.csv", "log.txt"], # file paths
    server_url="https://your.server",
    api_token="your_token"
)
```

**Returns:**
```json
{
  "status": "ok",
  "id": 31,
  "created_at": "2025-11-01 10:22:01",
  "run_id": "run_001"
}
```

---

### 2. `results_list()`

Lists all results for a given `hashID`.

```python
from client.client import results_list

items = results_list("abc123")
print(items)
```

**Example output:**

```json
[
  {
    "name": "run1",
    "run_id": "run_001",
    "notes": "baseline test",
    "created_at": "2025-11-01 10:22:01"
  }
]
```

---

### 3. `results_download()`

Downloads the most recent result for `(hashID, name)`.  
Optionally restrict by `runID`.

```python
from client.client import results_download

notes, filename, created_at, run_id, data = results_download(
    hashID="abc123",
    name="run1",
    runID="run_001"    # optional
)

with open(filename, "wb") as f:
    f.write(data)
```

**Returns tuple:**
```
(notes, filename, created_at, run_id, data_bytes)
```

---

## 🧰 Example Workflow

```python
from client.client import results_upload, results_list, results_download

# Upload
results_upload(
    hashID="qkd001",
    name="alignment_1",
    notes="test alignment",
    runID="runA",
    files=["data.csv", "config.yml"]
)

# List
print(results_list("qkd001"))

# Download
notes, fname, created_at, rid, blob = results_download(
    "qkd001",
    "alignment_1",
    runID="runA"
)

with open(fname, "wb") as f:
    f.write(blob)
```

---

## 🛡️ Error Handling

All functions raise `requests.HTTPError` on failures.

```python
try:
    results_download("abc123", "missing")
except requests.HTTPError as e:
    print("Error:", e)
```

---

## 🧾 License

MIT License © 2025  
Developed by **Tanvirul Zaman**
