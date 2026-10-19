"""Publish only the accepted artifacts recorded in a release definition.

Each release is described by a JSON file under .github/releases/ recording the
accepted source commit, tag commit, CI run and artifact IDs and ZIP digests.
Publication never rebuilds or replaces an already published release.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

REPOSITORY = 'eduardodaluz/deepWin'
CONFIG_DIR = Path('.github/releases')
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
CONFIG_KEYS = {'tag', 'title', 'version', 'tag_commit', 'source', 'notes',
               'release_only', 'builds'}
BUILD_KEYS = {'run', 'workflow', 'artifact', 'name', 'file', 'digest'}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def api(endpoint):
    return json.loads(command('gh', 'api', f'repos/{REPOSITORY}/{endpoint}'))


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_config(argument):
    """Accept only release definitions stored under .github/releases/."""
    path = Path(argument)
    require(path.parent == CONFIG_DIR and path.suffix == '.json'
            and '..' not in path.parts,
            f'Release definition must be a JSON file under {CONFIG_DIR}/: {argument}')
    require(path.is_file(), f'Release definition not found: {argument}')
    return path


def load_config(path):
    """Load and validate the release definition schema."""
    data = json.loads(Path(path).read_text())
    require(isinstance(data, dict), 'Release definition must be a JSON object')
    require(set(data) == CONFIG_KEYS,
            f'Release definition keys differ from the expected schema: {sorted(data)}')
    require(re.match(r'v\d+\.\d+\.\d+', str(data['tag'])), 'Unexpected tag format')
    require(isinstance(data['title'], str) and data['title'].strip(),
            'Release title must be a non-empty string')
    require(isinstance(data['version'], str) and data['version'].strip(),
            'Release version must be a non-empty string')
    for key in ('tag_commit', 'source'):
        require(HEX40.fullmatch(str(data[key])), f'{key} must be a 40-hex commit')
    require(Path(data['notes']).is_file(), f'Release notes file missing: {data["notes"]}')
    require(isinstance(data['release_only'], list) and data['release_only']
            and all(isinstance(item, str) and item for item in data['release_only']),
            'release_only must be a non-empty list of paths')
    require(isinstance(data['builds'], list) and data['builds'], 'builds must be non-empty')
    for build in data['builds']:
        require(set(build) == BUILD_KEYS, f'Build entry keys differ: {sorted(build)}')
        require(isinstance(build['run'], int) and build['run'] > 0
                and isinstance(build['artifact'], int) and build['artifact'] > 0,
                f'Run and artifact IDs must be positive integers: {build.get("file")}')
        require(isinstance(build['workflow'], str) and build['workflow'].endswith('.yml')
                and Path(build['workflow']).name == build['workflow'],
                f'Workflow path must be a bare file name: {build.get("workflow")}')
        require(isinstance(build['name'], str) and build['name']
                and isinstance(build['file'], str) and Path(build['file']).name == build['file'],
                f'Artifact and file names must be bare names: {build.get("name")}')
        require(HEX64.fullmatch(str(build['digest'])),
                f'Artifact digest must be a 64-hex SHA-256: {build.get("file")}')
    return data


def validate_run(build, run, artifact, source):
    require(run['id'] == build['run'] and run['head_sha'] == source
            and run['head_branch'] == 'main' and run['event'] == 'push'
            and run['status'] == 'completed' and run['conclusion'] == 'success'
            and run['path'] == f'.github/workflows/{build["workflow"]}'
            and run['head_repository']['full_name'] == REPOSITORY,
            f'Unapproved build provenance: {build["run"]}')
    require(artifact['id'] == build['artifact'] and artifact['name'] == build['name']
            and not artifact['expired']
            and artifact['workflow_run']['id'] == build['run']
            and artifact['workflow_run']['head_sha'] == source
            and artifact['digest'] == f'sha256:{build["digest"]}',
            f'Unapproved artifact: {build["artifact"]}')


def prepare_asset(build, archive, output):
    require(sha256(archive) == build['digest'], 'Artifact ZIP digest mismatch')
    filename = build['file']
    # Select just the installer and its sidecar, without extracting ZIP paths.
    with zipfile.ZipFile(archive) as bundle:
        selected = {}
        for name in (filename, filename + '.sha256'):
            matches = [item for item in bundle.infolist()
                       if Path(item.filename).name == name and not item.is_dir()]
            require(len(matches) == 1, f'Missing or duplicate asset: {name}')
            selected[name] = matches[0]
        checksum = bundle.read(selected[filename + '.sha256']).decode('ascii')
        with bundle.open(selected[filename]) as source, (output / filename).open('xb') as target:
            shutil.copyfileobj(source, target)
    expected = f'{sha256(output / filename)}  {filename}\n'
    require(checksum == expected, f'Package checksum mismatch: {filename}')
    (output / (filename + '.sha256')).write_text(expected)
    return expected


def validate_uploaded(release, assets, tag, draft=True):
    require(release['tag_name'] == tag and release['draft'] == draft
            and not release['prerelease'], 'Release is not the expected draft')
    uploaded = release['assets']
    require(len(uploaded) == len(assets)
            and {item['name'] for item in uploaded} == set(assets),
            'Uploaded asset set differs from the approved files')
    for item in uploaded:
        local = assets[item['name']]
        require(item['state'] == 'uploaded' and item['size'] == local.stat().st_size
                and item.get('digest') == f'sha256:{sha256(local)}',
                f'Uploaded asset verification failed: {item["name"]}')


def find_release(tag):
    # The tag endpoint omits drafts; listing includes them for this repository token.
    pages = json.loads(command('gh', 'api', '--paginate', '--slurp',
                              f'repos/{REPOSITORY}/releases?per_page=100'))
    matches = [item for page in pages for item in page if item['tag_name'] == tag]
    require(len(matches) <= 1, 'Multiple releases use the expected tag')
    return matches[0] if matches else None


def validate_draft(release, notes, title, tag):
    require(release['draft'] and not release['prerelease']
            and release['tag_name'] == tag and release['name'] == title
            and release['body'].strip() == notes.strip(),
            'Existing release is not the expected unpublished draft')


def already_published(release, tag):
    return (bool(release) and not release['draft'] and not release['prerelease']
            and release['tag_name'] == tag and bool(release['published_at']))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--config', required=True, help='Release definition under .github/releases/')
    args = parser.parse_args()
    config = load_config(resolve_config(args.config))
    tag, source = config['tag'], config['source']
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY
            and os.environ.get('GITHUB_REF') == 'refs/heads/main'
            and os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch',
            'Publication runs only from a manual dispatch on main')
    require(Path('VERSION').read_text().strip() == config['version'], 'Version mismatch')

    existing = find_release(tag)
    if already_published(existing, tag):
        # Publication already happened; never rebuild, edit or replace it.
        summary = {'status': 'already-published', 'tag': tag,
                   'url': existing['html_url'], 'build_source': source}
        Path('release-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(summary, indent=2), flush=True)
        return

    require(command('git', 'rev-parse', f'{tag}^{{commit}}') == config['tag_commit'],
            'Release tag changed after authorization')
    subprocess.run(['git', 'merge-base', '--is-ancestor', config['tag_commit'], 'HEAD'], check=True)
    subprocess.run(['git', 'merge-base', '--is-ancestor', source, config['tag_commit']], check=True)
    changed = set(command('git', 'diff', '--name-only', source, 'HEAD').splitlines())
    allowlist = set(config['release_only'])
    require(changed <= allowlist,
            f'Application changed after acceptance: {changed - allowlist}')
    notes = Path(config['notes']).read_text()
    if existing:
        validate_draft(existing, notes, config['title'], tag)

    with tempfile.TemporaryDirectory(prefix='deepwin-release-') as temporary:
        directory = Path(temporary)
        output = directory / 'assets'
        output.mkdir()
        checksums = []
        for build in config['builds']:
            validate_run(build, api(f'actions/runs/{build["run"]}'),
                         api(f'actions/artifacts/{build["artifact"]}'), source)
            archive = directory / f'{build["artifact"]}.zip'
            with archive.open('xb') as stream:
                subprocess.run(['gh', 'api',
                                f'repos/{REPOSITORY}/actions/artifacts/{build["artifact"]}/zip'],
                               stdout=stream, check=True)
            checksums.append(prepare_asset(build, archive, output))
            print(f'Validated: {build["file"]}', flush=True)
        (output / 'SHA256SUMS').write_text(''.join(checksums))
        assets = {path.name: path for path in output.iterdir()}
        if not existing:
            subprocess.run(['gh', 'release', 'create', tag, '--repo', REPOSITORY,
                            '--verify-tag', '--draft', '--title', config['title'],
                            '--notes-file', config['notes'],
                            *map(str, sorted(assets.values()))], check=True)
            existing = find_release(tag)
            require(existing is not None, 'Created draft not found')
        release = api(f'releases/{existing["id"]}')
        validate_draft(release, notes, config['title'], tag)
        validate_uploaded(release, assets, tag)
        # Publication is the final mutation, after checking all remote digests.
        subprocess.run(['gh', 'api', '--method', 'PATCH',
                        f'repos/{REPOSITORY}/releases/{release["id"]}',
                        '-F', 'draft=false', '-f', 'make_latest=true'],
                       stdout=subprocess.DEVNULL, check=True)
        published = api(f'releases/{release["id"]}')
        validate_uploaded(published, assets, tag, draft=False)
        require(not published['draft'] and published['published_at'], 'Release was not published')
        summary = {'url': published['html_url'], 'tag': tag, 'build_source': source,
                   'assets': {name: sha256(path) for name, path in sorted(assets.items())}}
        Path('release-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
