"""Fetch package data from registries (npm, pypi, cargo, go, composer, maven, nuget, rubygems, pub, hex, swift, cocoapods, cpan, hackage, cran, conda, homebrew)"""
import re
import aiohttp
from datetime import datetime
from api.config import REGISTRIES, OSV_API, DEPS_DEV_API
from api.cache import cache_get, cache_set
from api.database import get_pool
from packaging.version import Version, InvalidVersion


async def fetch_npm(name: str) -> dict | None:
    url = f"{REGISTRIES['npm']}/{name}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

    latest = data.get("dist-tags", {}).get("latest", "")
    time_data = data.get("time", {})
    versions_list = list(data.get("versions", {}).keys())
    latest_info = data.get("versions", {}).get(latest, {})
    maintainers = data.get("maintainers", [])
    repo = data.get("repository", {})
    repo_url = repo.get("url", "") if isinstance(repo, dict) else str(repo) if repo else ""
    if repo_url.startswith("git+"):
        repo_url = repo_url[4:]
    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]

    deprecated = latest_info.get("deprecated")

    # Fetch weekly downloads from npm API
    downloads_weekly = await fetch_npm_downloads(name)

    return {
        "ecosystem": "npm",
        "name": name,
        "latest_version": latest,
        "description": data.get("description", ""),
        "license": data.get("license", ""),
        "homepage": data.get("homepage", ""),
        "repository": repo_url,
        "downloads_weekly": downloads_weekly,
        "maintainers_count": len(maintainers),
        "deprecated": bool(deprecated),
        "deprecated_message": deprecated if isinstance(deprecated, str) else None,
        "first_published": time_data.get("created"),
        "last_published": time_data.get(latest),
        "versions": versions_list[-20:],
        "all_version_count": len(versions_list),
        "dependencies": list(latest_info.get("dependencies", {}).keys()),
    }


async def fetch_npm_downloads(name: str) -> int:
    """Fetch weekly downloads from npm downloads API."""
    url = f"https://api.npmjs.org/downloads/point/last-week/{name}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return 0
                data = await resp.json()
                return data.get("downloads", 0)
    except Exception:
        return 0


