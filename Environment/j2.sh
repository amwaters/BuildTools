#!/bin/bash
set -euo pipefail
export SCRIPT_DIR="$(dirname "$(realpath "$0")")"

python3 -c "$(cat << 'EOF'

import argparse, jinja2, os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('template', type=str)
args = parser.parse_args()

template_path = Path(args.template)

template = jinja2.Environment(loader=jinja2.ChoiceLoader([
    jinja2.DictLoader({
        '<root>': template_path.read_text()
    }),
    jinja2.FileSystemLoader(template_path.parent),
    jinja2.FileSystemLoader(os.getenv('SCRIPT_DIR')),
    jinja2.FileSystemLoader(Path.cwd())
]))

template = template.get_template('<root>')
for piece in template.generate():
    print(piece, end='')

EOF
)" "$1"
