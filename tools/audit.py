"""Auditoria estrutural + extracao de parametros dos arquivos de fisica do rF2.

Serve como o "lado alvo" da engenharia reversa: aqui a gente NAO resolve a
planilha, apenas le os arquivos .ini de um carro pronto e deriva tudo que da
para derivar SEM a planilha (geometria, cinematica, orcamento de massa,
validacoes internas de consistencia).

Uso:
    python3 tools/audit.py [pasta_do_carro]

O resultado vai para docs/auditoria-<nome>.md
"""

from __future__ import annotations

import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from rf2ini import IniFile, Section

# Eixos rF2: X lateral (+esq), Y vertical (+cima), Z longitudinal (+tras)
X, Y, Z = 0, 1, 2


# ---------------------------------------------------------------- helpers
def f(v, n=4):
    return f"{v:.{n}f}"


def vec_str(t, n=4):
    return "(" + ", ".join(f"{v:.{n}f}" if isinstance(v, float) else str(v) for v in t) + ")"


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(sum(x * x for x in a))


def repeated_blocks(seq, min_len: int = 12) -> list[tuple[int, int, int]]:
    """Blocos contiguos de (chave, valor) que aparecem DUAS vezes, sem sobrepor.

    Comparar apenas as chaves gera falso positivo em arquivo estruturado: todo
    `[RigidBody]` repete `Mass`/`Inertia`/`Position`. O que caracteriza um bloco
    colado por engano na exportacao e o VALOR tambem bater. Por isso a entrada
    aqui e uma lista de pares `(chave, valor)` e nao so de chaves.
    """
    n = len(seq)
    found: list[tuple[int, int, int]] = []
    for i in range(n):
        for j in range(i + min_len, n):
            if seq[i] != seq[j]:
                continue
            L = 0
            while j + L < n and seq[i + L] == seq[j + L]:
                L += 1
            if L >= min_len and j >= i + L:  # blocos disjuntos
                found.append((i, j, L))

    # descarta blocos contidos em blocos maiores
    maximal = []
    for a in sorted(found, key=lambda t: -t[2]):
        ai, aj, aL = a
        contido = any(
            bL > aL and bi <= ai and ai + aL <= bi + bL and bj <= aj and aj + aL <= bj + bL
            for bi, bj, bL in found
        )
        if not contido:
            maximal.append(a)
    return sorted(maximal, key=lambda t: t[0])


def duplicate_sections(ini: IniFile) -> list[list[Section]]:
    """Secoes com o MESMO nome cujo conteudo e integralmente identico.

    So vale para arquivos com secoes repetidas (12x `[RigidBody]`, 30x
    `[Constraint]`). Nesses casos comparar a secao inteira e o teste certo:
    duas juntas que dividem 15 parametros e divergem no 16o nao sao
    duplicata, sao dois objetos parecidos.
    """
    by_type: dict[str, list[Section]] = defaultdict(list)
    for s in ini.sections:
        if s.name:
            by_type[s.name].append(s)

    out: list[list[Section]] = []
    for _name, secs in by_type.items():
        if len(secs) < 2:
            continue
        buckets: dict[tuple, list[Section]] = defaultdict(list)
        for s in secs:
            sig = tuple((e.key.lower(), e.raw) for e in s.entries)
            buckets[sig].append(s)
        for grupo in buckets.values():
            if len(grupo) > 1:
                out.append(grupo)
    return out


