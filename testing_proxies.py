import os
import requests
from dotenv import load_dotenv
import urllib3

# Disable SSL warnings (since we’re ignoring SSL errors)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Target URL
URL = "https://www.asd20.org"

def make_proxy(user, pwd, host, port):
    proxy = f"http://{user}:{pwd}@{host}:{port}"
    return {"http": proxy, "https": proxy}

def test_proxy(label, proxies):
    print(f"\n=== Testing {label} ===")
    try:
        response = requests.get(URL, proxies=proxies, timeout=20, verify=False)
        print(f"Status: {response.status_code}")
        print("Body preview:", response.text[:200].replace("\n", " "))
    except Exception as e:
        print(f"Error using {label}: {e}")

def main():
    # From .env
    env_proxies = make_proxy(
        os.getenv("PROXY_USERNAME"),
        os.getenv("PROXY_PASSWORD"),
        os.getenv("PROXY_HOST"),
        os.getenv("PROXY_PORT"),
    )

    # Direct hardcoded proxy
    direct_proxies = make_proxy(
        "brd-customer-hl_667fd069-zone-residential_proxy_lir",
        "lc9l7vpvbj7v",
        "brd.superproxy.io",
        "33335",
    )

    # Run tests
    test_proxy("ENV Proxy", env_proxies)
    test_proxy("Direct Proxy", direct_proxies)

if __name__ == "__main__":
    main()


    print("#####################")
    print("Loaded .env proxy configuration:")
    print("HOST:", os.getenv("PROXY_HOST"))
    print("PORT:", os.getenv("PROXY_PORT"))
    print("USER:", os.getenv("PROXY_USERNAME"))
    print("PASS:", os.getenv("PROXY_PASSWORD")[:4] + "****")  # hide most of it

