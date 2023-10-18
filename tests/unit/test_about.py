from vorta._version import __version__


def test_vorta_and_borg_info(qapp):
    tab = qapp.main.aboutTab

    assert tab.vorta_version == __version__
    assert tab.borg_version == tab.borgVersion.text()
    assert tab.borg_path in tab.borgPath.text()
