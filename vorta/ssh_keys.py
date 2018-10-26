import os
from paramiko.rsakey import RSAKey
from paramiko.ecdsakey import ECDSAKey
from paramiko.ed25519key import Ed25519Key
from paramiko import SSHException


def get_private_keys():
    key_formats = [RSAKey, ECDSAKey, Ed25519Key]

    ssh_folder = os.path.join(os.path.expanduser('~'), '.ssh')

    available_private_keys = []
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