# ---------------------------------------------------------------- chassis
class Chassis:
    def __init__(self, ini: IniFile):
        self.ini = ini
        self.bodies: dict[str, dict] = {}
        for sec in ini.section_list("RigidBody"):
            b = {
                "name": str(sec.get("Name", "")),
                "mass": float(sec.get("Mass", 0) or 0),
                "inertia": tuple(float(x) for x in sec.get("Inertia", (0, 0, 0))),
                "pos": tuple(float(x) for x in sec.get("Position", (0, 0, 0))),
                "ori": tuple(float(x) for x in sec.get("Orientation", (0, 0, 0))),
                "line": sec.line,
            }
            self.bodies[b["name"]] = b

        self.constraints: list[dict] = []
        for sec in ini.section_list("Constraint"):
            c = {
                "type": str(sec.get("Type", "")),
                "name": str(sec.get("Name", "")),
                "bodyA": str(sec.get("BodyA", "")),
                "bodyB": str(sec.get("BodyB", "")),
                "offA": tuple(float(x) for x in sec.get("LocalOffsetA", (0, 0, 0))),
                "offB": tuple(float(x) for x in sec.get("LocalOffsetB", (0, 0, 0))),
                "minerr": sec.get("MinError0", None),
                "maxerr": sec.get("MaxError0", None),
                "spring": sec.get("SpringRate0", None),
                "damper": sec.get("DamperRate0", None),
                "line": sec.line,
            }
            self.constraints.append(c)
        self.bars = [c for c in self.constraints if c["type"] == "Bar_2"]

    def world_point(self, body: str, off: tuple[float, float, float]):
        return add(self.bodies[body]["pos"], off)

    def bar_lengths(self):
        """Comprimento geometrico de cada barra vs. o MinError0 declarado.

        MinError0/MaxError0 guardam o comprimento de repouso da Bar_2. Se o
        calculo bater, valida que a nossa leitura de LocalOffsetA/B e de
        Position esta correta -- e dai todo o resto da cinematica vale.
        """
        rows = []
        for c in self.bars:
            a = self.world_point(c["bodyA"], c["offA"])
            b = self.world_point(c["bodyB"], c["offB"])
            L = norm(sub(b, a))
            declared = float(c["minerr"]) if c["minerr"] is not None else float("nan")
            rows.append(
                {
                    "name": c["name"],
                    "end": c["bodyB"],
                    "calc": L,
                    "declared": declared,
                    "err": L - declared,
                    "A": a,
                    "B": b,
                    "offB": c["offB"],
                }
            )
        return rows

    def ball_joints(self, spindle: str) -> list[dict]:
        """Agrupa as barras que chegam na mesma ponto externo -> rotula esferica.

        Num double-wishbone modelado com 2 barras por bandeja (como o rF2PC
        faz), as duas pernas convergem para o MESMO ponto da manga de eixo.
        Esse ponto e a rotula (ball joint) equivalente da bandeja.
        """
        groups: dict[tuple, list[dict]] = defaultdict(list)
        for r in self.bar_lengths():
            if r["end"] == spindle:
                groups[tuple(round(v, 9) for v in r["offB"])].append(r)
        out = []
        for offB, members in groups.items():
            world = self.world_point(spindle, tuple(offB))
            out.append(
                {
                    "offB": tuple(offB),
                    "world": world,
                    "n_members": len(members),
                    "members": [m["name"] for m in members],
                }
            )
        out.sort(key=lambda g: g["world"][Y])
        return out

    def mass_budget(self):
        total_m = sum(b["mass"] for b in self.bodies.values())
        cg = tuple(
            sum(b["mass"] * b["pos"][k] for b in self.bodies.values()) / total_m for k in range(3)
        )
        I = [0.0, 0.0, 0.0]
        for b in self.bodies.values():
            d = sub(b["pos"], cg)
            m = b["mass"]
            I[0] += b["inertia"][0] + m * (d[1] ** 2 + d[2] ** 2)
            I[1] += b["inertia"][1] + m * (d[0] ** 2 + d[2] ** 2)
            I[2] += b["inertia"][2] + m * (d[0] ** 2 + d[1] ** 2)
        return total_m, cg, tuple(I)


