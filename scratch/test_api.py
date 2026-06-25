import json
import urllib.request
import urllib.parse

def test_api():
    base_url = "https://genshin-impact.fandom.com/api.php"
    
    # Query parameters
    params = {
        "action": "query",
        "titles": "Nahida",
        "prop": "extracts|links",
        "explaintext": "1",
        "exintro": "1",
        "plnamespace": "0",
        "pllimit": "20",
        "format": "json",
        "redirects": "1"
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "GraphyraDemoCorpusGenerator/1.0 (contact: test@example.com)"}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error calling MediaWiki API: {e}")

if __name__ == "__main__":
    test_api()
