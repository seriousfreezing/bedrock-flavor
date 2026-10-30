import csv
import argparse
import difflib
import json
import re
from pathlib import Path
from pack_paths import add_pack_argument, get_pack_paths

scriptDir = Path(__file__).resolve().parent
inputPath = scriptDir / "Input"
parser = argparse.ArgumentParser()
add_pack_argument(parser)
parser.add_argument("je_langs", nargs="?")
parser.add_argument("be_langs", nargs="?")
args = parser.parse_args()
extraPath, outputPath = get_pack_paths(scriptDir, args.pack)
outputPath.mkdir(exist_ok=True)

jeLangs = [ 
    "bg_bg", "cs_cz", "da_dk", "de_de", "el_gr", "en_gb", "en_au",
    "en_ca", "en_nz", "en_us", "es_es", "es_mx", "et_ee", "fi_fi", 
    "fr_ca", "fr_fr", "hu_hu", "id_id", "it_it", "ja_jp", "ko_kr", 
    "no_no", "nl_nl", "pl_pl", "pt_br", "pt_pt", "ru_ru", "sk_sk", 
    "sv_se", "tr_tr", "uk_ua", "zh_cn", "zh_tw",
]
beLangs = [
    "bg_BG", "cs_CZ", "da_DK", "de_DE", "el_GR", "en_GB", "en_GB",
    "en_GB", "en_GB", "en_US", "es_ES", "es_MX", "et_EE", "fi_FI", 
    "fr_CA", "fr_FR", "hu_HU", "id_ID", "it_IT", "ja_JP", "ko_KR", 
    "nb_NO", "nl_NL", "pl_PL", "pt_BR", "pt_PT", "ru_RU", "sk_SK", 
    "sv_SE", "tr_TR", "uk_UA", "zh_CN", "zh_TW",
]

# Optionally provide Java and Bedrock language lists as comma-separated arguments.
if (args.je_langs is None) != (args.be_langs is None):
    raise SystemExit("Provide both Java and Bedrock language lists, or neither.")
if args.je_langs is not None:
    jeLangs = [lang.strip() for lang in args.je_langs.split(",") if lang.strip()]
    beLangs = [lang.strip() for lang in args.be_langs.split(",") if lang.strip()]

if len(jeLangs) != len(beLangs):
    raise SystemExit("Java and Bedrock language lists must have the same number of entries.")

if jeLangs:
    languagePairs = list(zip(jeLangs, beLangs))
    for jeLang, beLang in languagePairs:
        if not (inputPath / (jeLang + ".json")).exists() or not (inputPath / (beLang + ".lang")).exists():
            raise SystemExit("Missing input file for language pair: " + jeLang + ", " + beLang)
else:
    languagePairs = []
    for beFile in sorted(inputPath.glob("*.lang")):
        jeLang = beFile.stem.lower()
        if (inputPath / (jeLang + ".json")).exists():
            languagePairs.append((jeLang, beFile.stem))
        else:
            print("No matching Java Edition language file for " + beFile.name)

mapDict = {}


def parse_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def parse_unicode_escapes(paths):
    escapes = {}
    for path in paths:
        with open(path, "r", encoding="utf-8") as file:
            for code in re.findall(r"\\u([0-9a-fA-F]{4})", file.read()):
                escapes[chr(int(code, 16))] = code
    return escapes


def parse_csv(path, toDict):
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8", newline="") as file:
        for row in csv.reader(file):
            if len(row) >= 2:
                toDict[row[0]] = row[1]


def parse_lang(path):
    parsed = {}
    with open(path, "r", encoding="utf-8") as file:
        for row in file:
            row = row.rstrip("\r\n")
            if row and not row.startswith("##") and "=" in row:
                key, value = row.split("=", 1)
                parsed[key.strip()] = value
    return parsed


print("Opening mapped strings...")
parse_csv(extraPath / "mappings.csv", mapDict)
parse_csv(extraPath / "extra-mappings.csv", mapDict)

