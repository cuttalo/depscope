"""DepScope Configuration"""
import os

DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://depscope:CHANGEME@localhost:5432/depscope"  # override via env
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Rate limiting
RATE_LIMIT_PER_MINUTE = 100
RATE_LIMIT_PER_HOUR = 2000

# Registry URLs
REGISTRIES = {
    "npm": "https://registry.npmjs.org",
    "pypi": "https://pypi.org/pypi",
    "cargo": "https://crates.io/api/v1/crates",
    "go": "https://proxy.golang.org",
    "composer": "https://repo.packagist.org",
    "maven": "https://search.maven.org",
    "nuget": "https://api.nuget.org",
    "rubygems": "https://rubygems.org",
    "pub": "https://pub.dev/api/packages",
    "hex": "https://hex.pm/api/packages",
    "swift": "https://swiftpackageindex.com/api",
    "cocoapods": "https://trunk.cocoapods.org/api/v1/pods",
    "cpan": "https://fastapi.metacpan.org/v1",
    "hackage": "https://hackage.haskell.org",
    "cran": "https://crandb.r-pkg.org",
    "conda": "https://api.anaconda.org/package/conda-forge",
    "homebrew": "https://formulae.brew.sh/api/formula",
}

# External APIs
DEPS_DEV_API = "https://api.deps.dev/v3"
OSV_API = "https://api.osv.dev/v1"
LIBRARIES_IO_API = "https://libraries.io/api"

# Cache TTLs (seconds)
CACHE_TTL_PACKAGE = 3600       # 1 hour
CACHE_TTL_VULN = 21600         # 6 hours
CACHE_TTL_HEALTH = 86400       # 24 hours

VERSION = "0.2.0"

# Privacy: salt per pseudonimizzare IP nelle analytics
IP_HASH_SALT = os.getenv("DEPSCOPE_IP_HASH_SALT", "depscope-intel-salt-2026-rotate-me-periodically")
