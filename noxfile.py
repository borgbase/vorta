import re

import nox


@nox.session
# @nox.parametrize("borgbackup", ["1.1.18", "1.2.2", "1.2.3", "1.2.4", "2.0.0b5"])
@nox.parametrize(
    "python, borgbackup",
    [
        (python, borgbackup)
        # All supported Python and BorgBackup versions
        for python in ("3.8", "3.9", "3.10", "3.11")
        for borgbackup in ("1.1.18", "1.2.2", "1.2.4", "2.0.0b5")

        # Python version requirements for borgbackup versions
        if (borgbackup == "1.1.18" and python >= "3.5")
        or (borgbackup == "1.2.2" and python >= "3.8")
        or (borgbackup == "1.2.4" and python >= "3.8")
        or (borgbackup == "2.0.0b5" and python >= "3.9")
    ]
)
def run_tests(session, borgbackup):
    # install borgbackup
    if (borgbackup == "1.1.18"):
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

    session.log(f"CLI version: {cli_version}")
    session.log(f"Python version: {python_version}")

    assert cli_version == borgbackup
    assert python_version == borgbackup

    session.run("pytest", *session.posargs, env={"BORG_VERSION": borgbackup})
