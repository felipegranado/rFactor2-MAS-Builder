# Auditoria de fisica — `FGT_GTE_2019`

> Gerado por `tools/audit.py`. Nenhum numero aqui foi digitado a mao: tudo e lido ou derivado dos arquivos `.ini`.


## 1. Inventario

| Arquivo | Bytes | Linhas | CRLF | Secoes |
|---|---:|---:|:--:|---:|
| `FGT_GTE_2019_Chassis.ini` | 14375 | 773 | sim | 42 |
| `FGT_GTE_2019_damage.ini` | 11828 | 160 | sim | 2 |
| `FGT_GTE_2019_engine.ini` | 17060 | 359 | sim | 0 |
| `FGT_GTE_2019_gears.ini` | 2387 | 96 | sim | 2 |

- Pneu: `GY30-68-18x12.5_31-71-18x13_2022.tbc` — 15654 bytes, **4 compostos** (Soft, Medium, Hard, P2M (Rain)).

## 2. Defeitos de estrutura


### 2.1 `FGT_GTE_2019_engine.ini`: bloco de 77 parametros repetido

- Bloco A: linhas **206–282** · Bloco B: linhas **283–359**

| Chaves que ACUMULAM linha (tabela) | Chaves escalares (ultima vence) |
|---|---|
| `TurbineFlowEffects`, `CompressorPressRatio`, `CompressorEfficiency`, `CompressorSurgeLineFlow` | `TurboInertia`, `TurboFriction`, `TurboStaticFrictionWatts`, `TurbineFlowTable`, `IntakeVolumePerRevolution`, `ExhaustBaseProperties`, `CompressorTable`, `BoostTurboPressure`, `WastegateBoostMeasurement`, `Wastegate`, `IntakeLeak`, `DumpValve` |

**Impacto: real.** As escalares sao apenas sobrescritas pelo ultimo valor (inofensivo), mas as de tabela sao *acumuladas*: o rF2 le o bloco como o dobro de linhas. **A curva fica corrompida.**

**Correcao:** remover o bloco B (linhas 283–359) e manter apenas o A.

## 3. Orcamento de massa (`_Chassis.ini`)

| Corpo | Massa (kg) | Inercia (Ixx, Iyy, Izz) | Posicao (x, y, z) |
|---|---:|---|---|
| `Front_Subbody` | 557.3336 | (245.3225, 345.0480, 156.2392) | (0.0000, 0.0000, -1.1395) |
| `Rear_Subbody` | 629.4216 | (277.0536, 389.6781, 176.4479) | (0.0000, 0.0000, 1.0105) |
| `FL_SPINDLE` | 7.9221 | (0.0290, 0.0283, 0.0396) | (0.7871, 0.2676, -1.4363) |
| `FR_SPINDLE` | 7.9221 | (0.0290, 0.0283, 0.0396) | (-0.7871, 0.2676, -1.4363) |
| `RL_SPINDLE` | 9.1144 | (0.0369, 0.0265, 0.0462) | (0.8050, 0.2721, 1.2737) |
| `RR_SPINDLE` | 9.1144 | (0.0369, 0.0265, 0.0462) | (-0.8050, 0.2721, 1.2737) |
| `FL_WHEEL` | 27.7411 | (1.1625, 0.7819, 0.7819) | (0.8321, 0.2676, -1.4363) |
| `FR_WHEEL` | 27.7411 | (1.1625, 0.7819, 0.7819) | (-0.8321, 0.2676, -1.4363) |
| `RL_WHEEL` | 30.6448 | (1.3227, 0.9069, 0.9069) | (0.8400, 0.2721, 1.2737) |
| `RR_WHEEL` | 30.6448 | (1.3227, 0.9069, 0.9069) | (-0.8400, 0.2721, 1.2737) |
| `FUEL_TANK` | 0.4000 | (0.0049, 0.0212, 0.0163) | (0.0000, 0.0000, 0.0000) |
| `DRIVER_HEAD` | 6.5900 | (0.0451, 0.0360, 0.0390) | (0.0000, 0.0000, 0.0000) |
| **TOTAL** | **1344.5900** | | |

