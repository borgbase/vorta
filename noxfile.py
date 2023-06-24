import os
import platform
import re
import sys

import nox

borg_version = os.getenv("BORG_VERSION")

if borg_version:
    # Use specified borg version
    supported_borgbackup_versions = [borg_version]
else:
    # Generate a list of borg versions compatible with system installed python version
    system_python_version = platform.python_version_tuple()
    system_python_version = tuple(int(part) for part in system_python_version)

    supported_borgbackup_versions = [
        borgbackup
        for borgbackup in ("1.1.18", "1.2.2", "1.2.4", "2.0.0b5")
        # Python version requirements for borgbackup versions
        if (borgbackup == "1.1.18" and system_python_version >= (3, 5, 0))
        or (borgbackup == "1.2.2" and system_python_version >= (3, 8, 0))
        or (borgbackup == "1.2.4" and system_python_version >= (3, 8, 0))
        or (borgbackup == "2.0.0b5" and system_python_version >= (3, 9, 0))
    ]


@nox.session
@nox.parametrize("borgbackup", supported_borgbackup_versions)
def run_tests(session, borgbackup):
    # install borgbackup
    if (borgbackup == "1.1.18" or sys.platform == 'darwin'):
        session.install(f"borgbackup=={borgbackup}")
    else:
        session.install(f"borgbackup[pyfuse3]=={borgbackup}")

    # install dependencies
    session.install("-r", "requirements.d/dev.txt")
    session.install("-e", ".")

    # check versions
    cli_version = session.run("borg", "--version", silent=True).strip()
    cli_version = re.search(r"borg (\S+)", cli_version).group(1)
    python_version = session.run("python", "-c", "import borg; print(borg.__version__)", silent=True).strip()

    session.log(f"Borg CLI version: {cli_version}")
    session.log(f"Borg Python version: {python_version}")

    assert cli_version == borgbackup
    assert python_version == borgbackup

    session.run("pytest", *session.posargs, env={"BORG_VERSION": borgbackup})
