import json
import re
import pyodbc
import urllib.request
import xml.etree.ElementTree as Et
from datetime import datetime
from itertools import groupby

"""
Generates the signature json from a backup of the PRONOM MSSQL database. To restore, download the backup file then:
docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=P@ssw0rd" -v $PWD/backup:/var/opt/mssql/backup  -p 1433:1433 \
 --name pronom --hostname sql1 -d mcr.microsoft.com/mssql/server:2022-latest
RESTORE DATABASE PRONOM
    FROM DISK = '/var/opt/mssql/backup/PRONOM6_backup.bak'
    WITH MOVE 'Pronom4' TO '/var/opt/mssql/data/PRONOM6.mdf',
    MOVE 'ftrow_PRONOM_Search' TO '/var/opt/mssql/data/ftrow_PRONOM_Search.ndf',
    MOVE 'Pronom4_log' TO '/var/opt/mssql/data/PRONOM6_1.ldf'
GO
"""


def to_camel_case(s):
    """
    Converts a PascalCase string to camelCase.
    - Lowercases up to the second instance of an uppercase letter.
    - Keeps the rest of the string as is.

    :param s: The input PascalCase string.
    :return: The camelCase string.
    """
    # Match everything until the second uppercase letter or the end of the string
    match = re.match(r"([A-Z][a-z]*)([A-Z].*)?", s)
    if not match:
        return s.lower()  # If no match, return lowercased string

    # Lowercase the first part, leave the second part as is
    first, rest = match.groups()
    return first.lower() + (rest or "")


def generate_container_signatures():
    contents = urllib.request.urlopen(
        "https://cdn.nationalarchives.gov.uk/documents/container-signature-20240715.xml").read()
    container_string = re.sub(r'\s+', ' ', contents.decode('utf-8'))
    container_xml = Et.fromstring(container_string)
    container_signatures = container_xml[0]
    file_format_mappings = container_xml[1]

    all_signatures = {}
    all_mappings = {}
    for mapping in file_format_mappings:
        all_mappings[mapping.attrib['signatureId']] = mapping.attrib['Puid']

    for signature in container_signatures:
        signature_byte_sequences = process_byte_sequences(signature)
        signature_json = {
            'containerType': signature.attrib['ContainerType'],
            'id': signature.attrib['Id'],
            'description': signature[0].text,
            'files': []
        }
        if len(signature_byte_sequences) > 0:
            signature_json['byteSequences'] = signature_byte_sequences

        for file in signature.iter('File'):
            file_json = {'path': [f for f in file if f.tag == 'Path'][0].text}
            file_byte_sequences = process_byte_sequences(file)
            if len(file_byte_sequences) > 0:
                file_json['byteSequences'] = file_byte_sequences
            signature_json['files'].append(file_json)
        puid = all_mappings[signature_json['id']]
        if puid in all_signatures:
            all_signatures[puid].append(signature_json)
        else:
            all_signatures[puid] = [signature_json]
    return all_signatures


def process_byte_sequences(elem):
    all_sequences = []
    for byte_sequence in elem.findall(
            'BinarySignatures/InternalSignatureCollection/InternalSignature/ByteSequence'):
        byte_sequence_json = {'subSequences': []}
        if 'Reference' in byte_sequence.attrib:
            byte_sequence_json['reference'] = byte_sequence.attrib['Reference']
        for sub_sequence in byte_sequence.iter('SubSequence'):
            sub_sequence_json = {to_camel_case(key): value for key, value in sub_sequence.attrib.items()}

            sequence = sub_sequence.find('Sequence')
            if sequence is not None:
                sub_sequence_json['sequence'] = sequence.text
            right_fragment = sub_sequence.find('RightFragment')
            if right_fragment is not None:
                right_fragment_json = {to_camel_case(key): value for key, value in right_fragment.attrib.items()}
                sub_sequence_json['rightFragment'] = right_fragment_json

            byte_sequence_json['subSequences'].append(sub_sequence_json)
        all_sequences.append(byte_sequence_json)
    return all_sequences


def get_connection(server, database, username, password):
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        f"TrustServerCertificate=Yes;"
    )

    # Connect to the database
    return pyodbc.connect(conn_str)


def get_file_format_ids():
    conn = get_connection("localhost", "PRONOM", "sa", "P@ssw0rd")
    cursor = conn.cursor()
    cursor.execute(f"SELECT file_format_id From file_formats;")
    rows = cursor.fetchall()
    return [row[0] for row in rows]


def execute_procedure(procedure_name, file_format_id):
    conn = get_connection("localhost", "PRONOM", "sa", "P@ssw0rd")

    cursor = conn.cursor()
    cursor.execute(f"EXEC {procedure_name} {file_format_id}")

    return cursor.fetchall()


