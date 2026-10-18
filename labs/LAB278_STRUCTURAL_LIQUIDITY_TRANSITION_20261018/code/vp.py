"""Structural volume profile helpers (LAB278). Log-price bins, step STEP. Hourly profile slices -> rolling window sums."""
import numpy as np,pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
STEP=0.002; P0=np.log(8000.0)
def b(p): return np.floor((np.log(p)-P0)/STEP).astype(int)
def bprice(k): return np.exp(P0+(k+0.5)*STEP)
NB=int(np.ceil((np.log(250000)-P0)/STEP))+2
def hourly_from_bars(t,lo,hi,v,hours):
    """uniform spread of bar volume over [lo,hi] bins; returns float32 matrix len(hours) x NB"""
    hix=np.searchsorted(hours.values,t.floor("1h").values)
    a=b(lo); z=b(hi); w=v/(z-a+1)
    D=np.zeros((len(hours),NB+1),np.float64)
    np.add.at(D,(hix,a),w); np.add.at(D,(hix,z+1),-w)
    return np.cumsum(D,axis=1)[:,:NB].astype(np.float32)
def hourly_from_points(t,p,v,hours):
    hix=np.searchsorted(hours.values,t.floor("1h").values)
    M=np.zeros((len(hours),NB),np.float64); np.add.at(M,(hix,b(p)),v); return M.astype(np.float32)
def window(CUM,h,W):
    """profile from hours (h-W, h]  (CUM = cumsum over hours with leading zero row)"""
    return CUM[h+1]-CUM[max(h+1-W,0)]
def nodes(P,sig=2.0,lvn_ratio=0.5,min_prom=0.15):
    """HVN = peaks of smoothed profile with prominence >= min_prom*max; LVN = min between adjacent HVNs if <= lvn_ratio*min(two HVN)"""
    s=gaussian_filter1d(P.astype(float),sig)
    if s.max()<=0: return s,np.array([],int),[]
    pk,_=find_peaks(s,prominence=min_prom*s.max())
    lv=[]
    for a,c in zip(pk[:-1],pk[1:]):
        m=a+int(np.argmin(s[a:c+1]))
        if s[m]<=lvn_ratio*min(s[a],s[c]): lv.append((a,m,c))
    return s,pk,lv
