import os
import urllib.request

FAKE_COUNT = 5
REAL_COUNT = 5

FAKE_DIR = "tests/fixtures/fake"
REAL_DIR = "tests/fixtures/real"

os.makedirs(FAKE_DIR, exist_ok=True)
os.makedirs(REAL_DIR, exist_ok=True)

for i in range(FAKE_COUNT):
    url = "https://thispersondoesnotexist.com"
    path = f"{FAKE_DIR}/fake_{i}.jpg"
    urllib.request.urlretrieve(url, path)
    print(f"Downloaded {path}")

for i in range(REAL_COUNT):
    url = f"https://picsum.photos/seed/face{i}/400/400"
    path = f"{REAL_DIR}/real_{i}.jpg"
    urllib.request.urlretrieve(url, path)
    print(f"Downloaded {path}")