"""Health score calculation - pure algorithmic, no AI"""
from datetime import datetime, timezone


def calculate_health_score(pkg_data: dict, vulns: list = None, github: dict = None) -> dict:
    """
    Calculate a 0-100 health score based on multiple signals.
    Returns score + breakdown.
    """
    scores = {}

    # 1. Maintenance (0-25): how actively maintained
    maintenance = 0
    last_pub = pkg_data.get("last_published")
    if last_pub:
        if isinstance(last_pub, str):
            try:
                last_pub = datetime.fromisoformat(last_pub.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                last_pub = None
    if last_pub:
        if last_pub.tzinfo is None:
            last_pub = last_pub.replace(tzinfo=timezone.utc)
        days_since = (datetime.now(timezone.utc) - last_pub).days
        if days_since < 30:
            maintenance = 25
        elif days_since < 90:
            maintenance = 20
        elif days_since < 180:
            maintenance = 15
        elif days_since < 365:
            maintenance = 10
        elif days_since < 730:
            maintenance = 5
        else:
            maintenance = 0
    scores["maintenance"] = maintenance

    # 2. Popularity (0-20): downloads/stars
    popularity = 0
    downloads = pkg_data.get("downloads_weekly", 0) or pkg_data.get("downloads_monthly", 0) or 0
    if downloads > 10_000_000:
        popularity = 20
    elif downloads > 1_000_000:
        popularity = 17
    elif downloads > 100_000:
        popularity = 14
    elif downloads > 10_000:
        popularity = 10
    elif downloads > 1_000:
        popularity = 6
    elif downloads > 100:
        popularity = 3
    scores["popularity"] = popularity

    # 3. Security (0-25): vulnerabilities
    security = 25
    if vulns:
        critical = sum(1 for v in vulns if v.get("severity") == "critical")
        high = sum(1 for v in vulns if v.get("severity") == "high")
        medium = sum(1 for v in vulns if v.get("severity") == "medium")
        security -= critical * 10 + high * 5 + medium * 2
        security = max(0, security)
    scores["security"] = security

    # 4. Maturity (0-15): age + version count
    maturity = 0
    version_count = pkg_data.get("all_version_count", 0)
    if version_count > 50:
        maturity = 15
    elif version_count > 20:
        maturity = 12
    elif version_count > 10:
        maturity = 9
    elif version_count > 5:
        maturity = 6
    elif version_count > 1:
        maturity = 3
    scores["maturity"] = maturity

    # 5. Community (0-15): maintainers, contributors, issues, github stars
    community = 0
    maintainers = pkg_data.get("maintainers_count", 0)
    if maintainers >= 5:
        community = 5
    elif maintainers >= 3:
        community = 4
    elif maintainers >= 2:
        community = 3
    elif maintainers >= 1:
        community = 2

    if github:
        stars = github.get("stars", 0)
        forks = github.get("forks", 0)
        # Stars scoring
        if stars > 50000:
            community += 7
        elif stars > 10000:
            community += 5
        elif stars > 1000:
            community += 3
        elif stars > 100:
            community += 1
        # Forks as proxy for contributors
        if forks > 1000:
            community += 3
        elif forks > 100:
            community += 2
        elif forks > 10:
            community += 1
        community = min(15, community)

        # Archived penalty: severe
        if github.get("is_archived"):
            community = 0
            # Also penalize maintenance
            maintenance = max(0, maintenance - 15)

        # Stale repo penalty: last push > 1 year
        pushed_at = github.get("pushed_at")
        if pushed_at:
            if isinstance(pushed_at, str):
                try:
                    pushed_at_dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                    days_since_push = (datetime.now(timezone.utc) - pushed_at_dt).days
                    if days_since_push > 365:
                        maintenance = max(0, maintenance - 5)
                    elif days_since_push > 730:
                        maintenance = max(0, maintenance - 10)
                except (ValueError, TypeError):
                    pass
    scores["community"] = community
    scores["maintenance"] = maintenance  # update in case of github penalties

    # Deprecation penalty
    if pkg_data.get("deprecated"):
        scores["deprecated_penalty"] = -30
    else:
        scores["deprecated_penalty"] = 0

    total = max(0, min(100, sum(scores.values())))

    # Risk level
    if total >= 80:
        risk = "low"
    elif total >= 60:
        risk = "moderate"
    elif total >= 40:
        risk = "high"
    else:
        risk = "critical"

    return {
        "score": total,
        "risk": risk,
        "breakdown": {k: v for k, v in scores.items() if k != "deprecated_penalty"},
        "deprecated": pkg_data.get("deprecated", False),
        "max_score": 100,
    }
