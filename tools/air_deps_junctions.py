"""Point an AIR project's .air/deps/<alias> entries at live path packages.

On Windows without symlink privilege, airproj materialises path dependencies
as copies under .air/deps/.store, so the compiler meets the same module both
as the live source and as a copy ("module name ... belongs to more than one
source file"). Directory junctions need no privilege and canonicalise to the
live package, so every module keeps exactly one identity.

  python air_deps_junctions.py PROJECT_DIR [PROJECT_DIR ...]

Each PROJECT_DIR needs an air.lock.json. Existing .air/deps content is removed
only if it contains no junctions or symlinks (it is generated data).
"""
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def has_reparse(path):
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            info = os.lstat(os.path.join(root, name))
            if getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                return os.path.join(root, name)
    return None


def is_reparse(path):
    try:
        return bool(os.lstat(path).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except FileNotFoundError:
        return False


def link_project(project):
    project = Path(project).resolve()
    lock = json.loads((project / 'air.lock.json').read_text(encoding='utf-8'))
    deps = project / '.air' / 'deps'
    if deps.exists():
        for entry in deps.iterdir():
            if is_reparse(entry):
                os.rmdir(entry)  # removes only the link
            elif entry.is_dir():
                found = has_reparse(entry)
                if found:
                    sys.exit(f'refusing to delete {entry}: contains link {found}')
                shutil.rmtree(entry)
            else:
                entry.unlink()
    deps.mkdir(parents=True, exist_ok=True)
    for package in lock['packages']:
        if package.get('source') != 'path':
            continue
        target = (project / package['location']).resolve()
        if not (target / 'air.project.json').exists():
            sys.exit(f'{project}: {package["alias"]} -> {target} is not an AIR package')
        link = deps / package['alias']
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)],
                       check=True, stdout=subprocess.DEVNULL)
        print(f'{link} -> {target}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for item in sys.argv[1:]:
        link_project(item)
