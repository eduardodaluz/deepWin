# DeepWin

## Painel nativo do Deepin

O **DeepWin** foi feito com o SDK **DTK 6 Widgets**
em C++, com integração ao tema do Deepin. As decisões de arquitetura estão
em [analise-gui-deepin.md](analise-gui-deepin.md).

O comando de abertura é `deepwin` e o identificador do aplicativo/pacote é
`devedu.deepin-configs`. A entrada no menu usa `devedu.deepin-configs.desktop`.

Ele permite habilitar e desabilitar dez recursos:

- Colagem ao confirmar um item do histórico.
- Vírgula como separador decimal na calculadora Deepin.
- Quatro combinações para áreas de trabalho e monitores.
- Captura de área com Win+Shift+S.
- Miniaturas ao clicar em um grupo de janelas na barra de tarefas.
- Download automático de paisagens.
- Disponibilidade do comando `zclaude`.

### Instalação pelo pacote Debian

O pacote de teste da fase 1 tem como alvo **Deepin 25 amd64**, já validado em
imagem limpa e em VM com sessão gráfica completa: instalação, abertura,
atualização com recursos ativos, remoção e o comando de restauração
independente. O workflow de Actions gera e valida o pacote a cada push e
publica o artefato para download. O estado do trabalho está na
[passagem de desenvolvimento](continuidade-desenvolvimento.md).
O pacote inclui a GUI DTK,
o plugin da calculadora e os recursos de integração; não requer Ansible,
compilador ou SDK na máquina que vai executar o aplicativo.

Instale o arquivo pelo instalador gráfico do Deepin ou, na pasta do download:

```bash
sudo apt install ./devedu.deepin-configs_1.1.0-3_amd64.deb
deepwin
```

A instalação não ativa ajustes nem baixa o Claude. Ative os recursos desejados
no painel. Para remover o pacote, use `sudo apt remove devedu.deepin-configs`.
Os dados e ajustes já ativados são preservados. Para desfazê-los, use **Restaurar
alterações** antes de remover a GUI, ou o comando de restauração persistente
explicado abaixo. Em uma máquina com instalação local antiga, use
`/usr/bin/deepwin` para garantir que está abrindo o pacote.

Para gerar o pacote a partir do repositório, com Docker disponível:

```bash
./bin/build-deb --container
```

O build usa uma imagem oficial do Deepin 25, com digest fixado, e instala as
ferramentas somente no container. Executa CMake, a suíte de testes, debhelper e
Lintian. Os pacotes, relatórios e checksums ficam em `dist/`.
`./bin/verify-deb` valida instalação, abertura, reinstalação
e remoção em uma imagem limpa, sem montar a pasta pessoal do usuário; o fluxo
completo já passa. Para build nativo,
instale as dependências de `debian/control` e execute `./bin/build-deb`.
A validação em container não substitui o aceite final em uma VM com desktop
Deepin completo; este pacote deve ser tratado inicialmente como versão de teste.

### Build pelo pacote Linyaps (.uab)

O candidato da fase 2 empacota a mesma aplicação para o **Linyaps** (antigo
Linglong), formato de distribuição do Deepin 25. A prova de integração com o
sistema hospedeiro está registrada na
[matriz de acesso](matriz-acesso-linyaps.md): o container expõe o D-Bus da
sessão, o `$HOME` real, o systemd do usuário e a raiz do host em leitura, e o
painel opera sem ponte adicional.

Para gerar o artefato, basta Docker no host de build; o build inteiro acontece
no builder oficial do Linyaps, com slots fixados (`org.deepin.base/25.2.2` +
`org.deepin.runtime.dtk/25.2.2`) e cache de camadas em um volume nomeado:

```bash
./bin/build-uab            # primeira execução baixa os slots (~2 GB de cache)
./bin/build-uab --offline  # reusa o cache já preparado
```

