# Registro de verificação — v0.5.0

Data: 17/07/2026

## Verificações automatizadas

O conjunto de trinta e nove testes cobre:

- TLE nominal com duas linhas;
- TLE nominal com nome e três linhas;
- números de catálogo NORAD Alpha-5;
- rejeição de linhas pertencentes a catálogos diferentes;
- rejeição de catálogos duplicados;
- preenchimento seguro de configurações parciais;
- sanidade física da observação topocêntrica;
- convergência de AOS e LOS para a máscara de elevação;
- persistência da janela selecionada sem perda dos dados da estação;
- rejeição e recuperação segura de escalas inválidas;
- espaçamento adaptativo da grade para as cinco janelas;
- alinhamento das marcações com o relógio local;
- exigência de instantes com fuso horário na linha do tempo;
- posicionamento do instante atual após 30 minutos de histórico;
- preservação da duração total selecionada;
- formatação e limite inferior da contagem regressiva para LOS;
- posicionamento do cartão à direita da passagem quando há espaço;
- reposicionamento automático à esquerda junto à borda da tela;
- contenção integral do cartão na janela compacta do aplicativo.
- contador para AOS antes da passagem;
- contador para LOS durante a passagem;
- tempo decorrido desde LOS após a passagem;
- rejeição de instante sem fuso horário no contador.
- leitura de lista com um número NORAD por linha;
- suporte a catálogos acima de cinco dígitos;
- rejeição de nomes, linhas TLE e catálogos repetidos na nova lista;
- validação de resposta OMM/JSON do CelesTrak;
- rejeição de resposta referente a outro catálogo;
- reconstrução de satélites na ordem solicitada a partir do cache;
- separação física entre lista NORAD e cache orbital;
- propagação SGP4 inicializada por OMM.
- reutilização de cache recente sem download duplicado;
- download apenas dos catálogos ausentes em cache recente;
- atualização completa quando o cache ultrapassa o intervalo mínimo.
- interrupção imediata das consultas após erro da fonte remota.

Resultado: **39/39 aprovados**.

Foi realizada uma verificação estática de compatibilidade com a gramática do
Python 3.10 e, adicionalmente, toda a suíte foi executada em **Python 3.10.20**.
O módulo principal foi importado e o pacote PyInstaller foi gerado com sucesso
nesse mesmo interpretador. A dependência de `datetime.UTC`, introduzida somente
no Python 3.11, foi removida.

## Comparação orbital independente

O propagador e a transformação topocêntrica foram comparados com Skyfield 1.54
em 193 amostras e 14 passagens do caso de teste Vanguard 1/SJC.

| Grandeza | Maior diferença observada |
| --- | ---: |
| Elevação | 0,004687° |
| Azimute | 0,004762° |
| Distância | 0,087 km |
| AOS/LOS | 0,132 s |

As diferenças são compatíveis com as simplificações de TEME–ECEF documentadas
e são pequenas para a finalidade de planejamento de passagens.

## Empacotamento

O projeto foi empacotado com sucesso em ambiente limpo usando PyInstaller 6.21.
O arquivo `build_windows.bat` executa o mesmo fluxo em Windows e produz o
executável independente da plataforma.
