# Continuidade do desenvolvimento do DeepWin

Registro de passagem iniciado em **17/10/2026** e atualizado a cada retomada;
as seções antigas são história executada e ficam intactas. A seção seguinte é
o ponto de partida atual para o próximo agente.

## Ponto de partida para o próximo agente

Atualizado em **18/10/2026**, ao preparar a publicação autorizada do Release.

- Repositório: <https://github.com/eduardodaluz/deepWin>, branch `main`.
  Consulte `git log -1` para o commit atual. **Nenhum commit contém linha de
  coautoria do Claude**: o mantenedor pediu a remoção (seis commits
  reescritos com árvores idênticas e force push com lease) e commits novos
  devem sair sem o trailer.
- O mantenedor **autorizou explicitamente o push à `main`** após a rejeição
  automática inicial. Código validado nos três workflows: `07fb017`.
  **CI Debian, Linyaps e portátil verdes**, com artefatos publicados nos runs
  [39179478622](https://github.com/eduardodaluz/deepWin/actions/runs/39179478622),
  [39179478573](https://github.com/eduardodaluz/deepWin/actions/runs/39179478573)
  e [39179478620](https://github.com/eduardodaluz/deepWin/actions/runs/39179478620).
- **Fase 1 (.deb): concluída e publicada em CI.** Candidato
  `devedu.deepin-configs_1.1.0-3_amd64.deb`; workflow Debian verde em todos
  os pushes; aceite em VM completo (adendo de 18/10).
- **Fase 2 (Linyaps `.uab`): concluída e aceita em VM.** Candidato atual
  `devedu.deepin-configs_1.1.0.0_x86_64_main.uab`, sha256
  `de77d61478d540d837d2c6bf5026cf0fd09cc7c587cde41c8311786b06e8bc87` — este é
  o build com o pin `org.deepin.runtime.dtk/25.2.2` e os fixes de
  `XDG_DATA_DIRS`; o `8a68fdd8…` citado no adendo da fase 2 foi o build
  intermediário em 6.7.0. Os sete critérios da L2 têm evidência (adendos
  seguintes).
- **CI da fase 2 concluída.** O pull no runner passou após o espelhamento;
  a CI revelou mais duas diferenças em relação ao host de desenvolvimento
  (namespaces e UID do staging), corrigidas e validadas localmente e no
  runner limpo. Build, smoke tests, exportação e upload passaram.
  **Implementado nesta retomada:**
  override `DEEPWIN_BUILDER_IMAGE`, origem fixada por digest, pull separado
  com três tentativas limitadas e logs anexados mesmo em falha. A variável
  de repositório `DEEPWIN_BUILDER_IMAGE` permite trocar a origem.
  **Espelho publicado após o login do mantenedor:**
  `ghcr.io/eduardodaluz/linyaps-builder@sha256:9170f635112d5068ef815d6e55d6bd3969e668151bd31a33ca48086f53fd372a`.
  O workflow usa esse digest como padrão. **A imagem é pública e o pull
  anônimo pelo digest passou**, usando configuração Docker temporária vazia.
  Procedimento em [packaging/linyaps-builder.md](packaging/linyaps-builder.md).
- **Fase 3 (portátil `.tar.xz`): concluída, aceita em imagem limpa, snapshot
  de VM com sessão gráfica e [CI](https://github.com/eduardodaluz/deepWin/actions/runs/39179478620).** Candidato local
  `DeepWin-1.1.0-amd64-portable.tar.xz`, SHA-256
  `2c4130b5bb0bb9ef8ed8751b0bb6aac9a35f39f5abc4ea5784a3ed1861a2038e`.
  Reutiliza o staging CMake e os runtimes nativos Qt/DTK/Python do Deepin 25;
  não é autocontido. A aplicação abre por `./deepwin`; menu opcional por
  `./register-menu` e `./unregister-menu`, preservando personalizações.
  Build, verificação limpa, menu seguro, movimentação/remoção, restauração
  real e rollback entre versões foram testados; consultar o último adendo.
- **Publicação autorizada pelo mantenedor** após o aceite dos três formatos:
  primeiro Release **1.1.0**, com `.deb`, `.uab` e `.tar.xz` juntos.
  [Notas finais](packaging/release-notes-1.1.0.md) e workflow de publicação
  preparados. O push da tag `v1.1.0` dispara a validação dos artefatos
  imutáveis dos três runs aprovados, criação de rascunho, upload e conferência
  dos sete anexos antes de publicar. Não reutiliza credenciais do Docker.
  Até a execução do workflow, não considerar a publicação concluída.
- Ambiente preservado: VM de aceite **desligada** em `~/deepwin-vm/`
  (quando no ar, SSH porta 2222, usuário `deepwin` com sudo NOPASSWD;
  para tocar a sessão gráfica por SSH, exportar `DISPLAY=:0`,
  `XDG_SESSION_TYPE=x11`, `XDG_RUNTIME_DIR=/run/user/1000` e
  `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`; grab do teclado
  no QEMU é Ctrl+Alt+G). Volume Docker `ll-builder-cache` (~2 GB com Base e
  Runtime develop) mantém os builds `--offline` rápidos. Em `/tmp` da VM há
  um backup do stub de unidade removido (`/tmp/stub-backup/`), descartável.
- Monitores de CI sem autenticação: a API pública rate-limita a 60 req/h —
  pollar a cada 5-8 minutos. Logs de run exigem auth; o workflow do UAB já
  publica a cauda do `build.log` como anotação de erro, legível sem auth em
  `check-runs/{id}/annotations`.

Restrições permanentes: licença MIT; e-mail `eduardo.r.luz@gmail.com` é
público por escolha expressa; ordem dos formatos `.deb` → Linyaps →
portátil; nunca embutir caminhos pessoais, backups, chaves ou downloads do
Claude em pacotes ou documentação pública; preservar dados XDG, wrappers e
unidades customizadas — conflitos se informam, nunca se sobrescrevem.

Sequência sugerida para a próxima passagem:

1. Concluir a publicação autorizada e conferir o Release público `v1.1.0`,
   com os três instaladores, três checksums individuais e `SHA256SUMS`.
2. Itens menores registrados: reboot completo da VM como teste
   complementar (autologin não confirmado), decisão de submeter o `.uab` à
   loja Linyaps (etapa distinta da geração do pacote), e reavaliar a
   privatização de `XDG_*_HOME` quando sair a próxima minor do linyaps
   (1.15+).

## Funcionalidades anteriores ao empacotamento

O painel usa C++ com DTK 6 Widgets/Qt 6, conforme a exigência de interface
nativa do SDK Deepin. O backend Python consulta e aplica as integrações.
Os nomes estabelecidos são `DeepWin`, comando `deepwin` e identificador
`devedu.deepin-configs`.

Já haviam sido implementados e enviados ao repositório:

- Colagem ao confirmar com Enter um item do histórico Win+V, com tratamento de
  terminais usando Ctrl+Shift+V e serviço de usuário para a integração X11.
- Painel para habilitar/desabilitar dez recursos, incluindo atalhos de áreas
  de trabalho/monitores e captura de área Win+Shift+S.
- Consulta e controle do serviço/timer de download de paisagens, preservando
  a imagem atual ao desativar o download.
- Gerenciamento do `zclaude`: stable, versões anteriores, instalação existente
  e desfazer a última troca, com versões isoladas. A chave da Z.AI permanece
  fora do repositório e não deve ser lida nem copiada pelo empacotamento.
- Miniaturas ao clicar em grupos de janelas da dock, reutilizando o recurso
  nativo por uma sobreposição QML por usuário, com restauração.
- Vírgula como decimal na calculadora Deepin mediante plugin Qt genérico,
  restrito à aplicação/campos esperados e controlado por flag por usuário.
  A integração preserva os caminhos de tema Qt ao iniciar pelo Linglong.
- Backups do estado original e restauração das alterações pelo painel.

O último commit de funcionalidade antes do plano foi
`9b62d66673a584fadcb035b9b9cd58f385ed288b`, referente à calculadora.
Os detalhes das integrações estão no [README](README.md) e em
[analise-gui-deepin.md](analise-gui-deepin.md).

## O que foi implementado na fase 1, ainda sem commit

### Build e pacote

- `VERSION` define `1.1.0`; `debian/changelog` define `1.1.0-1`.
- `LICENSE` contém MIT, copyright 2026 eduardodaluz.
- `CMakeLists.txt` compila a GUI DTK e o plugin da calculadora, configura
  instalação em staging e registra testes Python e Qt no CTest.
- `bin/build-deepwin` usa CMake quando o SDK está instalado e mantém o fallback
  anterior de compilação com o SDK em cache para desenvolvimento.
- `debian/` contém control, rules, changelog, copyright, formato de fonte,
  documentação, manpage e uma justificativa de override do Lintian.
- O pacote instala `/usr/bin/deepwin`, componentes privados em
  `/usr/lib/deepwin/` e metadados de desktop em `/usr/share/`.
- `packaging/` contém launcher, desktop entry, metainfo, manpage, templates de
  unidades systemd e Dockerfiles de build/validação.
- `bin/build-deb` prepara uma cópia dos fontes por lista permitida, gera
  `.deb`, `.buildinfo`, `.changes`, relatório Lintian e checksums em `dist/`.
  Suporta build nativo, `--container`, `--reuse-image` e `--output`.
  Usa lock para evitar builds concorrentes no mesmo checkout.
- A imagem de build usa a base oficial Deepin 25 com digest fixado. Foi
  necessário obter o Lintian do repositório `beige` antes de configurar
  `crimson` para o SDK: no repositório atual faltava uma dependência Perl do
  Lintian. Essa preparação fica no container, sem instalar SDK no host.
- O pacote de execução não exige Git, Ansible, CMake ou compilador. As
  dependências de runtime estão em `debian/control`; Node/npm são sugeridos
  para a integração que precisa deles.
- `.github/workflows/deb.yml` prepara build, verificação e upload de artefatos.
  **Ainda não foi enviado nem executado no GitHub.**

### Recursos persistentes, estado e migração

- `resources.json` lista somente recursos distribuídos do programa.
  `gui/resources.py` resolve checkout/pacote e cria uma cópia persistente dos
  helpers em `$XDG_DATA_HOME/devedu.deepin-configs/runtime/releases/<hash>/`.
  A troca de `runtime/current` é atômica; versões anteriores são preservadas.
- Há validação de propriedade, manifesto e hashes, além de rejeição de
  caminhos/symlinks indevidos. Caches Python legítimos não invalidam o runtime;
  o backend também evita gravar bytecode.
- Essa cópia permite que integrações já ativadas e o comando
  `runtime/current/bin/deepwin-restore` sobrevivam à remoção da GUI.
  **A verificação automatizada dessa remoção ainda não chegou a executar.**
- `gui/user_services.py` prepara unidades de colagem/wallpaper por usuário
  somente ao ativar o recurso, com snapshots, identificação de propriedade e
  rollback. Unidades personalizadas ou modificadas devem ser preservadas.
- `gui/backend.py` distingue unidade ausente de erro de consulta, verifica
  requisitos nativos e permite preparar integrações numa instalação nova.
  A ausência do schema de screenshots é tratada antes de chamar Gio.Settings,
  evitando abortar o processo em ambientes sem o desktop completo.
- Estado e backups continuam nos diretórios XDG por usuário. O formato de
  `originals.json` foi preservado; `schema.json` identifica a versão do estado
  e formatos futuros desconhecidos são recusados.
- Há migração do estado legado ao abrir o launcher instalado e antes de
  operações mutáveis no backend. **Esses últimos ajustes foram feitos depois
  do último build/teste completo e precisam ser revalidados.**
- Calculadora separa o plugin distribuído da flag gravável por usuário; dock e
  `zclaude` passam a resolver helpers pelo runtime persistente.
- `bin/deepwin` considera checkout, pacote instalado e instalação local;
  `deepwin.yml` foi atualizado para instalar os novos recursos na modalidade
  por código-fonte.
- Consultar status deve continuar sem ativar recursos ou criar backups.
  Instalar o pacote deve apenas instalar o aplicativo; a ativação é explícita
  no painel.

### Mapa das alterações locais

Arquivos rastreados modificados antes desta documentação:

```text
.gitignore                 README.md                  analise-gui-deepin.md
bin/build-deepwin          bin/deepwin                bin/deepwin-calculator
bin/zclaude                deepwin.yml                gui/backend.py
gui/calculator_decimal.py  gui/dock_preview.py        gui/main.cpp
tests/test_config_manager.py
```

Arquivos/diretórios novos da implementação:

```text
.dockerignore             .github/workflows/deb.yml  CMakeLists.txt
LICENSE                   VERSION                    resources.json
bin/build-deb             bin/deepwin-restore        bin/verify-deb
debian/                   packaging/                 gui/resources.py
gui/user_services.py      tests/test_packaged_resources.py
```

Esta passagem também adiciona este documento e atualiza o status inicial do
plano e as ressalvas de validação no README. Para o inventário exato, usar
`git status --short`, incluindo os arquivos não rastreados.

## Verificações já realizadas

Ambiente de referência: Deepin 25 amd64, X11, dde-shell 2.0.52, Qt 6.8 e DTK 6.
Os resultados abaixo são de execuções anteriores à interrupção; não significam
que os últimos ajustes já foram incorporados ao pacote existente.

| Verificação | Resultado observado |
| --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests -q` | 113 testes passaram na última execução completa |
| CTest no build do pacote | 2/2 testes passaram: suíte Python e teste Qt da calculadora |
| `./bin/build-deb --container --reuse-image` | Pacote gerado com sucesso |
| Lintian | Sem erros ou avisos não tratados; um override justificado por não ser upload ao Debian com ITP |
| GUI do pacote extraído, na sessão Deepin existente, com `QT_QPA_PLATFORM=offscreen` e `--smoke-test --check-integrations` | PASS, dez recursos consultados |
| Execução em imagem limpa sem ferramentas de desenvolvimento | A ausência de Git/SDK/compilador/Ansible foi confirmada; a etapa seguinte falhou, conforme abaixo |

Os testes adicionados cobrem cópia/atualização e integridade do runtime,
preservação de customizações, ausência de efeitos de status, importação sem os
fontes originais, preparação/rollback de serviços, schema futuro e ausência de
schema Gio. O teste Qt cobre campos aceitos, modificadores, keypad, outra
aplicação, sequência de teclas e desativação por flag.

**Cuidado com o isolamento:** o ambiente do agente pode herdar `XDG_DATA_HOME`
real. Os testes de Manager foram corrigidos para definir `XDG_DATA_HOME` e
`XDG_CONFIG_HOME` temporários; não remover essa proteção. Antes da correção,
algumas execuções puderam preparar cópias de recursos do programa no diretório
de dados real, sem ativar ajustes.

Na última consulta da sessão real havia dez recursos ativos e duas entradas
de restauração. As unidades existentes do usuário não foram substituídas ou
desativadas pelo trabalho de empacotamento. A instalação local da GUI foi
atualizada durante o desenvolvimento, mas não está garantidamente sincronizada
com as últimas edições. O `.deb` **não foi instalado globalmente no host**.

## Falha pendente na validação em imagem limpa

`bin/verify-deb` usa `packaging/Dockerfile.test-deb` e
`packaging/verify-installed.sh` para instalar, abrir, reinstalar e remover o
pacote numa imagem descartável sem montar a pasta pessoal do host.

A execução parou em `/usr/bin/deepwin --version`, com erro Qt de conexão ao
display/plugin `xcb` e saída 134. A construção de DApplication ocorre antes do
tratamento de `--version`. O script só define `QT_QPA_PLATFORM=offscreen` na
**linha seguinte**, do smoke test.

O diagnóstico aponta para a configuração headless do teste. A GUI extraída já
abriu no teste da sessão existente; não concluir que o aplicativo falha numa
sessão gráfica com base apenas nesse erro.

Possíveis correções, **ainda não aplicadas**:

1. Exportar `QT_QPA_PLATFORM=offscreen` antes de todas as chamadas da GUI no
   script de verificação; usar sessão D-Bus privada se necessário.
2. Alternativamente, tratar a consulta simples de versão antes de inicializar
   Qt, mantendo o comportamento consistente entre launchers.

Após corrigir, executar o fluxo inteiro. A reinstalação, a remoção e a
disponibilidade do comando persistente de restauração **não foram validadas
por esse fluxo**, pois ficam depois da linha que falhou. A etapa final atual
usa `deepwin-restore --help`; isso comprova disponibilidade/importação do
helper, não a restauração funcional de todos os recursos numa sessão real.

## Artefatos e evidências locais

Os diretórios `.build/` e `dist/` são ignorados pelo Git. No momento da passagem:

```text
dist/devedu.deepin-configs_1.1.0-1_amd64.deb                 ~72 KiB
dist/devedu.deepin-configs-dbgsym_1.1.0-1_amd64.deb          ~696 KiB
dist/*.deb.sha256
dist/devedu.deepin-configs_1.1.0-1_amd64.buildinfo
dist/devedu.deepin-configs_1.1.0-1_amd64.changes
dist/deepwin-lintian.txt
.build/deb-stage/                                         extração de teste
```

Logs temporários existentes na máquina de trabalho:

- `/tmp/deepwin-deb-final-build.log`: último build bem-sucedido.
- `/tmp/deepwin-deb-verify.log`: falha de display na validação limpa.

Imagem local de build: `deepwin-deb-build:1.1.0`, ID curto `e3513e609922`.
Não havia build ou validação ativo no momento da passagem. Não remover imagens,
containers ou caches de outros trabalhos para continuar este projeto.

O pacote existente é anterior às últimas edições do launcher e da migração do
backend. A preparação normalizada do contexto Docker de `bin/build-deb` também
precisa de validação pelo caminho completo sem `--reuse-image`.

## Sequência sugerida na passagem de 17/10 (executada; mantida como registro)

1. Ler este documento, o diff e os arquivos novos. Preservar as escolhas MIT,
   e-mail público e ordem dos três formatos.
2. Corrigir a execução headless de `bin/verify-deb` e revisar a migração recente.
3. Executar novamente a suíte Python, reconstruir o pacote e executar
   `./bin/verify-deb` até passar o fluxo completo. Não editar fontes durante a
   geração do candidato final: o build usa uma cópia dos fontes.
4. Validar também `./bin/build-deb --container` sem reutilizar a imagem, pois
   esse é o caminho usado pelo workflow. Manter SDK/dependências de build no
   container, sem instalar ferramentas globalmente no host sem necessidade.
5. Validar instalação nova, atualização e restauração numa VM Deepin 25 com
   sessão gráfica completa, incluindo unidades personalizadas, migração
   legada, dock e calculadora. O container não cobre esse aceite.
6. Revisar ABI do plugin da calculadora antes de ampliar plataformas. A
   referência testada é Qt 6.8 do Deepin 25; não foi implementada uma garantia
   genérica para outras versões menores do Qt.
7. Atualizar os checklists do plano conforme a evidência, revisar documentação
   e conteúdo do pacote, e então preparar commit/push e eventual release.
   A automação do GitHub ainda precisa passar depois do envio.
8. Iniciar Linyaps e portátil somente após concluir os critérios anteriores
   definidos no [plano](plano-distribuicao-deepwin.md).

Não embutir caminhos pessoais, backups, chaves, downloads do Claude ou SDK em
pacotes/documentação pública. O e-mail do mantenedor é público por escolha
expressa. Preserve dados XDG, wrappers e unidades customizadas; conflitos devem
ser informados, sem sobrescrever alterações do usuário.

## Adendo de retomada — 17/10/2026, mesma data

A sequência sugerida foi retomada e os passos 1 a 4 foram concluídos.

Correções aplicadas:

- `gui/main.cpp`: `--version` e `-v` respondem antes de inicializar o Qt e sem
  exigir display, com saída `DeepWin <versão>`; o parser Qt não trata mais
  versão. `--help` continua exigindo sessão gráfica (o parser Qt precisa da
  aplicação construída) e permanece fora do escopo desta fase.
- `packaging/verify-installed.sh`: exporta `QT_QPA_PLATFORM=offscreen` antes de
  todas as chamadas da GUI.
- `gui/backend.py`: a restauração de backup com arquivos de serviço (serviço
  carregado e unidade gerenciada) passou a recusar sobrescrever uma unidade
  customizada quando o registro do painel foi removido — antes, o
  `restore_files` gravaria por cima. Mesmo padrão já usado no ramo `absent`.
- `tests/test_packaged_resources.py`: teste novo para o caso acima. Detalhe
  descoberto ao escrevê-lo: o backup segue política de primeira alteração, então
  um backup com `files` exige que a unidade gerenciada exista antes da primeira
  mudança — o teste a prepara com `user_services.prepare` direto.

Verificações nesta retomada:

| Verificação | Resultado |
| --- | --- |
| Suíte Python | 114 testes passando (113 anteriores + o novo) |
| `./bin/build-deb --container --reuse-image` | Pacote gerado |
| `./bin/verify-deb` | Fluxo completo com os cinco PASS, incluindo reinstalação, remoção e `deepwin-restore --help` pelo runtime preservado |
| `./bin/build-deb --container` sem reuso de imagem | Imagem reconstruída do zero (256 pacotes), CTest 2/2, Lintian sem erros |
| `deepwin --version` do pacote extraído, sem `DISPLAY` e sem offscreen | `DeepWin 1.1.0`, saída 0 |
| Reprodutibilidade do `.deb` | Builds sucessivos geraram bytes idênticos (mesmo `SOURCE_DATE_EPOCH` do changelog); confirmado pelas camadas `CACHED` do Docker por hash de conteúdo |

O pacote revalidado contém as últimas edições de launcher e migração que o
`.deb` anterior não tinha.

Pendências inalteradas: aceite em VM Deepin 25 com sessão gráfica completa
(passo 5), revisão da ABI do plugin da calculadora (passo 6), commit/push e
execução do workflow no GitHub (passo 7), fases 2 e 3 (passo 8). Nada foi
publicado: sem release, tag ou push. Os arquivos de log citados acima foram
atualizados em `/tmp`.

## Aceite em VM — 18/10/2026

O passo 5 foi executado numa VM Deepin 25.2.0 amd64 limpa: KVM no host, ISO
`25.2.0` verificada contra o `SHA256SUMS` oficial, disco em `~/deepwin-vm/`
(forá do repositório), sessão X11 real, Solid ativo e `dde-shell` 2.0.49. O
pacote foi instalado como 1.1.0-1 e atualizado até 1.1.0-3 com recursos ativos.

Três falhas reais que só o aceite em sessão completa expôs, corrigidas nos
pacotes 1.1.0-2 e 1.1.0-3:

1. **Duas gerações do serviço de atalhos.** Em instalação nova do 25.2.0,
   `org.deepin.dde.Keybinding1` é servido pelo `dde-session-daemon`
   (identificador curto `screenshot`, `GetShortcut(id, tipo)` com resposta em
   JSON, `ModifiedAccel`/`LookupConflictingShortcut`), não pelo plugin do
   dde-shell com que o backend foi escrito. O recurso de captura quebrava com
   erro de assinatura D-Bus. Compatibilidade nas duas gerações, com detecção
   por `TypeError` e espera por releitura, porque o daemon antigo aplica
   `ModifiedAccel` de forma assíncrona e a confirmação imediata falhava às
   vezes. O daemon antigo também não persiste no schema dsettings: após
   reiniciar a sessão, o serviço pode voltar à combinação anterior.
2. **Falso "personalizado" na prévia da dock.** Consultas novas reconstruíam
   o `DockPreview` com o helper padrão em vez do caminho do runtime persistente,
   e o drop-in gravado apontando para o runtime era tratado como personalização.
   O `Manager` passou a resolver o caminho do runtime no construtor.
3. **Recusa de restauração sobre unidade customizada** (correção da retomada
   anterior) — validada agora em serviço real.

Resultados observados na VM:

| Cenário | Resultado |
| --- | --- |
| Instalação nova por apt sobre Solid (`usr-overlay` somente leitura) | Só arquivos; nenhum estado criado; escrita direta em `/usr/lib/deepwin` recusada fora do gerenciador de pacotes |
| Smoke test na sessão real com `--check-integrations` | PASS, 10 recursos, exit 0 |
| Ativação dos 10 recursos na sessão real | Unidades ativas, timer horário, 10 entradas de backup, runtime persistente |
| Interação humana | Prévias em grupo na dock; vírgula na calculadora reabrindo pelo menu; recorte Win+Shift+S; colagem Win+V + Enter, inclusive em terminal; workspaces com Ctrl+Win+←/→ usando o grab Ctrl+Alt+G do QEMU |
| Atualização 1.1.0-1 → 2 → 3 com recursos ativos | Backups, runtime, unidades, flags e wrapper preservados byte a byte |
| Unidade customizada antes de restaurar | Recusa com backup preservado; conteúdo do usuário intacto |
| Migração com estado antigo e novo simultâneos | Recusa informada por CLI e pelo launcher, exit 1 |
| Remoção com ajustes ativos | Binários removidos; colagem ativa via runtime; `deepwin-restore wallpaper` executou restauração real (unidades do timer removidas, imagem atual preservada); reinstalação seguinte normal |
| `bin/verify-deb` do candidato 1.1.0-3 | Cinco PASS, camadas reexecutadas |

Testes unitários subiram de 114 para 116 (compatibilidade de gerações e
resolução do helper). Testes interativos não reproduzíveis na VM: atalho de
troca de monitor (`Shift+Win+←/→`) exige segundo monitor.

Resta para concluir a fase 1: nada pendente de validação. A implementação
inteira foi commitada e enviada (`0a2f879`), e o workflow do GitHub passou a
executar build e verificação a cada push. Duas falhas do workflow na máquina
limpa foram corrigidas no caminho: o `packaging/Dockerfile.deb` fonte estava
engolido pela regra `*.deb` do `.gitignore` (`00c0ddb`) e um diretório `cmake/`
vazio, que o git não versiona, constava da lista de cópia do `bin/build-deb`
(`95858d6`). A execução verde cobre build em container, verificação em imagem
limpa e o artefato `deepwin-deb-amd64` publicado no run. A revisão da ABI do
plugin da calculadora foi registrada na [análise](analise-gui-deepin.md):
superfície estável do Qt 6, metadados Qt 6.8, carrega em qualquer runtime
≥ 6.8 e recusa se degrada sem quebrar; condição de reavaliação é mudança de
major do Qt ou alvo com Qt anterior a 6.8. Um aviso do Lintian no changelog
(`wrong-day-of-week`) foi corrigido: 18/10/2026 é domingo. O `--help` da GUI
continua exigindo sessão gráfica, fora do escopo desta fase.

## Fase 2, Linyaps — 18/10/2026

A fase 2 foi disparada com subagentes em três frentes paralelas: pesquisa do
tooling Linyaps atual, pesquisa do modelo de sandbox e inventário dos
touchpoints do repositório. A L1 (prova de integração antes do empacotamento)
foi concluída no mesmo dia.

Evidências da L1, registradas na [matriz de acesso](matriz-acesso-linyaps.md):

- Leitura do código-fonte do linyaps na tag 1.14.3 (a mesma do Deepin 25
  local): o sandbox monta o socket do D-Bus de sessão do host sem filtro, o
  `$HOME` real em leitura/escrita no mesmo caminho, dconf gravável,
  X11/Wayland, rede compartilhada e `/run/host/rootfs` (raiz do host em
  leitura). Sem facetas/permissões declaráveis no manifesto.
- Sonda descartável dentro de um sandbox real via
  `ll-cli run org.deepin.calculator`: `systemctl --user` alcançou o manager do
  host por fallback ao bus (listou unidades do host, leu unidade fornecida por
  app linyaps, aceitou `daemon-reload`); escritas em `~/.config` e
  `~/.local/share` persistiram no host com os mesmos timestamps;
  `RequestName` aceito; QML da taskmanager legível em `/run/host/rootfs`.
- `~/.ssh`, `~/.gnupg` e `~/.linglong` são mascarados; `XDG_RUNTIME_DIR` do
  app é privado; sem sudo/docker dentro do container — irrelevante ao painel.
- Risco registrado: a FAQ oficial declara intenção de privatizar `XDG_*_HOME`
  por app; no 1.14.3 o gatilho é a existência de `~/.linglong/<id>/config` —
  nenhum fluxo do painel cria esse diretório. Reavaliar em cada minor do
  linyaps.

Decisão L1: **acesso direto aprovado** — a arquitetura atual funciona dentro
do sandbox sem ponte. Unidades fornecidas pelo pacote
(`$PREFIX/lib/systemd/user`, com `ExecStart` reescrito para `ll-cli run`)
ficam registradas como endurecimento futuro.

Spike de build: builder oficial em Docker
(`registry.cn-hangzhou.aliyuncs.com/linyaps/builder:1.13.8_amd64`,
`--privileged`, cache em volume nomeado); slots `org.deepin.base/25.2.2` →
25.2.2.8 e `org.deepin.runtime.dtk/6.7.0` → 6.7.0.50 resolvidos no repo
estável (a doc lista 25.2.2, os apps reais da deepin usam a série 6.7.0). O
builder puxa sozinho os módulos develop com toolchain completa — o truque
`apt --download-only` dos apps da deepin é desnecessário. O apt dentro do
sandbox de build mostrou-se não confiável (indexes parciais), e commit de
layer com estado sujo do apt leva dezenas de minutos.

Implementação (L2 local, pendente de aceite em VM):

- `linglong.yaml` na raiz, slots fixados, script de build que extrai
  `pydeps/`, compila por CMake contra `/runtime` e remove os artefatos para o
  delta do layer ficar mínimo.
- `bin/build-uab`: staging, pré-download dos debs beige das dependências
  Python (versões fixadas, casando com os slots), build/smoke/export no
  Docker, checksum em `dist/`.
- O runtime Linyaps não traz `python3-dbus` nem `gi`; o `.deb` os obtém por
  `Depends`. O pacote Linyaps embarca cópias podadas (51 arquivos,
  `cpython-312`, beige 2.80) listadas no novo `files_optional` do
  `resources.json`, instaladas em `lib/deepwin/pydeps` por um bloco
  condicional do CMake e materializadas no runtime por usuário pelo mecanismo
  existente — sem mudança no protocolo de releases; no `.deb` as entradas
  opcionais ausentes são silenciosas.
- `bootstrap_runtime_python()` em `gui/backend.py` e no helper de colagem:
  insere `pydeps/dist-packages` no `sys.path`, pré-carrega a biblioteca
  nativa em escopo global (sem `LD_LIBRARY_PATH`) e prepara
  `GI_TYPELIB_PATH` antes das importações tardias de `dbus`/`gi`. No `.deb`
  é no-op. O `deepwin-restore` é coberto pelo bootstrap do backend.
- `Native.host_tool()`: os helpers executam no host, então as checagens de
  `xdotool`/`curl`/`file`/`gsettings` consultam primeiro
  `/run/host/rootfs/usr/bin` quando existente.
- `resolve_system_dir()` na prévia da dock: QML lido de
  `/run/host/rootfs/usr/share/dde-shell` quando o caminho do sistema não
  existe (container), sem mudança fora dele.
- `packaging/extract-pydeps`: monta `pydeps/` dos debs pré-baixados com o
  manifesto como lista autoritativa; entrada listada e ausente falha o build.
- Seletor de versões do Claude fica indisponível no pacote Linyaps (sem
  `npm` no sandbox); o wrapper `zclaude` roda no host e não é afetado.

Resultados: 125 testes Python (eram 116), cobrindo bootstrap, `host_tool`,
fallback do dock e extração; candidato
`devedu.deepin-configs_1.1.0.0_x86_64_main.uab` (211 MiB, sha256
`8a68fdd814ea1719bf6b682d62fd15fcb957e2eb4c4dc029d2c2fe57505e53e4`) gerado
por `bin/build-uab --offline`, com smoke de importação `dbus`/`gi` e
`deepwin --version` aprovados dentro do sandbox; rebuild do `.deb` 1.1.0-3 e
`bin/verify-deb` reexecutados na imagem limpa — PASS, zero regressão da
fase 1. Pendências da L2: instalar e exercitar o `.uab` em VM Deepin 25
limpa (incluindo a prova fina de X11 do helper de colagem e a persistência
de estado após reinício do container) e a decisão do mantenedor sobre publicar
o workflow Linyaps na CI. Commit local sem push.

## Aceite L2 na VM — 18/10/2026 (mesma data, resultados)

A VM de aceite (Deepin 25.2.0, Linyaps **1.13.7** — mais antiga que a 1.14.3
de desenvolvimento, o que valida a faixa inferior) recebeu o `.uab` com o
`.deb` 1.1.0-3 ainda instalado e recursos ativos da fase 1.

Instalação e descoberta de distribuição:

- `ll-cli install ./arquivo.uab` **não puxa Base/Runtime do repositório**:
  o instalador procura os refspecs em `local:` e falha
  (`Refspec 'local:main/org.deepin.runtime.dtk/6.7.0.50/...' not found`) se o
  runtime não estiver no OSTree local. O runtime pôde ser instalado antes por
  ref (`sudo ll-cli install org.deepin.runtime.dtk/6.7.0.50`, do mirror
  estável), mas a decisão tomada foi **mudar o pin para
  `org.deepin.runtime.dtk/25.2.2`**: uma instalação stock do Deepin 25 já
  carrega a série 25.2.2 (a calculadora da VM roda nela), o develop existe no
  repo estável e o `.uab` passa a instalar sem passo extra. O usuário precisa
  de `sudo` para instalar UAB ("Error 9: not authorized" sem ele).
- A calculadora da VM usa `base/25.2.2` + `runtime.dtk/25.2.2`, igual ao novo
  pin — o plugin da calculadora compila contra o Qt da mesma série em que a
  calculadora executa.

Resultados dentro do sandbox (backend via `ll-cli run`, ambiente de sessão
exportado no SSH):

| Verificação | Resultado |
| --- | --- |
| `deepwin --version` e importação `dbus`/`gi` (pydeps) dentro do sandbox | PASS nos dois builds (6.7.0 e 25.2.2) |
| Status completo pelo sandbox | **10/10 recursos disponíveis** após o fix de `XDG_DATA_DIRS`; `restore_count: 9` — os backups do `.deb` compartilhados |
| Prévia da dock pelo sandbox | disponível e refletindo a ativação do `.deb`, com QML lido de `/run/host/rootfs` |
| Escrita: `set clipboard on` pelo sandbox | systemd do **host** aplicou (serviço `active` + `enabled`, unidade no home real apontando ao runtime persistente) |
| Unidade externa modificada (stub `ExecStart=/bin/true` com hash divergente do marcador) | recusada com "A unidade contém personalizações" — proteção de ownership funcionando através do sandbox |

Falhas encontradas e corrigidas no caminho:

1. **Catálogos do host invisíveis no rootfs do app** (calculadora, captura e
   wallpaper indisponíveis no primeiro status): schemas do dsettings em
   `/usr/share` do host e o launcher da calculadora em
   `/var/lib/linglong/entries/apps/share` do host (o catálogo de desktops do
   Linyaps 1.13.x fica sob o segmento `apps`; o menu do DeepWin já nasce
   registrado nele). Correção única no bootstrap: quando
   `/run/host/rootfs` existe, prefixar `usr/share` e
   `var/lib/linglong/entries/share` do hospedeiro em `XDG_DATA_DIRS` do
   processo (backend e helper de colagem; no `.deb` é no-op porque o caminho
   não existe).
2. **CI do Linyaps falhou no runner do GitHub** (Debian passou no mesmo
   push): os logs exigem autenticação e as anotações só diziam "exit code
   1". O workflow agora tecla o build em `build.log`, emite a cauda como
   `::error::` (vira anotação legível pela API) e usa `pipefail` para o
   `tee` não mascarar o resultado.

Provas ainda pendentes da L2: provas visuais humanas (prévias da dock,
vírgula na calculadora, atalhos) com o grab `Ctrl+Alt+G`, persistência de
estado após reinício do container, e remoção do app Linyaps preservando
serviços e helpers. Testes unitários: 126.

Remoção do container validada por SSH na sequência: `ll-cli uninstall`
remove o app, o serviço de colagem **segue ativo e habilitado** (executa do
runtime persistente no home), os helpers e o `deepwin-restore` continuam
funcionais sem o aplicativo, e a reinstalação seguinte é limpa. A
persistência "após reinício do container" é inerente ao modelo — cada
`ll-cli run` é um container novo, e os mesmos estados foram lidos
consistentemente entre execuções. Reboot completo da VM ficou para a rodada
manual do mantenedor (sem certeza de autologin, o reboot derrubaria a sessão
que os testes usam).

Provas visuais humanas confirmadas pelo mantenedor na sessão da VM
(grab `Ctrl+Alt+G`): DeepWin aberto pelo menu a partir do app Linyaps, dez
switches refletindo os estados reais, vírgula decimal na calculadora
reabrindo pelo menu, prévia ao clicar em grupo da dock, recorte
Win+Shift+S, colagem Win+V + Enter, e workspaces Ctrl+Win+←/→. Com isso,
todos os critérios de aceite da fase 2 estão satisfeitos, pendendo apenas o
job do GitHub Actions para o `.uab` no commit `e0877d1` (o workflow passou a
publicar o log de falha como anotação depois do primeiro run cego).

Encerramento do dia: o job Debian ficou verde em todos os pushes, mas o job
Linyaps falhou nos três (`0f7199d`, `e0877d1`, `ed6a057`) sempre no mesmo
ponto — a cauda do log publicada como anotação mostra o `docker pull` de
`registry.cn-hangzhou.aliyuncs.com/linyaps/builder` começando e o runner
morrendo ali. O mesmo `bin/build-uab` passa na máquina local, então a falha
é o registro da Aliyun acessado dos runners americanos do GitHub, não o
build. Correção recomendada para a próxima passagem: espelhar a imagem do
builder para o ghcr.io da conta do mantenedor (`docker tag` + `docker push`
a partir desta máquina) e acrescentar um override de ambiente (ex.
`DEEPWIN_BUILDER_IMAGE`) em `bin/build-uab` para o CI usá-lo; em paralelo,
separar o pull em passo próprio com retentativas. A fase 2 segue aceita em
VM; o único item aberto é esse espelhamento de imagem na CI.

## Retomada da CI Linyaps — 18/10/2026, à noite

A base remota e local era `471a2dd`. A última execução pública consultada,
[39149160166](https://github.com/eduardodaluz/deepWin/actions/runs/39149160166),
confirmou a falha durante o download das camadas do builder, antes de
compilar. `gh` não está instalado e não há configuração de login Docker no
GHCR. O acesso SSH ao GitHub e a conectividade HTTPS com GHCR funcionam
fora do sandbox. Foi pedido ao mantenedor executar `docker login ghcr.io
-u eduardodaluz` em outro terminal; não solicitar o token na conversa.

Implementação desta retomada:

- `bin/build-uab` aceita `DEEPWIN_BUILDER_IMAGE`, informa a imagem selecionada
  no log e fixa o padrão no digest observado da imagem oficial 1.13.8 amd64
  (`sha256:1ef5b6244f3a7f8b2227e88d171bd0b6cda7cb7c4310a609a70a70e35f08b85b`).
  O lock passa a cobrir também a preparação do cache dos debs Python.
- O workflow usa a variável de repositório homônima, com fallback para a
  origem oficial enquanto o espelho não estiver publicado. O pull foi
  separado em passo com três tentativas de até 180 s, kill após mais 15 s,
  e pausa de 15 s entre falhas. `pull.log` e `build.log` viram artefatos
  mesmo em falha; as anotações escapam `%` e CR e aceitam linha final sem
  newline ou ausência de um dos logs.
- `packaging/linyaps-builder.md` documenta publicação do espelho, visibilidade
  pública, validação anônima e seleção por digest. README corrigido para o
  runtime 25.2.2, instalação por sudo e aceite em VM já concluído.

Verificações realizadas:

| Verificação | Resultado |
| --- | --- |
| Suíte Python | 126 testes, todos passando |
| Scripts Bash extraídos do workflow | Sintaxe válida; simulações cobriram sucesso imediato, falha seguida de sucesso e três falhas com saída 1 |
| Anotações de falha | Percentuais, CR, linha final incompleta e logs ausentes tratados corretamente |
| Imagem oficial × tag local GHCR | Mesmo ID `30bb6af47cf2e1a8d56700900933934733383c6b286c4bf6c09ef3d0f6d5b6c5` |
| Build completo com `DEEPWIN_BUILDER_IMAGE=ghcr.io/eduardodaluz/linyaps-builder:1.13.8_amd64 ./bin/build-uab --offline` | PASS, incluindo `pydeps OK`, `DeepWin 1.1.0` e exportação UAB |

O novo build local substituiu o arquivo de mesmo nome em `dist/`; SHA-256
`c78852d7e9a89300a166d3e04a4e56dd133765e45e55909435480905e533fc35`.
O hash do candidato aceito em VM permanece registrado no início do documento;
a reconstrução desta retomada não teve novo aceite gráfico. Log completo:
`/tmp/deepwin-uab-ci-fix-build.log`.

Pendente: autorização explícita para enviar os commits locais à `main`,
publicação efetiva do espelho (aguarda autenticação GHCR), seleção na CI e
confirmação de run verde. A revisão automática rejeitou o comando
`git push origin main` por considerar o envio à branch padrão uma alteração
remota que requer autorização explícita; nenhum push foi realizado.
A tag GHCR local **não comprova** publicação nem pull pela rede. Fase 3
não iniciada e nenhum Release/tag publicado.

## Espelho publicado após autenticação — 18/10/2026

O mantenedor concluiu `docker login ghcr.io -u eduardodaluz` usando um PAT
clássico com `write:packages`, e o push de
`ghcr.io/eduardodaluz/linyaps-builder:1.13.8_amd64` terminou com sucesso.
O digest retornado pelo GHCR foi
`sha256:9170f635112d5068ef815d6e55d6bd3969e668151bd31a33ca48086f53fd372a`.
O digest do manifesto mudou no destino; a identidade do conteúdo é conferida
pelo ID Docker da imagem. O pull autenticado pelo digest teve sucesso, e o
ID retornado coincide com o original:
`30bb6af47cf2e1a8d56700900933934733383c6b286c4bf6c09ef3d0f6d5b6c5`.

O teste com `docker --config <diretório temporário vazio> pull <digest>`
retornou `unauthorized`: o pacote nasceu privado. Foi solicitado ao
mantenedor abrir
<https://github.com/users/eduardodaluz/packages/container/linyaps-builder/settings>
e mudar a visibilidade para **Public**. Repetir o pull anônimo depois da
confirmação. Não há token ou outra credencial gravada no projeto.

O workflow local foi preparado para usar o digest do GHCR por padrão,
mantendo o override via variável de repositório; não é mais necessário
criar a variável para selecionar o espelho do mantenedor. YAML e todos os
blocos Bash do workflow passaram na validação sintática.

O envio dos commits à `main` continua aguardando autorização explícita,
solicitada novamente nesta retomada por causa da rejeição automática anterior.
O sucesso do login Docker informado pelo mantenedor autoriza prosseguir com
o espelhamento, mas não foi tratado como aprovação do push ao Git.

## Visibilidade pública e autorização de push — 18/10/2026

O mantenedor confirmou os dois passos pendentes: tornar o pacote público e
**autorizar o envio dos commits para `origin/main` e a execução da CI**.
O teste anônimo foi repetido com uma configuração Docker temporária vazia,
sem credenciais, e passou para o digest GHCR
`sha256:9170f635112d5068ef815d6e55d6bd3969e668151bd31a33ca48086f53fd372a`.
A autorização elimina o bloqueio anterior do push; a confirmação da CI
continua sendo o próximo passo. Sem Release ou tag de aplicação publicados.

## Diagnóstico além do pull — 18/10/2026

O push autorizado enviou a correção e o registro até `d5a6765`. O run Debian
[39176490074](https://github.com/eduardodaluz/deepWin/actions/runs/39176490074)
passou. No run Linyaps
[39176490142](https://github.com/eduardodaluz/deepWin/actions/runs/39176490142),
o pull pelo GHCR passou em 12 s, mas o build falhou 7 s depois.

As anotações individuais por linha esgotavam o espaço de diagnóstico com o
progresso do pull, ocultando a mensagem do build. `92a55fe` passou a emitir
uma anotação multiline por arquivo, com escape de LF/CR/%. A nova execução
[39176871739](https://github.com/eduardodaluz/deepWin/actions/runs/39176871739)
mostrou o erro real: `failed to run in namespace ... clone failed: Operation
not permitted`, antes da compilação. A hipótese inicial de falha exclusiva
do registro não explicava esse segundo bloqueio; a imagem local continua
compilando corretamente.

`80b680a` fixa o runner Linyaps em Ubuntu 24.04, prepara temporariamente
`kernel.apparmor_restrict_unprivileged_userns=0` na VM descartável do GitHub
e restaura o valor anterior via trap EXIT ao terminar o build. O builder
oficial usa usuário não root e precisa criar esses namespaces mesmo dentro
do Docker privilegiado. Nenhum sysctl da máquina de desenvolvimento foi
alterado. Simulações validaram restauração após sucesso e falha, valor já
igual a zero e ausência da chave; YAML/Bash passaram na validação sintática.

O download anônimo do log completo retornou HTTP 403. A revisão automática
rejeitou reutilizar o token Docker na API do GitHub por falta de autorização
específica. Nenhuma credencial foi lida ou reutilizada; o diagnóstico acima
foi obtido apenas das anotações públicas após compactar o relatório.

## Staging com UID diferente — 18/10/2026

No run com o ajuste de namespaces,
[39177006827](https://github.com/eduardodaluz/deepWin/actions/runs/39177006827),
o builder iniciou corretamente e leu o manifesto, mas falhou com `stage
prepare error`. A causa foi reproduzida localmente: o staging do runner
pertence ao UID 1001, enquanto `builder` na imagem oficial é UID 1000.
O mesmo projeto que compila com UID 1000 falhou imediatamente ao trocar
apenas a propriedade da cópia temporária para UID 1001.

`bin/build-uab` agora inicia um wrapper root no container para normalizar
somente a propriedade do staging; executa o build, smoke e export como
`builder` via `runuser`, e restaura o UID/GID original por trap EXIT.
`chown -hR` não segue links. O checkout e o home continuam fora das
montagens; o cache de Base/Runtime conserva a identidade do builder.

Validação real em Docker, não apenas simulação:

- Reprodução anterior: staging UID 1001, saída 255 e `stage prepare error`.
- Com o wrapper: build completo sobre staging UID 1001, `pydeps OK`,
  `DeepWin 1.1.0`, exportação UAB e UID 1001 restaurado ao terminar.
- Falha controlada no processo builder: saída 23 preservada e propriedade
  restaurada também para o arquivo criado durante a execução.
- Suíte Python: 126 testes passando.

Log da prova completa: `/tmp/deepwin-uab-uid-fix-build.log`. O UAB dessa prova
ficou no staging descartável; o candidato existente em `dist/` não foi
substituído. Correção pronta para enviar ao próximo run da CI.

## CI Debian e Linyaps concluída — 18/10/2026

O commit de código `fa99d90` passou nos dois workflows em runners limpos:

| Workflow | Resultado | Artefato |
| --- | --- | --- |
| [Debian package — 39177256036](https://github.com/eduardodaluz/deepWin/actions/runs/39177256036) | Sucesso, incluindo build/CTest/Lintian e verificação de instalação limpa | `deepwin-deb-amd64`, ID `12154851428` |
| [Linyaps package — 39177256037](https://github.com/eduardodaluz/deepWin/actions/runs/39177256037) | Sucesso: pull GHCR, build, smoke tests, exportação e upload | `deepwin-uab-amd64`, ID `12154624527` |
| Logs do Linyaps no mesmo run | Upload aprovado | `deepwin-uab-logs`, ID `12154704117` |

O build Linyaps com cache vazio levou aproximadamente 7 min 16 s. A API
confirmou os três artefatos disponíveis e não expirados. Cada workflow
inclui os checksums dos pacotes; os digests exibidos pela API de artefatos
são dos arquivos ZIP do Actions, não o SHA-256 do `.deb` ou `.uab` isolado.

Com isso, a última pendência da fase 2 foi encerrada. README, plano e ponto
de partida deste documento foram atualizados. As seções anteriores desta
passagem continuam como histórico dos diagnósticos e bloqueios superados.
O rascunho `packaging/release-notes-1.1.0.md` prepara a próxima decisão do
mantenedor, sem publicar Release nem criar tag. Fase 3 está liberada para
iniciar, mas não foi implementada nesta correção da CI.

O commit seguinte altera apenas documentação; os testes e o build validados
são os do código `fa99d90`. Não é necessário repetir os builds por essas
edições documentais.

## Fase 3 implementada com subagentes — 18/10/2026

O mantenedor solicitou explicitamente iniciar o portátil com subagentes.
Três frentes trabalharam em build, menu opcional e verificação/CI, seguidas
de revisão independente. A composição do primeiro Release também foi
decidida: **aguardar o aceite do portátil e publicar `.deb`, `.uab` e
`.tar.xz` juntos no Release 1.1.0**. Nenhuma publicação ou tag foi feita.

Implementação:

- `bin/build-portable` usa os mesmos fontes permitidos e alvos CMake, com
  build nativo ou Docker (`--container`, `--reuse-image`, `--output`), lock,
  staging validado por lista exata, tar normalizado e SHA-256. O prefixo
  temporário `/opt/deepwin-portable` evita o tratamento especial `usr/` que
  GNUInstallDirs aplica a `/`; somente a árvore instalada vai para o arquivo.
- `DeepWin-1.1.0-amd64-portable.tar.xz` contém `./deepwin`, `bin/deepwin`,
  `lib/deepwin/`, metadados de desktop e README. O launcher resolve recursos
  relativamente à extração, sem fallback para o `.deb` instalado. As
  bibliotecas Qt 6.8+/DTK 6/Python D-Bus/GI são requisitos nativos explícitos;
  não há bibliotecas GUI privadas, SDK ou Python embutido. O ambiente Qt e
  de bibliotecas do hospedeiro é preservado.
- `./register-menu` e `./unregister-menu` são opcionais; `--help` não escreve
  estado. A entrada `devedu.deepin-configs-portable.desktop` e seu marcador
  em XDG usam hashes, validação de ownership, lock e rollback, recusando
  arquivos personalizados. Paths com espaços e caracteres reservados são
  escapados em duas camadas e testados com lançamento real por GLib.
- `bin/verify-portable` valida checksum e segurança do tar e prepara outra
  imagem Deepin só com runtimes, sem instalar DeepWin ou SDK. O teste exige
  os launchers anunciados, executa usuário não root em pasta somente leitura,
  consulta status sem alterações, testa GUI, menu, schema futuro e runtime
  persistente após mover/remover a origem.
- `.github/workflows/portable.yml` fixa Ubuntu 24.04, executa build e
  verificação e anexa arquivo/checksum e logs. Falhas viram uma anotação
  compacta por log; o envio e a primeira execução ainda estão pendentes.

Evidências:

| Verificação | Resultado |
| --- | --- |
| Suíte Python | 142 testes passando, incluindo 16 casos de segurança do menu |
| Build Docker, com e sem `--reuse-image` | PASS; o caminho completo de preparação da imagem também foi exercitado |
| `bin/verify-portable` | PASS com somente runtimes: plugin Qt, versão, status sem efeitos, GUI, menu GLib, pasta com espaços/caracteres especiais, schema futuro recusado, movimento/remoção e helpers preservados |
| VM Deepin 25.2.0 em snapshot descartável | GUI nativa com 10/10 recursos disponíveis, em pasta somente leitura, com screenshot inspecionada |
| Coexistência e remoção de formatos na VM | Backups e unidades anteriores preservados; `.deb` e `.uab` removidos de verdade no snapshot, portátil continuou abrindo sem eles |
| Colagem ativada pelo portátil; pasta movida/removida | Serviço reiniciado a partir do runtime depois de apagar a origem; `deepwin-restore clipboard` restaurou de verdade, reduzindo os backups de 9 para 8 |
| Troca de versão e retorno | `1.1.0 → fixture 1.1.1 → 1.1.0`, GUI e runtime na versão esperada, hashes de backups e schema preservados |
| Candidato final | Checksum conferido e GUI nativa com dez recursos consultados |

A fixture 1.1.1 foi compilada de uma cópia isolada em `/tmp`, alterando somente
o `VERSION` dessa cópia. Não é candidato nem release; o projeto real continua
em 1.1.0. O teste de schema futuro usa formato 999 e confirma recusa sem
alterar dados. A normalização do tar não declara reprodutibilidade genérica
entre toolchains diferentes.

Logs locais: `/tmp/deepwin-portable-final-build.log`,
`/tmp/deepwin-portable-final-verify.log`,
`/tmp/deepwin-portable-vm-persistence.log`,
`/tmp/deepwin-portable-vm-rollback.log` e
`/tmp/deepwin-portable-vm-final.log`. Captura em
`/tmp/deepwin-portable-native.png`, fora do pacote e do repositório.
O snapshot foi desligado após o aceite; o disco original da VM foi preservado,
incluindo seus aplicativos e configuração anterior de login.

Falta enviar a implementação e confirmar a CI portátil. O candidato local
usa o timestamp de fonte da base desta passagem; artefatos de outro commit
podem ter SHA-256 diferente por metadados de empacotamento. Use sempre o
checksum que acompanha o artefato efetivamente baixado.

## Aceite final dos três formatos na CI — 18/10/2026

A implementação foi enviada no commit `07fb017`. Os três workflows passaram
no mesmo código, sem regressão das fases anteriores:

| Workflow | Resultado | Artefato disponível |
| --- | --- | --- |
| [Portable archive — 39179478620](https://github.com/eduardodaluz/deepWin/actions/runs/39179478620) | Build, verificação limpa e upload aprovados | `deepwin-portable-amd64`, ID `12155179755` |
| [Debian package — 39179478622](https://github.com/eduardodaluz/deepWin/actions/runs/39179478622) | Build, CTest/Lintian e verificação de instalação aprovados | `deepwin-deb-amd64`, ID `12155199625` |
| [Linyaps package — 39179478573](https://github.com/eduardodaluz/deepWin/actions/runs/39179478573) | Build, smoke, exportação e upload aprovados | `deepwin-uab-amd64`, ID `12155493804` |

A API confirmou os pacotes e os dois artefatos de logs disponíveis e não
expirados. Cada grupo de pacote contém seu checksum; o README acompanha o
portátil. Com isso, os critérios locais, de VM e de CI da fase 3 estão
concluídos. Os checklists antigos das fases 1 e 2 permanecem históricos.

**Decisão final de composição do primeiro Release:** versão **1.1.0**, com
`.deb`, `.uab` e `.tar.xz` juntos, seus SHA-256 e requisitos por formato.
O mantenedor escolheu aguardar o portátil e esse aceite foi concluído.
Os três arquivos estão preparados como artefatos de CI; falta a confirmação
da publicação em Releases, conforme combinado ao escolher a composição.
Nenhuma tag ou Release foi criado nesta implementação.

O registro final altera só documentação e referencia o código aprovado
`07fb017`, sem necessidade de repetir builds por essas alterações.

## Preparação da publicação autorizada — 18/10/2026

Após o aceite dos três formatos, o mantenedor respondeu **“Pode seguir”**,
autorizando a publicação do primeiro Release. As notas foram finalizadas.
O workflow `release.yml`, restrito à tag `v1.1.0`, usa o `GITHUB_TOKEN` da
própria execução com `actions:read` e `contents:write`; não depende de login
local no GitHub CLI nem acessa o token Docker/GHCR.

O publicador fixa os IDs dos três runs e artefatos já aceitos, confere origem,
resultado, commit e digest do ZIP, seleciona somente instaladores/checksums
e valida cada checksum. Recusa alteração de código depois do aceite ou
Release já existente. Cria um rascunho com sete anexos (três instaladores,
três sidecars e `SHA256SUMS`), confere tamanho e digest remoto de todos e só
então publica. A tag inclui apenas documentação e essa automação sobre o
código aprovado. Se falhar depois de criar o rascunho, inspecionar o estado
antes de tentar novamente; não sobrescreve nem apaga releases.

Validação local: seis testes da publicação aprovados, incluindo ZIP alterado,
checksum incorreto, nomes duplicados, origem divergente, artefato expirado e
anexos remotos ausentes/adicionais/alterados; YAML e `git diff --check` válidos.
Nenhum código da aplicação foi alterado.
