# Removes lines from extra-mappings.csv that already exist in mappings.csv

import argparse
from pathlib import Path
from pack_paths import add_pack_argument, get_pack_paths

# File names
script_dir = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
add_pack_argument(parser)
args = parser.parse_args()
extra_path, _ = get_pack_paths(script_dir, args.pack)
mappings_file = extra_path / 'mappings.csv'
extra_mappings_file = extra_path / 'extra-mappings.csv'

def read_mappings(file_name):
    with open(file_name, 'r', encoding='utf-8') as file:
        return set(file.readlines())

def remove_duplicate_generic_mappings():
    mappings = read_mappings(mappings_file)
    with open(extra_mappings_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    with open(extra_mappings_file, 'w', encoding='utf-8') as file:
        for line in lines:
            if line.strip() and line not in mappings:
                file.write(line)

def main():
    remove_duplicate_generic_mappings()

if __name__ == "__main__":
    main()