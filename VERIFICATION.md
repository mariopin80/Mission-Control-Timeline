# Registro de verificação — v0.9.0

Data: 24/07/2026

## Verificações automatizadas

O conjunto de 60 testes cobre:

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
- posicionamento do instante atual após 15 minutos de histórico;
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
- troca imediata para a fonte de contingência após erro da fonte principal;
- conversão da resposta TLE do SatNOGS para o cache OMM.
- seleção do AOS futuro mais próximo entre diferentes satélites;
- descarte de passagens já iniciadas ou encerradas na indicação de próximo AOS;
- emissão única do alerta de dois minutos;
- emissão de cinco eventos distintos na contagem regressiva final;
- bloqueio de bipes repetidos dentro do mesmo segundo;
- reinicialização segura dos alertas para a passagem seguinte;
- som habilitado por padrão e persistência da opção de silenciamento;
- recuperação segura para o padrão ativo quando a configuração é inválida.
- idioma inglês por padrão e persistência da seleção;
- recuperação segura para inglês quando o idioma salvo é inválido;
- aceitação de vírgulas, ponto e vírgula, espaços e linhas no editor NORAD;
- rejeição de duplicatas, nomes e entrada vazia no editor;
- migração preservativa do cache orbital legado para o AppData.
- presença de licença, termos de uso e aviso de privacidade nos seis idiomas;
- rótulos legais localizados em todos os idiomas da interface;
- geração do documento combinado apresentado pelo instalador.
- validação e criação de pasta personalizada gravável;
- cópia atômica dos dados para um novo local com preservação do original;
- inicialização de um novo local sem importar o cache anterior.

Resultado: **60/60 aprovados**.

Foi realizada uma verificação estática de compatibilidade com a gramática do
Python 3.10. A suíte da v0.9.0 foi executada em **Python 3.12.13**. A base
anterior também havia sido validada em **Python 3.10.20**, e as novas
construções permanecem compatíveis com a versão mínima. A dependência de
`datetime.UTC`, introduzida somente no Python 3.11, continua ausente.

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

O projeto foi empacotado com sucesso em um teste de fumaça `onedir` usando
PyInstaller 6.21. O arquivo `build_windows.bat` executa o fluxo equivalente em
Windows, incorpora os metadados de versão e, quando o Inno Setup 6 está
disponível, gera também o instalador por usuário.
