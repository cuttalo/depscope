"""DepScope Python Client — Package Intelligence for AI Agents."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx


class DepScope:
    """Client for the DepScope API.

    Args:
        api_key: Optional API key (not required for the free tier).
        base_url: Base URL for the DepScope API.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://depscope.dev",
        timeout: float = 30.0,
    ) -> None:
        headers: Dict[str, str] = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
        )

    def _get(self, path: str) -> Any:
        resp = self._client.get(path)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json: Any) -> Any:
        resp = self._client.post(path, json=json)
        resp.raise_for_status()
        return resp.json()

    # ── Core endpoints ──────────────────────────────────────────

    def check(self, ecosystem: str, package: str) -> Dict[str, Any]:
        """Full package check: health score, vulnerabilities, metadata.

        >>> ds.check("npm", "express")
        """
        return self._get(f"/api/check/{ecosystem}/{package}")

    def latest(self, ecosystem: str, package: str) -> str:
        """Return the latest version string for a package.

        >>> ds.latest("pypi", "fastapi")
        0.111.0
        """
        data = self._get(f"/api/latest/{ecosystem}/{package}")
        return data.get("latest_version", data.get("version", ""))

    def exists(self, ecosystem: str, package: str) -> bool:
        """Check whether a package exists in the registry.

        >>> ds.exists("cargo", "serde")
        True
        """
        data = self._get(f"/api/exists/{ecosystem}/{package}")
        return bool(data.get("exists", False))

    def health(self, ecosystem: str, package: str) -> Dict[str, Any]:
        """Return health score and breakdown only.

        >>> ds.health("npm", "lodash")
        {score: 72, risk: moderate, ...}
        """
        return self._get(f"/api/health/{ecosystem}/{package}")

    def vulns(self, ecosystem: str, package: str) -> List[Dict[str, Any]]:
        """Return known vulnerabilities for a package.

        >>> ds.vulns("pypi", "mlflow")
        [{vuln_id: CVE-..., severity: critical, ...}, ...]
        """
        data = self._get(f"/api/vulns/{ecosystem}/{package}")
        return data.get("vulnerabilities", data if isinstance(data, list) else [])

    def compare(self, ecosystem: str, *packages: str) -> Dict[str, Any]:
        """Compare multiple packages side-by-side.

        >>> ds.compare("npm", "express", "fastify", "hono")
        """
        joined = ",".join(packages)
        return self._get(f"/api/compare/{ecosystem}/{joined}")

    def search(self, ecosystem: str, query: str) -> List[Dict[str, Any]]:
        """Search for packages by keyword.

        >>> ds.search("npm", "http client")
        """
        data = self._get(f"/api/search/{ecosystem}/{query}")
        return data.get("results", data if isinstance(data, list) else [])

    def alternatives(self, ecosystem: str, package: str) -> List[Dict[str, Any]]:
        """Find healthier alternatives to a package.

        >>> ds.alternatives("npm", "request")
        [{package: undici, score: 88}, ...]
        """
        data = self._get(f"/api/alternatives/{ecosystem}/{package}")
        return data.get("alternatives", data if isinstance(data, list) else [])

    def scan(self, ecosystem: str, packages: Dict[str, str]) -> Dict[str, Any]:
        """Scan multiple packages at once (e.g. from a lock file).

        >>> ds.scan("npm", {"express": "^4.18", "lodash": "*"})
        """
        return self._post("/api/scan", {"ecosystem": ecosystem, "packages": packages})

    # ── Context manager ─────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "DepScope":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
