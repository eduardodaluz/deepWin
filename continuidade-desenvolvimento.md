# Continuidade do desenvolvimento do DeepWin

Registro de passagem iniciado em **17/10/2026** e atualizado a cada retomada;
as seções antigas são história executada e ficam intactas. A seção seguinte é
o ponto de partida atual para o próximo agente.

## Ponto de partida para o próximo agente

Atualizado em **18/10/2026**, na retomada da correção da CI do Linyaps.

- Repositório: <https://github.com/eduardodaluz/deepWin>, branch `main`,
  base desta retomada `471a2dd`, com `origin/main` igual antes das alterações.
  Consulte `git log -1` para o commit atual. **Nenhum commit contém linha de
  coautoria do Claude**: o mantenedor pediu a remoção (seis commits
  reescritos com árvores idênticas e force push com lease) e commits novos
  devem sair sem o trailer.
- Alterações desta retomada estão **commitadas apenas localmente**.
  `git push origin main` foi rejeitado pela revisão automática: ela exige
  autorização explícita do mantenedor para alterar a branch padrão.
  `origin/main` permanece em `471a2dd`; não há run da CI com estas mudanças.
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
- **Único item aberto da fase 2: o job `Linyaps package` na CI.** Falha nos
  três pushes sempre no mesmo ponto — o `docker pull` de
  `registry.cn-hangzhou.aliyuncs.com/linyaps/builder:1.13.8_amd64` não chega
  aos runners do GitHub; o mesmo `bin/build-uab` passa nesta máquina. O
  build do projeto não falhou. **Preparação implementada nesta retomada:**
  override `DEEPWIN_BUILDER_IMAGE`, origem fixada por digest, pull separado
  com três tentativas limitadas e logs anexados mesmo em falha. A variável
  de repositório `DEEPWIN_BUILDER_IMAGE` seleciona o espelho na CI; sem ela,
  mantém-se a origem oficial. **Espelho ainda não publicado:** não há login
  Docker/GHCR nesta sessão, e foi solicitado ao mantenedor autenticar em
  outro terminal. A tag GHCR existe apenas localmente, com ID idêntico ao
  original. Procedimento em [packaging/linyaps-builder.md](packaging/linyaps-builder.md).
  Não apontar a CI para uma imagem remota ainda inexistente ou privada.
- **Fase 3 (portátil `.tar.xz`): não iniciada** — é a próxima após a CI do
  Linyaps fechar; a base comum (runtime persistente, staging, migração) já
  está estável e reutilizada pelos dois formatos prontos.
- **Sem release, tag ou instalador publicado**: os artefatos existem como
  artefatos de CI e em `dist/` local. Publicar o primeiro Release é decisão
  do mantenedor.
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

1. Concluir o login no GHCR, publicar a imagem já etiquetada localmente,
   torná-la pública e validar pull anônimo. Configurar a variável do
   repositório `DEEPWIN_BUILDER_IMAGE` com o digest retornado pelo GHCR;
   rodar a CI até o `Linyaps package` ficar verde. Override e retentativas
   já estão implementados; consultar o adendo mais recente.
2. Decidir com o mantenedor o primeiro Release (`.deb` + `.uab` + checksums
   + requisitos de runtime na página).
3. Iniciar a fase 3 conforme o [plano](plano-distribuicao-deepwin.md).
4. Itens menores registrados: reboot completo da VM como teste
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
