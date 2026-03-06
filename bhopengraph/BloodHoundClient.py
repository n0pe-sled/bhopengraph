#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File name          : BloodHoundClient.py

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class BloodHoundClientError(Exception):
    """Base exception for BloodHoundClient errors."""
    pass


class BloodHoundAuthError(BloodHoundClientError):
    """Raised on 401/403 authentication/authorization failures."""
    pass


class BloodHoundAPIError(BloodHoundClientError):
    """Raised on non-2xx API responses (other than 401/403)."""

    def __init__(self, message, status_code=None, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class BloodHoundClient:
    """Client for the BloodHound API with HMAC-signed authentication.

    Uses only stdlib modules. Supports CRUD operations on custom node icons.
    """

    def __init__(self, base_url: str, token_id: str, token_key: str):
        self.base_url = base_url.rstrip("/")
        self.token_id = token_id
        self.token_key = token_key

    def _sign_request(self, method: str, uri: str, body: bytes = None) -> dict:
        """Compute HMAC-SHA256 signature chain and return the 3 auth headers."""
        now = datetime.now(timezone.utc)
        request_date = now.isoformat(timespec="seconds").replace("+00:00", "Z")

        # Step 1: HMAC(token_key, method + path)
        digester = hmac.new(self.token_key.encode("utf-8"), digestmod=hashlib.sha256)
        digester.update((method.upper() + uri).encode("utf-8"))

        # Step 2: HMAC(operation_digest, datetime[:13])
        digester = hmac.new(digester.digest(), digestmod=hashlib.sha256)
        digester.update(request_date[:13].encode("utf-8"))

        # Step 3: HMAC(date_digest, body) — always chain, even without body
        digester = hmac.new(digester.digest(), digestmod=hashlib.sha256)
        if body is not None:
            digester.update(body)

        signature = base64.b64encode(digester.digest()).decode("utf-8")

        return {
            "Authorization": f"bhesignature {self.token_id}",
            "RequestDate": request_date,
            "Signature": signature,
        }

    def _request(self, method: str, path: str, body: dict = None) -> dict:
        """Make an authenticated HTTP request to the BloodHound API."""
        uri = path if path.startswith("/") else f"/{path}"
        url = self.base_url + uri

        body_bytes = None
        if body is not None:
            body_bytes = json.dumps(body).encode("utf-8")

        headers = self._sign_request(method, uri, body_bytes)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"

        req = Request(url, data=body_bytes, headers=headers, method=method.upper())

        try:
            with urlopen(req) as response:
                response_body = response.read().decode("utf-8")
                if response_body:
                    return json.loads(response_body)
                return {}
        except HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass

            if e.code in (401, 403):
                raise BloodHoundAuthError(
                    f"Authentication failed (HTTP {e.code}): {error_body}"
                )
            raise BloodHoundAPIError(
                f"API request failed (HTTP {e.code}): {error_body}",
                status_code=e.code,
                response_body=error_body,
            )

    def get_custom_nodes(self) -> dict:
        """Get all custom node types."""
        return self._request("GET", "/api/v2/custom-nodes")

    def get_custom_node(self, kind_name: str) -> dict:
        """Get a specific custom node type by kind name."""
        return self._request("GET", f"/api/v2/custom-nodes/{kind_name}")

    def create_custom_node(self, kind_name: str, icon_config: dict) -> dict:
        """Create a new custom node type."""
        payload = {"name": kind_name, "config": {"icon": icon_config}}
        return self._request("POST", "/api/v2/custom-nodes", body=payload)

    def update_custom_node(self, kind_name: str, icon_config: dict) -> dict:
        """Update an existing custom node type."""
        payload = {"config": {"icon": icon_config}}
        return self._request("PUT", f"/api/v2/custom-nodes/{kind_name}", body=payload)

    def delete_custom_node(self, kind_name: str) -> dict:
        """Delete a custom node type."""
        return self._request("DELETE", f"/api/v2/custom-nodes/{kind_name}")

    def upload_icons(self, icons_config: dict) -> list:
        """Upload icons from config dict. Upsert: tries PUT first, POST on 404.

        Accepts the API-aligned list format::

            {"custom_nodes": [{"kindName": "...", "config": {"icon": {...}}}]}

        """
        results = []
        for entry in icons_config.get("custom_nodes", []):
            kind_name = entry["kindName"]
            icon_config = entry["config"]["icon"]
            try:
                result = self.update_custom_node(kind_name, icon_config)
                results.append({"kind": kind_name, "action": "updated", "result": result})
            except BloodHoundAPIError as e:
                if e.status_code == 404:
                    result = self.create_custom_node(kind_name, icon_config)
                    results.append({"kind": kind_name, "action": "created", "result": result})
                else:
                    raise
        return results

    def upload_icons_from_file(self, filepath: str) -> list:
        """Load icons from a JSON file and upload them."""
        icons_config = self.load_icons_from_file(filepath)
        return self.upload_icons(icons_config)

    @classmethod
    def load_icons_from_file(cls, filepath: str) -> dict:
        """Load and parse an icons JSON file."""
        with open(filepath, "r") as f:
            return json.load(f)

    def __repr__(self):
        return f"BloodHoundClient(base_url='{self.base_url}', token_id='{self.token_id}')"