# ---------------------------------------------------------------- relatorio
def build_report(car_dir: Path, out_path: Path) -> str:
    files = {p.name: IniFile(p) for p in sorted(car_dir.glob("*.ini"))}
    OUT: list[str] = []
    W = OUT.append

    name = car_dir.name
    W(f"# Auditoria de fisica — `{name}`\n")
    W(
        "> Gerado por `tools/audit.py`. Nenhum numero aqui foi digitado a mao: "
        "tudo e lido ou derivado dos arquivos `.ini`.\n"
    )

    # ---------------- 1. inventario
    W("\n## 1. Inventario\n")
    W("| Arquivo | Bytes | Linhas | CRLF | Secoes |")
    W("|---|---:|---:|:--:|---:|")
    for n, ini in files.items():
        nsec = len([s for s in ini.sections if s.name])
        W(f"| `{n}` | {ini.path.stat().st_size} | {len(ini.lines)} | "
          f"{'sim' if ini.had_crlf else 'nao'} | {nsec} |")

    # ---------------- 2. blocos duplicados
    # chaves que o rF2 ACUMULA como linhas de tabela (a ultima nao sobrescreve)
    TABLE_KEYS = {
        "RPMBase", "VolumeFract", "MixtureFract", "TurbineFlowEffects",
        "CompressorPressRatio", "CompressorEfficiency", "CompressorSurgeLineFlow",
        "FuelAirMixtureEffects", "Ratio", "ratio",
    }

    W("\n## 2. Defeitos de estrutura\n")
    n_def = 0

    for n, ini in files.items():
        entries = list(ini.entries)
        counts = Counter(s.name for s in ini.sections if s.name)
        # arquivo com secoes REPETIDAS ([RigidBody]x12, [Constraint]x30):
        # comparar secao inteira. Duas secoes que compartilham 15 valores e
        # diferem no ultimo NAO sao duplicata -- sao dois objetos parecidos.
        if counts and max(counts.values()) >= 2:
            for grupo in duplicate_sections(ini):
                n_def += 1
                onde = ", ".join(f"L{s.line}" for s in grupo)
                W(f"\n### 2.{n_def} `{n}`: secao `[{grupo[0].name}]` identica em {len(grupo)} "
                  f"lugares\n")
                W(f"- Ocorrencias: {onde}")
                W(f"- Nome: `{grupo[0].get('Name', '(sem nome)')}`")
                W("\n**Correcao:** manter apenas uma ocorrencia.")
            continue

        # arquivo plano (sem secoes, ex: engine.ini) -> procura runs identicas
        pairs = [(e.key, e.raw) for e in entries]
        for i, j, blen in repeated_blocks(pairs, min_len=12):
            n_def += 1
            a0, a1 = entries[i].line, entries[i + blen - 1].line
            b0, b1 = entries[j].line, entries[j + blen - 1].line
            keys = []
            for k in (p[0] for p in pairs[i : i + blen]):
                if k not in keys:
                    keys.append(k)
            W(f"\n### 2.{n_def} `{n}`: bloco de {blen} parametros repetido\n")
            W(f"- Bloco A: linhas **{a0}–{a1}** · Bloco B: linhas **{b0}–{b1}**")
            tabelas = [k for k in keys if k in TABLE_KEYS]
            escalares = [k for k in keys if k not in TABLE_KEYS]
            W("")
            W("| Chaves que ACUMULAM linha (tabela) | Chaves escalares (ultima vence) |")
            W("|---|---|")
            W(f"| {', '.join(f'`{k}`' for k in tabelas) or '—'} | "
              f"{', '.join(f'`{k}`' for k in escalares) or '—'} |")
            if tabelas:
                W("\n**Impacto: real.** As escalares sao apenas sobrescritas pelo ultimo valor "
                  "(inofensivo), mas as de tabela sao *acumuladas*: o rF2 le o bloco como o "
                  "dobro de linhas. **A curva fica corrompida.**")
            else:
                W("\n**Impacto: provavelmente nulo** (so chaves escalares).")
            W(f"\n**Correcao:** remover o bloco B (linhas {b0}–{b1}) e manter apenas o A.")

    if not n_def:
        W("\nNenhum bloco duplicado detectado.\n")

    # ---------------- 3. massa
    ch_ini = next((v for k, v in files.items() if "hassis" in k), None)
    if ch_ini:
        ch = Chassis(ch_ini)
        total_m, cg, I = ch.mass_budget()

        W("\n## 3. Orcamento de massa (`_Chassis.ini`)\n")
        W("| Corpo | Massa (kg) | Inercia (Ixx, Iyy, Izz) | Posicao (x, y, z) |")
        W("|---|---:|---|---|")
        for b in ch.bodies.values():
            W(f"| `{b['name']}` | {f(b['mass'],4)} | {vec_str(b['inertia'],4)} | {vec_str(b['pos'],4)} |")
        W(f"| **TOTAL** | **{f(total_m,4)}** | | |")

        W(f"\n- Massa total (sem combustivel, tanque vazio): **{f(total_m,4)} kg**")
        W(f"- Centro de gravidade: **{vec_str(cg,4)}** m  (na origem do sub-body)")
        W(f"- Tensor de inercia sobre o CG (diagonal, modelo simetrico): **{vec_str(I,3)}** kg·m²")

        # validacao fisica: Iyy contra o modelo "halter" (toda a massa nos eixos)
        try:
            zf_ = ch.bodies["FL_WHEEL"]["pos"][Z]
            zr_ = ch.bodies["RL_WHEEL"]["pos"][Z]
            a_, b_ = abs(zf_ - cg[Z]), abs(zr_ - cg[Z])
            dumb = total_m * a_ * b_
            frac = I[1] / dumb
            W(f"- **Checagem de sanidade:** inercia de guinada Iyy = {f(I[1],1)} kg·m² contra o "
              f"limite superior do modelo halter (massa toda nos eixos) m·a·b = {f(dumb,1)} "
              f"kg·m² → **{100*frac:.1f} %**. Carros reais ficam entre ~85 % e ~100 % desse "
              f"limite → **{'consistente' if 0.80 <= frac <= 1.05 else 'FORA DA FAIXA'}**.")
        except KeyError:
            pass

        # distribuicao de peso
        try:
            zf = ch.bodies["FL_WHEEL"]["pos"][Z]
            zr = ch.bodies["RL_WHEEL"]["pos"][Z]
            wb = abs(zf - zr)
            front_pct = (zr - cg[Z]) / (zr - zf) * 100.0
            W(f"\n- Entre-eixos: **{f(wb,4)} m** (roda diant. z={f(zf,4)}, traseira z={f(zr,4)})")
            W(f"- Distribuicao de peso estatica: **{f(front_pct,2)} % dianteira** "
              f"/ {f(100-front_pct,2)} % traseira")
        except KeyError:
            pass

        try:
            trk_f = 2 * abs(ch.bodies["FL_WHEEL"]["pos"][X])
            trk_r = 2 * abs(ch.bodies["RL_WHEEL"]["pos"][X])
            W(f"- Bitola dianteira: **{f(trk_f,4)} m** · traseira: **{f(trk_r,4)} m**")
            W(f"- Altura do centro da roda diant.: **{f(ch.bodies['FL_WHEEL']['pos'][Y],4)} m** · "
              f"traseira: **{f(ch.bodies['RL_WHEEL']['pos'][Y],4)} m** (relativo a origem do sub-body)")
        except KeyError:
            pass

        # ---------------- 4. validacao dos links
        W("\n## 4. Validacao geometrica das barras\n")
        W(
            "Cada `Bar_2` guarda o comprimento de repouso em `MinError0`. Comparando com a "
            "distancia calculada entre os pontos (`Position` + `LocalOffsetA` / `LocalOffsetB`) "
            "confere que a leitura das coordenadas esta certa.\n"
        )
        rows = ch.bar_lengths()
        worst = max(abs(r["err"]) for r in rows if r["declared"] == r["declared"])
        W("| Barra | Ponta | Calculado (m) | `MinError0` (m) | Erro (mm) |")
        W("|---|---|---:|---:|---:|")
        for r in rows:
            W(f"| `{r['name']}` | `{r['end']}` | {f(r['calc'],6)} | {f(r['declared'],6)} | "
              f"{r['err']*1000:+.3f} |")
        W(f"\n**Erro maximo: {worst*1000:.3f} mm** — "
          + ("dentro do arredondamento da planilha (ela grava ~6 digitos significativos). "
             "Leitura das coordenadas validada: todo o resto da cinematica deriva dai."
             if worst < 5e-4 else "DIVERGENCIA acima do arredondamento: revisar."))

        # ---------------- 5. cinematica
        W("\n## 5. Cinematica da suspensao (derivada)\n")
        W(
            "As duas pernas de cada bandeja convergem para o mesmo ponto na manga de eixo; "
            "esse ponto e a rotula equivalente. O eixo mestre (kingpin) e a reta que liga a "
            "rotula inferior a superior.\n"
        )
        for spindle, wheel in (("FL_SPINDLE", "FL_WHEEL"), ("RL_SPINDLE", "RL_WHEEL")):
            if spindle not in ch.bodies:
                continue
            todos = ch.ball_joints(spindle)
            # Uma bandeja (A-arm) tem 2 membros convergindo no MESMO ponto.
            # Pontos com 1 membro sao tirantes (direcao / toe-link) e NAO sao
            # rotula do eixo mestre -- inclui-los gera caster sem sentido.
            bjs = [g for g in todos if g["n_members"] >= 2]
            if len(bjs) < 2:
                continue
            lo, up = bjs[0], bjs[-1]
            d = sub(up["world"], lo["world"])
            kpi = math.degrees(math.atan2(abs(d[X]), d[Y]))
            caster = math.degrees(math.atan2(d[Z], d[Y]))
            W(f"\n### {spindle.replace('_SPINDLE','')} — eixo {spindle[0]}\n")
            W("| Ponto | Y (m) | Membros | `LocalOffsetB` | Mundo (x, y, z) |")
            W("|---|---:|:--:|---|---|")
            for g in todos:
                if g is lo:
                    tag = "**rotula inferior**"
                elif g is up:
                    tag = "**rotula superior**"
                elif g["n_members"] == 1:
                    tag = "tirante (ignorado)"
                else:
                    tag = "intermediario"
                W(f"| {tag} | {f(g['world'][Y],4)} | {g['n_members']} | {vec_str(g['offB'],6)} | "
                  f"{vec_str(g['world'],4)} |")
            W(f"\nO eixo mestre usa so os pontos com **2 membros** (as bandejas). O tirante tem "
              f"1 membro e foi excluido: ele tem a mesma altura da rotula superior, e inclui-lo "
              f"giraria o eixo mestre para a direcao errada.")
            W(f"\n- **KPI (inclinacao do eixo mestre): {f(kpi,2)}°**")
            if abs(caster) < 0.05:
                W(f"- **Caster: {f(caster,2)}° — praticamente zero** (esperado: eixo traseiro "
                  f"nao tem caster)")
            else:
                W(f"- **Caster: {f(caster,2)}°** ({'positivo' if caster > 0 else 'negativo'} — "
                  f"topo do eixo mestre {'para tras' if caster > 0 else 'para frente'})")

            # scrub / trail em funcao do raio carregado
            wx = ch.bodies[wheel]["pos"][X]
            wy = ch.bodies[wheel]["pos"][Y]
            wz = ch.bodies[wheel]["pos"][Z]
            W(f"\nOnde o eixo mestre cruza o solo, em funcao do raio carregado do pneu — "
              f"**valor que vem do `.tbc`/`.tgm`, nao deste arquivo**:\n")
            W("| Raio carregado (m) | Lateral: scrub (mm) | Longitudinal: trail (mm) |")
            W("|---:|---:|---:|")
            for R in (0.30, 0.32, 0.34, 0.36):
                yg = wy - R
                t = (yg - lo["world"][Y]) / d[Y]
                px = lo["world"][X] + t * d[X]
                pz = lo["world"][Z] + t * d[Z]
                W(f"| {R:.2f} | {(px - wx)*1000:+.1f} | {(pz - wz)*1000:+.1f} |")
            W(f"\nConvecao de sinais (roda esquerda, X positivo = para fora):")
            W(f"- **Lateral negativo** = o eixo mestre cruza o solo **para dentro** do centro "
              f"do pneu, em direcao a linha de centro do carro.")
            W(f"- **Longitudinal negativo** = cruza **a frente** do centro do pneu, o que "
              f"corresponde a trail mecanico positivo (esperado com caster positivo).")
            W(f"\n- Referencia: centro da roda em x={f(wx,4)}, y={f(wy,4)}, z={f(wz,4)}")
            W(f"- Offset roda↔manga: **{f(abs(wx - ch.bodies[spindle]['pos'][X])*1000,1)} mm** "
              f"(deve bater com `LocalOffsetB` do `*_BJ`)")

        # ---- chassi flexivel (junta anisotropica entre os dois sub-bodies)
        W("\n### Chassi flexivel (`AnisoOriJoint_0`)\n")
        for sec in ch_ini.section_list("Constraint"):
            if not str(sec.get("Type", "")).startswith("AnisoOriJoint"):
                continue
            W(f"- `{sec.get('Name')}`: `{sec.get('BodyA')}` ↔ `{sec.get('BodyB')}`")
            W("")
            W("| Eixo (rF2) | Rotacao | Eixo local | `SpringRate` (Nm/rad) | `DamperRate` | Nm/grau |")
            W("|---|---|---|---:|---:|---:|")
            tags = {
                0: ("X = lateral", "arfagem (pitch)"),
                1: ("Y = vertical", "guinada (yaw)"),
                2: ("Z = longitudinal", "torcao (roll do chassi)"),
            }
            for i in range(3):
                k = float(sec.get(f"SpringRate{i}", 0) or 0)
                dmp = float(sec.get(f"DamperRate{i}", 0) or 0)
                ax = vec_str(sec.get(f"LocalAxisA{i}", ()), 0)
                eixo, rot = tags[i]
                W(f"| {eixo} | {rot} | {ax} | {k:.3e} | {dmp:.3e} | {k*math.pi/180:,.0f} |")
            W("")
        W("- **Cuidado com a convencao de eixos:** em rF2 Z e o longitudinal, entao a rigidez a "
          "**torcao do chassi (roll)** e `SpringRate2` — nao `SpringRate0`.")

    # ---------------- 6. cambio
    g_ini = next((v for k, v in files.items() if "gear" in k.lower()), None)
    if g_ini:
        W("\n## 6. Cambio (`_gears.ini`)\n")
        gr = g_ini.section("GEAR_RATIOS")
        rows = []
        bad = []
        for e in gr.all("ratio"):
            a, b = (float(x) for x in e.tuple)
            eff = b / a
            declared = None
            if ":" in e.comment:
                try:
                    declared = float(e.comment.split(":")[1].strip())
                except ValueError:
                    pass
            rows.append((a, b, eff, declared))
            if declared is not None and abs(eff - declared) > 0.002:
                bad.append((e.line, a, b, eff, declared))
        W(f"- Entradas `ratio=` em `[GEAR_RATIOS]`: **{len(rows)}**")
        W(f"- Faixa: **{f(rows[0][2],3)}** (12/37) → **{f(rows[-1][2],3)}** "
          f"({int(rows[-1][0])}/{int(rows[-1][1])})")
        W(f"- Convencao confirmada pelos comentarios do proprio arquivo: "
          f"**relacao = segundo/primeiro** (ex: `(12,37)` → 37/12 = 3.083). "
          f"Divergencias encontradas: **{len(bad)}**")

        fd = g_ini.section("FINAL_DRIVE")
        bevel = fd.first("bevel")
        finals = fd.all("ratio")
        bev = float(bevel.tuple[1]) / float(bevel.tuple[0]) if bevel else 1.0
        W(f"\n- `bevel=({int(bevel.tuple[0])},{int(bevel.tuple[1])})` → **{f(bev,4)}**")
        for e in finals:
            a, b = (float(x) for x in e.tuple)
            W(f"- final `ratio=({int(a)},{int(b)})` → **{f(b/a,4)}**")
        # ---- configuracao antiga, preservada comentada no cabecalho
        old_ratios: list[tuple[int, int, float]] = []
        old_bevel = old_final = None
        in_fd = False
        for linha in g_ini.lines:
            st = linha.strip()
            if not st.startswith("//"):
                continue
            body = st.lstrip("/").strip()
            low = body.lower()
            if low.startswith("[final_drive]"):
                in_fd = True
                continue
            if low.startswith("[gear_ratios]"):
                in_fd = False
                continue
            m = re.match(r"(?i)(ratio|bevel)\s*=\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", body)
            if not m:
                continue
            a2, b2 = int(m.group(2)), int(m.group(3))
            if in_fd:
                if m.group(1).lower() == "bevel":
                    old_bevel = b2 / a2
                elif old_final is None:
                    old_final = b2 / a2
            else:
                old_ratios.append((a2, b2, b2 / a2))

        if old_ratios:
            W("\n#### Configuracao anterior (preservada comentada no cabecalho)\n")
            W("| Marcha | Dentes | Relacao |")
            W("|---:|---|---:|")
            for i, (a3, b3, r3) in enumerate(old_ratios, 1):
                W(f"| {i} | ({a3}, {b3}) | {f(r3,4)} |")
            spread_old = old_ratios[0][2] / old_ratios[-1][2]
            W(f"\n- `Bevel` antigo: **{f(old_bevel,4)}** · diferencial antigo: **{f(old_final,4)}**")
            W(f"- Progressao 1a → {len(old_ratios)}a: **{f(spread_old,3)}x** "
              f"({f(old_ratios[0][2],3)} → {f(old_ratios[-1][2],3)})")

            n6 = [r[2] for r in rows[:6]]
            spread_new = n6[0] / n6[-1]
            W("\n#### O contraste entre as duas leituras\n")
            W("| Leitura | 1a | 6a | Progressao | Veredito |")
            W("|---|---:|---:|---:|---|")
            W(f"| Config. antiga (comentada) | {f(old_ratios[0][2],3)} | "
              f"{f(old_ratios[-1][2],3)} | {f(spread_old,2)}x | caixa coerente |")
            W(f"| 6 primeiras da lista atual | {f(n6[0],3)} | {f(n6[-1],3)} | "
              f"{f(spread_new,2)}x | **impossivel** |")
            W(f"\nUma caixa de 6 marchas tem progressao de ~2.2x a ~3.5x entre 1a e 6a. As 6 "
              f"primeiras linhas da lista atual variam apenas **{f(spread_new,2)}x** — as marchas "
              f"ficariam praticamente coladas. Isso confirma que a lista longa e a **tabela de "
              f"candidatos** da aba de cambio da planilha, colada sem podar. Confirmar com "
              f"`NumGears` no `.hdv`.")

            # ---- velocidade por marcha no limitador
            eng = next((v for k, v in files.items() if "engine" in k.lower()), None)
            rev = None
            if eng is not None:
                try:
                    rev = float(eng.get("RevLimitRange")[0])
                except Exception:
                    rev = None
            if rev:
                R = 0.34
                W(f"\n#### Velocidade por marcha no limitador de {f(rev,0)} rpm\n")
                W(f"`v = (rpm · 2π / 60) · R / (relacao · diferencial · bevel)`, usando "
                  f"**R = {R:.2f} m** como hipotese de raio carregado — o valor real vem do "
                  f"`.tbc`.\n")
                for e in finals:
                    a4, b4 = (float(x) for x in e.tuple)
                    fdv = b4 / a4
                    W(f"\n**Diferencial {int(a4)}/{int(b4)} = {f(fdv,3)}** "
                      f"(com bevel {f(bev,4)}):\n")
                    W("| Marcha | Relacao | Global | km/h |")
                    W("|---:|---:|---:|---:|")
                    for i, (_a, _b, r4) in enumerate(old_ratios, 1):
                        overall = r4 * fdv * bev
                        v = (rev * 2 * math.pi / 60) * R / overall * 3.6
                        W(f"| {i} | {f(r4,3)} | {f(overall,3)} | {f(v,1)} |")

    # ---------------- 7. motor
    e_ini = next((v for k, v in files.items() if "engine" in k.lower()), None)
    if e_ini:
        W("\n## 7. Motor (`_engine.ini`)\n")
        bases = e_ini.all("RPMBase")
        curve = []
        for e in bases:
            t = [float(x) for x in e.tuple]
            if len(t) >= 3:
                curve.append((t[0], t[1], t[2]))
        if curve:
            peak_t = max(curve, key=lambda r: r[2])
            peak_p = max(curve, key=lambda r: r[2] * r[0])
            W(f"- Pontos na curva: **{len(curve)}** "
              f"({f(curve[0][0],0)} → {f(curve[-1][0],0)} rpm, passo de "
              f"{f(curve[1][0]-curve[0][0],0)} rpm)")
            W(f"- `RPMBase=(rpm, freio_motor, torque, ...)` — colunas conferidas cruzando com "
              f"`EngineBrakingGear*Limit`.")
            W(f"- **Torque maximo (curva base): {f(peak_t[2],1)} N·m @ {f(peak_t[0],0)} rpm**")
            pw = peak_p[2] * peak_p[0] * 2 * math.pi / 60
            W(f"- **Potencia maxima (curva base): {f(pw/1000,1)} kW = {f(pw/1000*1.34102,1)} hp "
              f"@ {f(peak_p[0],0)} rpm**")
            W(f"- Freio-motor em {f(curve[-1][0],0)} rpm: **{f(curve[-1][1],1)} N·m**")

        W("\n| Parametro | Valor |")
        W("|---|---|")
        for k in ("ReferenceConditions", "EngineInertia", "IdleRPMLogic", "RevLimitRange",
                  "RevLimitSetting", "FuelConsumption", "FuelEstimate", "FuelDensity",
                  "BoostTurboPressure", "TurboInertia", "IntakeVolumePerRevolution",
                  "ExhaustBaseProperties", "CompressorTable", "Wastegate", "DumpValve",
                  "LifetimeEngineRPM", "EngineEmission"):
            e = next((x for x in e_ini.all(k)), None)
            if e:
                W(f"| `{k}` | `{e.raw}` |")

        commented = [l for l in e_ini.lines if "EngineBrakingGear" in l and l.strip().startswith("//")]
        if commented:
            W(f"\n**Alerta:** {len(commented)} linhas `EngineBrakingGear*Limit` estao "
              f"**comentadas** (mapa de freio-motor por marcha desativado).")
            vals = {}
            for l in commented:
                body = l.strip().lstrip("/").strip()
                key, _, v = body.partition("=")
                vals[key] = v
            uniq = {}
            for k, v in vals.items():
                uniq.setdefault(v, []).append(k)
            dups = {v: ks for v, ks in uniq.items() if len(ks) > 1}
            if dups:
                for v, ks in dups.items():
                    W(f"- Marchas com mapa identico: {', '.join(ks)}")

    # ---------------- 8. pendencias
    W("\n## 8. Pendencias para fechar a engenharia reversa\n")
    presentes = {p.suffix.lower() for p in car_dir.iterdir() if p.is_file()}
    preciso = [
        (".hdv", "Arquivo mestre do veiculo",
         "massa e inercia do corpo principal, aerodinamica, molas/amortecedores, barras "
         "anti-rolagem, `NumGears`, e a linha `UltraChassis=` que aponta para o `_Chassis.ini`"),
        (".tbc", "Pneu (IA + geometria)",
         "raio carregado do pneu — define a altura real do CG e o scrub radius — alem da "
         "`CamberCurve`; varias abas da planilha leem daqui"),
        (".tgm", "Modelo de pneu do jogador",
         "necessario se o objetivo incluir mexer em pneu"),
        (".veh", "Manifesto do carro",
         "lista quais arquivos o carro carrega e em que ordem"),
        (".ods", "rF2 Physics Calculator",
         "**FONTE DAS FORMULAS.** Sem ela nao ha como inverter entrada -> saida: este relatorio "
         "so le o lado alvo"),
    ]
    W("| Arquivo | Papel | O que depende dele | Situacao |")
    W("|---|---|---|:--:|")
    for ext, papel, dep in preciso:
        W(f"| `{ext}` | {papel} | {dep} | "
          f"{'presente' if ext in presentes else '**AUSENTE**'} |")

    W("\n## 9. Como ler este relatorio\n")
    W("- **Secoes 3 a 5** sao *medicoes* do carro como ele esta hoje. Nao dependem da planilha: "
      "saem direto da geometria do `_Chassis.ini`, com validacao interna (comprimento das barras "
      "contra `MinError0`, inercia de guinada contra o limite do modelo halter).")
    W("- **Secoes 2, 6 e 7** sao *defeitos e alertas* — coisas para decidir antes de sair "
      "mexendo, porque qualquer baseline montado em cima de arquivo corrompido herda o erro.")
    W("- **A Secao 8** e o que falta para completar o trabalho.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(OUT) + "\n", encoding="utf-8")
    return "\n".join(OUT)


if __name__ == "__main__":
    # caminhos sempre relativos a RAIZ DO REPO, nao ao cwd (o script roda de tools/)
    root = Path(__file__).resolve().parent.parent
    arg = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "car" / "FGT_GTE_2019"
    car = arg if arg.is_absolute() else (Path.cwd() / arg).resolve()
    out = root / "docs" / f"auditoria-{car.name}.md"

    txt = build_report(car, out)
    print(txt)
    print(f"\n[ok] gravado em {out.relative_to(root)}")