def get_internal_signatures(file_format_id):
    signatures_result = []
    byte_sequence_rows = execute_procedure("proc_get_format_int_sig_byte_sequences_by_id", file_format_id)
    internal_signatures = execute_procedure("proc_get_format_internal_signatures_by_id", file_format_id)
    byte_sequences = []
    for byte_sequence_row in byte_sequence_rows:
        each_identifier = {}
        for key in byte_sequence_row.cursor_description:
            if key[0] in ["PositionType", "Offset", "MaxOffset", "ByteSequence", "Endianness", "SignatureID"]:
                value = byte_sequence_row[byte_sequence_row.cursor_description.index(key)]
                each_identifier[to_camel_case(key[0])] = value

        byte_sequences.append(each_identifier)

    byte_sequences.sort(key=lambda x: x['signatureID'])
    grouped_items = {key: list(group) for key, group in groupby(byte_sequences, key=lambda x: x['signatureID'])}

    for sig in internal_signatures:
        signature_id = sig[1]
        list(map(lambda d: d.pop("signatureID", None), grouped_items[signature_id]))
        result = {
            "signatureID": signature_id,
            "name": sig[2],
            "note": sig[3],
            "byteSequences": grouped_items[signature_id]
        }
        signatures_result.append(result)

    return signatures_result


def get_external_signatures(file_format_id):
    external_signatures_result = []
    rows = execute_procedure("proc_get_format_external_signatures_by_id", file_format_id)
    for row in rows:
        each_identifier = {}
        for key in row.cursor_description:
            if key[0] in ["ExternalSignature", "SignatureType"]:
                value = row[row.cursor_description.index(key)]
                each_identifier[to_camel_case(key[0])] = value
        external_signatures_result.append(each_identifier)
    return external_signatures_result


def get_format_identifiers(file_format_id):
    identifiers_result = []
    rows = execute_procedure("proc_get_format_identifiers_by_id", file_format_id)
    for row in rows:
        each_identifier = {}
        for key in row.cursor_description:
            if key[0] in ["IdentifierText", "IdentifierType"]:
                value = row[row.cursor_description.index(key)]
                each_identifier[to_camel_case(key[0])] = value
        identifiers_result.append(each_identifier)
    return identifiers_result


def get_format_relationships(file_format_id):
    format_relationship_result = []
    rows = execute_procedure("proc_get_format_relationships_by_id", file_format_id)
    for row in rows:
        each_identifier = {}
        for key in row.cursor_description:
            if key[0] in ["RelationshipType", "RelatedFormatName", "RelatedFormatID"]:
                value = row[row.cursor_description.index(key)]
                each_identifier[to_camel_case(key[0])] = value
        format_relationship_result.append(each_identifier)
    return format_relationship_result


def get_format(file_format_id, all_actors):
    rows = execute_procedure("proc_get_format_detail_by_id", file_format_id)
    detail_result = {}
    for row in rows:
        for key in row.cursor_description:
            value = row[row.cursor_description.index(key)]
            detail_result[to_camel_case(key[0])] = value

    detail_result['identifiers'] = get_format_identifiers(file_format_id)
    detail_result['internalSignatures'] = get_internal_signatures(file_format_id)
    detail_result['externalSignatures'] = get_external_signatures(file_format_id)
    detail_result['relationships'] = get_format_relationships(file_format_id)
    support = get_support(file_format_id)
    developer = get_developer(file_format_id)
    source = get_source(file_format_id)
    if support is not None:
        actor_id = support['actorId']
        detail_result['supportedBy'] = actor_id
        all_actors[actor_id] = support
    if developer is not None:
        actor_id = developer['actorId']
        detail_result['developedBy'] = actor_id
        all_actors[actor_id] = developer
    if source is not None:
        actor_id = source['actorId']
        detail_result['source'] = actor_id
        all_actors[actor_id] = source
    return detail_result


def process_actor(actor_rows):
    if len(actor_rows) > 0:
        actor_result = {}
        row = actor_rows[0]
        for key in row.cursor_description:
            value = row[row.cursor_description.index(key)]
            if value is not None:
                if type(value) is datetime:
                    actor_result[key[0]] = value.strftime("%Y-%m-%d")
                else:
                    actor_result[key[0]] = value
        return actor_result


def get_source(file_format_id):
    sql = f'''
    SELECT source_actor.actor_id actorId,
       dbo.func_get_actor_compound_name(source_actor.name_text, source_actor.organisation_name_text) name   ,
       source_actor.address_text                                                                        address,
       c.country_name_text addressCountry,
       source_actor.telephone_text telephone,
       source_actor.support_website_text,
       source_actor.support_website_text supportWebsite,
       source_actor.website_text companyWebsite,
       source_actor.contact_email_text contact,
       source_actor.source_date sourceDate
    FROM file_formats ff
         JOIN actors source_actor on source_actor.actor_id = ff.source_id
         LEFT JOIN dbo.countries c on source_actor.country_code_text = c.country_code_text
         WHERE ff.file_format_id = {file_format_id};
    '''
    conn = get_connection("localhost", "PRONOM", "sa", "P@ssw0rd")
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    return process_actor(rows)


