"""Fail closed on unexpected public files and selected credential patterns."""
import argparse
import ast
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {'README.md','CHANGELOG.md','LICENSE','RELEASING.md','pyproject.toml','.gitignore','.gitattributes','.readthedocs.yaml','PKG-INFO'}
DIRECTORIES = {'metacar_multiagent','tests','docs','scripts','.github'}
SECRETS = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|pypi-[A-Za-z0-9_-]{40,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')

def allowed(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name:
        return False
    if name in ROOT_FILES or name == 'examples/minimal_control.py':
        return True
    return (len(p.parts)>1 and p.parts[0] in DIRECTORIES and
            not any(x in {'__pycache__','_build','.env','Artifacts'} for x in p.parts) and
            p.suffix in {'.py','.md','.rst','.toml','.txt','.yml','.yaml'})

def check_content(name, data):
    if SECRETS.search(data):
        raise ValueError('Potential credential: '+name)
    if PurePosixPath(name).suffix in {'.md','.rst'} and any(word in data for word in [b'SOP', '\u5ba1\u8bae'.encode('utf-8')]):
        raise ValueError('Internal process wording in public documentation: '+name)

def git(*args):
    return subprocess.check_output(['git',*args], cwd=ROOT)

def check_repository():
    paths=set(git('ls-files','-z').split(b'\0')) | set(git('ls-files','--others','--exclude-standard','-z').split(b'\0'))
    for raw in sorted(paths-{b''}):
        name=raw.decode('utf-8')
        if not allowed(name): raise ValueError('Unexpected public path: '+name)
        path=ROOT/name
        if path.is_symlink(): raise ValueError('Public symlink: '+name)
        if path.exists(): check_content(name,path.read_bytes())
    # Audit the branch being published, including its reachable history.
    # Unrelated local refs are not publication inputs; never push them in bulk.
    history=git('log','HEAD','--format=','--name-only','--diff-filter=ACMR','-z')
    for raw in history.split(b'\0'):
        name=raw.decode('utf-8').strip('\n')
        if name and not allowed(name): raise ValueError('Unexpected historical path: '+name)
    objects=git('rev-list','--objects','HEAD').splitlines()
    blobs=0
    for line in objects:
        parts=line.split(b' ',1)
        if len(parts)!=2: continue
        oid,name=parts
        if git('cat-file','-t',oid.decode()).strip()!=b'blob': continue
        check_content(name.decode('utf-8'),git('cat-file','blob',oid.decode()))
        blobs+=1
    print(f'Public path/history/credential checks passed: {len(paths-{b""})} paths, {blobs} historical blobs. Not a general secret or answer-leak proof.')

def check_archive(path):
    if path.name.endswith('.whl'):
        with zipfile.ZipFile(path) as z:
            entries=[(i.filename,z.read(i)) for i in z.infolist() if not i.is_dir()]
        for name,data in entries:
            p=PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name: raise ValueError('Unsafe wheel path')
            if not (name.startswith('metacar_multiagent/') or p.parts[0].startswith('metacar_multiagent-') and p.parts[0].endswith('.dist-info')):
                raise ValueError('Unexpected wheel content: '+name)
            check_content(name,data)
    else:
        with tarfile.open(path) as t:
            for item in t.getmembers():
                if item.isdir(): continue
                if not item.isfile(): raise ValueError('Nonregular source archive entry')
                parts=PurePosixPath(item.name).parts
                if len(parts)<2 or not allowed('/'.join(parts[1:])): raise ValueError('Unexpected sdist content: '+item.name)
                check_content(item.name,t.extractfile(item).read())

def check_version(tag):
    version=re.search(r'^version\s*=\s*"([^"]+)"', (ROOT/'pyproject.toml').read_text('utf-8'), re.M).group(1)
    module=ast.parse((ROOT/'metacar_multiagent/__init__.py').read_text('utf-8'))
    actual=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets))
    assert actual==version
    if tag:
        assert tag=='v'+version, 'Tag does not match version'
        assert git('rev-parse',tag+'^{commit}').strip()==git('rev-parse','HEAD').strip(), 'Tag does not identify HEAD'

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--tag')
    p.add_argument('--artifacts',nargs='*',type=Path,default=[])
    args=p.parse_args()
    check_repository()
    check_version(args.tag)
    for artifact in args.artifacts: check_archive(artifact)