O builder 1.13.8 amd64 é fixado por digest. Para usar um espelho, defina
`DEEPWIN_BUILDER_IMAGE` com a referência Docker completa. A CI usa o espelho
do mantenedor no GHCR, também fixado por digest; a variável de repositório
com esse mesmo nome permite trocar a origem. O download tem três
tentativas de até três minutos, em passo separado. Os logs de download e
build são anexados ao run mesmo quando ele falha. O procedimento de
espelhamento está em [packaging/linyaps-builder.md](packaging/linyaps-builder.md).

O `.uab` e o checksum ficam em `dist/`. No alvo com Deepin 25, que já traz o
ambiente Linyaps, instale com `sudo ll-cli install ./devedu.deepin-configs_*.uab`
ou pelo instalador gráfico. As dependências Python (`python3-dbus`,
`python3-gi`) não existem no runtime Linyaps e viajam extraídas dos debs
beige dentro do pacote, carregadas por um bootstrap no backend e no helper de
colagem; no `.deb` elas continuam vindo por `Depends`. No pacote Linyaps, a
instalação de versões do Claude pelo seletor da GUI fica indisponível (sem
`npm` no sandbox); o comando `zclaude` do terminal segue funcionando, pois
executa no host. O candidato foi aceito em VM Deepin 25.2.0 com Linyaps
1.13.7, incluindo os dez recursos e a preservação dos helpers após remoção.
A série Base/Runtime 25.2.2 deve estar instalada; a instalação de um arquivo
UAB não baixa esses componentes automaticamente. O workflow Linyaps gera o
UAB com checksum e passou também no runner limpo do GitHub. A primeira
publicação em Releases ainda depende de decisão do mantenedor; há um
[rascunho das notas](packaging/release-notes-1.1.0.md) para revisão.

### Execução pelo portátil (.tar.xz)

O portátil para **Deepin 25 amd64** contém a aplicação e seus helpers,
reutilizando os runtimes nativos Qt 6.8+/DTK 6 Widgets/Python 3 com D-Bus/GI.
Não é autocontido: os requisitos e a limpeza estão no
[README incluído no arquivo](packaging/portable/README.md).

```bash
sha256sum -c DeepWin-1.1.0-amd64-portable.tar.xz.sha256
tar -xJf DeepWin-1.1.0-amd64-portable.tar.xz
cd DeepWin-1.1.0-amd64-portable
./deepwin
```

Extrair e abrir não instala um pacote DeepWin, registra menu ou ativa
ajustes. O registro no menu é opcional e explícito, com `./register-menu`;
`./unregister-menu` remove apenas essa entrada. Após mover a pasta, execute
o registro novamente para atualizar o caminho. Launchers personalizados
são preservados, inclusive quando impedem uma atualização ou remoção.

Preferências, backups e runtime persistente são compartilhados com os outros
formatos. Os helpers preparados ao ativar ajustes continuam funcionando
depois de mover ou apagar a pasta portátil. Remova o registro de menu antes
de apagar a pasta e use a restauração descrita abaixo para desfazer ajustes.

Para gerar e validar o arquivo sem instalar ferramentas no host:

```bash
./bin/build-portable --container
./bin/verify-portable
```

`--reuse-image` reutiliza o ambiente de build já preparado; `--output`
seleciona outro diretório de saída. Os comandos de build geram o `.tar.xz`
e seu SHA-256 em `dist/`. A validação usa outro container com somente
dependências de execução, sem instalar o pacote DeepWin, e testa caminhos
com espaços, pasta somente leitura, menu e persistência após remoção.

O primeiro Release **1.1.0 reunirá `.deb`, `.uab` e `.tar.xz`**, conforme
decisão do mantenedor, após o aceite do portátil. Os artefatos ainda não
foram publicados em Releases.

### Instalação pelo código-fonte

