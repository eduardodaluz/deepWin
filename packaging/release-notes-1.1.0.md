# DeepWin 1.1.0 — rascunho da primeira release

Painel nativo DTK 6/Qt 6 para configurar dez integrações do desktop Deepin:
colagem pelo histórico, atalhos de áreas de trabalho e monitores, captura de
área, prévias de grupos da dock, vírgula decimal na calculadora e controle
do download de paisagens. Inclui gerenciamento opcional do Claude/Z.AI.

## Plataforma e arquivos

Referência validada: **Deepin 25 amd64**, com aceite gráfico em Deepin
25.2.0 e sessão X11. O formato de distribuição não remove os requisitos dos
serviços nativos do Deepin. A colagem automática exige X11.

Arquivos gerados pela CI e previstos para anexar ao Release:

- `devedu.deepin-configs_1.1.0-3_amd64.deb` e seu SHA-256.
- `devedu.deepin-configs_1.1.0.0_x86_64_main.uab` e seu SHA-256.

Os números dos pacotes seguem as convenções de cada formato; ambos são a
aplicação 1.1.0. O portátil `.tar.xz` será entregue em fase posterior.

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

## Dados e remoção

Backups, preferências e runtime persistente são compartilhados pelos dois
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
- 126 testes Python e build UAB local aprovados nesta passagem.
- CI Debian: [build e verificação aprovados](https://github.com/eduardodaluz/deepWin/actions/runs/39177256036).
- CI Linyaps: [build, smoke tests e exportação aprovados](https://github.com/eduardodaluz/deepWin/actions/runs/39177256037).
- Artefatos `deepwin-deb-amd64` e `deepwin-uab-amd64` disponíveis nos runs
  acima; anexar os pacotes e seus checksums gerados antes de publicar.

Licença MIT. Este arquivo é um rascunho para revisão; não houve publicação de
Release nem criação de tag.
