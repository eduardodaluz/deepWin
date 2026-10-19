# DeepWin 1.1.0

Painel nativo DTK 6/Qt 6 para configurar dez integrações do desktop Deepin:
colagem pelo histórico, atalhos de áreas de trabalho e monitores, captura de
área, prévias de grupos da dock, vírgula decimal na calculadora e controle
do download de paisagens. Inclui gerenciamento opcional do Claude/Z.AI.

## Plataforma e arquivos

Referência validada: **Deepin 25 amd64**, com aceite gráfico em Deepin
25.2.0 e sessão X11. O formato de distribuição não remove os requisitos dos
serviços nativos do Deepin. A colagem automática exige X11.

Esta primeira versão reúne três formatos:

- `devedu.deepin-configs_1.1.0-3_amd64.deb` e seu SHA-256.
- `devedu.deepin-configs_1.1.0.0_x86_64_main.uab` e seu SHA-256.
- `DeepWin-1.1.0-amd64-portable.tar.xz` e seu SHA-256.

Os números dos pacotes seguem as convenções de cada formato; todos são a
aplicação 1.1.0.

Cada arquivo tem um checksum `.sha256` adjacente. Baixe o instalador e seu
checksum na mesma pasta e confira com `sha256sum -c NOME-DO-ARQUIVO.sha256`.
O arquivo `SHA256SUMS` reúne os checksums dos três instaladores.

## Instalação

Escolha um dos formatos. O aplicativo funciona como usuário comum e instalar
os arquivos não ativa ajustes automaticamente; a ativação ocorre no painel.

Debian, a partir da pasta que contém o pacote:

```bash
sudo apt install ./devedu.deepin-configs_1.1.0-3_amd64.deb
deepwin
```

Linyaps:

```bash
sudo ll-cli install ./devedu.deepin-configs_1.1.0.0_x86_64_main.uab
ll-cli run devedu.deepin-configs
```

No formato UAB, Base `org.deepin.base/25.2.2` e Runtime
`org.deepin.runtime.dtk/25.2.2` precisam estar disponíveis no sistema.
Instalar um arquivo UAB não baixa esses componentes automaticamente. Essa
série estava presente na instalação stock Deepin 25 usada no aceite.

A interface também pode ser aberta pelo menu. Node/npm e credenciais Z.AI
são opcionais para o uso geral. No aplicativo Linyaps, instalar versões do
Claude pelo seletor da GUI permanece indisponível; o wrapper `zclaude`
executado no host continua utilizável.

Portátil, depois de conferir o arquivo de checksum adjacente:

```bash
sha256sum -c DeepWin-1.1.0-amd64-portable.tar.xz.sha256
tar -xJf DeepWin-1.1.0-amd64-portable.tar.xz
cd DeepWin-1.1.0-amd64-portable
./deepwin
```

O portátil usa os runtimes Qt 6.8+/DTK 6/Python D-Bus/GI do hospedeiro e não
é autocontido. Não exige instalar o pacote DeepWin, Git, SDK ou compilador.
O [README do portátil](https://github.com/eduardodaluz/deepWin/blob/v1.1.0/packaging/portable/README.md) lista as dependências nativas e
a limpeza. `./register-menu` e `./unregister-menu` gerenciam somente o
registro opcional no menu; abrir a interface não faz esse registro.

## Dados e remoção

Backups, preferências e runtime persistente são compartilhados pelos três
formatos, em diretórios XDG do usuário. Arquivos e unidades personalizados
são preservados; conflitos são informados.

Remover o aplicativo preserva dados e integrações já ativadas. Para desfazer
os ajustes, use a restauração do painel antes de remover a GUI ou o helper
preservado após removê-la:

```bash
"${XDG_DATA_HOME:-$HOME/.local/share}/devedu.deepin-configs/runtime/current/bin/deepwin-restore" --help
```

## Validação

- Aceite de instalação, atualização e remoção em VM Deepin com Solid ativo.
- Interação humana com dock, calculadora, captura, colagem e workspaces.
- Preservação de backups, serviços e comando de restauração após remoção.
- 142 testes Python aprovados após adicionar a integração opcional de menu.
- Portátil validado em imagem limpa, sem pacote DeepWin ou SDK, e em sessão
  gráfica real de uma VM Deepin 25: caminhos com espaços, pasta somente
  leitura, coexistência e remoção dos outros formatos, serviço persistente
  e restauração real após apagar a pasta.
- CI Debian: [build e verificação aprovados](https://github.com/eduardodaluz/deepWin/actions/runs/39179478622).
- CI Linyaps: [build, smoke tests e exportação aprovados](https://github.com/eduardodaluz/deepWin/actions/runs/39179478573).
- CI portátil: [build e verificação aprovados](https://github.com/eduardodaluz/deepWin/actions/runs/39179478620).
- Os três instaladores vêm dos runs acima, no mesmo commit de código
  [`07fb017`](https://github.com/eduardodaluz/deepWin/commit/07fb017ab558f54b7282821d7ca305e8289f4b66).
  A tag acrescenta somente documentação e automação de publicação; os
  arquivos são os já aprovados pela CI, com checksums conferidos antes da
  publicação.

Licença MIT.
