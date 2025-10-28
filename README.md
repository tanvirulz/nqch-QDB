# QiboDB Client API

The **QiboDB Client** is a lightweight Python interface for interacting with the QiboDB server.  
It allows you to upload, list, and download experimental data or result bundles from a remote QiboDB instance.

---

## Overview

QiboDB is a simple result and calibration database system.  
Each record in the database is associated with:
- a **`hashID`** — links related results,
- a **`name`** — identifies a particular result or dataset,
- an optional **`experimentID`** — tags results belonging to the same experiment,
- optional **`notes`**, and
- an uploaded binary archive (ZIP, etc.).

The client handles HTTP communication, authorization, and data serialization automatically.

---
## Usages

See the function docstrings in `client/client.py` for the usages and `test_client.py` for examples. 

## Installation

Install dependencies (usually just `requests`):

```bash
pip install requests
```

## License
MIT License © 2025  
Developed by [Tanvirul Islam](https://github.com/tanvirulz)
