import json
import os
import sys
import jsonschema


def decode_json(file_path):
    with open(file_path, "r") as json_file:
        try:
            json_as_dict = json.load(json_file)
        except Exception as err:
            print(f"Error parsing JSON: {err}")
        return json_as_dict


def raise_validation_errors(errors, file_path):
    if errors:
        seperator = "\n   - "
        raise Exception(
            f"Errors detected for file '{file_path}':{seperator}{seperator.join(errors)}")


def validate_json(json_metadata, schema):
    errors = []
    metadata_schema = decode_json(f".github/scripts/json_schemas/{schema}.json")

    try:
        validator = jsonschema.Draft202012Validator(schema=metadata_schema,
                                                    format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER)
        validator.validate(json_metadata)
    except jsonschema.exceptions.ValidationError as err:
        errors.append(f"{err.path[0]}: {err.message}")

    return errors


def check_relationship(all_json, format_json, relationship, first_type, second_type):
    if relationship["relationshipType"] == first_type:
        related_id = relationship["relatedFormatID"]
        has_two_way = len([x for x in all_json[related_id]["relationships"] if
                           x["relationshipType"] == second_type and x["relatedFormatID"] == format_json[
                               "fileFormatID"]]) == 1
        if not has_two_way:
            def get_puid(obj): return [x for x in obj["identifiers"] if x["identifierType"] == "PUID"][0]["identifierText"]
            puid = get_puid(format_json)
            related_puid = get_puid(all_json[related_id])
            raise Exception(f"No two way relationship between {puid} and {related_puid}")


relationship_pairs = [
    ("Has priority over", "Has lower priority than"),
    ("Is subtype of", "Is supertype of"),
    ("Is previous version of", "Is subsequent version of"),
    ("Can be contained by", "Can contain"),
    ("Equivalent to", "Equivalent to")
]

def json_by_id():
    all_json = {}
    for sub_dir in ["fmt", "x-fmt"]:
        sig_files = os.listdir(f"signatures/{sub_dir}")
        for file in sig_files:
            json_path = f"signatures/{sub_dir}/{file}"
            sig = decode_json(json_path)
            all_json[sig["fileFormatID"]] = sig
    return all_json


def json_from_git_status(git_status):
    status_and_path = git_status.split("\t")
    file_status = status_and_path[0]

    if file_status != "D":  # D for "Deleted file"
        actor_file_path = status_and_path[1]
        return decode_json(actor_file_path)
    else:
        return {}


def run():
    cli_args = sys.argv
    cli_args_len = len(cli_args) - 1
    if cli_args_len == 1:
        changed_files_file_name = cli_args[1]
        changed_files = []
        with open(changed_files_file_name, "r") as file:
            for file_path in file:
                changed_files.append(file_path.strip())
        if len(changed_files) == 0:
            raise Exception("No files were added/changed in this PR")

        actor_files_paths = [file for file in changed_files if file[2:].startswith(f"submissions/actors/")]
        for actor_file_path in actor_files_paths:
            actor_errors = validate_json(json_from_git_status(actor_file_path), "actors-metadata-schema")
            raise_validation_errors(actor_errors, actor_file_path)

        signature_file_paths = [file for file in changed_files if file[2:].startswith(f"submissions/") or file[2:].startswith(f"signatures/")]
        if signature_file_paths:
            all_json = json_by_id()
            for signature_submission in signature_file_paths:
                submission_json = json_from_git_status(signature_submission)
                signature_errors = validate_json(submission_json, "signature-schema")
                raise_validation_errors(signature_errors, signature_submission)
                if "relationships" in submission_json:
                    for each_relationship in submission_json["relationships"]:
                        for each_pair in relationship_pairs:
                            check_relationship(all_json, submission_json, each_relationship, each_pair[0], each_pair[1])
                            check_relationship(all_json, submission_json, each_relationship, each_pair[1], each_pair[0])
    else:
        raise Exception(f"1 argument was required but received {cli_args_len}")



if __name__ == "__main__":
    run()
