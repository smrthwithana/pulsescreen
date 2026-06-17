from __future__ import annotations

try:
    from beatbridge.main import main
except ModuleNotFoundError as exc:
    missing = exc.name or "a dependency"
    print(f"Missing dependency: {missing}")
    print("Install the project dependencies with: python -m pip install -r requirements.txt")
    raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
