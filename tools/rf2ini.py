"""Parser minimo para os arquivos INI do rFactor 2 (.ini / .hdv / .tbc / .veh / .pm).

Os arquivos de parametros do rF2 *parecem* INI, mas tem particularidades que
quebram um parser de INI generico:

  - nao ha secao obrigatoria: engine.ini e uma lista plana de `Chave=Valor`;
  - chaves se repetem de proposito: `RPMBase=`, `TurbineFlowEffects=`,
    `CompressorPressRatio=` etc. sao LINHAS DE TABELA, nao overrides;
  - valores podem ser tuplas `Inertia=(a,b,c)`, strings `Name="FL_WHEEL"`
    ou escalares `Mass=557.3336`;
  - comentarios com `//` podem vir depois do valor e carregam informacao util
    (ex: `ratio=(12, 37) // 0: 3.083`);
  - quebras de linha sao CRLF.

Por isso este parser preserva a ORDEM e a MULTIPLICIDADE das chaves, em vez de
jogar tudo num dicionario (onde a ultima linha venceria e a tabela seria perdida).

Convecao de eixos do rF2 (documentada na aba Working da rF2 Physics Calculator):
    X -> lateral     (+esquerda / -direita)
    Y -> vertical    (+cima    / -baixo)
    Z -> longitudinal(+tras    / -frente)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

_SECTION_RE = re.compile(r"^\s*\[\s*(?P<name>[^\]]+?)\s*\]\s*$")


def _coerce(raw: str) -> Any:
    """Converte o lado direito de uma atribuicao no tipo mais provavel."""
    s = raw.strip()
    if not s:
        return ""

    # tupla: Inertia=(245.32,345.05,156.24) / LocalAxisA0=(1,0,0)
    if s.startswith("(") and s.endswith(")"):
        inner = s[1:-1].strip()
        if not inner:
            return ()
        parts = [p.strip() for p in inner.split(",")]
        out: list[Any] = []
        for p in parts:
            out.append(_scalar(p))
        return tuple(out)

    # string entre aspas: Name="FL_WHEEL"
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]

    return _scalar(s)


def _scalar(s: str) -> Any:
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


@dataclass
class Entry:
    """Uma linha `Chave=Valor` do arquivo."""

    key: str
    raw: str
    line: int
    comment: str = ""

    @property
    def value(self) -> Any:
        return _coerce(self.raw)

    @property
    def tuple(self) -> tuple[Any, ...]:
        v = self.value
        return v if isinstance(v, tuple) else (v,)

    def num(self, index: int | None = None) -> float:
        """Valor numerico: escalar, ou o item `index` de uma tupla."""
        v = self.value
        if isinstance(v, tuple):
            v = v[index or 0]
        return float(v)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<L{self.line} {self.key}={self.raw}>"


@dataclass
class Section:
    name: str
    line: int
    entries: list[Entry] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        e = self.first(key)
        return e.value if e is not None else default

    def first(self, key: str) -> Entry | None:
        for e in self.entries:
            if e.key.lower() == key.lower():
                return e
        return None

    def all(self, key: str) -> list[Entry]:
        return [e for e in self.entries if e.key.lower() == key.lower()]

    def __getitem__(self, key: str) -> Any:
        e = self.first(key)
        if e is None:
            raise KeyError(key)
        return e.value


class IniFile:
    """Arquivo INI do rF2 preservando ordem, secoes e chaves repetidas."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        blob = self.path.read_bytes()
        self.had_crlf = blob.count(b"\r\n") > 0
        text = blob.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
        self.lines = text.split("\n")
        self.sections: list[Section] = []
        self._parse()

    # -- parsing ---------------------------------------------------------
    def _parse(self) -> None:
        current = Section(name="", line=0)
        self.sections.append(current)
        for i, raw_line in enumerate(self.lines, start=1):
            m = _SECTION_RE.match(raw_line)
            if m:
                current = Section(name=m.group("name"), line=i)
                self.sections.append(current)
                continue

            # separa comentario preservando-o (util p/ ratio=(12, 37) // 0: 3.083)
            comment = ""
            body = raw_line
            if "//" in body:
                body, comment = body.split("//", 1)
                comment = comment.strip()
            body = body.strip()
            if not body or "=" not in body:
                continue
            key, _, value = body.partition("=")
            current.entries.append(
                Entry(key=key.strip(), raw=value.strip(), line=i, comment=comment)
            )

    # -- acesso ----------------------------------------------------------
    @property
    def entries(self) -> Iterator[Entry]:
        for s in self.sections:
            yield from s.entries

    def section(self, name: str) -> Section:
        for s in self.sections:
            if s.name.lower() == name.lower():
                return s
        raise KeyError(name)

    def section_list(self, name: str) -> list[Section]:
        """Secoes repetidas (ex: varios `[RigidBody]` / `[Constraint]`)."""
        return [s for s in self.sections if s.name.lower() == name.lower()]

    def get(self, key: str, default: Any = None) -> Any:
        for e in self.entries:
            if e.key.lower() == key.lower():
                return e.value
        return default

    def all(self, key: str) -> list[Entry]:
        return [e for e in self.entries if e.key.lower() == key.lower()]

    def key_sequence(self) -> list[str]:
        return [e.key for e in self.entries]

    def __repr__(self) -> str:  # pragma: no cover
        return f"<IniFile {self.path.name}: {len(self.sections)} secoes>"
