import subprocess
import os
import json
import xml.etree.ElementTree as Et
import itertools
import sys

droid_path = sys.argv[1]


def get_position_type(position):
    match position:
        case 'Absolute from BOF':
            return 'BOFoffset'
        case 'Absolute from EOF':
            return 'EOFoffset'
        case _:
            return 'Variable'


def get_identifiers(format_json, identifier_type):
    identifiers = format_json['identifiers']
    text = [
        identifier['identifierText'] for identifier in identifiers if identifier['identifierType'] == identifier_type
    ]
    if len(text) > 0:
        return text[0]
    else:
        return None


def generate_files_signatures():
    all_files = []
    all_internal_signatures = []
    all_container_signatures = []
    for sig_dir in ['x-fmt', 'fmt']:
        path = f'signatures/{sig_dir}'
        files = sorted(os.listdir(path), key=lambda x: int(x[:-5]))
        for file in files:
            with (open(f'{path}/{file}', 'r') as format_file):
                format_json = json.load(format_file)
                all_files.append(format_json)
                all_internal_signatures.extend(format_json['internalSignatures'])
                if 'containerSignatures' in format_json:
                    for container_signature in format_json['containerSignatures']:
                        container_signature['puid'] = get_identifiers(format_json, "PUID")
                        all_container_signatures.append(container_signature)
    return all_files, all_internal_signatures, all_container_signatures


def get_binary_signatures(all_internal_signatures):
    all_byte_sequences = [seq for signature in all_internal_signatures for seq in signature['byteSequences']]
    sorted_internal_signatures = sorted(all_byte_sequences, key=lambda x: x['positionType'])
    grouped_internal_signatures = itertools.groupby(sorted_internal_signatures, lambda x: x['positionType'])
    cwd = os.getcwd()
    results_for_type = {}
    for position_type, signatures in grouped_internal_signatures:

        expressions = [sig['byteSequence'] for sig in signatures]
        os.chdir(droid_path)
        command = ['./sigtool', '-b', '-p', '-a', get_position_type(position_type)]
        command.extend(expressions)
        result = subprocess.run(command, stdout=subprocess.PIPE)
        output_rows = result.stdout.decode('utf-8').split('\n')
        output_object = {}
        for row in output_rows:

            each_field = row.split("\t")
            if len(each_field) > 1:
                output_object[each_field[0]] = each_field[1]
        results_for_type[get_position_type(position_type)] = output_object
    os.chdir(cwd)
    return results_for_type


def add_extensions(file_format_element, format_json):
    if 'externalSignatures' in format_json:
        file_extension_signatures = [
            x['externalSignature'] for x in format_json['externalSignatures'] if
            x['signatureType'] == 'File extension'
        ]
        for ex in file_extension_signatures:
            extension_element = Et.Element('Extension')
            extension_element.text = str(ex)
            file_format_element.append(extension_element)


def generate_file_format_element(format_json):
    puid = get_identifiers(format_json, "PUID")
    file_format_attributes = {
        'ID': str(format_json['fileFormatID']),
        "PUID": puid,
        "Name": format_json['formatName']
    }
    if 'version' in format_json and format_json['version'] is not None:
        file_format_attributes['Version'] = format_json['version']
    mime_type = get_identifiers(format_json, "MIME")
    if mime_type is not None:
        file_format_attributes['MIMEType'] = mime_type
    return Et.Element('FileFormat', attrib=file_format_attributes)


def add_relationships(file_format_element, format_json):
    if 'relationships' in format_json:
        relationships = [r for r in format_json['relationships'] if r['relationshipType'] == 'Has priority over']
        for relationship in relationships:
            priority_element = Et.Element('HasPriorityOverFileFormatID')
            priority_element.text = str(relationship['relatedFormatID'])
            file_format_element.append(priority_element)


def create_signature_file(all_files, all_internal_signatures):
    root_attributes = {
        'xmlns': 'http://www.nationalarchives.gov.uk/pronom/SignatureFile',
        'DateCreated': '2024-07-08T11:54:20',
        'Version': '119'
    }
    root_element = Et.Element('FFSignatureFile', attrib=root_attributes)
    internal_signature_collection = Et.Element('InternalSignatureCollection')
    file_format_collection = Et.Element('FileFormatCollection')
    root_element.append(internal_signature_collection)
    root_element.append(file_format_collection)
    binary_signatures = get_binary_signatures(all_internal_signatures)
    for format_json in all_files:
        internal_signatures = format_json['internalSignatures']

        file_format_element = generate_file_format_element(format_json)

        add_relationships(file_format_element, format_json)
        add_extensions(file_format_element, format_json)
        signatures_by_id = itertools.groupby(internal_signatures, lambda x: x['signatureID'])
        for signature_id, internal_signatures in signatures_by_id:
            signature_id_element = Et.Element('InternalSignatureID')
            signature_id_element.text = str(signature_id)
            file_format_element.append(signature_id_element)
            signature_element_attributes = {'ID': str(signature_id), 'Specificity': 'Specific'}
            signature_element = Et.Element('InternalSignature', attrib=signature_element_attributes)
            for internal_signature in internal_signatures:
                if 'specificity' in internal_signature and internal_signature['specificity']:
                    signature_element.attrib['Specificity'] = internal_signature['specificity']
                byte_sequences = internal_signature['byteSequences']
                for byte_sequence in byte_sequences:
                    position_type = get_position_type(byte_sequence['positionType'])
                    seq_string = byte_sequence['byteSequence']
                    if position_type in binary_signatures and seq_string in binary_signatures[position_type]:
                        sigtool_response = binary_signatures[position_type][seq_string]
                        sigtool_element = Et.fromstring(sigtool_response)
                        if 'endianness' in byte_sequence and byte_sequence['endianness']:
                            sigtool_element.attrib['Endianness'] = byte_sequence['endianness']
                        for sub_sequence in sigtool_element.iter('SubSequence'):
                            position = int(sub_sequence.attrib['Position'])
                            existing_min_seq_offset = int(sub_sequence.attrib['SubSeqMinOffset'])
                            existing_max_seq_offset = int(sub_sequence.attrib['SubSeqMaxOffset'])
                            offset = byte_sequence['offset'] if byte_sequence['offset'] is not None else 0
                            max_offset = byte_sequence['maxOffset'] if byte_sequence[
                                                                           'maxOffset'] is not None else 0
                            min_seq_offset = int(existing_min_seq_offset) + int(offset) \
                                if position == 1 else existing_min_seq_offset
                            max_seq_offset = int(existing_max_seq_offset) + int(offset) + int(max_offset)
                            sub_sequence.attrib['SubSeqMinOffset'] = str(min_seq_offset)
                            if (position_type == 'Variable' and 'Reference' in sigtool_element.attrib
                                    and sigtool_element.attrib['Reference'] == 'Variable'):
                                del sigtool_element.attrib['Reference']
                            if position == 1 and position_type != 'Variable':
                                sub_sequence.attrib['SubSeqMaxOffset'] = str(max_seq_offset)
                            else:
                                del sub_sequence.attrib['SubSeqMaxOffset']
                        signature_element.append(sigtool_element)
            internal_signature_collection.append(signature_element)
        file_format_collection.append(file_format_element)

    Et.indent(root_element, space="\t", level=0)
    Et.ElementTree(root_element).write('signature-file.xml')


