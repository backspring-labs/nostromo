"""Independent no-model deadline/routing timer; never reads a role provider key."""
from .cli import call


def main():
    failed = False
    for item in call({"command": "tracked", "args": {}}):
        try:
            call({"command": "advance", "args": {"campaign": item["id"]}})
        except Exception:
            failed = True
            print(item["id"] + ": automation unreadable; no success inferred", flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