async def fetch_pypi(name: str) -> dict | None:
    url = f"{REGISTRIES['pypi']}/{name}/json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

    info = data.get("info", {})
    releases = data.get("releases", {})
    versions_list = list(releases.keys())

    valid_versions = []
    for v in versions_list:
        try:
            valid_versions.append((Version(v), v))
        except InvalidVersion:
            pass
    valid_versions.sort(key=lambda x: x[0])

    last_release_date = None
    if versions_list:
        last_v = info.get("version", versions_list[-1])
        files = releases.get(last_v, [])
        if files:
            last_release_date = files[0].get("upload_time_iso_8601")

    # PyPI stats - use downloads from info if available
    downloads_weekly = 0
    try:
        async with aiohttp.ClientSession() as session:
            stats_url = f"https://pypistats.org/api/packages/{name.lower()}/recent"
            async with session.get(stats_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    downloads_weekly = stats.get("data", {}).get("last_week", 0)
    except Exception:
        pass

    return {
        "ecosystem": "pypi",
        "name": name,
        "latest_version": info.get("version", ""),
        "description": info.get("summary", ""),
        "license": info.get("license", ""),
        "homepage": info.get("home_page", "") or info.get("project_url", ""),
        "repository": _extract_pypi_repo(info),
        "downloads_weekly": downloads_weekly,
        "maintainers_count": 1 if info.get("author") else 0,
        "deprecated": "yanked" in str(info.get("classifiers", [])).lower(),
        "deprecated_message": None,
        "first_published": None,
        "last_published": last_release_date,
        "versions": [v[1] for v in valid_versions[-20:]],
        "all_version_count": len(valid_versions),
        "dependencies": info.get("requires_dist", []) or [],
    }


def _extract_pypi_repo(info: dict) -> str:
    urls = info.get("project_urls", {}) or {}
    for key in ["Source", "Repository", "Code", "GitHub", "Homepage"]:
        url = urls.get(key, "")
        if "github.com" in url or "gitlab.com" in url:
            return url
    return ""


async def fetch_cargo(name: str) -> dict | None:
    url = f"{REGISTRIES['cargo']}/{name}"
    async with aiohttp.ClientSession() as session:
        headers = {"User-Agent": "DepScope/0.1 (https://depscope.dev)"}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

    crate = data.get("crate", {})
    versions = data.get("versions", [])
    latest = crate.get("newest_version", "")

    return {
        "ecosystem": "cargo",
        "name": name,
        "latest_version": latest,
        "description": crate.get("description", ""),
        "license": versions[0].get("license", "") if versions else "",
        "homepage": crate.get("homepage", ""),
        "repository": crate.get("repository", ""),
        "downloads_weekly": crate.get("recent_downloads", 0),
        "maintainers_count": 0,
        "deprecated": False,
        "deprecated_message": None,
        "first_published": crate.get("created_at"),
        "last_published": crate.get("updated_at"),
        "versions": [v.get("num", "") for v in versions[:20]],
        "all_version_count": len(versions),
        "dependencies": [],
    }



async def fetch_go(name: str) -> dict | None:
    """Fetch Go module info from proxy.golang.org."""
    # Go module names use / (e.g. github.com/gin-gonic/gin)
    encoded = name.replace("/", "/")  # proxy handles slashes
    url = f"{REGISTRIES['go']}/{name}/@latest"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

    version = data.get("Version", "")
    time_str = data.get("Time", "")

    # Fetch version list
    versions_list = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{REGISTRIES['go']}/{name}/@v/list", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    versions_list = [v.strip() for v in text.strip().split("\n") if v.strip()]
    except Exception:
        pass

    # Extract repo URL from module name
    repo_url = ""
    if name.startswith("github.com/"):
        repo_url = f"https://{name}"
    elif name.startswith("golang.org/x/"):
        repo_url = f"https://github.com/golang/{name.split('/')[-1]}"

    # Try to get downloads from pkg.go.dev (no direct API, skip)
    return {
        "ecosystem": "go",
        "name": name,
        "latest_version": version,
        "description": "",
        "license": "",
        "homepage": f"https://pkg.go.dev/{name}",
        "repository": repo_url,
        "downloads_weekly": 0,
        "maintainers_count": 0,
        "deprecated": False,
        "deprecated_message": None,
        "first_published": None,
        "last_published": time_str,
        "versions": versions_list[-20:],
        "all_version_count": len(versions_list),
        "dependencies": [],
    }


async def fetch_composer(name: str) -> dict | None:
    """Fetch PHP/Composer package from packagist.org."""
    # name format: vendor/package (e.g. laravel/framework)
    if "/" not in name:
        return None
    url = f"https://repo.packagist.org/p2/{name}.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

    packages = data.get("packages", {}).get(name, [])
    if not packages:
        return None

    # Find latest stable version (not dev)
    stable = [p for p in packages if not p.get("version", "").startswith("dev-") and "alpha" not in p.get("version", "").lower() and "beta" not in p.get("version", "").lower() and "RC" not in p.get("version", "")]
    latest = stable[0] if stable else packages[0]

    # Get stats from packagist API
    downloads_weekly = 0
    description = ""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://packagist.org/packages/{name}.json", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    pdata = await resp.json()
                    pkg_info = pdata.get("package", {})
                    downloads_weekly = pkg_info.get("downloads", {}).get("daily", 0) * 7
                    description = pkg_info.get("description", "")
    except Exception:
        pass

    repo_url = ""
    source = latest.get("source", {})
    if source:
        repo_url = source.get("url", "")
        if repo_url.endswith(".git"):
            repo_url = repo_url[:-4]

    versions_list = [p.get("version", "") for p in packages if not p.get("version", "").startswith("dev-")]

    return {
        "ecosystem": "composer",
        "name": name,
        "latest_version": latest.get("version", ""),
        "description": description or latest.get("description", ""),
        "license": (latest.get("license") or [""])[0] if isinstance(latest.get("license"), list) else str(latest.get("license", "")),
        "homepage": latest.get("homepage", ""),
        "repository": repo_url,
        "downloads_weekly": downloads_weekly,
        "maintainers_count": len(latest.get("authors", [])),
        "deprecated": bool(latest.get("abandoned")),
        "deprecated_message": latest.get("abandoned") if isinstance(latest.get("abandoned"), str) else None,
        "first_published": None,
        "last_published": latest.get("time"),
        "versions": versions_list[:20],
        "all_version_count": len(versions_list),
        "dependencies": list(latest.get("require", {}).keys()),
    }


async def fetch_maven(name: str) -> dict | None:
    """Fetch Maven/Java package from search.maven.org.
    Name format: groupId:artifactId (e.g. org.springframework.boot:spring-boot)
    """
    if ":" not in name:
        return None
    group_id, artifact_id = name.split(":", 1)

    url = f"https://search.maven.org/solrsearch/select?q=g:{group_id}+AND+a:{artifact_id}&rows=1&wt=json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

    docs = data.get("response", {}).get("docs", [])
    if not docs:
        return None

    doc = docs[0]
    latest = doc.get("latestVersion", "")

    # Fetch all versions
    versions_list = []
    try:
        async with aiohttp.ClientSession() as session:
            vurl = f"https://search.maven.org/solrsearch/select?q=g:{group_id}+AND+a:{artifact_id}&core=gav&rows=20&wt=json"
            async with session.get(vurl, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    vdata = await resp.json()
                    versions_list = [d.get("v", "") for d in vdata.get("response", {}).get("docs", [])]
    except Exception:
        pass

    # Timestamps
    timestamp = doc.get("timestamp", 0)
    last_published = None
    if timestamp:
        from datetime import datetime, timezone
        last_published = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).isoformat()

    return {
        "ecosystem": "maven",
        "name": name,
        "latest_version": latest,
        "description": "",
        "license": "",
        "homepage": f"https://search.maven.org/artifact/{group_id}/{artifact_id}",
        "repository": "",
        "downloads_weekly": 0,
        "maintainers_count": 0,
        "deprecated": False,
        "deprecated_message": None,
        "first_published": None,
        "last_published": last_published,
        "versions": versions_list[:20],
        "all_version_count": doc.get("versionCount", len(versions_list)),
        "dependencies": [],
    }


async def fetch_nuget(name: str) -> dict | None:
    """Fetch NuGet/.NET package from api.nuget.org."""
    name_lower = name.lower()
    url = f"https://api.nuget.org/v3/registration5-gz-semver2/{name_lower}/index.json"
    async with aiohttp.ClientSession() as session:
        headers = {"Accept-Encoding": "gzip"}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

    items = data.get("items", [])
    if not items:
        return None

    # Get the last page of versions
    last_page = items[-1]
    # Some pages need fetching
    page_items = last_page.get("items", [])
    if not page_items and last_page.get("@id"):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(last_page["@id"], timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        page_data = await resp.json()
                        page_items = page_data.get("items", [])
        except Exception:
            pass

    if not page_items:
        return None

    latest_entry = page_items[-1]
    catalog = latest_entry.get("catalogEntry", {})
    latest_version = catalog.get("version", "")

    # Collect version numbers
    versions_list = [item.get("catalogEntry", {}).get("version", "") for item in page_items if item.get("catalogEntry")]

    # Get download count
    downloads_weekly = 0
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.nuget.org/v3-flatcontainer/{name_lower}/index.json", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    flat = await resp.json()
                    total_versions = len(flat.get("versions", []))
    except Exception:
        total_versions = len(versions_list)

    deprecated = catalog.get("deprecation") is not None
    dep_message = None
    if deprecated:
        dep_info = catalog.get("deprecation", {})
        dep_message = dep_info.get("message", "") or dep_info.get("alternatePackage", {}).get("id", "")

    return {
        "ecosystem": "nuget",
        "name": name,
        "latest_version": latest_version,
        "description": catalog.get("description", "")[:500],
        "license": catalog.get("licenseExpression", ""),
        "homepage": catalog.get("projectUrl", ""),
        "repository": catalog.get("projectUrl", ""),
        "downloads_weekly": downloads_weekly,
        "maintainers_count": len(catalog.get("authors", "").split(",")) if catalog.get("authors") else 0,
        "deprecated": deprecated,
        "deprecated_message": dep_message,
        "first_published": None,
        "last_published": catalog.get("published"),
        "versions": versions_list[-20:],
        "all_version_count": total_versions if 'total_versions' in dir() else len(versions_list),
        "dependencies": [d.get("id", "") for d in catalog.get("dependencyGroups", [{}])[0].get("dependencies", [])] if catalog.get("dependencyGroups") else [],
    }


async def fetch_rubygems(name: str) -> dict | None:
    """Fetch RubyGem from rubygems.org."""
    url = f"https://rubygems.org/api/v1/gems/{name}.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

    # Get versions list
    versions_list = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://rubygems.org/api/v1/versions/{name}.json", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    vdata = await resp.json()
                    versions_list = [v.get("number", "") for v in vdata[:20]]
    except Exception:
        pass

    repo_url = data.get("source_code_uri", "") or data.get("homepage_uri", "")

    return {
        "ecosystem": "rubygems",
        "name": name,
        "latest_version": data.get("version", ""),
        "description": (data.get("info") or "")[:500],
        "license": (data.get("licenses") or [""])[0] if isinstance(data.get("licenses"), list) else "",
        "homepage": data.get("homepage_uri", ""),
        "repository": repo_url,
        "downloads_weekly": data.get("version_downloads", 0),
        "maintainers_count": 0,
        "deprecated": False,
        "deprecated_message": None,
        "first_published": None,
        "last_published": data.get("version_created_at"),
        "versions": versions_list[:20],
        "all_version_count": data.get("version_downloads_count", len(versions_list)),
        "dependencies": [d.get("name", "") for d in data.get("dependencies", {}).get("runtime", [])] if isinstance(data.get("dependencies"), dict) else [],
    }


async def fetch_github_stats(repo_url: str) -> dict | None:
    """Fetch GitHub repo stats from the public API (no token, 60 req/h)."""
    if not repo_url or "github.com" not in repo_url:
        return None
    # Extract owner/repo from URL
    match = re.search(r'github\.com/([^/]+)/([^/\s#?]+)', repo_url)
    if not match:
        return None
    owner, repo = match.group(1), match.group(2)
    if repo.endswith('.git'):
        repo = repo[:-4]

    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Accept": "application/vnd.github.v3+json"}
            async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        return {
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "is_archived": data.get("archived", False),
            "pushed_at": data.get("pushed_at"),
            "subscribers_count": data.get("subscribers_count", 0),
        }
    except Exception:
        return None


async def save_github_stats(package_id: int, repo_url: str, stats: dict):
    """Save GitHub stats to the github_stats table."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO github_stats (package_id, repo_url, stars, forks, open_issues, is_archived, last_commit, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7::timestamptz, NOW())
                ON CONFLICT (package_id) DO UPDATE SET
                    stars = EXCLUDED.stars,
                    forks = EXCLUDED.forks,
                    open_issues = EXCLUDED.open_issues,
                    is_archived = EXCLUDED.is_archived,
                    last_commit = EXCLUDED.last_commit,
                    updated_at = NOW()
            """,
                package_id,
                repo_url,
                stats.get("stars", 0),
                stats.get("forks", 0),
                stats.get("open_issues", 0),
                stats.get("is_archived", False),
                _parse_dt(stats.get("pushed_at")),
            )
    except Exception:
        import traceback
        traceback.print_exc()



async def get_github_stats_from_db(repo_url: str) -> dict | None:
    """Load cached GitHub stats from the database as fallback when API is rate-limited."""
    if not repo_url:
        return None
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT stars, forks, open_issues, is_archived, last_commit
                FROM github_stats WHERE repo_url = $1
            """, repo_url)
            if row:
                return {
                    "stars": row["stars"] or 0,
                    "forks": row["forks"] or 0,
                    "open_issues": row["open_issues"] or 0,
                    "is_archived": row["is_archived"] or False,
                    "pushed_at": row["last_commit"].isoformat() if row["last_commit"] else None,
                }
    except Exception:
        pass
    return None



async def fetch_pub(name: str) -> dict | None:
    """Fetch Dart/Flutter package from pub.dev."""
    url = f"https://pub.dev/api/packages/{name}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
    except Exception:
        return None

    latest_pub = data.get("latest", {}).get("pubspec", {})
    latest_version_str = data.get("latest", {}).get("version", "")
    versions_list = [v.get("version", "") for v in data.get("versions", [])]

    # published dates
    last_published = data.get("latest", {}).get("published")

    return {
        "ecosystem": "pub",
        "name": name,
        "latest_version": latest_version_str,
        "description": latest_pub.get("description", ""),
        "license": "",
        "homepage": latest_pub.get("homepage", ""),
        "repository": latest_pub.get("repository", ""),
        "downloads_weekly": 0,
        "maintainers_count": len(latest_pub.get("authors", [])) if isinstance(latest_pub.get("authors"), list) else 0,
        "deprecated": bool(data.get("isDiscontinued")),
        "deprecated_message": "Discontinued" if data.get("isDiscontinued") else None,
        "first_published": None,
        "last_published": last_published,
        "versions": versions_list[-20:],
        "all_version_count": len(versions_list),
        "dependencies": list(latest_pub.get("dependencies", {}).keys()),
    }


async def fetch_hex(name: str) -> dict | None:
    """Fetch Elixir package from hex.pm."""
    url = f"https://hex.pm/api/packages/{name}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
    except Exception:
        return None

    releases = data.get("releases", [])
    versions_list = [r.get("version", "") for r in releases]
    latest_version = versions_list[0] if versions_list else ""

    meta = data.get("meta", {})
    links = meta.get("links", {})

    # Downloads
    downloads = data.get("downloads", {})
    downloads_weekly = downloads.get("week", 0) if isinstance(downloads, dict) else 0

    last_published = releases[0].get("inserted_at") if releases else None

    return {
        "ecosystem": "hex",
        "name": name,
        "latest_version": latest_version,
        "description": meta.get("description", ""),
        "license": (meta.get("licenses") or [""])[0] if isinstance(meta.get("licenses"), list) else "",
        "homepage": links.get("Homepage", "") or links.get("homepage", ""),
        "repository": links.get("GitHub", "") or links.get("github", "") or links.get("Repository", ""),
        "downloads_weekly": downloads_weekly,
        "maintainers_count": len(data.get("owners", [])),
        "deprecated": bool(data.get("retirements")),
        "deprecated_message": None,
        "first_published": data.get("inserted_at"),
        "last_published": last_published,
        "versions": versions_list[:20],
        "all_version_count": len(versions_list),
        "dependencies": [],
    }


async def fetch_swift(name: str) -> dict | None:
    """Fetch Swift package info via GitHub search for Package.swift repos."""
    # Search GitHub for Swift packages matching the name
    search_url = f"https://api.github.com/search/repositories?q={name}+language:swift&sort=stars&per_page=5"
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "DepScope/0.1 (https://depscope.dev)"}
            async with session.get(search_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
    except Exception:
        return None

    items = data.get("items", [])
    if not items:
        return None

    # Find exact match by repo name or first result
    repo = None
    for item in items:
        if item.get("name", "").lower() == name.lower():
            repo = item
            break
    if not repo:
        repo = items[0]

    repo_url = repo.get("html_url", "")

    # Try to get latest release/tag
    latest_version = ""
    versions_list = []
    try:
        async with aiohttp.ClientSession() as session:
            tags_url = f"https://api.github.com/repos/{repo['full_name']}/tags?per_page=20"
            headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "DepScope/0.1 (https://depscope.dev)"}
            async with session.get(tags_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    tags = await resp.json()
                    versions_list = [t.get("name", "") for t in tags]
                    latest_version = versions_list[0] if versions_list else ""
    except Exception:
        pass

    return {
        "ecosystem": "swift",
        "name": name,
        "latest_version": latest_version,
        "description": repo.get("description", ""),
        "license": repo.get("license", {}).get("spdx_id", "") if isinstance(repo.get("license"), dict) else "",
        "homepage": repo.get("homepage", "") or repo_url,
        "repository": repo_url,
        "downloads_weekly": 0,
        "maintainers_count": 1,
        "deprecated": repo.get("archived", False),
        "deprecated_message": "Archived" if repo.get("archived") else None,
        "first_published": repo.get("created_at"),
        "last_published": repo.get("pushed_at"),
        "versions": versions_list[:20],
        "all_version_count": len(versions_list),
        "dependencies": [],
    }


async def fetch_cocoapods(name: str) -> dict | None:
    """Fetch CocoaPods package from trunk.cocoapods.org."""
    url = f"https://trunk.cocoapods.org/api/v1/pods/{name}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
    except Exception:
        return None

    versions_data = data.get("versions", [])
    versions_list = [v.get("name", "") for v in versions_data]
    latest_version = versions_list[0] if versions_list else ""
    last_published = versions_data[0].get("created_at") if versions_data else None

    owners = data.get("owners", [])

    return {
        "ecosystem": "cocoapods",
        "name": name,
        "latest_version": latest_version,
        "description": "",
        "license": "",
        "homepage": f"https://cocoapods.org/pods/{name}",
        "repository": "",
        "downloads_weekly": 0,
        "maintainers_count": len(owners),
        "deprecated": bool(data.get("deprecated")),
        "deprecated_message": data.get("deprecated_in_favor_of"),
        "first_published": versions_data[-1].get("created_at") if versions_data else None,
        "last_published": last_published,
        "versions": versions_list[:20],
        "all_version_count": len(versions_list),
        "dependencies": [],
    }


async def fetch_cpan(name: str) -> dict | None:
    """Fetch Perl package from MetaCPAN."""
    # CPAN uses distribution names with hyphens (e.g. Moose, Moo, DateTime)
    url = f"https://fastapi.metacpan.org/v1/release/{name}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
    except Exception:
        return None

    version = data.get("version", "")
    license_list = data.get("license", [])
    lic = license_list[0] if isinstance(license_list, list) and license_list else str(license_list) if license_list else ""

    deps = data.get("dependency", [])
    dep_names = [d.get("module", "") for d in deps if d.get("relationship") == "requires"] if isinstance(deps, list) else []

    return {
        "ecosystem": "cpan",
        "name": name,
        "latest_version": version,
        "description": data.get("abstract", ""),
        "license": lic,
        "homepage": f"https://metacpan.org/release/{name}",
        "repository": "",
        "downloads_weekly": 0,
        "maintainers_count": 1 if data.get("author") else 0,
        "deprecated": data.get("status") == "backpan",
        "deprecated_message": None,
        "first_published": None,
        "last_published": data.get("date"),
        "versions": [version] if version else [],
        "all_version_count": 0,
        "dependencies": dep_names,
    }


async def fetch_hackage(name: str) -> dict | None:
    """Fetch Haskell package from Hackage."""
    url = f"https://hackage.haskell.org/package/{name}.json"
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Accept": "application/json"}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
    except Exception:
        return None

    # Hackage .json returns a dict of version -> status
    # Keys are version numbers
    if not isinstance(data, dict):
        return None

    versions_list = list(data.keys())
    # Sort versions, latest last
    versions_list_sorted = sorted(versions_list)
    latest_version = versions_list_sorted[-1] if versions_list_sorted else ""

    return {
        "ecosystem": "hackage",
        "name": name,
        "latest_version": latest_version,
        "description": "",
        "license": "",
        "homepage": f"https://hackage.haskell.org/package/{name}",
        "repository": "",
        "downloads_weekly": 0,
        "maintainers_count": 0,
        "deprecated": False,
        "deprecated_message": None,
        "first_published": None,
        "last_published": None,
        "versions": versions_list_sorted[-20:],
        "all_version_count": len(versions_list),
        "dependencies": [],
    }


async def fetch_cran(name: str) -> dict | None:
    """Fetch R package from crandb.r-pkg.org."""
    url = f"https://crandb.r-pkg.org/{name}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
    except Exception:
        return None

    version = data.get("Version", "")
    versions_list = list(data.get("versions", {}).keys()) if isinstance(data.get("versions"), dict) else [version] if version else []

    deps = data.get("Depends", {})
    imports = data.get("Imports", {})
    dep_names = list(deps.keys()) + list(imports.keys()) if isinstance(deps, dict) and isinstance(imports, dict) else []

    return {
        "ecosystem": "cran",
        "name": name,
        "latest_version": version,
        "description": data.get("Title", ""),
        "license": data.get("License", ""),
        "homepage": f"https://cran.r-project.org/package={name}",
        "repository": "",
        "downloads_weekly": 0,
        "maintainers_count": 1 if data.get("Maintainer") else 0,
        "deprecated": False,
        "deprecated_message": None,
        "first_published": data.get("crandb_file_date"),
        "last_published": data.get("date") or data.get("Date/Publication"),
        "versions": versions_list[-20:],
        "all_version_count": len(versions_list),
        "dependencies": dep_names,
    }


async def fetch_conda(name: str) -> dict | None:
    """Fetch conda-forge package from api.anaconda.org."""
    url = f"https://api.anaconda.org/package/conda-forge/{name}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
    except Exception:
        return None

    latest_version = data.get("latest_version", "")
    versions_list = data.get("versions", [])
    if not isinstance(versions_list, list):
        versions_list = []

    return {
        "ecosystem": "conda",
        "name": name,
        "latest_version": latest_version,
        "description": data.get("summary", ""),
        "license": data.get("license", ""),
        "homepage": data.get("home", "") or data.get("dev_url", ""),
        "repository": data.get("dev_url", "") or data.get("source_git_url", ""),
        "downloads_weekly": 0,
        "maintainers_count": 0,
        "deprecated": False,
        "deprecated_message": None,
        "first_published": data.get("created_at"),
        "last_published": data.get("modified_at"),
        "versions": versions_list[-20:] if versions_list else [],
        "all_version_count": len(versions_list),
        "dependencies": [],
    }


async def fetch_homebrew(name: str) -> dict | None:
    """Fetch Homebrew formula from formulae.brew.sh."""
    url = f"https://formulae.brew.sh/api/formula/{name}.json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
    except Exception:
        return None

    versions_stable = data.get("versions", {})
    latest_version = versions_stable.get("stable", "") if isinstance(versions_stable, dict) else ""

    # Versioned formulae list
    versioned = data.get("versioned_formulae", [])
    versions_list = [latest_version] + versioned if latest_version else versioned

    # Analytics for downloads
    downloads_30d = 0
    analytics = data.get("analytics", {})
    install_30d = analytics.get("install_30d", {})
    if isinstance(install_30d, dict):
        pkg_installs = install_30d.get(name, 0)
        if isinstance(pkg_installs, int):
            downloads_30d = pkg_installs

    deps = data.get("dependencies", [])

    return {
        "ecosystem": "homebrew",
        "name": name,
        "latest_version": latest_version,
        "description": data.get("desc", ""),
        "license": data.get("license", ""),
        "homepage": data.get("homepage", ""),
        "repository": "",
        "downloads_weekly": downloads_30d // 4 if downloads_30d else 0,
        "maintainers_count": 0,
        "deprecated": bool(data.get("deprecated")),
        "deprecated_message": data.get("deprecation_reason"),
        "first_published": None,
        "last_published": None,
        "versions": versions_list[:20],
        "all_version_count": len(versions_list),
        "dependencies": deps if isinstance(deps, list) else [],
    }


FETCHERS = {
    "npm": fetch_npm,
    "pypi": fetch_pypi,
    "cargo": fetch_cargo,
    "go": fetch_go,
    "composer": fetch_composer,
    "maven": fetch_maven,
    "nuget": fetch_nuget,
    "rubygems": fetch_rubygems,
    "pub": fetch_pub,
    "hex": fetch_hex,
    "swift": fetch_swift,
    "cocoapods": fetch_cocoapods,
    "cpan": fetch_cpan,
    "hackage": fetch_hackage,
    "cran": fetch_cran,
    "conda": fetch_conda,
    "homebrew": fetch_homebrew,
}


async def fetch_package(ecosystem: str, name: str) -> dict | None:
    fetcher = FETCHERS.get(ecosystem)
    if not fetcher:
        return None
    try:
        return await fetcher(name)
    except Exception:
        return None


def _version_in_range(version_str: str, range_str: str) -> bool:
    """Check if version is in an affected range like >=1.0.0,<2.0.0"""
    if not range_str or not version_str:
        return True  # assume affected if we can't parse
    try:
        ver = Version(version_str)
    except InvalidVersion:
        return True

    for part in range_str.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if part.startswith(">="):
                if not (ver >= Version(part[2:])):
                    return False
            elif part.startswith(">"):
                if not (ver > Version(part[1:])):
                    return False
            elif part.startswith("<="):
                if not (ver <= Version(part[2:])):
                    return False
            elif part.startswith("<"):
                if not (ver < Version(part[1:])):
                    return False
            elif part.startswith("="):
                if not (ver == Version(part[1:])):
                    return False
        except InvalidVersion:
            return True
    return True


def _is_vuln_relevant(vuln: dict, latest_version: str) -> bool:
    """Check if a vulnerability affects the latest version.
    If there's a fixed_version and latest >= fixed, the vuln is NOT relevant.
    Otherwise check if latest is in the affected range.
    """
    if not latest_version:
        return True

    fixed = vuln.get("fixed_version")
    if fixed:
        try:
            if Version(latest_version) >= Version(fixed):
                return False  # Fixed in a version <= latest
        except InvalidVersion:
            pass

    affected = vuln.get("affected_versions")
    if affected:
        return _version_in_range(latest_version, affected)

    return True  # Can't determine, include it


async def fetch_vulnerabilities(ecosystem: str, name: str, latest_version: str = None) -> list:
    """Fetch from OSV.dev, filtered to only vulns affecting latest version. Cached 6h in Redis."""
    # Check Redis cache first
    vuln_cache_key = f"vulns:{ecosystem}:{name}"
    cached = await cache_get(vuln_cache_key)
    if cached is not None:
        return cached

    payload = {"package": {"name": name, "ecosystem": _osv_ecosystem(ecosystem)}}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OSV_API}/query",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

        vulns = []
        for v in data.get("vulns", []):
            severity = "unknown"
            for s in v.get("severity", []):
                if s.get("type") == "CVSS_V3":
                    score = _parse_cvss_score(s.get("score", ""))
                    if score >= 9.0:
                        severity = "critical"
                    elif score >= 7.0:
                        severity = "high"
                    elif score >= 4.0:
                        severity = "medium"
                    else:
                        severity = "low"

            aliases = v.get("aliases", [])
            vuln_id = aliases[0] if aliases else v.get("id", "")

            affected = v.get("affected", [{}])
            fixed = None
            affected_range = None
            for a in affected:
                for r in a.get("ranges", []):
                    for evt in r.get("events", []):
                        if "fixed" in evt:
                            fixed = evt["fixed"]
                        if "introduced" in evt:
                            affected_range = f">={evt['introduced']}"

            vuln_entry = {
                "vuln_id": vuln_id,
                "severity": severity,
                "summary": v.get("summary", v.get("details", ""))[:500],
                "affected_versions": affected_range,
                "fixed_version": fixed,
                "source": "osv",
                "published_at": v.get("published"),
            }

            # Filter: only include vulns that affect the latest version
            if latest_version and not _is_vuln_relevant(vuln_entry, latest_version):
                continue

            vulns.append(vuln_entry)
        # Cache for 6 hours
        await cache_set(vuln_cache_key, vulns, ttl=21600)
        return vulns
    except Exception:
        return []


def _parse_dt(val):
    """Parse date string to datetime object for asyncpg."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        from datetime import timezone
        dt = datetime.fromisoformat(str(val).replace('Z', '+00:00'))
        return dt
    except (ValueError, TypeError):
        return None


async def save_package_to_db(pkg_data: dict, health_score: int, vulns: list = None):
    """Save/update package data in PostgreSQL for persistence."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            import json
            pkg_id = await conn.fetchval("""
                INSERT INTO packages (ecosystem, name, latest_version, description, license,
                    homepage, repository, downloads_weekly, first_published, last_published,
                    maintainers_count, deprecated, deprecated_message, health_score, data_json, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::timestamptz, $10::timestamptz,
                    $11, $12, $13, $14, $15::jsonb, NOW())
                ON CONFLICT (ecosystem, name) DO UPDATE SET
                    latest_version = EXCLUDED.latest_version,
                    description = EXCLUDED.description,
                    license = EXCLUDED.license,
                    homepage = EXCLUDED.homepage,
                    repository = EXCLUDED.repository,
                    downloads_weekly = EXCLUDED.downloads_weekly,
                    last_published = EXCLUDED.last_published,
                    maintainers_count = EXCLUDED.maintainers_count,
                    deprecated = EXCLUDED.deprecated,
                    deprecated_message = EXCLUDED.deprecated_message,
                    health_score = EXCLUDED.health_score,
                    data_json = EXCLUDED.data_json,
                    updated_at = NOW()
                RETURNING id
            """,
                pkg_data.get("ecosystem"),
                pkg_data.get("name"),
                pkg_data.get("latest_version"),
                (pkg_data.get("description") or "")[:500],
                str(pkg_data.get("license") or "")[:100],
                (pkg_data.get("homepage") or "")[:500],
                (pkg_data.get("repository") or "")[:500],
                pkg_data.get("downloads_weekly", 0) or 0,
                _parse_dt(pkg_data.get("first_published")),
                _parse_dt(pkg_data.get("last_published")),
                pkg_data.get("maintainers_count", 0),
                pkg_data.get("deprecated", False),
                pkg_data.get("deprecated_message"),
                health_score,
                json.dumps(pkg_data, default=str),
            )

            # Save vulnerabilities
            if vulns and pkg_id:
                for vuln in vulns:
                    await conn.execute("""
                        INSERT INTO vulnerabilities (package_id, vuln_id, severity, summary,
                            affected_versions, fixed_version, source, published_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::timestamptz, NOW())
                        ON CONFLICT (package_id, vuln_id) DO UPDATE SET
                            severity = EXCLUDED.severity,
                            summary = EXCLUDED.summary,
                            affected_versions = EXCLUDED.affected_versions,
                            fixed_version = EXCLUDED.fixed_version,
                            updated_at = NOW()
                    """,
                        pkg_id,
                        vuln.get("vuln_id", ""),
                        vuln.get("severity", "unknown"),
                        (vuln.get("summary") or "")[:500],
                        vuln.get("affected_versions"),
                        vuln.get("fixed_version"),
                        vuln.get("source", "osv"),
                        _parse_dt(vuln.get("published_at")),
                    )
    except Exception as e:
        import traceback
        traceback.print_exc()


def _osv_ecosystem(eco: str) -> str:
    return {"npm": "npm", "pypi": "PyPI", "cargo": "crates.io", "go": "Go", "composer": "Packagist", "maven": "Maven", "nuget": "NuGet", "rubygems": "RubyGems", "pub": "Pub", "hex": "Hex", "swift": "SwiftURL", "cocoapods": "CocoaPods", "cpan": "CPAN", "hackage": "Hackage", "cran": "CRAN", "conda": "PyPI", "homebrew": ""}.get(eco, eco)


def _parse_cvss_score(score_str: str) -> float:
    try:
        return float(score_str)
    except (ValueError, TypeError):
        return 5.0