- Massa total (sem combustivel, tanque vazio): **1344.5900 kg**
- Centro de gravidade: **(0.0000, 0.0303, -0.0002)** m  (na origem do sub-body)
- Tensor de inercia sobre o CG (diagonal, modelo simetrico): **(2179.821, 2484.092, 449.343)** kg·m²
- **Checagem de sanidade:** inercia de guinada Iyy = 2484.1 kg·m² contra o limite superior do modelo halter (massa toda nos eixos) m·a·b = 2459.8 kg·m² → **101.0 %**. Carros reais ficam entre ~85 % e ~100 % desse limite → **consistente**.

- Entre-eixos: **2.7100 m** (roda diant. z=-1.4363, traseira z=1.2737)
- Distribuicao de peso estatica: **47.01 % dianteira** / 52.99 % traseira
- Bitola dianteira: **1.6642 m** · traseira: **1.6800 m**
- Altura do centro da roda diant.: **0.2676 m** · traseira: **0.2721 m** (relativo a origem do sub-body)

## 4. Validacao geometrica das barras

Cada `Bar_2` guarda o comprimento de repouso em `MinError0`. Comparando com a distancia calculada entre os pontos (`Position` + `LocalOffsetA` / `LocalOffsetB`) confere que a leitura das coordenadas esta certa.

| Barra | Ponta | Calculado (m) | `MinError0` (m) | Erro (mm) |
|---|---|---:|---:|---:|
| `FL_FORE_LOWER` | `FL_SPINDLE` | 0.492682 | 0.492660 | +0.022 |
| `FL_REAR_LOWER` | `FL_SPINDLE` | 0.535903 | 0.535998 | -0.095 |
| `FL_FORE_UPPER` | `FL_SPINDLE` | 0.394415 | 0.394292 | +0.123 |
| `FL_REAR_UPPER` | `FL_SPINDLE` | 0.414407 | 0.414465 | -0.058 |
| `FL_STEERING` | `FL_SPINDLE` | 0.417197 | 0.417251 | -0.054 |
| `FR_FORE_LOWER` | `FR_SPINDLE` | 0.492682 | 0.492660 | +0.022 |
| `FR_REAR_LOWER` | `FR_SPINDLE` | 0.535903 | 0.535998 | -0.095 |
| `FR_FORE_UPPER` | `FR_SPINDLE` | 0.394415 | 0.394292 | +0.123 |
| `FR_REAR_UPPER` | `FR_SPINDLE` | 0.414407 | 0.414465 | -0.058 |
| `FR_STEERING` | `FR_SPINDLE` | 0.417197 | 0.417251 | -0.054 |
| `RL_FORE_LOWER` | `RL_SPINDLE` | 0.612976 | 0.613020 | -0.044 |
| `RL_REAR_LOWER` | `RL_SPINDLE` | 0.551162 | 0.551143 | +0.019 |
| `RL_FORE_UPPER` | `RL_SPINDLE` | 0.481752 | 0.481829 | -0.077 |
| `RL_REAR_UPPER` | `RL_SPINDLE` | 0.400136 | 0.400100 | +0.036 |
| `RL_TOELINK` | `RL_SPINDLE` | 0.469133 | 0.469214 | -0.081 |
| `RR_FORE_LOWER` | `RR_SPINDLE` | 0.612976 | 0.613020 | -0.044 |
| `RR_REAR_LOWER` | `RR_SPINDLE` | 0.551162 | 0.551143 | +0.019 |
| `RR_FORE_UPPER` | `RR_SPINDLE` | 0.481752 | 0.481829 | -0.077 |
| `RR_REAR_UPPER` | `RR_SPINDLE` | 0.400136 | 0.400100 | +0.036 |
| `RR_TOELINK` | `RR_SPINDLE` | 0.469133 | 0.469214 | -0.081 |

