"""Run the agreed language/theme/scale/size matrix in isolated subprocesses."""
import concurrent.futures
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
out=root/'build/ui-cohesion-matrix';out.mkdir(parents=True,exist_ok=True)
def run(case):
    lang,theme,scale,size=case
    name=f'{lang}-{theme}-{scale}-{size[0]}'
    env=dict(os.environ,QT_SCALE_FACTOR=str(scale),QT_FONT_DPI='96')
    result=subprocess.run([sys.executable,str(root/'tools/verify_ui_layout.py'),'--output',str(out/name),'--language',lang,'--theme',theme,'--width',str(size[0]),'--height',str(size[1])],env=env,capture_output=True,timeout=90)
    (out/(name+'.log')).write_bytes(result.stdout+result.stderr)
    report=json.loads((out/name/'layout.json').read_text(encoding='utf-8')) if (out/name/'layout.json').exists() else {}
    return dict(case=name,exit_code=result.returncode,pages=len(report.get('pages',[])),errors=report.get('errors',[]),overflows=sum(len(p['overflow']) for p in report.get('pages',[])))
cases=list(itertools.product(['zh','en'],['light','dark'],[1,1.25,1.5,2],[(1120,720),(1320,840)]))
reports=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for report in pool.map(run,cases):
        reports.append(report);print(json.dumps(report),flush=True)
(out/'results.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
raise SystemExit(any(r['exit_code'] or r['errors'] or r['overflows'] for r in reports))
