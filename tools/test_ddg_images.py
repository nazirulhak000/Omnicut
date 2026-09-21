import urllib.request
import urllib.parse
import json
import re

def search_posters(query, max_results=3):
    # Using DuckDuckGo image search endpoint
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    url = "https://duckduckgo.com/i.js?q=" + urllib.parse.quote(query) + "&o=json"
    req = urllib.request.Request(url, headers=headers)
    try:
        # First get vqd token
        token_req = urllib.request.Request("https://duckduckgo.com/?q=" + urllib.parse.quote(query), headers=headers)
        with urllib.request.urlopen(token_req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            vqd_match = re.search(r'vqd=([\d-]+)', html) or re.search(r'vqd=([a-zA-Z0-9_-]+)', html)
            vqd = vqd_match.group(1) if vqd_match else ""
        
        if not vqd:
            return []
            
        api_url = f"https://duckduckgo.com/i.js?q={urllib.parse.quote(query)}&o=json&vqd={vqd}&p=1"
        api_req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(api_req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = []
            for r in data.get("results", [])[:max_results]:
                results.append({"title": r.get("title"), "image": r.get("image")})
            return results
    except Exception as e:
        print(f"Error searching for {query}: {e}")
        return []

if __name__ == "__main__":
    res = search_posters("Xiaomi MIX Flip official launch poster", 3)
    for r in res:
        print(r)