**Erro maximo: 0.123 mm** — dentro do arredondamento da planilha (ela grava ~6 digitos significativos). Leitura das coordenadas validada: todo o resto da cinematica deriva dai.

## 5. Cinematica da suspensao (derivada)

As duas pernas de cada bandeja convergem para o mesmo ponto na manga de eixo; esse ponto e a rotula equivalente. O eixo mestre (kingpin) e a reta que liga a rotula inferior a superior.


### FL — eixo F

| Ponto | Y (m) | Membros | `LocalOffsetB` | Mundo (x, y, z) |
|---|---:|:--:|---|---|
| **rotula inferior** | 0.1444 | 2 | (-0.046111, -0.123200, -0.004797) | (0.7410, 0.1444, -1.4411) |
| **rotula superior** | 0.3594 | 2 | (-0.076052, 0.091800, 0.021670) | (0.7110, 0.3594, -1.4146) |
| tirante (ignorado) | 0.3594 | 1 | (-0.074211, 0.091800, -0.049734) | (0.7129, 0.3594, -1.4860) |

O eixo mestre usa so os pontos com **2 membros** (as bandejas). O tirante tem 1 membro e foi excluido: ele tem a mesma altura da rotula superior, e inclui-lo giraria o eixo mestre para a direcao errada.

- **KPI (inclinacao do eixo mestre): 7.93°**
- **Caster: 7.02°** (positivo — topo do eixo mestre para tras)

Com o raio do `.tbc` (**0.33875 m**):
- **Scrub radius: 61.1 mm** — o eixo mestre cruza o solo **para dentro** do centro do pneu
- **Trail mecanico: 31.3 mm** — cruza **a frente** do centro do pneu (com caster positivo o esperado e 'a frente')

Sensibilidade (caso o raio carregado real diverga do `.tbc`):

| Raio carregado (m) | Lateral: scrub (mm) | Longitudinal: trail (mm) |
|---:|---:|---:|
| 0.30 | -66.5 | -26.6 |
| 0.32 | -63.7 | -29.0 |
| 0.34 | -60.9 | -31.5 |
| 0.36 | -58.1 | -33.9 |

Convecao de sinais (roda esquerda; X positivo = para fora, Z positivo = para tras):
- **Lateral negativo** = o eixo mestre cruza o solo **para dentro** do centro do pneu, em direcao a linha de centro do carro.
- **Longitudinal negativo** = cruza **a frente** do centro do pneu, o que corresponde a trail mecanico positivo.

- Referencia: centro da roda em x=0.8321, y=0.2676, z=-1.4363
- Offset roda↔manga: **45.0 mm** (deve bater com `LocalOffsetB` do `*_BJ`)

### RL — eixo R

| Ponto | Y (m) | Membros | `LocalOffsetB` | Mundo (x, y, z) |
|---|---:|:--:|---|---|
| **rotula inferior** | 0.1305 | 2 | (-0.074400, -0.141600, -0.000094) | (0.7306, 0.1305, 1.2736) |
| tirante (ignorado) | 0.2665 | 1 | (-0.093924, -0.005590, 0.109890) | (0.7111, 0.2665, 1.3836) |
| **rotula superior** | 0.4125 | 2 | (-0.114700, 0.140400, -0.000128) | (0.6903, 0.4125, 1.2736) |

O eixo mestre usa so os pontos com **2 membros** (as bandejas). O tirante tem 1 membro e foi excluido: ele tem a mesma altura da rotula superior, e inclui-lo giraria o eixo mestre para a direcao errada.

- **KPI (inclinacao do eixo mestre): 8.13°**
- **Caster: -0.01° — praticamente zero** (esperado: eixo traseiro nao tem caster)

Com o raio do `.tbc` (**0.35527 m**):
- **Scrub radius: 78.9 mm** — o eixo mestre cruza o solo **para dentro** do centro do pneu
- **Trail mecanico: 0.1 mm** — cruza **a frente** do centro do pneu (com caster positivo o esperado e 'a frente')