def generate_binary_signatures(format_json):
    if 'byteSequences' in format_json:
        binary_signatures = Et.Element('BinarySignatures')
        internal_signature_collection = Et.Element('InternalSignatureCollection')
        internal_signature = Et.Element('InternalSignature')
        internal_signature_collection.append(internal_signature)
        binary_signatures.append(internal_signature_collection)
        for sequence in format_json['byteSequences']:
            byte_sequence_attributes = {'Reference': sequence['reference']} if 'reference' in sequence else {}
            byte_sequence_elem = Et.Element('ByteSequence', attrib=byte_sequence_attributes)
            for sub_sequence in sequence['subSequences']:
                sub_sequence_attributes = {
                    k[0].upper() + k[1:]: v for k, v in sub_sequence.items() if k not in ['sequence', 'rightFragment']
                }
                sub_sequence_elem = Et.Element('SubSequence', attrib=sub_sequence_attributes)
                sequence_elem = Et.Element('Sequence')
                sequence_elem.text = sub_sequence['sequence']
                if 'rightFragment' in sub_sequence:
                    right_fragment_attributes = {
                        k[0].upper() + k[1:]: v for k, v in sub_sequence['rightFragment'].items() if k != 'sequence'
                    }
                    right_fragment_elem = Et.Element('RightFragment', right_fragment_attributes)
                    right_fragment_elem.text = sub_sequence['rightFragment']['sequence']
                    sub_sequence_elem.append(right_fragment_elem)
                sub_sequence_elem.append(sequence_elem)
                byte_sequence_elem.append(sub_sequence_elem)
            internal_signature.append(byte_sequence_elem)
        return binary_signatures


def create_container_file(all_container_signatures):
    root_element = Et.Element('ContainerSignatureMapping', attrib={'schemaVersion': '1.0', 'signatureVersion': '38'})
    container_signatures_element = Et.Element('ContainerSignatures')
    format_mappings_element = Et.Element('FileFormatMappings')
    for signature in all_container_signatures:
        format_mapping_attributes = {'signatureId': signature['id'], 'Puid': signature['puid']}
        format_mappings_element.append(Et.Element('FileFormatMapping', attrib=format_mapping_attributes))
        signature_elem_attributes = {'Id': signature['id'], 'ContainerType': signature['containerType']}
        signature_element = Et.Element('ContainerSignature', attrib=signature_elem_attributes)
        description_element = Et.Element('Description')
        description_element.text = signature['description']
        signature_element.append(description_element)
        files_element = Et.Element('Files')
        signature_element.append(files_element)
        for file in signature['files']:
            file_element = Et.Element('File')
            path_element = Et.Element('Path')
            path_element.text = file['path']
            file_element.append(path_element)
            file_binary_signatures = generate_binary_signatures(file)
            if file_binary_signatures is not None:
                file_element.append(file_binary_signatures)
            files_element.append(file_element)
        container_signatures_element.append(signature_element)
    root_element.append(container_signatures_element)
    root_element.append(format_mappings_element)
    triggers_element = Et.Element('TriggerPuids')
    triggers_element.append(Et.Element('TriggerPuid', attrib={'ContainerType': 'OLE2', 'Puid': 'fmt/111'}))
    triggers_element.append(Et.Element('TriggerPuid', attrib={'ContainerType': 'ZIP', 'Puid': 'fmt/189'}))
    triggers_element.append(Et.Element('TriggerPuid', attrib={'ContainerType': 'ZIP', 'Puid': 'x-fmt/263'}))
    root_element.append(triggers_element)
    Et.ElementTree(root_element).write('container-signature-file.xml', xml_declaration=False)


def run():
    all_files, all_internal_signatures, all_container_signatures = generate_files_signatures()
    create_signature_file(all_files, all_internal_signatures)
    create_container_file(all_container_signatures)


run()
