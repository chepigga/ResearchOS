from pathlib import Path
p=Path('sell_core_014_b3_lhbos_long_history.py')
s=p.read_text()
old="prim=S[(S.phase_min==20)&(((S.view=='NATIVE')&(S.hold_h==48))|((S.view=='CANONICAL')&(S.hold_h.isin([48,72])))]"
new="prim=S[(S.phase_min==20)&(((S.view=='NATIVE')&(S.hold_h==48))|((S.view=='CANONICAL')&(S.hold_h.isin([48,72]))))]"
assert old in s
s=s.replace(old,new,1)
compile(s,str(p),'exec')
exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
