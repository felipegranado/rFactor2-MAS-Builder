# Ferramentas de analise de fisica (rFactor 2)

Engenharia reversa dos arquivos de fisica: le os `.ini` de um carro pronto e
deriva tudo que da para derivar **sem** a planilha (geometria, cinematica,
orcamento de massa, validacoes de consistencia).

## Uso

```bat
python tools\audit.py car\FGT_GTE_2019
```

Gera `docs\auditoria-<nome-do-carro>.md`. Os caminhos sao resolvidos a partir da
raiz do repositorio, entao tanto faz de onde voce chama.

## Arquivos

| Arquivo | Papel |
|---|---|
| `rf2ini.py` | Parser dos `.ini` do rF2. Preserva ordem e chaves repetidas (tabelas como `RPMBase=` se repetem de proposito — um parser de INI comum as perderia). |
| `audit.py` | Auditoria estrutural + derivacao de cinematica + geracao do relatorio. |

## Por que um parser proprio

Os `.ini` do rF2 nao sao INI de verdade:

- `engine.ini` nao tem secao nenhuma, e uma lista plana;
- `RPMBase=`, `TurbineFlowEffects=`, `CompressorPressRatio=` e companhia se
  repetem porque cada linha e uma **linha de tabela**, nao um override;
- comentarios depois do valor carregam informacao
  (`ratio=(12, 37) // 0: 3.083`).

Jogar isso num `dict` destruiria as tabelas. Por isso o parser devolve a lista
ordenada de entradas e permite consultar por nome quando se quer o escalar.

## Convencao de eixos do rF2

Diferente do que a maioria espera:

| Eixo | Direcao |
|---|---|
| X | lateral — **+esquerda** / -direita |
| Y | vertical — +cima / -baixo |
| Z | longitudinal — **+tras** / -frente |

Isso importa: no `AnisoOriJoint_0` do chassi flexivel, e o eixo **Z** que e
longitudinal, entao a rigidez a torcao (roll do chassi) e a `SpringRate2`.

## Validacoes internas

O relatorio nao confia na propria leitura — ele se autoverifica:

1. **Comprimento das barras:** cada `Bar_2` guarda o comprimento de repouso em
   `MinError0`. Recalcular a distancia entre os pontos e comparar valida todo o
   resto da cinematica. Erro tipico: < 0,2 mm (arredondamento da planilha).
2. **Inercia de guinada:** comparada com o limite superior do modelo halter
   (`m·a·b`, toda a massa concentrada nos eixos). Carro real fica entre ~85 % e
   ~100 % desse limite.
3. **Offset roda <-> manga:** tem que bater com o `LocalOffsetB` da junta
   esferica correspondente.
4. **Rotulas:** uma bandeja tem 2 barras convergindo no mesmo ponto. Pontos com
   1 membro sao tirantes (direcao / toe-link) e sao excluidos do eixo mestre.
