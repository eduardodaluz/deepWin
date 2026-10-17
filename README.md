# DeepWin

## Painel nativo do Deepin

O **DeepWin** foi feito com o SDK **DTK 6 Widgets**
em C++, usando as bibliotecas Qt/DTK e o tema do Deepin instalados. A avaliação
dos recursos e da escolha do SDK está em [analise-gui-deepin.md](analise-gui-deepin.md).

O comando de abertura é `deepwin` e o identificador do aplicativo/pacote é
`devedu.deepin-configs`. A entrada no menu usa `devedu.deepin-configs.desktop`.

Ele permite habilitar e desabilitar oito recursos:

- Colagem ao confirmar um item do histórico.
- Quatro combinações para áreas de trabalho e monitores.
- Captura de área com Win+Shift+S.
- Download automático de paisagens.
- Disponibilidade do comando `zclaude`.

O repositório é [eduardodaluz/deepWin](https://github.com/eduardodaluz/deepWin).
Nesta máquina, o código fica em `~/dev/src/deepWin/`.

Para instalar e adicionar ao menu, a partir da pasta do projeto:

```bash
ansible-playbook -i localhost, -c local deepwin.yml
deepwin
```

Também é possível abrir **DeepWin** pelo menu do Deepin.
Os estados são consultados na sessão atual e atualizados automaticamente.
Os atalhos são aplicados imediatamente pelas APIs nativas. Desativar uma
combinação preserva outras combinações atribuídas à mesma ação.

Antes da primeira alteração de cada recurso, o painel guarda o estado original
em `~/.local/state/devedu.deepin-configs/originals.json`, com permissões restritas.
O botão **Restaurar alterações** retorna esses recursos aos valores anteriores
ao uso do painel. Voltar manualmente ao estado inicial também limpa a respectiva
entrada de restauração. A chave da Z.AI não é lida nem alterada.

O download de paisagens é independente da rotação nativa de imagens do Deepin,
que também foi encontrada ativa. A tela informa essa diferença. Desativar o
download mantém a imagem atual; o painel não desativa a rotação nativa.

A GUI controla os serviços já instalados. Um recurso ausente ou bloqueado é
mostrado como indisponível; instale-o pelo respectivo playbook. A colagem em
modo de simulação é identificada no estado, caso o serviço esteja nesse modo.

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

Verificação sem alterar configurações:

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests -v
./bin/deepwin --smoke-test
```

Com a sessão desbloqueada, a GUI fechada, sem alterações pendentes no painel e com a colagem ativa,
é possível testar o switch e o diálogo DTK de restauração na sessão real:

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 tests/verify_configs_gui.py
```

Esse teste desativa a colagem brevemente e restaura seu estado ao terminar.

Para remover somente a GUI, feche a janela e execute:

```bash
ansible-playbook -i localhost, -c local deepwin.yml -e deepwin_state=absent
```

Os recursos configurados e os backups do painel são preservados. A GUI não
instala um serviço permanente: o controlador só executa enquanto a tela consulta
ou altera uma configuração.

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
libXfixes e `xdotool`, já presentes nesta máquina; não instala pacotes nem
altera o Deepin, o atalho Win+V ou os dados do histórico. O script não lê
nem registra o conteúdo copiado.

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
500 ms que esta versão do Deepin espera antes de aplicar a seleção.

Os terminais são identificados por nomes exatos de `WM_CLASS`, sem depender
do título da janela. A lista inclui Deepin Terminal, Kitty, Alacritty,
GNOME Terminal, Konsole, Xfce Terminal, MATE Terminal, QTerminal, LXTerminal,
Tilix, Terminator, Guake, Yakuake, WezTerm, Ghostty, GNOME Console e Ptyxis.
O atalho desses terminais deve continuar configurado como Ctrl+Shift+V.
Terminais embutidos em editores e classes personalizadas não reconhecidas
usam a regra do aplicativo que contém a janela.

Texto foi validado em editor GTK, Deepin Terminal, Kitty e Alacritty na sessão
real; imagens, arquivos e cada aplicativo de destino precisam de validação própria.
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
Execute dentro da sessão gráfica. Acrescente `--dry-run` para verificar
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

## Papel de parede de paisagem

O script `bin/refresh-deepin-wallpaper` consulta as paginas publicas de
[paisagens](https://unsplash.com/wallpapers/nature/landscape),
[montanhas](https://unsplash.com/wallpapers/nature/mountain) e
[florestas](https://unsplash.com/wallpapers/nature/forest) do Unsplash a cada
execucao, baixa uma imagem com largura de 3840 pixels e a aplica pelo esquema
de aparencia nativo do Deepin. Nao precisa de chave de API; requer Python 3 e
acesso a essas paginas. A descoberta depende do HTML publico do site e pode
precisar de atualizacao se o Unsplash mudar seu formato.

Os arquivos ficam em `~/Pictures/Wallpapers`. Antes de salvar, o script compara
o SHA-256 da imagem com os arquivos ja baixados e registra as URLs utilizadas
em `~/.local/state/deepin-wallpaper/used-landscape-urls`. Fotos ja utilizadas
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

Requisitos: `claude` instalado e `~/.local/bin` no `PATH`.
