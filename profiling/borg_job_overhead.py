import argparse
from os import path

from peewee import SqliteDatabase

from vorta import config
from vorta.application import VortaApp
from vorta.borg.create import BorgCreateJob
from vorta.borg.init import BorgInitJob
from vorta.store.connection import init_db
from vorta.store.models import BackupProfileModel, RepoModel, SourceFileModel

if __name__ == "__main__":
    parser = argparse.ArgumentParser('borg_job_overhead')
    parser.add_argument('--input', '-i', action='store', help='The file source')
    parser.add_argument('--output', '-o', action='store', help='The resulting repo')
    args = parser.parse_args()

    # Make sure this profile is empty for reproducible results
    config.init_dev_mode(path.join(args.output, 'profile'))
    repo_path = path.join(args.output, 'repo')

    sqlite_db = SqliteDatabase(
        config.SETTINGS_DIR / 'settings.db',
        pragmas={
            'journal_mode': 'wal',
        },
    )
    init_db(sqlite_db)

    app = VortaApp([], False)

    repo, _ = RepoModel.get_or_create(
        url=args.output, defaults={'name': 'test', 'extra_borg_arguments': [], 'encryption': 'none'}
    )
    profile = BackupProfileModel.create(name='t1', defaults={'repo': repo})

    job_param = {
        'extra_borg_arguments': [],
        'profile_name': 't1',
        'profile': profile,
        'profile_id': profile.id,
        'repo_url': repo_path,
        'encryption': 'none',
        "repo_name": "test",
        'repo_id': repo.id,
    }
    cmd = ['borg', 'init', '--info', '--log-json', '--encryption=none', repo_path]
    job_param['cmd'] = cmd

    job = BorgInitJob(cmd, job_param, 't1')
    job.run()

    cmd = [
        "borg",
        "create",
        "--list",
        "--progress",
        "--info",
        "--log-json",
        "--json",
        "--filter=AM",
        "-C",
        "lz4",
        f'{repo_path}::a1',
        args.input,
    ]
    job_param['cmd'] = cmd
    job = BorgCreateJob(cmd, job_param, 't1')
    job.run()
