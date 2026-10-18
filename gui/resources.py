"""Recursos distribuídos e runtime persistente, sem incluir dados pessoais."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

APP_ID = 'devedu.deepin-configs'


class ResourceError(RuntimeError):
    pass


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Resources:
    def __init__(self, home=None, root=None, data_home=None):
        self.home = Path(home or Path.home())
        self.root = Path(root or Path(__file__).resolve().parents[1]).resolve()
        self.data_home = Path(data_home or os.environ.get('XDG_DATA_HOME', self.home / '.local/share'))
        self.data = self.data_home / APP_ID
        self.runtime = self.data / 'runtime'
        self.current = self.runtime / 'current'

    def file(self, relative, required=True):
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts:
            raise ResourceError('Caminho de recurso inválido.')
        candidates = [self.root / path]
        if relative.startswith('qt6/'):
            candidates.append(Path(os.environ.get('DEEPWIN_BUILD_DIR', self.root / '.build/deepwin')) / path)
        if relative.startswith('systemd/'):
            candidates.append(self.root / 'packaging' / path)
        for candidate in candidates:
            if candidate.is_file() and not candidate.is_symlink():
                return candidate
        if not required:
            return None
        raise ResourceError('Recurso distribuído não encontrado: ' + relative)

    @property
    def version(self):
        return self.file('VERSION').read_text().strip()

    def files(self):
        try:
            manifest = json.loads(self.file('resources.json').read_text())
            if manifest.get('format') != 1 or not isinstance(manifest['files'], list):
                raise ValueError()
            optional = manifest.get('files_optional', [])
            if not isinstance(optional, list):
                raise ValueError()
            files = {name: self.file(name) for name in manifest['files']}
            # Extrações do pacote Linyaps ausentes no .deb; presentes entram
            # no runtime e no hash de identidade, ausentes são silenciosas.
            for name in optional:
                path = self.file(name, required=False)
                if path is not None:
                    files[name] = path
            return files
        except (KeyError, ValueError, TypeError, AttributeError) as error:
            raise ResourceError('Manifesto de recursos inválido.') from error

    def available(self):
        self.files()
        return True

    def validate_release(self, release):
        if release.is_symlink():
            raise ResourceError('O runtime contém uma personalização. Preserve-a antes de continuar.')
        try:
            marker = json.loads((release / 'runtime.json').read_text())
            if marker.get('owner') != APP_ID or marker.get('format') != 1:
                raise ValueError()
            actual = {}
            for path in release.rglob('*'):
                if '__pycache__' in path.parts and path.suffix == '.pyc':
                    continue
                if path.is_symlink():
                    raise ValueError()
                if path.is_file() and path != release / 'runtime.json':
                    actual[str(path.relative_to(release))] = sha256(path)
            if marker['files'] != actual:
                raise ValueError()
            return marker
        except (OSError, ValueError, KeyError, AttributeError) as error:
            raise ResourceError('O runtime foi personalizado. Nenhum arquivo foi sobrescrito.') from error

    @contextmanager
    def lock(self):
        if self.runtime.is_symlink():
            raise ResourceError('O diretório de runtime é um link personalizado. Nenhum arquivo foi alterado.')
        self.runtime.mkdir(parents=True, exist_ok=True)
        with (self.runtime / 'runtime.lock').open('a') as stream:
            os.chmod(stream.name, 0o600)
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def ensure(self):
        sources = self.files()
        hashes = {name: sha256(path) for name, path in sources.items()}
        identity = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:20]
        release = self.runtime / 'releases' / identity
        with self.lock():
            if self.current.exists() or self.current.is_symlink():
                if not self.current.is_symlink() or self.current.resolve().parent != (self.runtime / 'releases').resolve():
                    raise ResourceError('O caminho do runtime foi personalizado. Preserve-o antes de continuar.')
                self.validate_release(self.current.resolve())
            if release.exists():
                self.validate_release(release)
            else:
                release.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix='.runtime-', dir=release.parent) as temporary:
                    stage = Path(temporary) / 'payload'
                    stage.mkdir()
                    for name, source in sources.items():
                        target = stage / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source, target)
                        target.chmod(0o755 if name.startswith('bin/') else 0o644)
                    marker = {'owner': APP_ID, 'format': 1, 'version': self.version, 'files': hashes}
                    (stage / 'runtime.json').write_text(json.dumps(marker, indent=2))
                    self.validate_release(stage)
                    stage.rename(release)
            temporary_link = self.runtime / '.current-next'
            if temporary_link.exists() or temporary_link.is_symlink():
                raise ResourceError('Um arquivo temporário do runtime já existe. Preserve-o antes de continuar.')
            temporary_link.symlink_to(release.relative_to(self.runtime))
            os.replace(temporary_link, self.current)
        return self.current
