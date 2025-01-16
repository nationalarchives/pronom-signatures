import json
import os
import sys


def get_next_ids():
    all_file_format_ids = []
    all_signature_ids = []
    all_puid_ids = []
    for sig_dir in ['fmt', 'x-fmt']:
        path = f'signatures/{sig_dir}'
        files = os.listdir(path)
        for file in files:
            with (open(f'{path}/{file}', 'r') as format_file):
                format_json = json.load(format_file)
                all_file_format_ids.append(format_json['fileFormatID'])
                puid = [ifs['identifierText'] for ifs in format_json['identifiers'] if ifs['identifierType'] == 'PUID']
                all_puid_ids.append(int(puid[0].split('/')[1]))
                for signature in format_json['internalSignatures']:
                    all_signature_ids.append(signature['signatureID'])
    return sorted(all_file_format_ids)[-1], sorted(all_signature_ids)[-1], sorted(all_puid_ids)[-1]


def get_next_actor_id():
    all_ids = []
    actor_files = os.listdir('actors')
    for file in actor_files:
        with open(f'actors/{file}') as actor_file:
            actor_json = json.load(actor_file)
            all_ids.append(actor_json['actorId'])
    return max(all_ids)


def move_json():
    file_format_id, signature_id, puid_id = get_next_ids()
    if os.path.isdir('actors'):
        actor_path = 'submissions/actors'
        actor_submission_files = [f for f in os.listdir(actor_path) if os.path.isfile(f'{actor_path}/{f}')]
        next_id = get_next_actor_id() + 1
        for new_actor_submission in actor_submission_files:
            with open(f'submissions/actors/{new_actor_submission}') as new_submission_file:
                new_submission_json = json.load(new_submission_file)
                new_submission_json['actorId'] = next_id
                with open(f'actors/{next_id}.json', 'w') as new_actor_file:
                    json.dump(new_submission_json, new_actor_file, indent=2)
                os.remove(f'{actor_path}/{new_actor_submission}')
                next_id = next_id + 1

    if os.path.isdir('submissions'):
        submissions = [f for f in os.listdir('submissions') if os.path.isfile(f'submissions/{f}')]
        new_puid = f'fmt/{puid_id + 1}'
        for submission in submissions:
            with open(f'submissions/{submission}') as s:
                submission_json = json.load(s)
            submission_json['fileFormatID'] = file_format_id + 1
            for idx, signature in enumerate(submission_json['internalSignatures']):
                signature['signatureID'] = signature_id + (idx + 1)
            new_identifier = {'identifierType': 'PUID', 'identifierText': new_puid}
            existing_identifiers = submission_json['identifiers'] if 'identifiers' in submission_json else []
            existing_identifiers.append(new_identifier)
            submission_json['identifiers'] = existing_identifiers
            with open(f'signatures/{new_puid}.json', 'w') as sig:
                json.dump(submission_json, sig, indent=2)
            os.remove(f'submissions/{submission}')
        return new_puid


def move_files(puid):
    if os.path.isdir('submissions/files'):
        test_files = os.listdir('submissions/files')
        for idx, file in enumerate(test_files):
            suffix = file.split('.')[-1]
            new_puid_name = puid.replace('/', '-')
            os.rename(f'submissions/files/{file}', f'submissions/files/{new_puid_name}-{idx + 1}.{suffix}')


def delete_files():
    if os.path.isdir('submissions/files'):
        test_files = os.listdir('submissions/files')
        for file in test_files:
            os.remove(f'submissions/files/{file}')


def run():
    if len(sys.argv) > 1 and sys.argv[1] == "--release":
        move_json()
        delete_files()
    else:
        new_puid = move_json()
        move_files(new_puid)


if __name__ == "__main__":
    run()