Sensibilidade (caso o raio carregado real diverga do `.tbc`):

| Raio carregado (m) | Lateral: scrub (mm) | Longitudinal: trail (mm) |
|---:|---:|---:|
| 0.30 | -86.8 | -0.1 |
| 0.32 | -83.9 | -0.1 |
| 0.34 | -81.0 | -0.1 |
| 0.36 | -78.2 | -0.1 |

Convecao de sinais (roda esquerda; X positivo = para fora, Z positivo = para tras):
- **Lateral negativo** = o eixo mestre cruza o solo **para dentro** do centro do pneu, em direcao a linha de centro do carro.
- **Longitudinal negativo** = cruza **a frente** do centro do pneu, o que corresponde a trail mecanico positivo.

- Referencia: centro da roda em x=0.8400, y=0.2721, z=1.2737
- Offset roda↔manga: **35.0 mm** (deve bater com `LocalOffsetB` do `*_BJ`)

### Chassi flexivel (`AnisoOriJoint_0`)

- `Chassis_OJ`: `Front_Subbody` ↔ `Rear_Subbody`

| Eixo (rF2) | Rotacao | Eixo local | `SpringRate` (Nm/rad) | `DamperRate` | Nm/grau |
|---|---|---|---:|---:|---:|
| X = lateral | arfagem (pitch) | (1, 0, 0) | 5.200e+07 | 1.020e+05 | 907,571 |
| Y = vertical | guinada (yaw) | (0, 1, 0) | 6.500e+07 | 1.080e+05 | 1,134,464 |
| Z = longitudinal | torcao (roll do chassi) | (0, 0, 1) | 4.700e+06 | 2.850e+04 | 82,030 |

- **Cuidado com a convencao de eixos:** em rF2 Z e o longitudinal, entao a rigidez a **torcao do chassi (roll)** e `SpringRate2` — nao `SpringRate0`.

## 6. Cambio (`_gears.ini`)

- Entradas `ratio=` em `[GEAR_RATIOS]`: **67**
- Faixa: **3.083** (12/37) → **0.857** (28/24)
- Convencao confirmada pelos comentarios do proprio arquivo: **relacao = segundo/primeiro** (ex: `(12,37)` → 37/12 = 3.083). Divergencias encontradas: **0**

- `bevel=(28,27)` → **0.9643**
- final `ratio=(10,38)` → **3.8000**
- final `ratio=(10,31)` → **3.1000**

#### Configuracao anterior (preservada comentada no cabecalho)

| Marcha | Dentes | Relacao |
|---:|---|---:|
| 1 | (15, 31) | 2.0667 |
| 2 | (17, 28) | 1.6471 |
| 3 | (18, 25) | 1.3889 |
| 4 | (20, 24) | 1.2000 |
| 5 | (20, 21) | 1.0500 |
| 6 | (26, 24) | 0.9231 |

- `Bevel` antigo: **0.9643** · diferencial antigo: **3.8000**
- Progressao 1a → 6a: **2.239x** (2.067 → 0.923)

#### O contraste entre as duas leituras

| Leitura | 1a | 6a | Progressao | Veredito |
|---|---:|---:|---:|---|
| Config. antiga (comentada) | 2.067 | 0.923 | 2.24x | caixa coerente |
| 6 primeiras da lista atual | 3.083 | 2.500 | 1.23x | **impossivel** |

Uma caixa de 6 marchas tem progressao de ~2.2x a ~3.5x entre 1a e 6a. As 6 primeiras linhas da lista atual variam apenas **1.23x** — as marchas ficariam praticamente coladas. Isso confirma que a lista longa e a **tabela de candidatos** da aba de cambio da planilha, colada sem podar. Confirmar com `NumGears` no `.hdv`.

#### Velocidade por marcha no limitador de 7500 rpm

`v = (rpm · 2π / 60) · R / (relacao · diferencial · bevel)`, com **R = 0.35527 m** = raio traseiro do `.tbc` (eixo motriz).


