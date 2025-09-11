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
        server_url.rstrip("/") if server_url else cfg.get("server_url", "http://127.0.0.1:5000"),
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
) -> Tuple[Optional[str], str, bytes]:
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
          - data (bytes): Raw ZIP file contents.
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/calibrations/download"
    r = requests.post(url, json={"hashID": hashID}, headers=_auth_headers(api_token), timeout=300)
    if r.status_code >= 400:
        raise requests.HTTPError(f"Download failed ({r.status_code}): {r.text}")
    payload = r.json()
    data = base64.b64decode(payload["data_b64"])
    return payload.get("notes"), payload["filename"], data


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
    server_url: Optional[str] = None,
    api_token: Optional[str] = None
) -> dict:
    """Create a ZIP from `files` and upload it to the `results` table.

    Args:
        hashID: Identifier used to correlate results with a calibration or run.
        name: Logical name/grouping for this result (e.g., "daily-check").
        notes: Free-form notes for this result.
        files: List of file paths to include in the ZIP archive.
        server_url: Base server URL; if omitted, uses saved config or defaults to
            "http://127.0.0.1:5000".
        api_token: Optional bearer token; if omitted, uses saved config.

    Raises:
        ValueError: If `files` is empty.
        FileNotFoundError: If any file path does not exist.
        requests.HTTPError: If the server returns an error response.

    Returns:
        dict: The server's JSON response (e.g., {"status":"ok","id":1,"created_at":"..."}).
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

    files_payload = {"archive": ("results_bundle.zip", mem_zip.read(), "application/zip")}
    data_payload = {"hashID": hashID, "name": name, "notes": notes or ""}
    url = server_url + "/results/upload"
    resp = requests.post(url, data=data_payload, files=files_payload, headers=_auth_headers(api_token), timeout=300)
    if resp.status_code >= 400:
        raise requests.HTTPError(f"Upload failed ({resp.status_code}): {resp.text}")
    return resp.json()


def results_download(
    hashID: str,
    name: str,
    server_url: Optional[str] = None,
    api_token: Optional[str] = None
) -> Tuple[Optional[str], str, bytes]:
    """Download the latest results ZIP matching `hashID` and `name`.

    Args:
        hashID: Identifier to match entries in the results table.
        name: Logical result name/group to match.
        server_url: Optional override for the server base URL.
        api_token: Optional override for the bearer token.

    Raises:
        requests.HTTPError: On server error or not found (4xx/5xx).

    Returns:
        Tuple of (notes, filename, data):
          - notes (Optional[str]): Notes saved with the result.
          - filename (str): Original ZIP filename returned by the server.
          - data (bytes): Raw ZIP file contents.
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/results/download"
    r = requests.post(url, json={"hashID": hashID, "name": name}, headers=_auth_headers(api_token), timeout=300)
    if r.status_code >= 400:
        raise requests.HTTPError(f"Download failed ({r.status_code}): {r.text}")
    payload = r.json()
    data = base64.b64decode(payload["data_b64"])
    return payload.get("notes"), payload["filename"], data


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
    