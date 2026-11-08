import json, os
from tomas import TOMAS
D = os.path.dirname(os.path.abspath(__file__))
def calcular(total):
    w = json.load(open(os.path.join(D, "alineacion.json")))["words"]
    texto, starts, pos = "", [], 0
    for x in w:
        starts.append((len(texto), x["start"])); texto += x["text"]
    def t_at(i):
        best = 0
        for c, s in starts:
            if c <= i: best = s
            else: break
        return best
    out, cur = [], 0
    for anc, spec in TOMAS:
        i = texto.find(anc, cur)
        if i < 0: raise SystemExit(f"Ancla no encontrada: {anc!r}")
        cur = i + 1
        out.append([max(0.0, t_at(i) - 0.15), spec, anc])
    out[0][0] = 0.0
    res = []
    for k, (s, spec, anc) in enumerate(out):
        e = out[k + 1][0] if k + 1 < len(out) else total
        res.append((s, e, spec, anc))
    return res
if __name__ == "__main__":
    for s, e, spec, anc in calcular(560.0):
        flag = " <<<" if e - s > 6 or e - s < 2 else ""
        print(f"{s:7.2f} {e-s:5.2f} {spec['t']:7} {anc[:40]}{flag}")
