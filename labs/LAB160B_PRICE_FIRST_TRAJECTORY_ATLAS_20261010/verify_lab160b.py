from pathlib import Path
import importlib.util,numpy as np
P=Path(__file__).parent
sp=importlib.util.spec_from_file_location('lab160b',P/'run_lab160b.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
for seq,expected in [([100,98.8,100,105,104],7),([100,100.5,102,104,103],5),([100,103,102,100.1],3),([100,102,98,100],2),([100,100.8,100.1],1),([100,100.2,100.1],0)]:
 c=np.array(seq,dtype=float);r=m.paths(c,c,c,np.ones(len(c)),len(c)-1)[0]
 assert int(r[16])==expected,(seq,r)
 assert abs(r[0]-(c[-1]-c[0]))<1e-12
 assert abs(r[1]-max(0,max(c[1:])-c[0]))<1e-12
 assert abs(r[2]-max(0,c[0]-min(c[1:])))<1e-12
 if expected==7:assert r[5]>1.19 and r[1]==5 and r[0]==4
 if expected in [3,5,7]:
  inv=200-c;z=m.paths(inv,inv,inv,np.ones(len(c)),len(c)-1)[0];assert int(z[16])==expected+1
r=m.paths(np.array([100.,105.]),np.array([100.,98.]),np.array([100.,104.]),np.ones(2),1)[0]
assert r[16]==9 and r[5]==0 and r[6]==2
c=np.array([100.,np.nan,102.]);assert np.isnan(m.paths(c,c,c,np.ones(3),2)[0]).all()
c=np.array([100.,101.,102.,105.]);r=m.paths(c,c,c,np.ones(4),2)[0];assert r[0]==2 and r[1]==2
assert np.isnan(m.paths(c,c,c,np.ones(4),2)[-2:]).all()
print('PASS: delayed -1.2→+5 retained; all primary shape examples; mirror invariance; intrabar order ambiguity; missing/tail invalidation; future horizon boundary.')