overrides = parse_json(extraPath / "overrides.json")
prefixes = parse_json(extraPath / "prefixes.json")
sourceEnglish = parse_json(extraPath / "source-en_us.json")
if args.pack == "bedrocking":
    mapDict = {
        bedrockKey: sourceKey
        for bedrockKey, sourceKey in mapDict.items()
        if sourceKey in sourceEnglish
    }
unicodeEscapes = parse_unicode_escapes(extraPath.glob("*.json"))
sourceBedrockEnglish = parse_lang(inputPath / "en_US.lang")
sourceKeysByValue = {}
sourceKeysByCasefoldedValue = {}
for beKey, value in sourceBedrockEnglish.items():
    sourceKeysByValue.setdefault(value, []).append(beKey)
    sourceKeysByCasefoldedValue.setdefault(value.casefold(), []).append(beKey)

# Output key order: Bedrocking follows source-en_us.json; BedrockFlavor follows the
# Java Edition en_us.json first, then the extra keys from source-en_us.json.
referenceKeys = list(sourceEnglish)
if args.pack != "bedrocking" and (inputPath / "en_us.json").exists():
    referenceKeys = list(parse_json(inputPath / "en_us.json")) + referenceKeys
referenceOrder = {}
for referenceKey in referenceKeys:
    referenceOrder.setdefault(referenceKey, len(referenceOrder))

for jeLang, beLang in languagePairs:
    jeFile = inputPath / (jeLang + ".json")
    beFile = inputPath / (beLang + ".lang")
    jeDict = parse_json(jeFile)
    beDict = parse_lang(beFile)
    outputDict = {}

    if jeLang == "en_us":
        outputDict.update(sourceEnglish)

    for beKey, jeKey in mapDict.items():
        targetExists = jeKey in sourceEnglish if args.pack == "bedrocking" else jeKey in jeDict
        if beKey in beDict and targetExists:
            outputDict[jeKey] = beDict[beKey]

    for sourceKey, sourceValue in sourceEnglish.items():
        matchingKeys = sourceKeysByValue.get(sourceValue, [])
        if not matchingKeys:
            matchingKeys = sourceKeysByCasefoldedValue.get(sourceValue.casefold(), [])
        matchingKeys = [key for key in matchingKeys if key in beDict]
        if matchingKeys:
            beKey = max(
                matchingKeys,
                key=lambda key: difflib.SequenceMatcher(
                    None, sourceKey.casefold(), key.casefold()
                ).ratio(),
            )
            outputDict[sourceKey] = beDict[beKey]

    localeExtraPath = extraPath / ("extra-" + jeLang + ".json")
    if localeExtraPath.exists():
        outputDict.update(parse_json(localeExtraPath))

    prefixedKeys = set()
    for key, prefix in prefixes.items():
        targetKey = key if key in outputDict or key in jeDict else mapDict.get(key, key)
        if targetKey in outputDict or targetKey in jeDict:
            value = outputDict[targetKey] if targetKey in outputDict else jeDict[targetKey]
            while prefix and value.startswith(prefix):
                value = value[len(prefix):]
            outputDict[targetKey] = prefix + value
            prefixedKeys.add(targetKey)

    for key, value in overrides.items():
        targetKey = key if key in jeDict or key in outputDict else mapDict.get(key, key)
        outputDict[targetKey] = value

    outputDict = {
        key: value
        for key, value in outputDict.items()
        if value != jeDict.get(key) or key in prefixedKeys
    }

    outputDict = dict(
        sorted(outputDict.items(), key=lambda item: referenceOrder.get(item[0], len(referenceOrder)))
    )

    outputFile = outputPath / (jeLang + ".json")
    with open(outputFile, "w", encoding="utf-8") as file:
        serialized = json.dumps(outputDict, ensure_ascii=False, indent=4)
        for character, code in unicodeEscapes.items():
            serialized = serialized.replace(character, "\\u" + code)
        file.write(serialized + "\n")
    print("Ported " + beLang + ".lang to " + outputFile.as_posix())