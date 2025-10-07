"""DigitalOcean Functions entry point for GitLab MR Review."""

from __future__ import annotations

import json
import site
from pathlib import Path


def _bootstrap_site_packages() -> None:
    """Add the packaged virtualenv site-packages directory to sys.path."""
    base_dir = Path(__file__).parent
    site_root = base_dir / "virtualenv" / "lib"
    if not site_root.exists():
        return

    for child in site_root.iterdir():
        if child.is_dir() and child.name.startswith("python"):
            site_packages = child / "site-packages"
            if site_packages.exists():
                site.addsitedir(site_packages.as_posix())


_bootstrap_site_packages()

# Import gitlab_mr_review from same directory
from gitlab_mr_review.main import main as gitlab_main


def _parse_event(event: dict | None) -> dict:
    """Normalize an incoming DigitalOcean event into the payload dict."""
    if not isinstance(event, dict):
        return {}

    payload: dict = {}

    # Include query parameters if they exist
    if isinstance(event.get("query"), dict):
        payload.update(event["query"])

    http_section = event.get("http")
    if isinstance(http_section, dict):
        if isinstance(http_section.get("query"), dict):
            payload.update(http_section["query"])

    def _merge_body(body_value):
        if isinstance(body_value, str):
            try:
                payload.update(json.loads(body_value))
            except json.JSONDecodeError:
                pass
        elif isinstance(body_value, dict):
            payload.update(body_value)

    _merge_body(event.get("body"))

    if isinstance(http_section, dict):
        _merge_body(http_section.get("body"))

    if payload:
        return payload

    # Fall back to event if it already matches the expected payload shape
    if any(key in event for key in ("gitlab_token", "project_id", "merge_request_iid")):
        return event

    return {}


def main_handler(event: dict | None, context=None):
    """
    DigitalOcean Functions main handler

    Args:
        event: DigitalOcean Functions event payload

    Returns:
        Dict with statusCode and body
    """
    try:
        # Call main function
        payload = _parse_event(event)
        result = gitlab_main(payload)

        return result

    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'error': f'Internal server error: {str(e)}'
            }
        }


def main(event=None, context=None):
    """DigitalOcean Functions entry point expected by the runtime."""
    return main_handler(event, context)
