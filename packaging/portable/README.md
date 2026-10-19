# DeepWin portátil

Extraia `DeepWin-1.1.0-amd64-portable.tar.xz`, entre na pasta extraída e
execute como usuário comum:

```bash
./deepwin
```

A pasta pode ficar em qualquer caminho, inclusive com espaços, e não precisa
ser gravável para executar a interface. O pacote do DeepWin não é instalado
no sistema. Extrair e abrir não registra menu, autostart nem ativa ajustes.
Ative os recursos desejados explicitamente no painel.

## Requisitos

Esta distribuição tem como alvo **Deepin 25 amd64**, com sessão gráfica do
Deepin e runtimes nativos **Qt 6.8 ou superior da série 6**, **DTK 6 Widgets**
e **Python 3**, incluindo D-Bus/GI/Gio. Não é uma distribuição autocontida;
as bibliotecas do desktop são fornecidas pelo sistema hospedeiro. O arquivo
contém a aplicação, seu plugin da calculadora e os helpers, sem SDK,
compilador, Python embutido ou bibliotecas privadas Qt/DTK.

Se os runtimes não estiverem presentes, instale os pacotes de execução do
repositório do seu Deepin 25 antes de abrir:

```bash
sudo apt install libdtk6widget qt6-qpa-plugins python3 python3-dbus python3-gi gir1.2-glib-2.0 dbus-daemon
```

A colagem automática exige uma sessão **X11** e `xdotool`. Recursos
específicos usam os serviços nativos do Deepin, systemd do usuário,
`libx11-6`, `libxfixes3`, `libglib2.0-bin`, `curl`, `file` e `xdg-user-dirs`.
Node/npm e uma configuração Z.AI são opcionais para o gerenciamento do
Claude. A ausência de um requisito opcional aparece no painel; não impede a
abertura da interface. O formato portátil não amplia suporte a outros
desktops ou distribuições.

O launcher não define `LD_LIBRARY_PATH` nem caminhos globais de plugins Qt.
A aplicação e os helpers usam o ambiente nativo do hospedeiro.

## Menu opcional

Para registrar esta pasta no menu do usuário:

```bash
./register-menu
```

Para remover apenas esse registro:

```bash
./unregister-menu
```

Esses comandos criam ou removem uma entrada identificada como portátil,
separada das entradas Debian/Linyaps. Personalizações são preservadas;
conflitos são informados. Se mover a pasta, execute `./register-menu` na
nova localização para atualizar o caminho. Remova o registro antes de apagar
a pasta; apagar somente a pasta não consegue retirar uma entrada de menu
já gravada em outro local.

## Dados e ajustes persistentes

Preferências, backups e os recursos ativados usam os mesmos diretórios XDG
dos formatos Debian e Linyaps. A pasta portátil contém somente os arquivos
distribuídos do programa. Ao ativar um recurso, os helpers necessários são
copiados para um runtime persistente por usuário. Mover ou apagar a pasta
portátil não interrompe os serviços já preparados nesse runtime.

Para desfazer as alterações, use a restauração do painel antes de apagar a
pasta, ou o comando persistente depois de removê-la:

```bash
"${XDG_DATA_HOME:-$HOME/.local/share}/devedu.deepin-configs/runtime/current/bin/deepwin-restore"
```

O comando também aceita o identificador de um recurso, por exemplo
`clipboard`. A restauração exige a sessão e as dependências de execução do
usuário. Backups e unidades personalizados não são sobrescritos.

É possível extrair outra versão e voltar à anterior quando o esquema de
estado for compatível. Versões que não entendem o esquema existente devem
recusá-lo sem alterar backups; não edite o esquema manualmente para forçar
uma versão antiga a ler dados novos.

## Integridade e licença

Confira o checksum a partir da pasta que contém o arquivo e seu `.sha256`:

```bash
sha256sum -c DeepWin-1.1.0-amd64-portable.tar.xz.sha256
```

O código do DeepWin é distribuído sob MIT; veja `lib/deepwin/LICENSE`.
A primeira release reunirá `.deb`, `.uab` e este `.tar.xz` após o aceite
final dos três formatos. Este README não representa uma publicação em Releases.
