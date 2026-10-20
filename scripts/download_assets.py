import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

base = 'https://fuel.gazebosim.org/1.0/OpenRobotics/models/Standing%20person'
path = Path('assets/standing_person')
path.mkdir(parents=True, exist_ok=True)
metadata = json.load(urllib.request.urlopen(base, timeout=30))
if metadata['license_name'] != 'Creative Commons Zero v1.0 Universal':
    raise RuntimeError('Inspect changed asset license before proceeding')
archive = Path('assets/standing_person.zip')
if not archive.exists():
    urllib.request.urlretrieve(base+'/3/Standing%20person.zip', archive)
with zipfile.ZipFile(archive) as z:
    for name in z.namelist():
        if not (path/name).resolve().is_relative_to(path.resolve()):
            raise RuntimeError('Unsafe archive path')
    z.extractall(path)
metadata['downloaded_version'] = 3
metadata['archive_sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
metadata['source'] = base
Path('evidence').mkdir(exist_ok=True)
Path('evidence/standing_person_source.json').write_text(json.dumps(metadata,indent=2))
print('Downloaded version 3 to', path, '\nLicense:', metadata['license_name'])
