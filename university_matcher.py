def string_normalise(s: str) -> str:
    punct = '!@#$%^&*()\"№;%:?.,\\][~`/'
    university_name = s.strip().lower().replace('ё', 'е')
    result = university_name
    for i in university_name:
        if i in punct: 
            result = result.replace(i, '')
    result = ' '.join(result.split())
    return result

def damerau_levenshtein(a:str, b:str) -> int:
    a = string_normalise(a)   # User input
    b = string_normalise(b)   # Template from DB
    n, m = len(a), len(b)
    dp = [[0] * (m+1) for _ in range(n+1)]

    for i in range(n+1):
        dp[i][0] = i

    for j in range(m+1):
        dp[0][j] = j

        
    for i in range(1, n+1):
        for j in range(1, m+1):
            if a[i-1] == b[j-1]:
                cost = 0
            else:
                cost = 1
                
            deletion = dp[i-1][j] + 1
            insertion = dp[i][j-1] + 1
            replacement = dp[i-1][j-1] + cost
            
            dp[i][j] = min(deletion, insertion, replacement)
                
            if i > 1 and j > 1:
                if a[i-2] == b[j-1] and a[i-1] == b[j-2]:
                    transposition = dp[i-2][j-2] + 1
                    if transposition < dp[i][j]:
                        dp[i][j] = transposition
    return dp[n][m]

def similarity(a, b) -> float:
    a = string_normalise(a)
    b = string_normalise(b)
    max_length = max(len(b), len(a))
    distance = damerau_levenshtein(a, b)
    
    if max_length == 0:
        return 1
    else: 
        return 1 - distance/max_length
    
        
def find_best_universities(query: str, universities: dict) -> dict:
    similarity_top = []
    query = string_normalise(query)
    for university_id, university_name in universities.items():
        scores = []
        scores.append(similarity(query, university_name['name']))
        scores.append(similarity(query, university_name['short_name']))
        if len(query.split()) == 1:
            for variants in university_name['name'].split() + university_name['short_name'].split():
                scores.append(similarity(query, variants))
        
            
        similarity_top.append({'id': university_id, 'score': max(scores), 'name': university_name['name'], 'short_name': university_name['short_name']})
    similarity_top = sorted(similarity_top, key=lambda x: x['score'], reverse=True)[:3]
    if similarity_top[0]['score'] < 0.4:
        return {'status': 'not_found', 'candidates': []}
    elif similarity_top[0]['score'] >= 0.8:
        return {'status': 'found', 'candidates': [similarity_top[0]]}
    else:
        return {'status': 'suggest', 'candidates': similarity_top}