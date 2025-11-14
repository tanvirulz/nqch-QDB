import os
import io
import json
import base64
import zipfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import requests

CFG_PATHS = [
    Path(os.getenv("QIBO_CLIENT_CONFIG", "")) if os.getenv("QIBO_CLIENT_CONFIG") else None,
    Path.home() / ".qibo_client.json",
    Path.cwd() / ".qibo_client.json",
]
CFG_PATHS = [p for p in CFG_PATHS if p is not None]


def _read_cfg() -> dict:
    """Return the merged client configuration from the first readable config path.

    Search order:
      1) env var QIBO_CLIENT_CONFIG (if set)
      2) ~/.qibo_client.json
      3) ./ .qibo_client.json

    Returns:
        dict: Parsed JSON configuration or {} if not found.
    """
    for p in CFG_PATHS:
        try:
            if p.exists():
                with open(p, "r") as f:
                    return json.load(f)
        except Exception:
            continue
    return {}


def _write_cfg(data: dict) -> None:
    """Write client configuration to a persistent file.

    Target path:
      - If QIBO_CLIENT_CONFIG is set, write there.
      - Otherwise, write to ~/.qibo_client.json

    Args:
        data: Configuration dictionary to write.
    """
    target = None
    if os.getenv("QIBO_CLIENT_CONFIG"):
        target = Path(os.getenv("QIBO_CLIENT_CONFIG"))
    else:
        target = Path.home() / ".qibo_client.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w") as f:
        json.dump(data, f, indent=2)


def set_server(server_url: str, api_token: Optional[str] = None) -> None:
    """Persist the default server URL and optional API token for this client.

    The values are saved to a JSON config file so that subsequent function calls
    can omit the `server_url` and `api_token` parameters.

    Args:
        server_url: Base URL of the server (e.g., "http://127.0.0.1:5050").
        api_token: Optional bearer token for Authorization header.
    """
    data = _read_cfg()
    data["server_url"] = server_url.rstrip("/")
    if api_token is not None:
        data["api_token"] = api_token
    _write_cfg(data)


def _get_defaults(server_url: Optional[str], api_token: Optional[str]) -> Tuple[str, Optional[str]]:
    """Resolve server_url and api_token from arguments or persisted config.

    Args:
        server_url: Optional explicit server URL.
        api_token: Optional explicit token.

    Returns:
        (server_url, api_token): Final values after consulting config.
    """
    cfg = _read_cfg()
    return (
        server_url.rstrip("/") if server_url else cfg.get("server_url", "http://127.0.0.1:5050"),
        api_token if api_token is not None else cfg.get("api_token")
    )


def _auth_headers(api_token: Optional[str]) -> dict:
    """Build Authorization header dict if a token is provided."""
    return {"Authorization": f"Bearer {api_token}"} if api_token else {}


def calibrations_upload(
    hashID: str,
    notes: str,
    files: List[str],
    server_url: Optional[str] = None,
    api_token: Optional[str] = None
) -> dict:
    """Create a ZIP from `files` and upload it as a calibration bundle.

    This bundles all given files into an in-memory ZIP archive and posts it to
    the server's `/calibrations/upload` endpoint along with `hashID` and `notes`.
    If `api_token` is provided (or saved in the client config), it is sent as
    a Bearer token.

    Args:
        hashID: Unique identifier for the calibration record.
        notes: Free-form notes associated with this upload.
        files: List of file paths to include in the ZIP archive.
        server_url: Base server URL; if omitted, uses saved config or defaults to
            "http://127.0.0.1:5000".
        api_token: Optional bearer token; if omitted, uses saved config.

    Raises:
        ValueError: If `files` is empty.
        FileNotFoundError: If any file path does not exist.
        requests.HTTPError: If the server returns an error response.

    Returns:
        dict: The server's JSON response, typically including:
            {"status": "ok", "id": <int>, "created_at": "<timestamp>"}.
    """
    server_url, api_token = _get_defaults(server_url, api_token)

    if not files:
        raise ValueError("Provide at least one file to upload.")
    for p in files:
        if not os.path.isfile(p):
            raise FileNotFoundError(f"File not found: {p}")

    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, arcname=os.path.basename(p))
    mem_zip.seek(0)

    files_payload = {"archive": ("calibration_bundle.zip", mem_zip.read(), "application/zip")}
    data_payload = {"hashID": hashID, "notes": notes or ""}
    url = server_url + "/calibrations/upload"
    resp = requests.post(url, data=data_payload, files=files_payload, headers=_auth_headers(api_token), timeout=300)
    if resp.status_code >= 400:
        raise requests.HTTPError(f"Upload failed ({resp.status_code}): {resp.text}")
    return resp.json()


