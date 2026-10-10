import importlib.util,ast
from pathlib import Path
import numpy as np,pandas as pd
P=Path(__file__).parent
sp=importlib.util.spec_from_file_location('atlas',P/'run_lab160.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
root=P.parents[1];src=root/'labs/LAB158_VOLUME_PROFILE_OI_CROWD_ACCEPTANCE_20261010/run_lab158.py'
tree=ast.parse(src.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['vap_profile','shape_name']]
ns={'np':np,'PROFILE_BINS':40,'VALUE_FRAC':.7};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(src),'exec'),ns)
rng=np.random.default_rng(160);c=100+np.cumsum(rng.normal(0,.1,800));h=c+rng.uniform(0,.2,800);l=c-rng.uniform(0,.2,800);v=rng.uniform(1,20,800)
a=m.profiles(h,l,c,v)
for i in [287,288,400,799]:
 p=ns['vap_profile'](pd.DataFrame({'high':h[i-287:i+1],'low':l[i-287:i+1],'close':c[i-287:i+1],'volume':v[i-287:i+1]}))
 np.testing.assert_allclose(a[i,:3],[p['poc'],p['val'],p['vah']],rtol=1e-12)
 assert ['D','P','b','DOUBLE'][int(a[i,3])]==ns['shape_name'](p)
# Causal prefix invariance
np.testing.assert_allclose(m.profiles(h[:401],l[:401],c[:401],v[:401])[-1],a[400])
atr=np.ones(800);out=m.labels(h,l,c,atr,72)
for i in [0,100,400]:
 hh=h[i+1:i+73];ll=l[i+1:i+73]
 np.testing.assert_allclose(out[i,:3],[c[i+72]-c[i],max(0,max(hh)-c[i]),max(0,c[i]-min(ll))])
 for k,level in enumerate(m.LEVELS):
  u=np.where(hh>=c[i]+level)[0];d=np.where(ll<=c[i]-level)[0]
  assert out[i,5+k]==((u[0]+1)*5 if len(u) else -1)
  assert out[i,9+k]==((d[0]+1)*5 if len(d) else -1)
hh=np.array([100.,102.,100.]);ll=np.array([100.,99.,100.]);cc=np.array([100.,100.,100.]);aa=np.ones(3)
assert m.labels(hh,ll,cc,aa,1)[0,13]==-1
hh[1]=np.nan
assert np.isnan(m.labels(hh,ll,cc,aa,1)[0]).all()
print('PASS: LAB158 profile parity; prefix invariance; future-bar exclusion and barrier timing; same-bar ambiguity; missing-path invalidation.')
