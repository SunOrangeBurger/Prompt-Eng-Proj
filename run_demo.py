"""Start a fresh demo, display the dashboard and run real Ollama repairs."""
import argparse

from peogai.server import serve


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5-coder:7b")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--no-autostart", action="store_true")
    args = parser.parse_args()
    serve(args.model, 2, args.port, not args.no_open, not args.no_autostart)