def calibrations_list(server_url: Optional[str] = None, api_token: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return metadata for all calibration uploads (newest first).

    Args:
        server_url: Optional override for the server base URL.
        api_token: Optional override for the bearer token.

    Raises:
        requests.HTTPError: On server error.

    Returns:
        List of dicts with keys:
          - id (int)
          - hashID (str)
          - notes (str | None)
          - created_at (str)
          - filename (str)
          - size (int)  # size of stored ZIP in bytes
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/calibrations/list"
    r = requests.get(url, headers=_auth_headers(api_token), timeout=120)
    if r.status_code >= 400:
        raise requests.HTTPError(f"List failed ({r.status_code}): {r.text}")
    return r.json().get("items", [])


def calibrations_download(
    hashID: str,
    server_url: Optional[str] = None,
    api_token: Optional[str] = None
) -> Tuple[Optional[str], str, str, bytes]:
    """Download the latest calibration ZIP for a given `hashID`.

    Args:
        hashID: The calibration record identifier to fetch.
        server_url: Optional override for the server base URL.
        api_token: Optional override for the bearer token.

    Raises:
        requests.HTTPError: On server error or not found (4xx/5xx).

    Returns:
        Tuple of (notes, filename, data):
          - notes (Optional[str]): Notes saved with the record.
          - filename (str): Original ZIP filename returned by the server.
          - created_at (str): UTC date-time for calibration entry to the db
          - data (bytes): Raw ZIP file contents.
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/calibrations/download"
    r = requests.post(url, json={"hashID": hashID}, headers=_auth_headers(api_token), timeout=300)
    if r.status_code >= 400:
        raise requests.HTTPError(f"Download failed ({r.status_code}): {r.text}")
    payload = r.json()
    data = base64.b64decode(payload["data_b64"])
    return payload.get("notes"), payload["filename"], payload["created_at"], data


def calibrations_get_latest(
    server_url: Optional[str] = None,
    api_token: Optional[str] = None
) -> Dict[str, Any]:
    """Return metadata for the most recently uploaded calibration.

    Args:
        server_url: Optional override for the server base URL.
        api_token: Optional override for the bearer token.

    Raises:
        requests.HTTPError: On server error (>=400).

    Returns:
        Dict with keys:
          - hashID (str)
          - notes (str | None)
          - created_at (str)
        If no calibrations exist, returns {}.
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/calibrations/latest"
    r = requests.get(url, headers=_auth_headers(api_token), timeout=120)
    if r.status_code == 404:
        return {}
    if r.status_code >= 400:
        raise requests.HTTPError(f"Latest failed ({r.status_code}): {r.text}")
    return r.json()


def results_upload(
    hashID: str,
    name: str,
    notes: str,
    files: List[str],
    runID: Optional[str] = None,  # NEW
    server_url: Optional[str] = None,
    api_token: Optional[str] = None
) -> dict:
    """
    Create a ZIP from `files` and upload it as a "result" bundle.

    Args:
        hashID: Required. Identifier tying related results together.
        name: Required. Logical name/group for this particular result.
        notes: Free-form notes.
        files: List of file paths to include in the ZIP.
        runID: Optional string to tag this result with an run.
        server_url: Override server URL; otherwise use stored default.
        api_token: Override API token; otherwise use stored default.

    Returns:
        dict with keys like:
          {
            "status": "ok",
            "id": <int>,
            "created_at": "<timestamp>",
            "run_id": "<runID or null>"
          }
    """
    server_url, api_token = _get_defaults(server_url, api_token)

    if not files:
        raise ValueError("No files provided for upload.")

    # create in-memory zip
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            pth = Path(p)
            if not pth.exists():
                raise FileNotFoundError(f"File not found: {pth}")
            zf.write(pth, arcname=pth.name)
    mem.seek(0)
    zip_bytes = mem.read()

    url = server_url + "/results/upload"
    multipart = {
        "hashID": (None, hashID),
        "name": (None, name),
        "notes": (None, notes or ""),
        "archive": ("bundle.zip", zip_bytes, "application/zip"),
    }

    # NEW: only send runID if provided
    if runID is not None:
        multipart["runID"] = (None, runID)


    r = requests.post(
        url,
        files=multipart,
        headers=_auth_headers(api_token),
        timeout=300
    )
    if r.status_code >= 400:
        raise requests.HTTPError(f"Upload failed ({r.status_code}): {r.text}")
    return r.json()


def results_list(
    hashID: str,
    server_url: Optional[str] = None,
    api_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all results rows that share the same hashID.

    Returns a list of dicts, newest first:
      {
        "name": str,
        "run_id": Optional[str],  # NEW
        "notes": Optional[str],
        "created_at": str,
      }
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/results/list"

    r = requests.get(
        url,
        params={"hashID": hashID},
        headers=_auth_headers(api_token),
        timeout=120
    )
    if r.status_code >= 400:
        raise requests.HTTPError(f"Results list failed ({r.status_code}): {r.text}")
    return r.json().get("items", [])



def results_download(
    hashID: str,
    name: str,
    runID: Optional[str] = None,  # NEW
    server_url: Optional[str] = None,
    api_token: Optional[str] = None
) -> Tuple[Optional[str], str, str, Optional[str], bytes]:
    """
    Download the most recent result matching (hashID, name),
    and optionally filter by runID.

    Args:
        hashID: Required identifier group.
        name: Result name to download.
        runID: Optional filter; only match results from this run.
        server_url, api_token: Overrides.

    Returns:
        (
            notes,          # Optional[str]
            filename,       # str
            created_at,     # str
            run_id,         # Optional[str]
            data_bytes      # bytes
        )
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/results/download"

    payload = {"hashID": hashID, "name": name}
    if runID is not None:
        payload["runID"] = runID


    r = requests.post(
        url,
        json=payload,
        headers=_auth_headers(api_token),
        timeout=300
    )
    if r.status_code >= 400:
        raise requests.HTTPError(f"Download failed ({r.status_code}): {r.text}")

    payload = r.json()
    data_bytes = base64.b64decode(payload["data_b64"])

    return (
        payload.get("notes"),
        payload["filename"],
        payload["created_at"],
        payload.get("run_id"),
        data_bytes,
    )

def set_best_run(
    calibrationHashID: str,
    runID: str,
    server_url: Optional[str] = None,
    api_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mark a (calibrationHashID, runID) pair as the current best run.
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/bestruns/set"

    payload = {
        "calibrationHashID": calibrationHashID,
        "runID": runID,
    }

    r = requests.post(
        url,
        json=payload,
        headers=_auth_headers(api_token),
        timeout=60,
    )

    if r.status_code >= 400:
        raise requests.HTTPError(f"set_best_run failed ({r.status_code}): {r.text}")

    return r.json()

def get_best_run(
    server_url: Optional[str] = None,
    api_token: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Returns (calibration_hash_id, run_id, created_at)
    from the most recently inserted best run.
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/bestruns/get"

    r = requests.get(
        url,
        headers=_auth_headers(api_token),
        timeout=60,
    )

    if r.status_code >= 400:
        raise requests.HTTPError(f"get_best_run failed ({r.status_code}): {r.text}")

    payload = r.json()
    if payload.get("status") != "ok":
        raise requests.HTTPError(f"Server error: {payload}")

    return (
        payload["calibration_hash_id"],
        payload["run_id"],
        payload["created_at"],
    )

from typing import List, Tuple, Optional, Dict, Any
import requests
# ... existing imports & helpers ...


def get_best_n_runs(
    n: int,
    server_url: Optional[str] = None,
    api_token: Optional[str] = None,
) -> List[Tuple[str, str, str]]:
    """
    Get up to `n` previous best runs.

    Returns a list of tuples:
        [
          (calibration_hash_id, run_id, created_at),
          ...
        ]
    ordered from newest (most recent best run) to oldest,
    up to the requested limit `n`.
    """
    if n <= 0:
        raise ValueError("n must be a positive integer")

    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/bestruns/list"

    r = requests.get(
        url,
        params={"limit": n},
        headers=_auth_headers(api_token),
        timeout=60,
    )
    if r.status_code >= 400:
        raise requests.HTTPError(f"get_best_n_runs failed ({r.status_code}): {r.text}")

    payload = r.json()
    if payload.get("status") != "ok":
        raise requests.HTTPError(f"Server error in get_best_n_runs: {payload}")

    items = payload.get("items", [])
    result: List[Tuple[str, str, str]] = []
    for it in items:
        result.append(
            (
                str(it["calibration_hash_id"]),
                str(it["run_id"]),
                str(it["created_at"]),
            )
        )
    return result

def unpack(foldername: str, zipdata: bytes) -> None:
    """
    Create a folder named `foldername` and unzip the given zip bytes into it.

    Args:
        foldername: Path to the output folder.
        zipdata: Bytes representing a .zip archive.
    """
    # Ensure the folder exists
    os.makedirs(foldername, exist_ok=True)

    # Wrap the raw zipdata in a BytesIO and extract
    with zipfile.ZipFile(io.BytesIO(zipdata)) as zf:
        zf.extractall(path=foldername)
    
def test():
    print ("import works!")
    