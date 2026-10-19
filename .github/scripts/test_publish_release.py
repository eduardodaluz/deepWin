"""Refusal checks for publishing accepted CI artifacts from a release definition."""
import hashlib
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

import publish_release as release


class ReleaseDefinitionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def definition(self, config, name='v9.9.9.json'):
        path = self.root / name
        path.write_text(json.dumps(config))
        return path

    def sample(self):
        return {
            'tag': 'v9.9.9', 'title': 'DeepWin 9.9.9', 'version': '9.9.9',
            'tag_commit': 'a' * 40, 'source': 'b' * 40,
            'notes': str(self.root / 'notes.md'), 'release_only': ['README.md'],
            'builds': [dict(run=1, workflow='deb.yml', artifact=2, name='deepwin-deb-amd64',
                            file='pkg_9.9.9_amd64.deb', digest='c' * 64)],
        }

    def test_valid_definition_loads(self):
        (self.root / 'notes.md').write_text('notes')
        config = release.load_config(self.definition(self.sample()))
        self.assertEqual(config['tag'], 'v9.9.9')
        self.assertEqual(config['builds'][0]['file'], 'pkg_9.9.9_amd64.deb')

    def test_committed_release_definition_parses(self):
        committed = Path('.github/releases/v1.1.0.json')
        if not committed.is_file():  # direct invocation outside a checkout
            self.skipTest('committed definition not present')
        config = release.load_config(committed)
        self.assertEqual(config['version'], '1.1.0')
        self.assertEqual(len(config['builds']), 3)

    def test_definition_paths_outside_release_directory_are_refused(self):
        for argument in ('other.json', '.github/releases/v9.9.9.json.txt',
                         '.github/releases/sub/v9.9.9.json',
                         '.github/releases/../v9.9.9.json'):
            with self.subTest(argument=argument), self.assertRaisesRegex(
                    RuntimeError, 'under .github/releases'):
                release.resolve_config(argument)
        with self.assertRaisesRegex(RuntimeError, 'not found'):
            release.resolve_config('.github/releases/v9.9.9.json')

    def test_incomplete_or_malformed_definition_is_refused(self):
        (self.root / 'notes.md').write_text('notes')
        base = self.sample()
        for change in ({'tag': 'latest'}, {'source': 'not-a-commit'},
                       {'builds': []}, {'release_only': []},
                       {'notes': str(self.root / 'absent.md')}, {'title': ''}):
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                release.load_config(self.definition({**base, **change}))
        missing = {key: value for key, value in base.items() if key != 'title'}
        with self.assertRaisesRegex(RuntimeError, 'schema'):
            release.load_config(self.definition(missing))

    def test_build_entry_field_types_are_refused(self):
        (self.root / 'notes.md').write_text('notes')
        build = self.sample()['builds'][0]
        for change in ({'run': 'one'}, {'artifact': -2}, {'workflow': '../x.yml'},
                       {'file': 'sub/dir.deb'}, {'digest': 'c' * 63}, {'name': ''}):
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                release.load_config(self.definition(
                    {**self.sample(), 'builds': [{**build, **change}]}))


class ReleaseValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / 'assets'
        self.output.mkdir()
        self.build = dict(run=1, workflow='deb.yml', artifact=2, name='deepwin-deb-amd64',
                          file='devedu.deepin-configs_1.1.0-3_amd64.deb', digest='0' * 64)
        self.source = 'b' * 40
        self.tag = 'v1.1.0'

    def archive(self, checksum=None, duplicate=False):
        filename = self.build['file']
        package = b'accepted package fixture'
        checksum = checksum or f'{hashlib.sha256(package).hexdigest()}  {filename}\n'
        path = self.root / 'artifact.zip'
        with zipfile.ZipFile(path, 'w') as bundle:
            # ZIP paths are never extracted; even these names stay in output.
            bundle.writestr('../../' + filename, package)
            bundle.writestr('dist/' + filename + '.sha256', checksum)
            bundle.writestr('unapproved-debug.deb', b'not a release asset')
            if duplicate:
                bundle.writestr('duplicate/' + filename, package)
        self.build['digest'] = release.sha256(path)
        return path

    def test_only_installer_and_sidecar_selected_without_zip_path_extraction(self):
        release.prepare_asset(self.build, self.archive(), self.output)
        filename = self.build['file']
        self.assertEqual({p.name for p in self.output.iterdir()}, {filename, filename + '.sha256'})
        self.assertEqual((self.output / filename).read_bytes(), b'accepted package fixture')
        self.assertFalse((self.root.parent / filename).exists())

    def test_zip_tampering_is_refused_before_writing(self):
        archive = self.archive()
        with archive.open('ab') as stream:
            stream.write(b'tampering')
        with self.assertRaisesRegex(RuntimeError, 'ZIP digest mismatch'):
            release.prepare_asset(self.build, archive, self.output)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_wrong_sidecar_is_refused(self):
        archive = self.archive(checksum='0' * 64 + '  unexpected-file.deb\n')
        with self.assertRaisesRegex(RuntimeError, 'Package checksum mismatch'):
            release.prepare_asset(self.build, archive, self.output)

    def test_duplicate_filename_is_refused(self):
        archive = self.archive(duplicate=True)
        with self.assertRaisesRegex(RuntimeError, 'duplicate asset'):
            release.prepare_asset(self.build, archive, self.output)

    def test_unapproved_run_or_expired_artifact_is_refused(self):
        build = self.build
        run = dict(id=build['run'], head_sha=self.source, head_branch='main', event='push',
                   status='completed', conclusion='success',
                   path=f'.github/workflows/{build["workflow"]}',
                   head_repository={'full_name': release.REPOSITORY})
        artifact = dict(id=build['artifact'], name=build['name'], expired=False,
                        workflow_run={'id': build['run'], 'head_sha': self.source},
                        digest=f'sha256:{build["digest"]}')
        release.validate_run(build, run, artifact, self.source)
        for field, value in [('head_sha', 'unaccepted'), ('conclusion', 'failure'),
                             ('event', 'pull_request'), ('head_branch', 'other')]:
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                release.validate_run(build, {**run, field: value}, artifact, self.source)
        with self.assertRaises(RuntimeError):
            release.validate_run(build, run, {**artifact, 'expired': True}, self.source)
        with self.assertRaises(RuntimeError):
            release.validate_run(build, run, {**artifact, 'id': 1}, self.source)

    def test_remote_missing_changed_or_extra_asset_blocks_publication(self):
        path = self.output / 'package.deb'
        path.write_bytes(b'approved')
        assets = {path.name: path}
        item = dict(name=path.name, size=path.stat().st_size, state='uploaded',
                    digest=f'sha256:{release.sha256(path)}')
        draft = dict(tag_name=self.tag, draft=True, prerelease=False, assets=[item])
        release.validate_uploaded(draft, assets, self.tag)
        for changes in ({'assets': []}, {'assets': [item, item]}, {'draft': False},
                        {'assets': [{**item, 'digest': 'sha256:wrong'}]},
                        {'assets': [{**item, 'state': 'starter'}]}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                release.validate_uploaded({**draft, **changes}, assets, self.tag)

    def test_draft_lookup_uses_paginated_listing_instead_of_tag_endpoint(self):
        draft = dict(id=42, tag_name=self.tag, draft=True)
        with patch.object(release, 'command', return_value=json.dumps([[], [draft]])) as command:
            self.assertEqual(release.find_release(self.tag), draft)
        self.assertIn('--paginate', command.call_args.args)
        self.assertTrue(command.call_args.args[-1].endswith('/releases?per_page=100'))

    def test_draft_resume_refuses_published_or_edited_release(self):
        draft = dict(tag_name=self.tag, draft=True, prerelease=False,
                     name='DeepWin 1.1.0', body='Approved notes\n')
        release.validate_draft(draft, 'Approved notes\n', 'DeepWin 1.1.0', self.tag)
        for changes in ({'draft': False}, {'body': 'Manual changes'}, {'tag_name': 'v9.0.0'}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                release.validate_draft({**draft, **changes}, 'Approved notes\n',
                                       'DeepWin 1.1.0', self.tag)

    def test_published_release_is_a_no_op_only_when_fully_published(self):
        published = dict(tag_name=self.tag, draft=False, prerelease=False,
                         published_at='2026-10-18T21:34:00Z')
        self.assertTrue(release.already_published(published, self.tag))
        for changes in ({'draft': True}, {'published_at': None}, {'tag_name': 'v9.0.0'},
                        {'prerelease': True}):
            with self.subTest(changes=changes):
                self.assertFalse(release.already_published({**published, **changes}, self.tag))
        self.assertFalse(release.already_published(None, self.tag))
