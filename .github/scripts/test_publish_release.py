"""Refusal checks for publishing accepted CI artifacts."""
import hashlib
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

import publish_release as release


class ReleaseValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / 'assets'
        self.output.mkdir()
        self.build = dict(release.BUILDS[0])

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
        run = dict(id=build['run'], head_sha=release.SOURCE, head_branch='main', event='push',
                   status='completed', conclusion='success',
                   path=f'.github/workflows/{build["workflow"]}',
                   head_repository={'full_name': release.REPOSITORY})
        artifact = dict(id=build['artifact'], name=build['name'], expired=False,
                        workflow_run={'id': build['run'], 'head_sha': release.SOURCE},
                        digest=f'sha256:{build["digest"]}')
        release.validate_run(build, run, artifact)
        for field, value in [('head_sha', 'unaccepted'), ('conclusion', 'failure'),
                             ('event', 'pull_request'), ('head_branch', 'other')]:
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                release.validate_run(build, {**run, field: value}, artifact)
        with self.assertRaises(RuntimeError):
            release.validate_run(build, run, {**artifact, 'expired': True})
        with self.assertRaises(RuntimeError):
            release.validate_run(build, run, {**artifact, 'id': 1})

    def test_remote_missing_changed_or_extra_asset_blocks_publication(self):
        path = self.output / 'package.deb'
        path.write_bytes(b'approved')
        assets = {path.name: path}
        item = dict(name=path.name, size=path.stat().st_size, state='uploaded',
                    digest=f'sha256:{release.sha256(path)}')
        draft = dict(tag_name=release.TAG, draft=True, prerelease=False, assets=[item])
        release.validate_uploaded(draft, assets)
        for changes in ({'assets': []}, {'assets': [item, item]}, {'draft': False},
                        {'assets': [{**item, 'digest': 'sha256:wrong'}]},
                        {'assets': [{**item, 'state': 'starter'}]}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                release.validate_uploaded({**draft, **changes}, assets)

    def test_draft_lookup_uses_paginated_listing_instead_of_tag_endpoint(self):
        import json
        draft = dict(id=42, tag_name=release.TAG, draft=True)
        with patch.object(release, 'command', return_value=json.dumps([[], [draft]])) as command:
            self.assertEqual(release.find_release(), draft)
        self.assertIn('--paginate', command.call_args.args)
        self.assertTrue(command.call_args.args[-1].endswith('/releases?per_page=100'))

    def test_draft_resume_refuses_published_or_edited_release(self):
        draft = dict(tag_name=release.TAG, draft=True, prerelease=False,
                     name='DeepWin 1.1.0', body='Approved notes\n')
        release.validate_draft(draft, 'Approved notes\n')
        for changes in ({'draft': False}, {'body': 'Manual changes'}, {'tag_name': 'v9.0.0'}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                release.validate_draft({**draft, **changes}, 'Approved notes\n')
