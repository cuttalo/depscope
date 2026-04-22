import os
"""Compute typosquat candidates: for each popular package, find lookalikes with much less downloads.

Algorithm:
- Top ~top_n packages per ecosystem as 'legitimate' anchors
- For each anchor, find candidates with Levenshtein distance 1-2 AND downloads <= 1/100 of the anchor
- Mark reason: char_swap, missing_char, extra_char, adjacent_swap, confusable
"""
import asyncio, asyncpg

DB = os.environ["DATABASE_URL"]
TOP_N = 500  # top packages per ecosystem to use as anchors

# Confusable pairs (simplified)
CONFUSABLES = {
    '0': 'o', '1': 'l', 'rn': 'm', 'vv': 'w',
}


def lev(a, b):
    """Damerau-Levenshtein distance, O(|a|*|b|)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    m, n = len(a), len(b)
    # Standard DP
    prev2 = None
    prev = list(range(n + 1))
    cur = [0] * (n + 1)
    for i in range(1, m + 1):
        cur[0] = i
        for j in range(1, n + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            cur[j] = min(
                prev[j] + 1,      # deletion
                cur[j-1] + 1,     # insertion
                prev[j-1] + cost  # substitution
            )
            if i > 1 and j > 1 and a[i-1] == b[j-2] and a[i-2] == b[j-1]:
                cur[j] = min(cur[j], prev2[j-2] + 1)  # transposition
        prev2 = prev[:]
        prev = cur[:]
    return prev[n]


def classify(a, b):
    d = lev(a, b)
    if d == 1:
        if len(a) == len(b):
            return "char_swap", 1
        elif abs(len(a) - len(b)) == 1:
            return "missing_or_extra_char", 1
    elif d == 2:
        # adjacent transposition detected?
        if len(a) == len(b):
            mismatches = sum(1 for i in range(len(a)) if a[i] != b[i])
            if mismatches == 2:
                return "adjacent_swap_or_double", 2
        return "close_name", 2
    return "close_name", d


async def main():
    conn = await asyncpg.connect(DB)
    ecosystems = await conn.fetch("SELECT DISTINCT ecosystem FROM packages WHERE downloads_weekly > 0")
    total_pairs = 0

    for r in ecosystems:
        eco = r["ecosystem"]
        # Anchors: top TOP_N by downloads
        anchors = await conn.fetch("""
            SELECT name, downloads_weekly FROM packages
            WHERE ecosystem=$1 AND downloads_weekly IS NOT NULL
            ORDER BY downloads_weekly DESC LIMIT $2
        """, eco, TOP_N)
        if not anchors:
            continue
        anchor_names = {a["name"].lower() for a in anchors}

        # Candidates: smaller packages within same ecosystem (excluding anchors)
        candidates = await conn.fetch("""
            SELECT name, COALESCE(downloads_weekly, 0) AS dw FROM packages
            WHERE ecosystem=$1 AND LOWER(name) NOT IN (
                SELECT LOWER(name) FROM packages
                WHERE ecosystem=$1
                ORDER BY downloads_weekly DESC NULLS LAST LIMIT $2
            )
        """, eco, TOP_N)

        # For each anchor, find candidates within distance ≤ 2
        ct = 0
        for a in anchors:
            aname_low = a["name"].lower()
            a_dw = a["downloads_weekly"] or 0
            # Minor ecosystems use GitHub-stars×10 proxy — their top pkgs are far
            # below the 1000-downloads gate we use for npm/pypi/etc.
            minor = eco in {"hex", "swift", "cocoapods", "hackage", "pub",
                             "cran", "homebrew", "conda", "cpan"}
            min_dw = 100 if minor else 1000
            if a_dw < min_dw:
                continue  # don't bother for small anchors
            for cand in candidates:
                cname_low = cand["name"].lower()
                if abs(len(cname_low) - len(aname_low)) > 2:
                    continue
                # quick prefix filter for speed
                if aname_low and cname_low and aname_low[:1] != cname_low[:1]:
                    # allow only confusable first chars (rare), else skip
                    continue
                d = lev(aname_low, cname_low)
                if d == 0 or d > 2:
                    continue
                # popularity gate: suspect must be << legit
                if cand["dw"] > a_dw / 100:
                    continue
                reason, dist = classify(aname_low, cname_low)
                try:
                    await conn.execute("""
                        INSERT INTO typosquat_candidates
                          (ecosystem, suspect, legitimate, distance, downloads_suspect, downloads_legit, reason)
                        VALUES ($1,$2,$3,$4,$5,$6,$7)
                        ON CONFLICT (ecosystem, suspect, legitimate) DO UPDATE SET
                          distance=EXCLUDED.distance,
                          downloads_suspect=EXCLUDED.downloads_suspect,
                          downloads_legit=EXCLUDED.downloads_legit,
                          reason=EXCLUDED.reason
                    """, eco, cand["name"], a["name"], dist, cand["dw"], a_dw, reason)
                    ct += 1
                except Exception as e:
                    pass
        total_pairs += ct
        print(f"[{eco}] anchors={len(anchors)} candidates={len(candidates)} pairs_found={ct}")

    print(f"TOTAL typosquat pairs: {total_pairs}")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
