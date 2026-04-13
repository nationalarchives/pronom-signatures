import json
import sys
import jsonschema


def validate_actor_fields(json_metadata, actor_file_name):
    errors = []
    with open(".github/scripts/json_schemas/actors-metadata-schema.json", "r") as metadata_schema_file:
        metadata_schema = json.load(metadata_schema_file)
    try:
        validator = jsonschema.Draft202012Validator(schema=metadata_schema,
                                                    format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER)
        validator.validate(json_metadata)
    except jsonschema.exceptions.ValidationError as err:
        errors.append(f"{err.path[0]}: {err.message}")

    return errors


def validate_actor_id_matches_file_name(actor_metadata, actor_file_name):
    error = []
    actor_id_in_file = int(actor_file_name.split(".")[0])
    actor_id = actor_metadata["actorId"]
    if actor_id_in_file != actor_id:
        error.append(f"the actorId provided '{actor_id}' does not match the id in the file name '{actor_file_name}'")
    return error


def decode_json(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def run():
    cli_args = sys.argv
    cli_args_len = len(cli_args) - 1
    if cli_args_len == 2:
        changed_files_file_name = cli_args[2]
        changed_files = []
        with open(changed_files_file_name, "r") as file:
            for file_path in file:
                changed_files.append(file_path.strip())
        if len(changed_files) == 0:
            raise Exception("No files were added/changed in this PR")

        what_to_validate = cli_args[1]
        if what_to_validate == "actors":
            print(f"changed_files", changed_files)
            actor_files_paths = [file for file in changed_files if file[2:].startswith(f"{what_to_validate}/")]
            print("actor_files_paths", actor_files_paths)
            for actor_file_path in actor_files_paths:
                status_and_path = actor_file_path.split("\t")
                file_status = status_and_path[0]

                if file_status != "D":  # D for "Deleted file"
                    actor_file_path = status_and_path[1]
                    actor_metadata = decode_json(actor_file_path)
                    actor_errors = validate_actor_fields(actor_metadata, actor_file_path)

                    actor_file_name = actor_file_path.split("/")[-1]
                    id_error = validate_actor_id_matches_file_name(actor_metadata, actor_file_name)

                    errors = actor_errors + id_error
                    if errors:
                        seperator = "\n   - "
                        raise Exception(f"Errors detected for file '{actor_file_path}':{seperator}{seperator.join(errors)}")
        else:
            raise Exception(f"'{what_to_validate}' is not a valid argument")

    else:
        raise Exception(f"2 arguments were required but received {cli_args_len}")


if __name__ == "__main__":
    run()
