"""Step `fetch-opendata`: download the UniTrento open datasets from the public catalogue pages.

Resource URLs are read from the public dataset HTML page (/dataset/<slug>): robots.txt of dati.trentino.it
disallows /api/, so the CKAN action API is not used.
Downloads are immutable: data/raw/opendata/<YYYY-MM-DD>/<slug>/<resource_id>.<ext> plus manifest.json.
robots.txt of every download host is honoured; a disallow stops the run (contact: opendata@unitn.it).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import logging
import re
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

from . import config, net

log = logging.getLogger(__name__)


class RobotsDenied(RuntimeError):
    pass


_last_request: dict[str, float] = {}


def _polite_get(robots: dict[str, RobotFileParser], s: requests.Session, url: str) -> requests.Response:
    """GET honouring robots.txt (disallow -> RobotsDenied) and its Crawl-delay per host."""
    if not _robots_allows(robots, s, url):
        raise RobotsDenied(f"robots.txt of {urlsplit(url).netloc} disallows {url}. "
                           "STOP: do not download; ask opendata@unitn.it.")
    parts = urlsplit(url)
    delay = robots[f"{parts.scheme}://{parts.netloc}"].crawl_delay(s.headers["User-Agent"]) or 0
    wait = _last_request.get(parts.netloc, 0) + float(delay) - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    try:
        r = s.get(url, timeout=net.TIMEOUT)
    finally:
        _last_request[parts.netloc] = time.monotonic()
    r.raise_for_status()
    return r


_ITEM_RE = re.compile(r'<li class="resource-item" data-id="([^"]+)">(.*?)</li>\s*(?=<li class="resource-item"|</ul>)', re.S)


def _package_from_html(page: str, slug: str) -> dict:
    """The subset of a CKAN package_show result used downstream, parsed from the dataset HTML page."""
    resources = []
    for rid, body in _ITEM_RE.findall(page):
        title = re.search(r'<a class="heading"[^>]*title="([^"]*)"', body)
        fmt = re.search(r'data-format="([^"]*)"', body)
        url = re.search(r'href="([^"]+)" class="resource-url-analytics"', body)
        desc = re.search(r'<p class="description">(.*?)</p>', body, re.S)
        if not url:
            log.warning("%s: resource %s has no download link on the page", slug, rid)
            continue
        resources.append({"id": rid, "name": html.unescape(title.group(1)) if title else rid,
                          "format": fmt.group(1).upper() if fmt else "", "url": html.unescape(url.group(1)),
                          "description": html.unescape(desc.group(1).strip()) if desc else ""})
    lic = re.search(r'rel="dc:rights">([^<]*)<', page)
    return {"name": slug, "license_id": lic.group(1).strip() if lic else None, "metadata_modified": None,
            "source": "html", "resources": resources}


def _robots_allows(cache: dict[str, RobotFileParser], s: requests.Session, url: str) -> bool:
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin not in cache:
        rp = RobotFileParser()
        try:
            r = s.get(origin + "/robots.txt", timeout=net.TIMEOUT)
        except requests.RequestException as e:
            log.warning("%s/robots.txt unreachable (%s): treating as allow-all", origin, e)
            rp.parse([])
        else:
            if r.status_code in (401, 403):  # same convention as RobotFileParser.read()
                rp.disallow_all = True
            elif r.status_code >= 400:
                rp.allow_all = True
            else:
                rp.parse(r.text.splitlines())
            (config.RAW / "opendata" / "robots").mkdir(parents=True, exist_ok=True)
            (config.RAW / "opendata" / "robots" / f"{parts.netloc}.txt").write_text(
                f"# {r.status_code} {dt.datetime.now().isoformat()}\n{r.text}", encoding="utf-8")
        cache[origin] = rp
    return cache[origin].can_fetch(s.headers["User-Agent"], url)


def run(cfg: dict, args=None) -> None:
    config.ensure_dirs()
    s = net.session(cfg)
    base = cfg["opendata"]["ckan_base"]
    out = config.RAW / "opendata" / dt.date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    manifest: list[dict] = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    done = {m["url"] for m in manifest}
    robots: dict[str, RobotFileParser] = {}

    for slug in cfg["opendata"]["datasets"]:
        pkg = _package_from_html(_polite_get(robots, s, f"{base}/dataset/{slug}").text, slug)
        d = out / slug
        d.mkdir(exist_ok=True)
        (d / "package.json").write_text(json.dumps(pkg, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info("%s: license=%s, %d resources", slug, pkg.get("license_id"), len(pkg["resources"]))
        for res in pkg["resources"]:
            url = res["url"]
            if url in done:
                continue
            ext = (res.get("format") or url.rsplit(".", 1)[-1]).lower().strip(". ") or "bin"
            path: Path = d / f"{res['id']}.{ext}"
            try:
                r = _polite_get(robots, s, url)
            except requests.RequestException as e:  # e.g. a single resource answering 500: keep the others
                log.error("skipped %s (%s): %s", res.get("name"), url, e)
                continue
            path.write_bytes(r.content)
            manifest.append({
                "dataset": slug, "resource_id": res["id"], "name": res.get("name"), "url": url,
                "path": str(path.relative_to(out)), "bytes": len(r.content),
                "sha256": hashlib.sha256(r.content).hexdigest(),
                "downloaded_at": dt.datetime.now().isoformat(timespec="seconds"),
            })
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
            log.info("downloaded %s (%s, %d bytes)", res.get("name"), ext, len(r.content))
    log.info("done: %d resources in %s", len(manifest), out)
