import re

import nox


@nox.session
# @nox.parametrize("borgbackup", ["2.0.0b5", "2.0.0b4"])
@nox.parametrize("borgbackup", ["1.1.18", "1.2.2", "1.2.3", "1.2.4"])
def run_tests(session, borgbackup):
    # install borgbackup
    session.install(f"borgbackup[pyfuse3]=={borgbackup}")

    # install dependencies
    session.install("-r", "requirements.d/dev.txt")
    session.install("-e", ".")

    # check versions
    cli_version = session.run("borg", "--version", silent=True).strip()
    cli_version = re.search(r"borg (\S+)", cli_version).group(1)
    python_version = session.run("python", "-c", "import borg; print(borg.__version__)", silent=True).strip()

    session.log(f"CLI version: {cli_version}")
    session.log(f"Python version: {python_version}")

    assert cli_version == borgbackup
    assert python_version == borgbackup

    # run tests
    session.run("pytest", *session.posargs)
