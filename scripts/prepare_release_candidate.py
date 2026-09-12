"""One bounded local packaging/installation audit; no publication or scene calls."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parents[1]
def run(args,cwd=ROOT):
    subprocess.run([str(a) for a in args],cwd=cwd,check=True)
def py(env):
    return env/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    out=args.output.resolve()
    if out.exists(): raise SystemExit('Output must be new; old evidence is preserved')
    out.mkdir(parents=True)
    status={'passed':False,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'working_tree_changes':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),
            'note':'Local preparation audit; not approval, tag movement or upload.'}
    try:
        run([sys.executable,ROOT/'scripts/check_public_release.py'])
        dist=out/'dist'
        run([sys.executable,'-m','build','--outdir',dist])
        artifacts=sorted(dist.iterdir())
        assert len(artifacts)==2
        run([sys.executable,'-m','twine','check','--strict',*artifacts])
        run([sys.executable,ROOT/'scripts/check_public_release.py','--artifacts',*artifacts])
        from validate_release import inspect_wheel, inspect_sdist, installed_probe, run as audit_run
        wheel=next(dist.glob('*.whl')); sdist=next(dist.glob('*.tar.gz'))
        status['artifacts']={'wheel':inspect_wheel(wheel),'sdist':inspect_sdist(sdist)}
        checks={}
        clean=out/'clean'; clean.mkdir()
        for label,artifact in [('wheel',wheel),('sdist',sdist)]:
            env=out/('venv-'+label); venv.EnvBuilder(with_pip=True).create(env)
            run([py(env),'-m','pip','install',artifact],cwd=clean)
            checks[label+'_probe']=installed_probe(py(env),clean)
            checks[label+'_tests']=audit_run([str(py(env)),'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_*.py'],clean)
            checks[label+'_dependencies']=audit_run([str(py(env)),'-m','pip','check'],clean)
        checks['source_tests']=audit_run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py'],ROOT)
        checks['docs']=audit_run([sys.executable,'-m','sphinx','-W','-E','-b','html',str(ROOT/'docs'),str(out/'html')],clean)
        status['checks']=checks
        status['passed']=all(x['passed'] for x in checks.values()) and all(x['passed'] for x in status['artifacts'].values())
        assert status['passed'], 'Audit failed; inspect report'
    finally:
        (out/'audit.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
    print('RELEASE_CANDIDATE_AUDIT_PASSED '+str(out/'audit.json'))

if __name__=='__main__': main()
