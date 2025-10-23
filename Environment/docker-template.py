#!/usr/bin/env python3

import sys
from pathlib import Path
from jinja2 import Environment, ChoiceLoader, FileSystemLoader


def main():
    if len(sys.argv) < 3:
        print("Usage: docker-template.py <input_file> <output_file>", file=sys.stderr)
        sys.exit(1)

    input_file = Path(sys.argv[1]).resolve()
    output_file = Path(sys.argv[2]).resolve()

    # Get directories for the loaders
    input_dir = input_file.resolve().parent
    script_dir = Path(__file__).resolve().parent

    # Create ChoiceLoader with FileSystemLoaders in order of precedence
    loaders = [
        FileSystemLoader(str(input_dir)),
        FileSystemLoader(str(script_dir)),
    ]

    # Create Jinja2 environment with ChoiceLoader
    env = Environment(loader=ChoiceLoader(loaders))

    # Load and render the template
    with open(input_file, "r") as f:
        template_content = f.read()

    template = env.from_string(template_content)
    output = template.render()

    # Write to output file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        f.write(output)


if __name__ == "__main__":
    main()
