# Continuidade do desenvolvimento do DeepWin

Registro de passagem em **17/10/2026**, a pedido do mantenedor. O trabalho foi
interrompido para documentação, sem retomar a implementação após esse pedido.

## Ponto de partida para o próximo agente

- Repositório: <https://github.com/eduardodaluz/deepWin>, branch `main`.
- `HEAD` e a referência local `origin/main` apontam para
  `3ed84646b64a77936a751bbfd186f057fae1f8fd` — planejamento dos três formatos.
  Essa comparação não consultou novamente o servidor remoto.
- A implementação de empacotamento descrita abaixo está no diretório de
  trabalho, **sem commit e sem push**. Há arquivos novos ainda não rastreados.
  Preserve essas alterações; não comece com reset/clean nem apenas com um clone
  remoto, que ainda não contém essa implementação.
- Prioridade autorizada: fase 1 `.deb`; depois fase 2 Linyaps/Linglong `.uab`;
  por último fase 3 portátil `.tar.xz`. As fases 2 e 3 continuam no planejamento.
- Há um `.deb` local de teste, mas **a fase 1 ainda não está concluída**.
  Não foi publicado release, tag ou instalador para distribuição.
- O usuário escolheu licença **MIT** e autorizou o e-mail público de mantenedor
  **eduardo.r.luz@gmail.com** nos metadados. Esses pontos já estão resolvidos.

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

## Sequência sugerida para retomar

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

Resta para concluir a fase 1: a decisão de commit/push e a execução do
workflow no GitHub. O caminho do workflow (build sem reuso de imagem) passou
também para o candidato final 1.1.0-3, com CTest 2/2, Lintian sem avisos e os
cinco PASS da verificação limpa reexecutados; os bytes desse artefato
(sha256 `35243d67…50334`) diferem do build com reuso porque a imagem
reconstruída baixa pacotes atuais do crimson, e ambos passam. Um aviso do
Lintian no changelog (`wrong-day-of-week`) foi corrigido: 18/10/2026 é
domingo. O `--help` da GUI continua exigindo sessão gráfica, fora do escopo
desta fase.
