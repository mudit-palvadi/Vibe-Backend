"""pings the old supabase project so it does not get paused

the free projects of supabase are paused after 7 days without activity,
this script keeps the project awake until the data is moved over to aws
"""

import os
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, "..", ".env")


def read_setting(name: str) -> str:
    """reads a setting from the environment, the .env file is the backup"""
    value = os.environ.get(name, "")

    if value:
        return value

    if not os.path.exists(ENV_PATH):
        return ""

    with open(ENV_PATH, encoding="utf-8") as env_file:
        for line in env_file:
            if line.strip().startswith(f"{name}="):
                return line.split("=", 1)[1].strip()

    return ""


def keepalive() -> None:
    supabase_url = read_setting("SUPABASE_URL")
    key = read_setting("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not key:
        print("the supabase url or the service role key is missing")
        return

    url = f"{supabase_url}/rest/v1/songs?select=id&limit=1"
    request = urllib.request.Request(
        url,
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        print(f"supabase answered with {response.status}")


if __name__ == "__main__":
    keepalive()
