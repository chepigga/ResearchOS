exec(open("zvel2.py").read().split('def cross')[0])
rng=np.random.default_rng(1); i=rng.integers(400,N-300,20000); s=rng.choice([-1,1],20000)
evaluate("випадковий момент і бік",list(zip(i,s)))