A interface requer uma sessão gráfica do Deepin, os runtimes DTK 6 Widgets e
Qt 6 Widgets, Python 3 com `python3-dbus` e `python3-gi`, além de Ansible.
Para compilar, são necessários `g++`, `pkg-config`, os headers DTK/Qt e o `moc` do Qt 6;
o instalador pode baixar esses headers e ferramentas com `apt-get` para um cache local.
Essas dependências precisam estar disponíveis antes da instalação.
A colagem automática requer uma sessão X11; cada recurso tem requisitos próprios,
descritos nas seções abaixo. Inclua `~/.local/bin` no `PATH` para usar os comandos
instalados pelo nome.

Clone o projeto na pasta de sua preferência:

```bash
git clone https://github.com/eduardodaluz/deepWin.git
cd deepWin
```

A partir da pasta do projeto, instale a interface e a entrada no menu:

```bash
ansible-playbook -i localhost, -c local deepwin.yml
deepwin
```

Também é possível abrir **DeepWin** pelo menu do Deepin.
Os estados são consultados na sessão atual e atualizados automaticamente.
Os atalhos são aplicados imediatamente pelas APIs nativas. Desativar uma
combinação preserva outras combinações atribuídas à mesma ação.

Antes da primeira alteração de cada recurso, o painel guarda o estado original
em `$XDG_STATE_HOME/devedu.deepin-configs/originals.json`, com permissões restritas
(por padrão, `~/.local/state/devedu.deepin-configs/originals.json`).
O botão **Restaurar alterações** retorna esses recursos aos valores anteriores
ao uso do painel. Voltar manualmente ao estado inicial também limpa a respectiva
entrada de restauração. A chave da Z.AI não é lida nem alterada. A troca da versão do Claude tem seu
próprio botão **Desfazer última troca**, descrito na seção do `zclaude`.

O download de paisagens é independente da rotação nativa de imagens do Deepin.
Se a rotação nativa estiver ativa, a tela informa essa condição. Desativar o
download mantém a imagem atual; o painel não altera a rotação nativa.

A instalação não habilita os recursos. O painel prepara as integrações
compatíveis na primeira ativação e informa quando falta uma dependência da
sessão. Unidades e arquivos personalizados existentes são preservados:


| Recurso | Preparação |
| --- | --- |
| Colagem automática | O painel prepara o serviço por usuário em sessão X11; a nova unidade executa colagem real. O playbook continua disponível para diagnóstico em simulação. |
| Atalhos | Usar uma sessão com KGlobalAccel e as APIs de atalhos do Deepin; `deepin-shortcuts.yml` aplica as combinações sugeridas. |
| Vírgula decimal | Calculadora Deepin com Qt 6 (Linglong ou launcher nativo compatível); instalado com a GUI, controle em Produtividade. |
| Miniaturas ao clicar | Requer o dock do `dde-shell` com QML compatível. O controle fica em Aparência e é instalado com a GUI. |
| Download agendado de paisagens | O painel prepara serviço e timer de uma hora por usuário. Timers existentes são preservados; `deepin-wallpaper.yml` continua fazendo uma troca única. |
| `zclaude` | Instalar o Claude Code e configurar a chave da Z.AI para usar o wrapper; `zclaude.yml` instala o comando. |

O painel identifica quando a colagem está em modo de simulação. Habilitar esse
recurso pela GUI não muda o modo de execução; use o playbook para ativar a
colagem real, conforme a seção correspondente.

Para compilar manualmente, usando headers oficiais em cache local:

```bash
./bin/build-deepwin --fetch-sdk
./bin/deepwin
```

O download extrai os pacotes de desenvolvimento em `.build/deepwin/sdk`;
não instala nem atualiza bibliotecas do sistema. Requer `g++`, `pkg-config`,
`apt-get` e os runtimes DTK 6/Qt 6. As versões dos headers de DTK/Qt são
selecionadas de acordo com as bibliotecas instaladas. Se o SDK já estiver
instalado ou em cache, basta `./bin/build-deepwin`.