**Diferencial 10/38 = 3.800** (com bevel 0.9643):

| Marcha | Relacao | Global | km/h |
|---:|---:|---:|---:|
| 1 | 2.067 | 7.573 | 132.6 |
| 2 | 1.647 | 6.035 | 166.4 |
| 3 | 1.389 | 5.089 | 197.4 |
| 4 | 1.200 | 4.397 | 228.4 |
| 5 | 1.050 | 3.847 | 261.1 |
| 6 | 0.923 | 3.382 | 297.0 |

**Diferencial 10/31 = 3.100** (com bevel 0.9643):

| Marcha | Relacao | Global | km/h |
|---:|---:|---:|---:|
| 1 | 2.067 | 6.178 | 162.6 |
| 2 | 1.647 | 4.924 | 204.0 |
| 3 | 1.389 | 4.152 | 241.9 |
| 4 | 1.200 | 3.587 | 280.0 |
| 5 | 1.050 | 3.139 | 320.0 |
| 6 | 0.923 | 2.759 | 364.0 |

## 7. Motor (`_engine.ini`)

- Pontos na curva: **43** (0 → 10500 rpm, passo de 250 rpm)
- `RPMBase=(rpm, freio_motor, torque, ...)` — colunas conferidas cruzando com `EngineBrakingGear*Limit`.
- **Torque maximo (curva base): 535.0 N·m @ 5500 rpm**
- **Potencia maxima (curva base): 312.6 kW = 419.2 hp @ 7250 rpm**
- Freio-motor em 10500 rpm: **-220.0 N·m**

| Parametro | Valor |
|---|---|
| `ReferenceConditions` | `(101325,1.225,0.0773036487322202)` |
| `EngineInertia` | `0.08` |
| `IdleRPMLogic` | `(1491,1890)` |
| `RevLimitRange` | `(7500,0,1)` |
| `RevLimitSetting` | `0` |
| `FuelConsumption` | `5.2e-5` |
| `FuelEstimate` | `0.8` |
| `FuelDensity` | `0.73` |
| `BoostTurboPressure` | `(128000,400)` |
| `TurboInertia` | `1.15e-4` |
| `IntakeVolumePerRevolution` | `0.9991` |
| `ExhaustBaseProperties` | `(1175,1180,0.187,0.222,-0.0000335)` |
| `CompressorTable` | `(16000,0.02)` |
| `Wastegate` | `(-1500,0,1500,1)` |
| `DumpValve` | `(200000,140000,0.000001)` |
| `LifetimeEngineRPM` | `(7500,200)` |
| `EngineEmission` | `(0,0.42,9999)` |

**Alerta:** 7 linhas `EngineBrakingGear*Limit` estao **comentadas** (mapa de freio-motor por marcha desativado).
- Marchas com mapa identico: EngineBrakingGear0Limit, EngineBrakingGear6Limit

## 8. Pneus (`_tbc`)

Arquivo: `GY30-68-18x12.5_31-71-18x13_2022.tbc`

| Eixo | `Radius` (m) | `Width` (m) | `Rim` (m) | `SpringBase` | `SpringkPa` | `Damper` |
|---|---:|---:|---:|---:|---:|---:|
| Dianteiro | 0.33875 | 0.3 | 0.2485 | 148501.1 | 731.13 | 750 |
| Traseiro | 0.35527 | 0.318 | 0.2485 | 170000 | 765 | 771 |

### Grip por composto

