# Mission Control Timeline

Aplicativo desktop para Windows que calcula e exibe, em uma linha do tempo
móvel configurável, os períodos em que os satélites de uma lista de números
NORAD estão acima da máscara de elevação de uma estação terrena.

## Versão 0.9.0

- escolha da pasta de dados durante a instalação, mantendo AppData como padrão;
- nova aba de armazenamento no Setup, com seleção e abertura da pasta;
- cópia segura das configurações, lista NORAD e cache orbital ao mudar o local;
- caminho personalizado preservado no Registro do Windows;
- aba Sobre reorganizada para manter os acessos à licença, termos e privacidade
  sempre visíveis ao lado do logo;
- licença freeware, termos de uso e aviso de privacidade em seis idiomas;
- aceite dos documentos legais durante a instalação, no idioma escolhido;
- documentos legais disponíveis individualmente na aba **About/Sobre**;
- rodapé do Setup fixado para manter **Salvar ajustes** e **Cancelar** sempre
  visíveis, inclusive com escala elevada do Windows;
- abas do Setup com fundo escuro e contraste reforçado;
- logo do programa incluído na aba **About/Sobre**;
- atalhos do Menu Iniciar e da Área de Trabalho apontam diretamente para o
  novo arquivo de ícone;
- janela móvel selecionável de 3, 6, 8, 12 ou 24 horas;
- marcador vermelho do horário atual após apenas 15 minutos de histórico;
- cabeçalho simplificado com a data local e a próxima passagem entre todos os
  satélites, mostrando nome e contagem regressiva para AOS;
- busca da próxima passagem em um horizonte de 24 horas, independentemente da
  escala selecionada na linha do tempo;
- alerta sonoro único quando faltam dois minutos para AOS;
- contagem regressiva sonora com um bip por segundo nos cinco segundos finais;
- botão persistente para ativar ou silenciar os alertas;
- grade adaptativa de 15 minutos a 3 horas conforme a escala escolhida;
- janela única de ajustes para lista NORAD, estação, idioma e informações
  sobre o programa;
- interface em inglês por padrão, com português, espanhol, italiano, francês
  e alemão;
- atualização automática de dados orbitais pelo CelesTrak ao iniciar e a cada 24 h;
- configurações, lista NORAD e cache orbital preservados no AppData do usuário;
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

### Correção da versão 0.7.1

- rodapé do editor NORAD fixado em uma linha própria do layout;
- botões **Cancelar** e **Salvar lista** permanecem visíveis com escala de tela
  elevada no Windows;
- altura inicial e mínima da janela ajustadas.

### Alterações da versão 0.7.0

- o botão **Lista NORAD** agora abre um editor dentro do programa;
- instruções e exemplo de preenchimento exibidos na própria janela;
- validação imediata da quantidade de satélites reconhecidos;
- aceitação de números separados por vírgulas, ponto e vírgula, espaços ou
  quebras de linha;
- rejeição de nomes, valores inválidos e catálogos duplicados antes de salvar;
- persistência canônica em `satellites.txt`, sem necessidade de localizar ou
  manter um TXT externo;
- migração automática do cache orbital antigo para a pasta de dados do usuário;
- distribuição PyInstaller alterada de executável autoextraível para `onedir`;
- metadados de produto e versão incorporados ao executável;
- projeto de instalador Inno Setup incluído para uma instalação convencional.

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
- `orbital_cache.json` gravado atomicamente na pasta de dados do usuário;
- uso automático do último cache válido quando a internet está indisponível;
- atualização parcial preserva os registros antigos dos catálogos que falharam.
- erros HTTP ou indisponibilidade do CelesTrak interrompem imediatamente a rodada,
  preservando o cache e evitando novas solicitações ao serviço.

## Executar pelo código-fonte no Windows

1. Instale Python 3.10 ou mais recente marcando a opção **Add Python to PATH**.
2. Dê duplo clique em `run_windows.bat`.
3. No programa, abra **Setup**, informe os números NORAD e os dados da estação.
4. Escolha o idioma desejado e salve os ajustes.

Na primeira execução, o script cria um ambiente virtual e instala somente a
biblioteca orbital necessária.

## Gerar o aplicativo e o instalador

Em um computador Windows, dê duplo clique em `build_windows.bat`. A distribuição
independente será criada em:

```text
dist\MissionControlTimeline\MissionControlTimeline.exe
```

O computador em que ela for executada não precisará ter Python instalado. O
formato `onedir` evita a extração de executáveis em uma pasta temporária a cada
abertura.

Se o **Inno Setup 6** estiver instalado, o mesmo script também criará:

```text
dist-installer\MissionControlTimeline_Setup_0.9.0.exe
```

O instalador é por usuário, não solicita privilégios administrativos e cria
atalhos no menu Iniciar e, opcionalmente, na área de trabalho.

## Formato da lista NORAD

Abra **Setup > Satellites** e informe os números separados por vírgulas,
espaços, ponto e vírgula ou linhas:

```text
25544, 43786, 27607
```

O programa valida a lista e salva internamente um número por linha. Os arquivos
de usuário ficam em:

```text
%LOCALAPPDATA%\MissionControlTimeline\
```

Não edite manualmente o `orbital_cache.json`. Depois da primeira atualização
bem-sucedida, o programa pode iniciar e calcular passagens sem conexão com a
internet.

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
