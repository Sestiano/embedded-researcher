"""HTTP session with timeouts, exponential backoff (honouring 429 / Retry-After) and a contact User-Agent."""

from __future__ import annotations

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)
TIMEOUT = 60  # seconds, applied to every request


def session(cfg: dict) -> requests.Session:
    email = cfg["contact"]["email"]
    if not email:
        log.warning("contact.email is empty in config.toml: set it, it is sent in the User-Agent")
    s = requests.Session()
    s.headers["User-Agent"] = f"unitn-net/0.1 (mailto:{email or 'unset'})"
    retry = Retry(
        total=5,
        backoff_factor=2,  # 0, 2, 4, 8, 16 s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def get_json(s: requests.Session, url: str, params: dict | None = None) -> dict:
    r = s.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()
