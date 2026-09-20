def string_normalise(s: str) -> str:
    punct = '!@#$%^&*()"№;%:?.,\\][~`/\\-\'_=+⸺'

    university_name = s.strip().lower().replace('ё', 'е')
    result = university_name

    for i in university_name:
        if i in punct:
            result = result.replace(i, '')

    result = ' '.join(result.split())

    return result


def damerau_levenshtein(a: str, b: str) -> int:
    n, m = len(a), len(b)

    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i

    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                cost = 0
            else:
                cost = 1

            deletion = dp[i - 1][j] + 1
            insertion = dp[i][j - 1] + 1
            replacement = dp[i - 1][j - 1] + cost

            dp[i][j] = min(deletion, insertion, replacement)

            if i > 1 and j > 1:
                if a[i - 2] == b[j - 1] and a[i - 1] == b[j - 2]:
                    transposition = dp[i - 2][j - 2] + 1

                    if transposition < dp[i][j]:
                        dp[i][j] = transposition

    return dp[n][m]


def similarity(a: str, b: str) -> float:
    max_length = max(len(a), len(b))

    if max_length == 0:
        return 1.0

    distance = damerau_levenshtein(a, b)

    return 1 - distance / max_length


def find_best_universities(query: str, universities: list) -> dict:
    similarity_top = []

    query = string_normalise(query)

    for university in universities:
        university_name = string_normalise(university['name'])
        university_short_name = string_normalise(university['short_name'])

        scores = []

        scores.append(similarity(query, university_name))
        scores.append(similarity(query, university_short_name))

        if len(query.split()) == 1:
            for variant in university_name.split() + university_short_name.split():
                scores.append(similarity(query, variant))

        similarity_top.append({
            'id': university['id'],
            'score': max(scores),
            'name': university['name'],
            'short_name': university['short_name']
        })

    similarity_top = sorted(similarity_top, key=lambda x: x['score'], reverse=True)[:3]

    if not similarity_top:
        return {'status': 'not_found', 'candidates': []}

    if similarity_top[0]['score'] < 0.4:
        return {'status': 'not_found', 'candidates': []}

    elif similarity_top[0]['score'] >= 0.8:
        return {'status': 'found', 'candidates': [similarity_top[0]]}

    else:
        return {'status': 'suggest', 'candidates': similarity_top}