def get_developer(file_format_id):
    sql = f'''
    select
    developer_actor.actor_id actorId,
    dbo.func_get_actor_compound_name(developer_actor.name_text , developer_actor.organisation_name_text) name,
    developer_actor.address_text address,
    c.country_name_text addressCountry,
    developer_actor.telephone_text telephone,
    developer_actor.support_website_text supportWebsite,
    developer_actor.website_text companyWebsite,
    developer_actor.contact_email_text contact,
    dbo.func_get_actor_compound_name(source_actor.name_text , source_actor.organisation_name_text) AS source,
    developer_actor.source_date sourceDate
        from file_formats ff
        JOIN format_developers fd on fd.file_format_id = ff.file_format_id
        JOIN actors developer_actor on developer_actor.actor_id = fd.developer_id
        JOIN actors source_actor on source_actor.actor_id = ff.source_id
        JOIN actors actor_source on actor_source.actor_id = developer_actor.source_id
        LEFT JOIN dbo.countries c on developer_actor.country_code_text = c.country_code_text
    where ff.file_format_id = {file_format_id};
    '''
    conn = get_connection("localhost", "PRONOM", "sa", "P@ssw0rd")
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    return process_actor(rows)


def get_support(file_format_id):
    sql = f'''
    select
    support_actor.actor_id actorId,
    dbo.func_get_actor_compound_name(support_actor.name_text , support_actor.organisation_name_text) As name,
    support_actor.address_text address,
    c.country_name_text addressCountry,
    support_actor.telephone_text telephone,
    support_actor.support_website_text supportWebsite,
    support_actor.website_text companyWebsite,
    support_actor.contact_email_text contact,
    dbo.func_get_actor_compound_name(source_actor.name_text , source_actor.organisation_name_text) AS source,
    support_actor.source_date sourceDate
    from file_formats ff
         JOIN format_support fs on fs.file_format_id = ff.file_format_id
         JOIN actors support_actor on support_actor.actor_id = fs.support_id
         JOIN actors source_actor on source_actor.actor_id = ff.source_id
         JOIN actors actor_source on actor_source.actor_id = support_actor.source_id
         LEFT JOIN dbo.countries c on support_actor.country_code_text = c.country_code_text
    where ff.file_format_id = {file_format_id};
    '''
    conn = get_connection("localhost", "PRONOM", "sa", "P@ssw0rd")
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    return process_actor(rows)


def execute_stored_procedures(procedures, file_format_id):
    """
    Executes a list of stored procedures and stores the results in a dictionary.

    :param procedures: A list of stored procedure names to execute.
    :param file_format_id: The ID of the file format
    :return: A dictionary with procedure names as keys and results as values.
    """
    # Create connection string

    conn = get_connection("localhost", "PRONOM", "sa", "P@ssw0rd")

    cursor = conn.cursor()

    results = {"fileFormatId": file_format_id}

    for procedure in procedures:
        try:
            # Execute the stored procedure
            cursor.execute(f"EXEC {procedure} {file_format_id}")

            # Fetch all rows
            rows = cursor.fetchall()

            snake_str = procedure.replace("proc_get_", "").replace("_by_id", "")
            pascal_key = to_camel_case("".join(x.capitalize() for x in snake_str.lower().split("_")))
            key = to_camel_case(pascal_key)
            # Process rows
            results[key] = [
                dict(zip([to_camel_case(desc[0]) for desc in cursor.description], row))
                for row in rows
            ]
        except pyodbc.Error as e:
            print(f"Error executing procedure '{procedure}': {e}")
            results[procedure] = None  # Store None in case of an error

    # Close the connection
    cursor.close()
    conn.close()

    return results


def run():
    container_signatures = generate_container_signatures()
    file_format_ids = get_file_format_ids()
    all_actors = {}
    for file_format_id in file_format_ids:
        format_json = get_format(file_format_id, all_actors)
        puid = [x for x in format_json["identifiers"] if x["identifierType"] == "PUID"][0]["identifierText"]
        if puid in container_signatures:
            format_json['containerSignatures'] = container_signatures[puid]
        with open(f'/home/sam/repositories/digitalpreservation/pronom-signatures/signatures/{puid}.json', 'w') as f:
            json.dump(format_json, f, indent=2)
    for actor_id, actor in all_actors.items():
        with open(f'/home/sam/repositories/digitalpreservation/pronom-signatures/actors/{actor_id}.json',
                  'w') as actor_file:
            actor_file.write(json.dumps(actor, indent=2))


# Example usage
if __name__ == "__main__":
    run()
