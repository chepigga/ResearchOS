import json
from pathlib import Path
R=Path(__file__).resolve().parent
x=json.loads((R/'output/side_execution_search.json').read_text())
out={k:{'perfect_count':v['perfect_count'],'best':v['best'],'top5':v['perfect_top20'][:5]} for k,v in x.items()}
(R/'output/side_best_summary.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
