# Mission Control — Satellite Pass Timeline

Aplicativo desktop para Windows que calcula e exibe, em uma linha do tempo
móvel configurável, os períodos em que satélites descritos por TLE estão acima
da máscara de elevação de uma estação terrena.

## Versão 0.4.1

- janela móvel selecionável de 3, 6, 8, 12 ou 24 horas;
- marcador vermelho do horário atual após apenas 30 minutos de histórico;
- grade adaptativa de 15 minutos a 3 horas conforme a escala escolhida;
- importação de arquivos TLE nos formatos de duas ou três linhas;
- propagação orbital SGP4;
- cálculo de AOS, LOS, máxima elevação, azimutes e distância;
- estação e máscara de elevação configuráveis;
- atualização contínua da janela e recálculo orbital periódico em segundo plano;
- painel superior ao vivo para satélites em visada, com elevação, azimute e
  contagem regressiva para o LOS;
- altura mínima reduzida para uso compacto com poucos satélites;
- cartão flutuante com AOS, máxima elevação, LOS, azimutes e distância ao
  clicar em uma passagem;
- fechamento automático do cartão ao clicar fora de uma passagem;
- aviso visual de TLE antigo;
- detalhes da passagem ao clicar em uma faixa.

## Executar pelo código-fonte no Windows

1. Instale Python 3.10 ou mais recente marcando a opção **Add Python to PATH**.
2. Dê duplo clique em `run_windows.bat`.
3. No programa, use **Importar TLE** e escolha um arquivo `.tle` ou `.txt`.
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

## Formato TLE aceito

Com nome (três linhas):

```text
NOME DO SATELITE
1 NNNNNU ...
2 NNNNN  ...
```

Sem nome (duas linhas):

```text
1 NNNNNU ...
2 NNNNN  ...
```

## Observações de engenharia

- O TLE deve ser recente. Para operações, atualize a lista regularmente.
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
