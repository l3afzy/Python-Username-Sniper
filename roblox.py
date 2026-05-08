import requests
import time
import random
import concurrent.futures
import sys
from colorama import Fore, Style, init

init()

MAX_WORKERS = 100
SESSION = requests.Session()


def load_user_agents(path="useragents.txt"):
    default = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"]
    try:
        with open(path) as f:
            agents = [line.strip() for line in f if line.strip()]
        if agents:
            return agents
    except FileNotFoundError:
        with open(path, "w") as f:
            f.write(default[0] + "\n")
        print(Fore.YELLOW + "useragents.txt not found, created with default" + Style.RESET_ALL)
    return default


USER_AGENTS = load_user_agents()


def write_valid(username):
    try:
        with open("valid.txt", "a") as f:
            f.write(f"{username}\n")
    except Exception as e:
        print(Fore.RED + f"Write error: {e}" + Style.RESET_ALL)


def print_progress(current, total):
    bar = "=" * int((current / total) * 50)
    pad = " " * (50 - len(bar))
    pct = (current / total) * 100
    sys.stdout.write(f"\r[{bar}{pad}] {current}/{total} ({pct:.1f}%)")
    sys.stdout.flush()


def check_username(username, total, current):
    username = username.strip()
    if not username or username == "S":
        return

    url = f"https://auth.roblox.com/v1/usernames/validate?Username={username}&Birthday=2000-01-01"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.roblox.com/",
        "DNT": "1",
        "Cache-Control": "no-cache",
    }

    for attempt in range(3):
        try:
            r = SESSION.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            break
        except (ValueError, requests.RequestException):
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
            continue
    else:
        print(Fore.YELLOW + f"\n  failed     {username}" + Style.RESET_ALL)
        return

    print_progress(current, total)

    code = data.get("code")
    if code == 0:
        print(Fore.GREEN + f"\n  AVAILABLE  {username}" + Style.RESET_ALL)
        write_valid(username)
    elif code == 1:
        print(Fore.LIGHTBLACK_EX + f"\n  taken      {username}" + Style.RESET_ALL)
    elif code == 2:
        print(Fore.RED + f"\n  censored   {username}" + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + f"\n  unknown({code}) {username} — {data.get('message', '')}" + Style.RESET_ALL)


def find_last_marker(usernames):
    for i in range(len(usernames) - 1, -1, -1):
        if usernames[i].strip() == "S":
            return i
    return -1


def update_marker(path, index):
    try:
        with open(path) as f:
            lines = f.read().splitlines()
        lines = [l for l in lines if l.strip() != "S"]
        pos = (index // 100) * 100
        if pos < len(lines):
            lines.insert(pos, "S")
        with open(path, "w") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print(Fore.RED + f"Marker update failed: {e}" + Style.RESET_ALL)


def shuffle_valid():
    try:
        with open("valid.txt") as f:
            usernames = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print(Fore.RED + "valid.txt not found" + Style.RESET_ALL)
        return

    if not usernames:
        print(Fore.RED + "No usernames in valid.txt" + Style.RESET_ALL)
        return

    try:
        n = int(input("Number of output files: ").strip())
        if n <= 0:
            raise ValueError
    except ValueError:
        print(Fore.RED + "Invalid number" + Style.RESET_ALL)
        return

    random.shuffle(usernames)
    size, rem = divmod(len(usernames), n)

    start = 0
    for i in range(n):
        end = start + size + (1 if i < rem else 0)
        chunk = usernames[start:end]
        path = f"valid_{i+1}.txt"
        with open(path, "w") as f:
            f.write("\n".join(chunk))
        print(Fore.GREEN + f"  {path} — {len(chunk)} usernames" + Style.RESET_ALL)
        start = end

    print(Fore.CYAN + f"Done. {len(usernames)} usernames → {n} files." + Style.RESET_ALL)


def run_checker():
    try:
        with open("usernames.txt") as f:
            raw = f.read().splitlines()
    except FileNotFoundError:
        print(Fore.RED + "usernames.txt not found" + Style.RESET_ALL)
        return

    usernames = [u for u in raw if u.strip()]
    marker = find_last_marker(usernames)
    start = marker + 1 if marker >= 0 else 0

    print(f"Resuming from {start}" if marker >= 0 else "Starting from beginning")

    usernames = [u for u in usernames if u.strip() != "S"]
    total = len(usernames)

    if not total:
        print(Fore.RED + "No usernames to check" + Style.RESET_ALL)
        return

    if not open("valid.txt", "a").close():
        pass

    print(f"{total} usernames — {MAX_WORKERS} threads — {len(USER_AGENTS)} UAs")

    counter = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(check_username, username, total, start + i + 1): username
            for i, username in enumerate(usernames[start:])
        }
        counter = start

        for future in concurrent.futures.as_completed(futures):
            counter += 1
            try:
                future.result()
            except Exception as e:
                print(Fore.RED + f"\nThread error: {e}" + Style.RESET_ALL)
            if counter % 100 == 0:
                update_marker("usernames.txt", counter)

    update_marker("usernames.txt", counter)
    print(f"\nDone. Checked {total} usernames.")

    try:
        with open("valid.txt") as f:
            count = sum(1 for l in f if l.strip())
        print(Fore.GREEN + f"{count} valid saved to valid.txt" + Style.RESET_ALL)
    except Exception:
        pass


if __name__ == "__main__":
    print("1. Username Checker")
    print("2. Shuffle valid.txt")

    try:
        choice = input("Choice: ").strip()
        if choice == "1":
            run_checker()
        elif choice == "2":
            shuffle_valid()
        else:
            print("Invalid choice")
    except KeyboardInterrupt:
        print("\nInterrupted")

    input("\nEnter to exit...")