| Composto | Eixo | `DryLatLong` | `LatPeak` | `LongPeak` | `Temperatures` |
|---|---|---|---|---|---|
| Soft | D | (1.9536162,1.9248216) | ( 0.112, 0.152, 11000) | (0.116, 0.128, 10600) | (94, 30) |
| Soft | T | (1.99978,1.9703) | ( 0.11, 0.15, 12000) | (0.115, 0.127, 10700) | (94, 30) |
| Medium | D | (1.93236,1.90388) | ( 0.112, 0.152, 11000) | (0.116, 0.128, 10600) | (97, 30) |
| Medium | T | (1.978035,1.9488834) | ( 0.135, 0.165, 12000) | (0.118, 0.131, 12000) | (97, 30) |
| Hard | D | (1.90944,1.8813) | ( 0.112, 0.152, 11000) | (0.116, 0.128, 10600) | (100, 30) |
| Hard | T | (1.954575,1.92576) | ( 0.11, 0.15, 12000) | (0.115, 0.127, 10700) | (100, 30) |
| P2M (Rain) | D | (1.8722202,1.844619) | ( 0.116, 0.158, 11000) | (0.119, 0.131, 10600) | (68, 21) |
| P2M (Rain) | T | (1.89035,1.86248) | ( 0.114, 0.156, 12000) | (0.118, 0.13, 10700) | (68, 21) |

Comparando apenas os slicks (Soft, Medium, Hard): o composto de chuva difere por design e foi excluido dessa checagem.


**Dianteiro: parametro fora do padrao entre os slicks**

| Parametro | Composto divergente | Valor | Demais slicks |
|---|---|---|---|
| `Transfer` | **Soft** | `(0.05, 1.92e-3, 3.1e-4)` | `(0.04, 1.92e-3, 2.9e-4)` (Medium, Hard) |

**Traseiro: parametro fora do padrao entre os slicks**

| Parametro | Composto divergente | Valor | Demais slicks |
|---|---|---|---|
| `HeatDistrib` | **Soft** | `(12.5,115)` | `(12.5,111)` (Medium, Hard) |
| `Heating` | **Soft** | `(0.5, 0.016)` | `(0.59, 0.016)` (Medium, Hard) |
| `LatPeak` | **Medium** | `( 0.135, 0.165, 12000)` | `( 0.11, 0.15, 12000)` (Soft, Hard) |
| `LongPeak` | **Medium** | `(0.118, 0.131, 12000)` | `(0.115, 0.127, 10700)` (Soft, Hard) |
| `PneumaticTrail` | **Soft** | `2.1e-6` | `2.0e-6` (Medium, Hard) |
| `Transfer` | **Soft** | `(0.054, 1.92e-3, 3.0e-4)` | `(0.042, 1.92e-3, 2.7e-4)` (Medium, Hard) |

## 9. Pendencias para fechar a engenharia reversa

| Arquivo | Papel | O que depende dele | Situacao |
|---|---|---|:--:|
| `.hdv` | Arquivo mestre do veiculo | massa e inercia do corpo principal, aerodinamica, molas/amortecedores, barras anti-rolagem, `NumGears`, e a linha `UltraChassis=` que aponta para o `_Chassis.ini` | **AUSENTE** |
| `.tbc` | Pneu (IA + geometria) | raio carregado do pneu — define a altura real do CG e o scrub radius — alem da `CamberCurve`; varias abas da planilha leem daqui | presente |
| `.tgm` | Modelo de pneu do jogador | necessario se o objetivo incluir mexer em pneu | **AUSENTE** |
| `.veh` | Manifesto do carro | lista quais arquivos o carro carrega e em que ordem | **AUSENTE** |
| `.ods` | rF2 Physics Calculator | **FONTE DAS FORMULAS.** Sem ela nao ha como inverter entrada -> saida: este relatorio so le o lado alvo | **AUSENTE** |

## 10. Como ler este relatorio

- **Secoes 3 a 5** sao *medicoes* do carro como ele esta hoje. Nao dependem da planilha: saem direto da geometria do `_Chassis.ini`, com validacao interna (comprimento das barras contra `MinError0`, inercia de guinada contra o limite do modelo halter).
- **Secoes 2, 6, 7 e 8** sao *defeitos e alertas* — coisas para decidir antes de sair mexendo, porque qualquer baseline montado em cima de arquivo corrompido herda o erro.
- **A Secao 9** e o que falta para completar o trabalho.
