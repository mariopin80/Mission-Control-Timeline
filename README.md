# Mission Control — Satellite Pass Timeline

Aplicativo desktop para Windows que calcula e exibe, em uma linha do tempo
móvel configurável, os períodos em que os satélites de uma lista de números
NORAD estão acima da máscara de elevação de uma estação terrena.

## Versão 0.6.0

- janela móvel selecionável de 3, 6, 8, 12 ou 24 horas;
- marcador vermelho do horário atual após apenas 30 minutos de histórico;
- cabeçalho simplificado com a data local e a próxima passagem entre todos os
  satélites, mostrando nome e contagem regressiva para AOS;
- busca da próxima passagem em um horizonte de 24 horas, independentemente da
  escala selecionada na linha do tempo;
- alerta sonoro único quando faltam dois minutos para AOS;
- contagem regressiva sonora com um bip por segundo nos cinco segundos finais;
- botão persistente para ativar ou silenciar os alertas;
- grade adaptativa de 15 minutos a 3 horas conforme a escala escolhida;
- importação de TXT com um número de catálogo NORAD por linha;
- atualização automática de dados orbitais pelo CelesTrak ao iniciar e a cada 24 h;
- cache OMM/JSON separado ao lado do executável para operação sem internet;
- propagação orbital SGP4;
- cálculo de AOS, LOS, máxima elevação, azimutes e distância;
- estação e máscara de elevação configuráveis;
- atualização contínua da janela e recálculo orbital periódico em segundo plano;
- dados ao vivo na própria linha do satélite em visada, imediatamente após a
  barra da passagem, com elevação, azimute e contagem regressiva para o LOS;
- altura mínima reduzida para uso compacto com poucos satélites;
- cartão flutuante com AOS, máxima elevação, LOS, azimutes e distância ao
  clicar em uma passagem;
- fechamento automático do cartão ao clicar fora de uma passagem;
- aviso visual de dados orbitais antigos;
- detalhes da passagem ao clicar em uma faixa.

### Alterações da versão 0.6.0

- remoção das informações redundantes “janela móvel” e “30 min de histórico” do
  cabeçalho;
- data local mantida na linha superior;
- identificação automática do AOS futuro mais próximo entre todos os satélites;
- proteção contra repetição dos alertas durante redesenhos e recálculos;
- frequências distintas para o aviso de dois minutos e a contagem final;
- botão **Som ativo/Som mudo**, com a preferência preservada entre execuções.

### Correções da versão 0.5.1

- SatNOGS usado automaticamente como contingência quando o CelesTrak falha;
- TLE obtido do SatNOGS convertido para o mesmo cache interno OMM;
- após uma falha do CelesTrak, os demais catálogos da rodada usam diretamente
  a contingência, sem insistir no servidor indisponível;
- mensagem de erro agora apresenta a causa técnica real em vez de afirmar
  genericamente que não há internet;
- identificação da fonte efetivamente usada na barra de estado.

### Alterações da versão 0.4.2

- contador contextual no cartão: `AOS EM`, `LOS EM` ou `LOS HÁ`;
- atualização do contador do cartão a cada segundo;
- remoção da faixa superior “Em visada”;
- elevação, azimute e tempo para LOS exibidos na própria linha do satélite,
  ao lado direito da barra da passagem ativa.

### Alterações da versão 0.5.0

- a lista de entrada contém somente números NORAD;
- dados orbitais obtidos em OMM/JSON, compatíveis com catálogos acima de 99999;
- atualização no início do programa, manual pelo botão **Atualizar** e automática
  após 24 horas de execução;
- cache com menos de duas horas é reutilizado no início para respeitar a política
  de uso do CelesTrak e evitar consultas duplicadas;
- download executado em segundo plano, sem bloquear a interface;
- `orbital_cache.json` gravado atomicamente na pasta do programa;
- uso automático do último cache válido quando a internet está indisponível;
- atualização parcial preserva os registros antigos dos catálogos que falharam.
- erros HTTP ou indisponibilidade do CelesTrak interrompem imediatamente a rodada,
  preservando o cache e evitando novas solicitações ao serviço.

## Executar pelo código-fonte no Windows

1. Instale Python 3.10 ou mais recente marcando a opção **Add Python to PATH**.
2. Dê duplo clique em `run_windows.bat`.
3. No programa, use **Lista NORAD** e escolha um arquivo `.txt`.
4. Abra **Estação** e informe as coordenadas reais da estação.

Na primeira execução, o script cria um ambiente virtual e instala somente a
biblioteca orbital necessária.

## Gerar o executável

Em um computador Windows, dê duplo clique em `build_windows.bat`. O executável
independente será criado em:

```text
dist\MissionPassTimeline.exe
```

O computador em que o `.exe` for executado não precisará ter Python instalado.

## Formato da lista NORAD

Informe um número de catálogo por linha. Linhas vazias e comentários iniciados
por `#` ou `;` são ignorados.

```text
25544
43786
27607
# comentários são permitidos
```

O arquivo `orbital_cache.json` é independente da lista e fica ao lado do
executável. Não o edite manualmente. Depois da primeira atualização bem-sucedida,
o programa pode iniciar e calcular passagens sem conexão com a internet.
O projeto inclui `example_satellites.txt` como modelo editável.

## Observações de engenharia

- A fonte automática padrão é o serviço GP do CelesTrak, com SatNOGS como
  contingência para catálogos disponíveis em TLE.
- Na primeira execução de uma lista nova, a internet é necessária para obter os
  dados que ainda não existirem no cache.
- A máscara padrão é 10°, mas deve refletir obstruções, horizonte e desempenho
  real da estação.
- A conversão TEME–ECEF usa GMST e WGS-84, adequada ao planejamento de
  passagens. Correções de polar motion e UT1 não são aplicadas nesta versão.
- A estação inicial SJC é provisória e deve ser substituída pelas coordenadas
  reais do local de operação.

### Correção da versão 0.4.1

- o cartão deixou de ser uma janela independente do sistema operacional;
- agora ele é um componente interno, limitado à área útil do aplicativo;
- mesmo na altura mínima, nenhuma parte do cartão ultrapassa a janela.

### Alterações da versão 0.4.0

- remoção completa do rodapé de informações;
- detalhes da passagem exibidos em um cartão ao lado da barra clicada;
- o cartão muda para o lado esquerdo quando não há espaço na tela;
- clique no fundo, cabeçalho ou controles fecha o cartão;
- altura mínima reduzida novamente para 260 px.

### Alterações da versão 0.3.0

- somente 30 minutos da linha do tempo ficam no passado;
- o restante da janela selecionada mostra contatos futuros;
- painel condicional “Em visada”, atualizado a cada segundo;
- suporte à exibição simultânea de vários satélites em visada;
- janela redimensionável verticalmente até 300 px.

### Alterações da versão 0.2.0

- substituição do dia civil fixo por uma janela móvel centrada no instante atual;
- seletor persistente de 3 h, 6 h, 8 h, 12 h e 24 h;
- faixas de passagem maiores nas escalas curtas;
- grade e rótulos adaptados automaticamente à duração selecionada.

### Correção da versão 0.1.1

- substituição de `datetime.UTC` por `timezone.utc`, garantindo compatibilidade
  com executáveis compilados em Python 3.10;
- checagem explícita da versão mínima do Python nos scripts do Windows.
