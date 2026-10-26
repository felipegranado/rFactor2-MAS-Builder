# Coloque aqui a rF2 Physics Calculator

Preciso do arquivo `.ods` da **rF2 Physics Calculator** para completar a
engenharia reversa. Ele e a **fonte das formulas** — e o unico jeito de inverter
o calculo (dos arquivos `.ini` de volta para as celulas de entrada) com
fidelidade, em vez de chutar valores.

Até agora tudo o que foi feito leu apenas o **lado alvo** (os arquivos do carro).
Sem a planilha nao existe a cadeia `entrada -> saida` para inverter.

## Como enviar (mais facil)

Pela interface web do GitHub, sem precisar de git:

1. Acesse
   <https://github.com/felipegranado/rFactor2-MAS-Builder/tree/arena/69ef92ff-rfactor2-mas-builder/planilha>
2. Clique em **Add file** → **Upload files**
3. Arraste o `.ods` para a pagina
4. Deixe marcado *"Commit directly to the
   `arena/69ef92ff-rfactor2-mas-builder` branch"*
5. Clique em **Commit changes**
6. Me avise aqui que subiu

Limite do GitHub: 25 MB por arquivo — a planilha tem bem menos que isso.

## Alternativa: Gist

Se preferir, crie um Gist **publico** em <https://gist.github.com> com o `.ods`
dentro e me passe a URL. Gists sao repositorios git, entao eu consigo clonar.

## Se o problema foi o tamanho no chat

Teste tambem renomear para `.txt` e anexar — o `.ods` e um ZIP, e eu descompacto
e leio o `content.xml` de dentro dele do mesmo jeito. Mas o caminho do GitHub e
mais confiavel.

## O que eu faco com o arquivo

O `.ods` e um ZIP de XML. Eu descompacto e leio o `content.xml`, que guarda
todas as formulas. A partir dai:

1. mapeio quais celulas sao **entradas** (as de borda branca) e quais sao as
   abas de **exportacao** (as laranjas);
2. reconstruo a cadeia de calculo e ligo cada saida a linha correspondente do
   `.hdv` / `_Chassis.ini` / `engine.ini`;
3. resolvo o problema ao contrario, por otimizacao numerica: acho o conjunto de
   entradas que reproduz os seus arquivos;
4. devolvo a planilha preenchida, o relatorio de residuos (onde bate exato e onde
   ha folga) e a tabela de sensibilidade.

Nada de LiberOffice e necessario para isso.
