"""Command-line entry point."""
import argparse
import json
from orion_ahop.pipeline import inspect_file

def main():
    parser = argparse.ArgumentParser(prog="orion-ahop")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect_cmd = commands.add_parser("inspect", help="inspect a CCSDS KVN file")
    inspect_cmd.add_argument("path")
    args = parser.parse_args()
    if args.command == "inspect":
        print(json.dumps(inspect_file(args.path), indent=2))

if __name__ == "__main__":
    main()
