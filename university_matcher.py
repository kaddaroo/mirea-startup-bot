def string_normalise(s: str) -> str:
    punct = '!@#$%^&*()"№;%:?.,\\][~`/\\-\'_=+⸺'

    result = s.strip().lower().replace("ё", "е")

    for char in result:
        if char in punct:
            result = result.replace(char, "")

    return " ".join(result.split())


def damerau_levenshtein(a: str, b: str) -> int:
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1

            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )

            if (
                i > 1
                and j > 1
                and a[i - 2] == b[j - 1]
                and a[i - 1] == b[j - 2]
            ):
                dp[i][j] = min(
                    dp[i][j],
                    dp[i - 2][j - 2] + 1,
                )

    return dp[n][m]


def similarity(a: str, b: str) -> float:
    a = string_normalise(a)
    b = string_normalise(b)
    max_length = max(len(a), len(b))

    if max_length == 0:
        return 1.0

    return 1 - damerau_levenshtein(a, b) / max_length


def _university_variants(university: dict) -> list[str]:
    variants = [
        university.get("name") or "",
        university.get("short_name") or "",
    ]

    aliases = university.get("aliases") or ""
    if isinstance(aliases, str):
        variants.extend(
            alias.strip()
            for alias in aliases.split(",")
            if alias.strip()
        )

    return variants


def find_best_universities(query: str, universities: list) -> dict:
    query = string_normalise(query)
    similarity_top = []

    for university in universities:
        variants = [
            string_normalise(value)
            for value in _university_variants(university)
            if value
        ]

        if not variants:
            continue

        scores = [similarity(query, variant) for variant in variants]

        if len(query.split()) == 1:
            for variant in variants:
                for word in variant.split():
                    scores.append(similarity(query, word))

        similarity_top.append(
            {
                "id": university["id"],
                "score": max(scores),
                "name": university["name"],
                "short_name": university.get("short_name") or university["name"],
                "aliases": university.get("aliases") or "",
            }
        )

    similarity_top = sorted(
        similarity_top,
        key=lambda item: item["score"],
        reverse=True,
    )[:3]

    if not similarity_top or similarity_top[0]["score"] < 0.4:
        return {"status": "not_found", "candidates": []}

    if similarity_top[0]["score"] >= 0.8:
        return {"status": "found", "candidates": [similarity_top[0]]}

    return {"status": "suggest", "candidates": similarity_top}
