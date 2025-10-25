import json
import glob
import os
import pickle
import shutil
import sqlite3
import yaml

LOCALIZATION_LIST = {
    "de": "de",
    "en-us": "en",
    "es": "es",
    "fr": "fr",
    "it": "it",
    "ja": "ja",
    "ko": "ko",
    "ru": "ru",
    "zh": "zh",
}


def convert_value(value, column, options, strings):
    if type(value) == dict:
        # Allow dicts that are a string in different languages. But all other need column definitions.
        if "en" not in value.keys():
            raise Exception("Define nested objects with 'columns'")

        # Sometimes localization is empty (or resolved to an invalid key); delete those keys.
        new_value = {}
        for language, v in list(value.items()):
            if v != "" and not v.startswith("EVE/Evetypes/Types/Descriptions"):
                new_value[language] = v
        # If the key is now empty, delete it.
        if not new_value:
            return None
        # Some files have empty language entries if the rest is present. Others
        # do not mention empty languages.
        if column.get("ignore-empty"):
            value = new_value

    if "type" in column:
        if column["type"] == "bool":
            value = bool(value)
        if column["type"] == "language":
            stringID = value
            value = {}

            for language in strings:
                if stringID not in strings[language]:
                    continue
                value[language] = strings[language][stringID][0]

    # This is an estimation, which fixes most rounding issues. Not all.
    # This can simply be explained that the original source is human-written,
    # and the source for this scripting is a Python float.
    if type(value) == float and column.get("round", True):
        value = round(value, ndigits=column.get("precision", 6))

    if "condition" in column:
        if column["condition"] == "if-true":
            if value is False:
                return None
        elif column["condition"] == "if-not-zero":
            if value == 0:
                return None
        elif column["condition"] == "if-not-zero-or-one":
            if value == 0 or value == 1:
                return None

    return value


def convert_object(json_value, columns, options, strings):
    jsonl_value = {}
    for jsonl_name, column in columns.items():
        if column is None:
            column = {}

        json_fields = column.get("json", jsonl_name).split(".")
        value = json_value
        for json_field in json_fields:
            if value is None:
                break
            value = value.get(json_field)
        if value is None:
            if column.get("condition") == "if-set":
                return None
            continue

        if column.get("type") == "number-dict":
            if "columns" in column:
                value = {int(k): convert_object(v, column["columns"], options, strings) for k, v in value.items()}
            else:
                value = {int(k): convert_value(v, column, options, strings) for k, v in value.items()}
        elif type(value) == list:
            jsonl_v = []
            for v in value:
                if "columns" in column:
                    jsonl_v.append(convert_object(v, column["columns"], options, strings))
                else:
                    jsonl_v.append(convert_value(v, column, options, strings))
            value = jsonl_v
        elif "columns" in column:
            value = convert_object(value, column["columns"], options, strings)
        else:
            value = convert_value(v, column, options, strings)

        if value is None:
            continue

        jsonl_value[jsonl_name] = value

    return jsonl_value


def main():
    # Load all the localizations.
    strings = {}
    for localization in glob.glob("data/localization_fsd_*.pickle"):
        language = os.path.splitext(os.path.basename(localization))[0].split("_")[-1]
        if language not in LOCALIZATION_LIST:
            continue

        print("Loading '" + LOCALIZATION_LIST[language] + "' ...")
        with open(localization, "rb") as f:
            strings[LOCALIZATION_LIST[language]] = pickle.load(f)[1]

    os.makedirs("jsonl", exist_ok=True)
    shutil.copy("data/build-number.txt", "jsonl/build-number.txt")

    with open("mapping.yaml") as f:
        mapping = yaml.safe_load(f)

    for jsonl_filename, jsonl_config in mapping.items():
        print(f"Creating {jsonl_filename}.jsonl ...")

        if jsonl_config.get("sqlite"):
            con = sqlite3.connect(f"data/{jsonl_config['sqlite']}")
            cur = con.cursor()
            res = cur.execute(f"SELECT * FROM cache")

            json_data = {}
            for row in res:
                json_data[row[0]] = json.loads(row[1])
        else:
            with open(f"json/{jsonl_config['json']}", encoding="utf-8") as f:
                json_data = json.load(f)

        options = jsonl_config.get("options", {})

        with open(f"jsonl/{jsonl_filename}.jsonl", "w", encoding="utf-8") as f:
            for json_key, json_value in json_data.items():
                jsonl_value = convert_object(json_value, jsonl_config["columns"], options, strings)
                if jsonl_value is None:
                    continue

                if options.get("key-type", "int") == "int":
                    json_key = int(json_key)

                # Create a record with the key and the converted data
                record = {
                    "id": json_key,
                    "data": jsonl_value
                }
                
                # Write as a single line of JSON
                f.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')


if __name__ == "__main__":
    main()