Verificações sem alterar configurações:

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests -v
./bin/deepwin --smoke-test
```

Os testes usam simulações e também executam o filtro Qt real quando o SDK/plugin
estão disponíveis. O build CMake inclui um teste próprio do plugin em offscreen.
O `--smoke-test` verifica a abertura e consulta de estados, aceitando recursos
opcionais indisponíveis. Use `--smoke-test --check-integrations` para exigir que
as dez integrações estejam disponíveis na sessão de teste.

Com a sessão desbloqueada, a GUI fechada, sem alterações pendentes no painel
e com a colagem ativa, é possível testar o switch e o diálogo DTK de restauração:

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 tests/verify_configs_gui.py
```

Esse teste desativa a colagem brevemente e restaura seu estado ao terminar.

Para remover somente a GUI, feche a janela e execute:

```bash
ansible-playbook -i localhost, -c local deepwin.yml -e deepwin_state=absent
```

Os recursos configurados, os backups do painel e o runtime de versões do
`zclaude` são preservados. A GUI não
instala um serviço permanente: o controlador só executa enquanto a tela consulta
ou altera uma configuração.

### Distribuição em instaladores

O [plano de distribuição](plano-distribuicao-deepwin.md) organiza as entregas
em três fases: **1. `.deb`**, **2. Linyaps/Linglong (`.uab`)** e
**3. portátil (`.tar.xz`)**. O alvo inicial é Deepin 25 em amd64, com os mesmos
ajustes e backups por usuário. A fase 1 está validada e publicada em CI; a
fase 2 tem o candidato `.uab` aceito em VM e workflow Linyaps verde, com
artefato e checksum disponíveis na CI. A fase 3 está validada em imagem
limpa, VM e no [workflow portátil](https://github.com/eduardodaluz/deepWin/actions/runs/39179478620),
com artefato e checksum. O primeiro Release 1.1.0 reunirá os três formatos.

### Runtime persistente e restauração

Ao ativar uma integração que precisa de arquivos do programa, o painel prepara
um runtime em `$XDG_DATA_HOME/devedu.deepin-configs/runtime/`. As gerações são
validadas por manifesto/hashes, e o ponteiro `current` é atualizado atomicamente.
Arquivos editados manualmente não são sobrescritos. Serviços e wrappers novos
usam esse caminho estável para continuarem funcionando após remover a GUI.

A restauração sem GUI fica disponível pelo próprio runtime:

```bash
"${XDG_DATA_HOME:-$HOME/.local/share}/devedu.deepin-configs/runtime/current/bin/deepwin-restore"
```

É possível acrescentar um identificador, como `clipboard`, para restaurar apenas
um recurso. A restauração exige a sessão do usuário e as dependências de execução;
ela preserva backups de recursos que não conseguir restaurar. Unidades criadas
pela primeira ativação são removidas quando o estado original era ausente.
Instalações anteriores permanecem compatíveis com seus helpers locais.

### Atualização do nome anterior

Feche a versão antiga antes de aplicar `deepwin.yml`. A instalação migra o
estado de `~/.local/state/deepin-configs/` para
`~/.local/state/devedu.deepin-configs/` e remove o launcher e a entrada antigos
do menu. Se os dois diretórios de estado existirem, a migração para sem
sobrescrever os backups. Os serviços dos recursos mantêm seus nomes próprios.

### Arquivos para o GitHub

O `.gitignore` cobre os artefatos de desenvolvimento DTK/Qt/CMake, o cache do
SDK, pacotes gerados, preferências locais do Qt Creator e arquivos privados.
Credenciais, `.env`, chaves e backups de execução não devem ser versionados.
Exemplos `.env.example` e `.env.sample`, fontes, traduções `.ts`, recursos `.qrc`,
templates `.desktop`, metadados Debian e a prévia da GUI continuam versionáveis.

## Atalhos do Deepin

O playbook `deepin-shortcuts.yml` configura o `dde-kwin` para usar:

| Atalho | Ação |
| --- | --- |
| `Ctrl+Win+←` | Área de trabalho anterior |
| `Ctrl+Win+→` | Próxima área de trabalho |
| `Shift+Win+←` | Mover a janela para o monitor anterior |
| `Shift+Win+→` | Mover a janela para o próximo monitor |
| `Win+Shift+S` | Capturar uma área da tela, com recorte e edição |

Ele altera `~/.config/kglobalshortcutsrc`, cria uma cópia única do estado
original em `~/.config/kglobalshortcutsrc.before-deepin-shortcuts` e configura
o atalho de captura pelo GSettings nativo do Deepin.

Execute a partir desta pasta:

```bash
ansible-playbook -i localhost, -c local deepin-shortcuts.yml
```

Para aplicar somente o atalho de captura:

```bash
ansible-playbook -i localhost, -c local deepin-shortcuts.yml --tags screenshot
```

O atalho de captura é aplicado imediatamente, inclusive no registro ativo do
`dde-session-daemon`. Para os atalhos do `dde-kwin`,
encerre a sessão do Deepin e entre novamente, pois ele os lê no início da
sessão.

## Colar com Enter no histórico do Deepin

O script `bin/deepin-clipboard-autopaste` observa o monitor de teclas nativo
do Deepin pelo D-Bus. Depois de um Enter no histórico, aguarda a atualização
da seleção CLIPBOARD, o fechamento do histórico e o retorno do foco ao
aplicativo de origem. Só então envia uma única colagem com `xdotool`:
Ctrl+Shift+V em terminais reconhecidos e Ctrl+V nos demais aplicativos.

Funciona em X11. Usa Python 3, `python3-dbus`, `python3-gi`, libX11,
libXfixes e `xdotool`. O playbook verifica essas dependências e interrompe
a instalação se alguma estiver ausente; ele não instala pacotes. A automação
preserva o atalho Win+V e os dados do histórico. O script não lê nem registra
o conteúdo copiado.

Para instalar e iniciar em **modo de simulação**, sem início automático:

```bash
ansible-playbook -i localhost, -c local deepin-clipboard.yml
journalctl --user -u deepin-clipboard-autopaste.service -f
```

Nesse modo, o log informa `SIMULAÇÃO: colaria` quando as condições forem
atendidas. Para ativar a colagem real e iniciar com a sessão do Deepin:

```bash
ansible-playbook -i localhost, -c local deepin-clipboard.yml \
  -e clipboard_autopaste_mode=paste \
  -e clipboard_autopaste_autostart=true
```

O serviço usa as variáveis DISPLAY e XAUTHORITY importadas pela sessão.
Troca de aplicativo, clique, rolagem ou outra tecla durante a espera
cancelam a colagem. O prazo padrão é de 1,5 segundo e inclui os cerca de
500 ms de atraso da seleção no `dde-clipboard` 6.1.33, referência da
implementação. Outras versões precisam de validação de compatibilidade.

Os terminais são identificados por nomes exatos de `WM_CLASS`, sem depender
do título da janela. A lista inclui Deepin Terminal, Kitty, Alacritty,
GNOME Terminal, Konsole, Xfce Terminal, MATE Terminal, QTerminal, LXTerminal,
Tilix, Terminator, Guake, Yakuake, WezTerm, Ghostty, GNOME Console e Ptyxis.
O atalho desses terminais deve continuar configurado como Ctrl+Shift+V.
Terminais embutidos em editores e classes personalizadas não reconhecidas
usam a regra do aplicativo que contém a janela.

Os testes gráficos cobrem texto em editor GTK e oferecem verificações para
Deepin Terminal, Kitty e Alacritty. Imagens, arquivos e cada aplicativo de
destino precisam de validação própria.
Existe uma pequena corrida entre a última verificação do foco e
o envio das teclas; a automação não deve ser tratada como uma operação
atômica do aplicativo de destino.

### Rollback

Para interromper a automação imediatamente e impedir seu início automático:

```bash
systemctl --user disable --now deepin-clipboard-autopaste.service
```

Para remover também o script e o serviço instalados:

```bash
ansible-playbook -i localhost, -c local deepin-clipboard.yml \
  -e clipboard_autopaste_state=absent
```

Isso remove apenas `~/.local/bin/deepin-clipboard-autopaste` e
`~/.config/systemd/user/deepin-clipboard-autopaste.service`. O histórico
nativo continua disponível pelo Win+V; nenhuma configuração nativa precisa
ser restaurada.

### Verificação

```bash
/usr/bin/python3 -m unittest discover -s tests -v
```

Com o serviço parado, o teste gráfico abaixo abre dois editores temporários,
cria itens de teste no histórico e valida a colagem e os cancelamentos.
Execute em uma sessão gráfica desbloqueada, com GTK 3 e seus bindings Python
disponíveis (`python3-gi` e `gir1.2-gtk-3.0`). Acrescente `--dry-run` para verificar
o fluxo sem enviar Ctrl+V:

```bash
/usr/bin/python3 tests/verify_clipboard_graphical.py
```

Com o serviço ativo, o teste de terminal abre uma janela temporária e executa
somente um leitor de bytes, sem shell e sem executar o texto colado:

```bash
/usr/bin/python3 tests/verify_clipboard_terminal.py
# Também aceita --terminal kitty e --terminal alacritty.
```

Para diagnóstico interativo, também com o serviço parado:

```bash
./bin/deepin-clipboard-autopaste --dry-run --diagnose
```

## Vírgula decimal na calculadora

Em **Produtividade → Vírgula decimal na calculadora**, habilite o ajuste.
Feche a calculadora e reabra pelo menu do Deepin. A tecla vírgula passa a ter
a mesma ação decimal da tecla ponto, inclusive no teclado numérico; por exemplo,
`1,5 + 0,5` resulta em `2`. O separador exibido continua seguindo a configuração
regional da própria calculadora.

A integração usa um plugin **Qt 6** com filtro de eventos dentro da calculadora,
nos modos básico e científico. Preserva a tecla ponto, os atalhos com
Ctrl/Alt/Shift/Win, o tema e os plugins nativos do Deepin. Não altera o mapa
do teclado, monitora outros aplicativos ou modifica os arquivos do Linglong.
O modo programador mantém as regras nativas para números inteiros.

O instalador compila o plugin com o mesmo SDK Qt 6 usado pela GUI. Os recursos
ficam em `$XDG_DATA_HOME/devedu.deepin-configs/` (padrão `~/.local/share/`):
`qt6/plugins/generic/libdeepwin-calculator.so`, `bin/deepwin-calculator` e a flag
`calculator-enabled.json`. Ao ativar, o painel cria apenas a sobreposição
`$XDG_DATA_HOME/applications/deepin-calculator.desktop`, preservando os nomes,
ícone e traduções do launcher oficial. Launchers pessoais ou editados não são
sobrescritos. A correção requer a calculadora Qt 6 e um launcher oficial compatível,
seja nativo ou `org.deepin.calculator` pelo Linglong. Abrir diretamente por
`ll-cli run` ou pelo executável original não carrega esse filtro.

Desativar o switch remove a flag e a sobreposição. Uma calculadora que já carregou
o plugin volta ao tratamento original na próxima tecla; a próxima abertura pelo
menu também usa o launcher original. **Restaurar alterações** oferece o mesmo
rollback. Remover apenas a GUI preserva esse recurso, assim como os demais ajustes.
As decisões e referências estão em [analise-calculadora-deepin.md](analise-calculadora-deepin.md).

## Miniaturas ao clicar no ícone de um aplicativo

Em **Aparência → Miniaturas ao clicar em grupos de janelas**, habilite o recurso
para abrir a prévia nativa ao clicar em um ícone com duas ou mais janelas. A
janela de destino só é ativada depois de clicar em uma miniatura. Com uma única
janela, o dock mantém sua ação normal; o botão direito e a prévia ao passar o
mouse também mantêm o comportamento nativo.

A mudança recarrega o `dde-shell`, incluindo a barra de tarefas. Os aplicativos
abertos permanecem em execução. Desativar o switch ou usar **Restaurar alterações**
retorna ao comportamento anterior.

O DeepWin gera uma cópia personalizada do componente nativo em
`$XDG_DATA_HOME/dde-shell/org.deepin.ds.dock.taskmanager/`
(por padrão, `~/.local/share/dde-shell/org.deepin.ds.dock.taskmanager/`). Os
arquivos de `/usr/share/dde-shell` são preservados. Uma personalização local
preexistente ou arquivos alterados manualmente são protegidos contra sobrescrita.

Um drop-in de usuário do serviço `dde-shell@DDE.service` atualiza essa cópia
antes de iniciar o shell após atualizações. Se o código nativo deixar de ser
compatível, o ajuste é suspenso e o pacote original volta a ser carregado.
O helper e o ajuste continuam disponíveis se apenas a GUI for removida.
A implementação e a compatibilidade estão descritas em
[analise-dock-deepin.md](analise-dock-deepin.md).

Para verificar com janelas descartáveis, com o recurso inicialmente desativado,
GTK 3 disponível e a sessão X11 desbloqueada:

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 tests/verify_dock_preview.py
```

O teste recarrega a barra, verifica o clique e a escolha de uma miniatura e
restaura o estado anterior automaticamente.

## Papel de parede de paisagem

O playbook `deepin-wallpaper.yml` executa uma troca de imagem por chamada.
Ele não cria agendamento automático. O controle de agendamento da GUI requer
as unidades `deepin-wallpaper.timer` e `deepin-wallpaper.service` previamente
configuradas no systemd do usuário; a frequência depende do timer.

O script `bin/refresh-deepin-wallpaper` consulta as paginas publicas de
[paisagens](https://unsplash.com/wallpapers/nature/landscape),
[montanhas](https://unsplash.com/wallpapers/nature/mountain) e
[florestas](https://unsplash.com/wallpapers/nature/forest) do Unsplash a cada
execucao, baixa uma imagem com largura de 3840 pixels e a aplica pelo esquema
de aparencia nativo do Deepin. Nao precisa de chave de API; requer Bash,
Python 3, `curl`, `file`, utilitários GNU e `gsettings`, além de acesso a essas
páginas. A descoberta depende do HTML público do site e pode precisar de
atualização se o Unsplash mudar seu formato.

Os arquivos ficam na subpasta `Wallpapers` do diretório de imagens retornado
por `xdg-user-dir PICTURES`; sem esse utilitário, o padrão é `~/Pictures/Wallpapers`.
Antes de salvar, o script compara o SHA-256 da imagem com os arquivos já baixados
e registra as URLs utilizadas em
`$XDG_STATE_HOME/deepin-wallpaper/used-landscape-urls`
(por padrão, `~/.local/state/deepin-wallpaper/used-landscape-urls`). Fotos ja utilizadas
sao identificadas mesmo quando os parametros da URL mudam. O historico antigo
e preservado. Se nao encontrar uma imagem nova ou os downloads falharem, o
comando informa o problema e termina com erro.
O CDN do Unsplash não fornece título nem nome de arquivo nos metadados HTTP.
Por isso, cada novo arquivo usa o identificador da foto da própria URL, no
formato `unsplash-photo-<identificador>-<data-hora>.jpg`.

Para trocar por uma paisagem aleatória:

```bash
ansible-playbook -i localhost, -c local deepin-wallpaper.yml
```

Ou para usar uma URL de imagem específica:

```bash
./bin/refresh-deepin-wallpaper --url 'https://exemplo.com/paisagem.jpg'
```

## Claude Code via Z.AI (zclaude)

O playbook `zclaude.yml` instala o script `bin/zclaude` em
`~/.local/bin/zclaude`. O comando executa o `claude` com
`ANTHROPIC_BASE_URL` e `ANTHROPIC_AUTH_TOKEN` apontando para a API da
Z.AI (GLM), sem alterar as configurações do `claude` original. A chave
fica em `~/.config/zai/api_key`, criada com permissão `0600` pelo
próprio comando (o caminho pode ser trocado pela variável
`ZAI_API_KEY_FILE` e a chave, por `ZAI_API_KEY`).

```bash
ansible-playbook -i localhost, -c local zclaude.yml
zclaude --setup   # salva a chave de API da Z.AI
zclaude           # abre o Claude Code via Z.AI
```

Para instalar em outra máquina alcançável por SSH, a partir desta pasta:

```bash
ansible-playbook -i <host>, zclaude.yml
```

Requisitos: `claude` instalado, uma chave da Z.AI e `~/.local/bin` no `PATH`.

### Selecionar a versão pela interface

Abra **Ferramentas → Versão do Claude para zclaude**. Também é possível abrir
essa seção diretamente com `deepwin --section tools`.

- **Stable:** instala a versão indicada pelo canal `stable` do registro npm.
  Ao abrir o `zclaude`, o DeepWin verifica atualizações em segundo plano no
  máximo uma vez por dia. A nova versão passa a valer nas próximas execuções.
  Se o download falhar, a versão instalada continua em uso.
- **Versão fixa:** escolha um número da lista de versões publicadas ou digite
  o número desejado, por exemplo `2.1.302`, e clique em **Aplicar**. O DeepWin
  confere a versão antes de ativá-la. Ela permanece fixa até uma nova seleção.
- **Claude do sistema:** usa o comando `claude` disponível no `PATH`, com a
  política de atualização da própria instalação.

**Buscar versões** atualiza a lista pelo registro oficial npm. Baixar versões
requer Node.js/npm compatíveis com o pacote escolhido e acesso à internet.
O [canal Stable é distinto de Latest](https://code.claude.com/docs/en/setup#configure-release-channel);
selecioná-lo pode instalar uma versão anterior à mais recente publicada.
A seleção não garante compatibilidade de todas as versões com a Z.AI.

As versões baixadas ficam em
`$XDG_DATA_HOME/devedu.deepin-configs/claude/versions/`
(por padrão, `~/.local/share/devedu.deepin-configs/claude/versions/`). Cada uma
fica em um diretório separado, preservando as versões usadas por sessões
abertas e permitindo reaproveitar downloads. O DeepWin gerencia as atualizações
dessas cópias; ele não atualiza a instalação principal do Claude.

A seleção fica em `$XDG_STATE_HOME/devedu.deepin-configs/claude-selection.json`
(por padrão, `~/.local/state/devedu.deepin-configs/claude-selection.json`).
**Desfazer última troca** restaura a seleção imediatamente anterior, inclusive
o comportamento anterior ao primeiro uso do seletor. Os executáveis baixados
são preservados. Esse botão é independente de **Restaurar alterações**, que
controla os switches do painel.

Antes da primeira seleção, o wrapper usa a cópia em
`~/.local/share/claude-glm/bin/claude` quando disponível, ou o `claude` do sistema.
`ZCLAUDE_CLAUDE_BIN` tem precedência sobre o seletor; remova essa variável do
ambiente para selecionar pela interface. As cópias isoladas continuam usando
`~/.claude-glm` (ou `CLAUDE_CONFIG_DIR`) sem reescrever suas configurações ou a
chave da Z.AI.

O guia [de diagnóstico do erro 1210](fix-glm-claudecode-erro1210.md) descreve um
contorno específico; instalar uma versão antiga não é requisito geral do projeto.

## Licença

O código do DeepWin é distribuído sob a [licença MIT](LICENSE). As dependências
e os arquivos nativos do Deepin mantêm suas próprias licenças.
