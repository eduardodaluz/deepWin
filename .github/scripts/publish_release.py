"""Publish only the three accepted 1.1.0 artifacts; never rebuild or replace them."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

REPOSITORY = 'eduardodaluz/deepWin'
TAG = 'v1.1.0'
SOURCE = '07fb017ab558f54b7282821d7ca305e8289f4b66'
# IDs and ZIP digests recorded from the successful runs before publication.
BUILDS = (
    dict(run=39179478622, workflow='deb.yml', artifact=12155199625,
         name='deepwin-deb-amd64', file='devedu.deepin-configs_1.1.0-3_amd64.deb',
         digest='6d62711083bd2d9efcd74eabcef5499e4aa089cfdf4d0cdf862940951bfbc78d'),
    dict(run=39179478573, workflow='uab.yml', artifact=12155493804,
         name='deepwin-uab-amd64', file='devedu.deepin-configs_1.1.0.0_x86_64_main.uab',
         digest='324b0680d2223eb36c92ad5e35ef4e60b3b9a0d365cf20a57c0e26e3b1d86850'),
    dict(run=39179478620, workflow='portable.yml', artifact=12155179755,
         name='deepwin-portable-amd64', file='DeepWin-1.1.0-amd64-portable.tar.xz',
         digest='69282fd9a1e42184416d9de12852ff0a8dd04b59d278f584c701de98bba1a530'),
)
# The release tag adds documentation and publication tooling to the accepted code.
RELEASE_ONLY = {
    'README.md', 'continuidade-desenvolvimento.md', 'plano-distribuicao-deepwin.md',
    'packaging/release-notes-1.1.0.md', '.github/workflows/release.yml',
    '.github/scripts/publish_release.py', '.github/scripts/test_publish_release.py',
}


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


def validate_run(build, run, artifact):
    require(run['id'] == build['run'] and run['head_sha'] == SOURCE
            and run['head_branch'] == 'main' and run['event'] == 'push'
            and run['status'] == 'completed' and run['conclusion'] == 'success'
            and run['path'] == f'.github/workflows/{build["workflow"]}'
            and run['head_repository']['full_name'] == REPOSITORY,
            f'Unapproved build provenance: {build["run"]}')
    require(artifact['id'] == build['artifact'] and artifact['name'] == build['name']
            and not artifact['expired']
            and artifact['workflow_run']['id'] == build['run']
            and artifact['workflow_run']['head_sha'] == SOURCE
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


def validate_uploaded(release, assets):
    require(release['tag_name'] == TAG and release['draft']
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


def main():
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY
            and os.environ.get('GITHUB_REF') == f'refs/tags/{TAG}'
            and os.environ.get('GITHUB_EVENT_NAME') == 'push', 'Unexpected release trigger')
    require(Path('VERSION').read_text().strip() == '1.1.0', 'Version mismatch')
    require(command('git', 'rev-parse', f'{TAG}^{{commit}}') == command('git', 'rev-parse', 'HEAD'),
            'Checkout does not match release tag')
    subprocess.run(['git', 'merge-base', '--is-ancestor', SOURCE, 'HEAD'], check=True)
    changed = set(command('git', 'diff', '--name-only', SOURCE, 'HEAD').splitlines())
    require(changed <= RELEASE_ONLY, f'Application changed after acceptance: {changed - RELEASE_ONLY}')
    # Authenticated, paginated listing also sees drafts. Never replace an existing release.
    releases = json.loads(command('gh', 'api', '--paginate', '--slurp',
                                 f'repos/{REPOSITORY}/releases?per_page=100'))
    require(all(release['tag_name'] != TAG for page in releases for release in page),
            'Release already exists; inspect it before retrying')

    with tempfile.TemporaryDirectory(prefix='deepwin-release-') as temporary:
        directory = Path(temporary)
        output = directory / 'assets'
        output.mkdir()
        checksums = []
        for build in BUILDS:
            validate_run(build, api(f'actions/runs/{build["run"]}'),
                         api(f'actions/artifacts/{build["artifact"]}'))
            archive = directory / f'{build["artifact"]}.zip'
            with archive.open('xb') as stream:
                subprocess.run(['gh', 'api',
                                f'repos/{REPOSITORY}/actions/artifacts/{build["artifact"]}/zip'],
                               stdout=stream, check=True)
            checksums.append(prepare_asset(build, archive, output))
            print(f'Validated: {build["file"]}', flush=True)
        (output / 'SHA256SUMS').write_text(''.join(checksums))
        assets = {path.name: path for path in output.iterdir()}
        subprocess.run(['gh', 'release', 'create', TAG, '--repo', REPOSITORY,
                        '--verify-tag', '--draft', '--title', 'DeepWin 1.1.0',
                        '--notes-file', 'packaging/release-notes-1.1.0.md',
                        *map(str, sorted(assets.values()))], check=True)
        release = api(f'releases/tags/{TAG}')
        validate_uploaded(release, assets)
        # Publication is the final mutation, after checking all seven remote digests.
        subprocess.run(['gh', 'release', 'edit', TAG, '--repo', REPOSITORY,
                        '--draft=false', '--latest'], check=True)
        published = api(f'releases/tags/{TAG}')
        require(not published['draft'] and published['published_at'], 'Release was not published')
        summary = {'url': published['html_url'], 'tag': TAG, 'build_source': SOURCE,
                   'assets': {name: sha256(path) for name, path in sorted(assets.items())}}
        Path('release-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
