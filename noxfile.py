import os
import re
import sys

import nox

borg_version = os.getenv("BORG_VERSION")

if borg_version:
    # Use specified borg version
    supported_borgbackup_versions = [borg_version]
else:
    # Default to latest stable version
    supported_borgbackup_versions = ["1.4.3"]


@nox.session(venv_backend="uv")
@nox.parametrize("borgbackup", supported_borgbackup_versions)
def run_tests(session, borgbackup):
    # install borgbackup
    if sys.platform == 'darwin':
        # in macOS there's currently no fuse package which works with borgbackup directly
        session.install(f"borgbackup=={borgbackup}")
    elif borgbackup == "1.1.18":
        # borgbackup 1.1.18 doesn't support pyfuse3
        session.install("llfuse")
        session.install(f"borgbackup[llfuse]=={borgbackup}")
    else:
        session.install(f"borgbackup[pyfuse3]=={borgbackup}")

    # install dev dependencies and package
    session.install("-e", ".[test]")

    # check versions
    cli_version = session.run("borg", "--version", silent=True).strip()
    cli_version = re.search(r"borg (\S+)", cli_version).group(1)
    python_version = session.run("python", "-c", "import borg; print(borg.__version__)", silent=True).strip()

    session.log(f"Borg CLI version: {cli_version}")
    session.log(f"Borg Python version: {python_version}")

    assert cli_version == borgbackup
    assert python_version == borgbackup

    session.run("pytest", *session.posargs, env={"BORG_VERSION": borgbackup})
