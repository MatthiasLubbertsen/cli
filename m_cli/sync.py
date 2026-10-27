import json
import os
import urllib.error
import urllib.request

# overridable so the sync code can be tested against a local fake server
API = os.environ.get("M_GITHUB_API", "https://api.github.com")
GIST_FILENAME = "m-commands.json"
GIST_DESCRIPTION = "m cli - synced commands (do not rename the file inside this gist)"
THEME_FILENAME = "theme.omp.json"
THEME_DESCRIPTION = "m cli - oh-my-posh theme (do not rename the file inside this gist)"


def _request(method, path, token, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "m-cli")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"github api error {e.code}: {detail}") from e


def find_gist_id(token, filename=GIST_FILENAME):
    page = 1
    while True:
        gists = _request("GET", f"/gists?per_page=100&page={page}", token)
        if not gists:
            return None
        for g in gists:
            if filename in g.get("files", {}):
                return g["id"]
        page += 1


def create_gist(token, content, filename=GIST_FILENAME, description=GIST_DESCRIPTION):
    body = {
        "description": description,
        "public": False,
        "files": {filename: {"content": content}},
    }
    return _request("POST", "/gists", token, body)["id"]


def push(token, gist_id, content, filename=GIST_FILENAME):
    body = {"files": {filename: {"content": content}}}
    _request("PATCH", f"/gists/{gist_id}", token, body)


def pull(token, gist_id, filename=GIST_FILENAME):
    result = _request("GET", f"/gists/{gist_id}", token)
    return result["files"][filename]["content"]


def raw_url(token, gist_id, filename):
    """Link that always serves the latest version of the file, no token needed
    (secret gists are readable by anyone who has the link)."""
    owner = _request("GET", f"/gists/{gist_id}", token)["owner"]["login"]
    return f"https://gist.githubusercontent.com/{owner}/{gist_id}/raw/{filename}"
