import os
from paramiko.rsakey import RSAKey
from paramiko.ecdsakey import ECDSAKey
from paramiko.ed25519key import Ed25519Key
from paramiko import SSHException


def get_private_keys():
    """Find SSH keys in standard folder."""
    key_formats = [RSAKey, ECDSAKey, Ed25519Key]

    ssh_folder = os.path.expanduser('~/.ssh')

    available_private_keys = []
    if os.path.isdir(ssh_folder):
        for key in os.listdir(ssh_folder):
            for key_format in key_formats:
                try:
                    parsed_key = key_format.from_private_key_file(os.path.join(ssh_folder, key))
                    key_details = {
                        'filename': key,
                        'format': parsed_key.get_name(),
                        'bits': parsed_key.get_bits(),
                        'fingerprint': parsed_key.get_fingerprint().hex()
                    }
                    available_private_keys.append(key_details)
                except (SSHException, UnicodeDecodeError, IsADirectoryError):
                    continue

    return available_private_keys


def prettyBytes(size):
    """from https://stackoverflow.com/questions/12523586/
            python-format-size-application-converting-b-to-kb-mb-gb-tb/37423778"""
    if type(size) != int:
        return ''
    power = 2**10
    n = 0
    Dic_powerN = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /=  power
        n += 1
    return str(round(size))+Dic_powerN[n]+'B'
