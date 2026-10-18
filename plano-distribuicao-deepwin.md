# Plano de distribuição do DeepWin

Status em 18/10/2026: fase 1 concluída — validada em VM Deepin 25.2.0 com
sessão gráfica completa e Solid ativo (D6), commits publicados e workflow do
GitHub Actions verde com artefato; candidato
`devedu.deepin-configs_1.1.0-3_amd64.deb`. Fase 2 iniciada e com a L1
concluída: a [matriz de acesso Linyaps](matriz-acesso-linyaps.md) registra a
prova empírica de que o container alcança a sessão hospedeira (D-Bus de
sessão, systemd do usuário, `$HOME` real, rootfs do host em leitura) e a
decisão por acesso direto. O candidato
`devedu.deepin-configs_1.1.0.0_x86_64_main.uab` foi gerado por `bin/build-uab`
em Docker, com smoke de `dbus`/`gi` dentro do sandbox. Pendem o aceite da
fase 2 em VM limpa e a decisão de publicar o workflow Linyaps na CI. A fase 3
permanece futura. O diagnóstico e os checklists abaixo registram o plano
original; consulte a [passagem de desenvolvimento](continuidade-desenvolvimento.md)
para o estado efetivo, os testes realizados e as pendências antes de marcar
entregas concluídas.

## Objetivo e sequência

Disponibilizar a mesma aplicação DTK, com os mesmos ajustes e backups por usuário,
em três formatos, nesta ordem:

| Fase | Formato | Entrega | Condição para iniciar |
| --- | --- | --- | --- |
| 1 | Debian | `devedu.deepin-configs_<versão>_<arquitetura>.deb` | Preparar a base comum descrita abaixo |
| 2 | Linyaps/Linglong | Aplicativo `devedu.deepin-configs` e exportação `.uab` | Fase 1 validada; provar a integração com o sistema hospedeiro |
| 3 | Portátil | `DeepWin-<versão>-<arquitetura>-portable.tar.xz` | Base comum estabilizada e fase 2 concluída |

A referência inicial é Deepin 25 em amd64. Outras arquiteturas entram após build
e testes próprios. O painel poderá indicar recursos incompatíveis como
indisponíveis; um empacotamento diferente não torna a colagem X11 compatível
com Wayland nem fornece as APIs do Deepin em outras distribuições.

## Diagnóstico do repositório

| Componente atual | Ajuste necessário para distribuição |
| --- | --- |
| `deepwin.yml` | Hoje compila e instala por usuário; manter como opção de desenvolvimento e migração |
| `bin/build-deepwin` | Separar compilação, preparação de dependências e instalação em diretório de staging |
| `bin/deepwin` | Resolver recursos do checkout, do pacote instalado e da distribuição portátil |
| `gui/backend.py` | Separar consultas de disponibilidade, preparação da integração e ativação do recurso |
| `gui/calculator_decimal.py` | Separar biblioteca/launcher distribuídos da flag gravada pelo usuário |
| `bin/deepwin-calculator` | Hoje deriva a flag da pasta do executável; isso precisa mudar para instalação somente leitura |
| `gui/dock_preview.py` | Resolver o helper persistente usado no `ExecStartPre`, sem depender do checkout |
| `bin/zclaude` | Encontrar o gerenciador de versões após instalação ou troca de formato |
| Colagem automática | Empacotar o script e o template da unidade; habilitar pelo painel na sessão do usuário |
| Wallpapers | Criar instalação genérica do serviço e timer; hoje o playbook apenas troca a imagem uma vez |
| Verificações | O smoke test atual exige todos os recursos; separar abertura da GUI de disponibilidade das integrações |
| Metadados | Criar versão central, licença de distribuição, metadados de pacote, ícone e descrição de release |

Nenhuma configuração, timer, caminho ou preferência existente em uma máquina de
desenvolvimento deve ser pré-requisito implícito para quem baixar um instalador.

## Base comum — primeira parte da fase 1

### B1. Layout dos arquivos e compilação

- [ ] Criar build CMake com os alvos da GUI DTK e do plugin Qt da calculadora,
      usando o SDK instalado no ambiente de build e geração de metadados via moc.
- [ ] Instalar os alvos em staging com `DESTDIR`/prefixo configurável. A montagem
      do pacote não deve baixar dependências nem copiar arquivos da conta local.
- [ ] Manter `bin/build-deepwin` como entrada conveniente para desenvolvimento;
      fazer a preparação opcional do SDK antes da etapa de compilação.
- [ ] Centralizar versão e manifesto dos recursos, compartilhados pelos formatos.
- [ ] Criar resolução explícita para modo checkout, instalado e portátil, com
      erro claro quando um recurso distribuído estiver ausente.

Layout proposto para o `.deb`: comando em `/usr/bin/deepwin`, componentes privados
em `/usr/lib/deepwin/` e metadados de desktop em `/usr/share/`. Os caminhos finais
serão definidos pelo build, sem nomes de usuário embutidos nos binários.

### B2. Estado, migração e continuidade dos recursos

O pacote contém os arquivos originais do programa. Preferências, backups,
downloads do Claude e flags continuam em diretórios XDG graváveis por usuário.
Os identificadores `DeepWin`, `deepwin` e `devedu.deepin-configs` são preservados.

- [ ] Acrescentar versão de esquema e migrações transacionais ao estado existente.
- [ ] Preservar `originals.json`, a seleção do Claude e os wrappers personalizados.
- [ ] Atualizar apenas arquivos reconhecidos como gerenciados pelo DeepWin,
      comparando manifesto e hashes antes de substituir ou remover.
- [ ] Serializar migração/ativação entre instalações de formatos diferentes;
      preservar também o controle de instância única da interface.
- [ ] Oferecer diagnóstico de instalações locais antigas que possam ocultar o
      novo `/usr/bin/deepwin` ou a entrada de menu do pacote.

Decisão de continuidade: ao ativar ajustes que dependem de helpers, preparar uma
cópia versionada dos componentes necessários em uma localização estável por
usuário. Serviços, wrappers e o plugin carregado pela calculadora apontarão para
esse runtime persistente, não para o checkout, um container ou uma pasta portátil
que possa desaparecer. A preparação ocorre pela aplicação na sessão do usuário.

Esse runtime deverá ter atualização atômica, verificação de ownership e uma forma
local de restaurar os ajustes mesmo após remover a GUI. Remover o pacote preserva
os dados e as integrações já ativadas, conforme o comportamento atual; remover
os ajustes será uma ação explícita de restauração/limpeza por usuário. Não depender
de um pacote auxiliar que possa ser removido por `autoremove` para garantir isso.
O desinstalador do sistema não deve percorrer contas nem apagar seus backups.

### B3. Preparação dos recursos pelo painel

- [ ] Distribuir templates de unidades systemd de usuário para colagem e wallpapers.
- [ ] Na primeira ativação, instalar os arquivos necessários, recarregar o systemd
      do usuário e iniciar/habilitar apenas o recurso selecionado.
- [ ] Capturar também a ausência original de unidades/arquivos. Se a ativação
      falhar, desfazer os arquivos recém-criados e preservar a configuração anterior.
- [ ] Reutilizar unidades compatíveis já existentes; preservar unidades personalizadas.
- [ ] Para wallpapers, oferecer frequência explícita, com proposta inicial de uma
      hora, sem copiar agendamento ou pastas de uma máquina de desenvolvimento.
- [ ] Ao ativar colagem pelo painel, iniciar o modo real documentado; manter o modo
      de simulação como opção explícita de diagnóstico, sem status enganoso.
- [ ] Manter Claude/Z.AI opcionais. A GUI deve abrir sem Node/npm, Claude ou chave;
      verificar esses requisitos somente nas operações que realmente precisam deles.

Instalar o aplicativo não habilita ajustes nem inicia downloads. A GUI continua
executando como usuário comum. Scripts de instalação do `.deb` não devem tentar
acessar o D-Bus de uma sessão gráfica ou executar o painel como root.

### B4. Dependências e compatibilidade

- [ ] Separar dependências de compilação das de execução, incluindo bibliotecas
      carregadas via Python/ctypes que não aparecem em `shlibs:Depends`.
- [ ] Verificar Python, D-Bus, GI/Gio/GLib, DTK/Qt, systemd e as ferramentas de cada
      recurso, como `xdotool`, curl e utilitários XDG.
- [ ] Validar o plugin decimal contra o Qt da calculadora, inclusive quando ela usa
      um runtime Linglong diferente daquele usado pela GUI.
- [ ] Preservar os plugins de tema do Deepin e restringir variáveis Qt ao processo
      que precisa delas; não exportar caminhos de plugin para a sessão inteira.
- [ ] Manter verificação de compatibilidade e fallback do QML de prévias do dock.
- [ ] Definir versões mínimas a partir dos builds e testes em ambiente limpo.

O Qt verifica compatibilidade de versão ao carregar plugins. Portanto, empacotar
bibliotecas da GUI não garante que o plugin funcione na calculadora hospedeira.
Essa compatibilidade terá uma verificação própria, conforme a
[documentação de implantação do Qt](https://doc.qt.io/qt-6/deployment-plugins.html).

### B5. Build, validação e publicação

- [ ] Construir em ambiente Deepin 25 limpo e versionado; preparar dependências
      antes do build. Testar a sessão gráfica em VM, além do build em container.
- [ ] Separar testes sem sessão, abertura básica da GUI e testes das integrações.
      Uma instalação nova não pode falhar no teste de abertura apenas por ter
      recursos opcionais ausentes.
- [ ] Criar automação de CI que gere artefatos de teste por commit e publique
      releases versionadas somente após os critérios de aceite.
- [ ] Publicar instruções, arquiteturas suportadas, notas de compatibilidade e
      SHA-256 dos arquivos entregues; nunca incluir SDK, backups ou credenciais.

## Fase 1 — pacote .deb

### Entregas e ordem de implementação

| Ordem | Trabalho | Resultado verificável |
| --- | --- | --- |
| D1 | Implementar B1 e a resolução de caminhos de B2 | GUI e plugin compilam e funcionam a partir de staging fora do checkout |
| D2 | Implementar migração, runtime persistente e B3 | Uma conta nova ativa os ajustes sem playbooks adicionais |
| D3 | Adicionar empacotamento Debian | `debian/control`, `rules`, `changelog`, `copyright`, formato de fonte e regras de instalação |
| D4 | Declarar dependências e metadados | Binários prontos, comando e menu disponíveis; sem compilador ou Ansible na máquina de uso |
| D5 | Automatizar build e revisão do pacote | `.deb` e resultados de validação anexados aos artefatos da CI |
| D6 | Validar e publicar a primeira release | Instalação, atualização, remoção e rollback aprovados em VM limpa |

Usar debhelper e geração das dependências ELF, acrescentando as dependências que
o backend carrega dinamicamente. A base de empacotamento segue o
[guia oficial de mantenedores Debian](https://www.debian.org/doc/manuals/debmake-doc/).
O Deepin documenta suporte a `.deb` por apt/dpkg com o Solid ativo; os testes
incluirão esse cenário, sem exigir desativar a proteção do sistema, conforme a
[FAQ oficial do Deepin 25](https://www.deepin.org/en/qa-deepin-25-qa-2/).

### Critérios de aceite

- [ ] Instalar pelo instalador gráfico e pelo gerenciador de pacotes em Deepin 25.
- [ ] Abrir pelo menu e por `deepwin`, sem Git, Ansible, SDK ou compilador.
- [ ] Abrir em conta nova sem chave Z.AI, Claude, timer ou automação prévia.
- [ ] Ativar, desativar e restaurar cada recurso compatível; testar terminais na colagem.
- [ ] Atualizar com ajustes ativos sem perder backups, preferências ou seleção de versão.
- [ ] Migrar a instalação local atual, preservando arquivos personalizados.
- [ ] Remover a GUI sem deixar serviços apontando para arquivos removidos; validar
      a restauração pelo runtime preservado e a reinstalação posterior.
- [ ] Validar o pacote com ferramentas Debian e registrar justificativas para
      eventuais avisos específicos do Deepin.

## Fase 2 — Linyaps/Linglong

### L1. Prova de integração antes do empacotamento final

O Linyaps executa a aplicação em container. Isso exige validar separadamente
D-Bus da sessão, systemd do usuário, configurações XDG reais, acesso X11 e os
arquivos usados pelo dock e pela calculadora. Montar uma pasta do host não prova
que os comandos executados no container controlam a sessão do host.

- [ ] Criar uma matriz experimental de acesso para cada integração, inicialmente
      com operações de consulta e testes descartáveis.
- [ ] Verificar os mecanismos da versão suportada do Linyaps para falar com a sessão
      hospedeira. Fixar Base, Runtime e fontes no manifesto.
- [ ] Se necessário, implementar uma ponte no host reutilizando o runtime da fase 1,
      com protocolo versionado para as operações do painel. A GUI não deve depender
      de executar comandos arbitrários do host a partir do container.
- [ ] Documentar como instalar/atualizar/remover essa ponte. Se houver componente
      nativo adicional obrigatório, identificá-lo antes de anunciar o formato como
      instalador completo; a dependência não pode ficar implícita.

A decisão entre acesso direto e ponte será registrada após a prova. Abrir a GUI
no container, isoladamente, não conclui a fase nem comprova os dez recursos.

### L2. Empacotamento e entrega

- [ ] Criar `linglong.yaml` com ID `devedu.deepin-configs`, comando, versão, SDK,
      dependências e instalação pelo prefixo fornecido pelo builder.
- [ ] Reutilizar os alvos de build da fase 1 e adaptar somente a implantação.
- [ ] Integrar menu, ícone e metadados com as convenções do Linyaps.
- [ ] Validar build, execução e exportação `.uab`; publicar no GitHub Releases.
- [ ] Preparar instruções para repositório/loja Linyaps, tratando submissão e
      aprovação da loja como uma etapa distinta da geração do pacote.

O fluxo e a configuração serão baseados no
[workflow oficial do ll-builder](https://github.com/OpenAtom-Linyaps/linyaps/blob/master/docs/pages/en/guide/start/ll-builder-workflow.md)
e na [referência oficial de configuração do runtime](https://github.com/OpenAtom-Linyaps/linyaps/blob/master/docs/pages/en/guide/extra/runtime_config.md).

### Critérios de aceite

- [ ] Instalar e abrir a exportação `.uab` em ambiente Deepin limpo.
- [ ] Confirmar que cada ajuste altera a sessão hospedeira e seu estado real.
- [ ] Compartilhar backups, bloqueios e preferências com a instalação `.deb`.
- [ ] Preservar serviços e helpers após atualização, remoção ou rollback do container.
- [ ] Validar a ponte, se necessária, sem sessão root ou credenciais embutidas.
- [ ] Informar requisitos de runtime e eventual componente hospedeiro na página de download.

## Fase 3 — distribuição portátil

### P1. Formato e execução

A primeira entrega portátil será um `.tar.xz` com diretório extraível e comando
`./deepwin`. AppImage poderá ser avaliado como embalagem posterior da mesma base;
não é requisito desta primeira entrega portátil.

- [ ] Gerar a árvore portátil a partir do mesmo staging e da mesma versão dos
      outros formatos, com resolução de recursos relativa ao launcher.
- [ ] Distribuir os componentes necessários da aplicação e levantar quais
      bibliotecas podem ser incluídas; documentar o que permanece dependente
      do Deepin hospedeiro, inclusive Python/GI e serviços nativos.
- [ ] Validar o conjunto final em máquina limpa. Não chamar de autocontido um
      arquivo que só funciona porque o SDK ou bibliotecas extras estão instalados.
- [ ] Preservar o ambiente nativo ao chamar serviços/ferramentas do host; bibliotecas
      da GUI portátil não devem contaminar o ambiente da calculadora ou do systemd.
- [ ] Permitir abrir sem registrar menu, autostart ou serviços automaticamente.
      Disponibilizar registro opcional no menu e sua remoção.

Portátil significa que a GUI pode ser executada sem instalar um pacote de sistema.
Ativar um ajuste persistente necessariamente grava configurações do usuário; isso
será explicado no produto. Os helpers estáveis preparados na fase 1 mantêm esses
ajustes funcionais mesmo que o diretório portátil seja movido ou removido.

### Critérios de aceite

- [ ] Extrair e abrir como usuário comum, sem instalação de pacote do DeepWin.
- [ ] Funcionar fora do checkout e em caminhos com espaços.
- [ ] Abrir a partir de uma pasta sem permissão de escrita, mantendo o estado em XDG.
- [ ] Mover/remover a pasta após ativar um ajuste sem quebrar o serviço ou o rollback.
- [ ] Reutilizar preferências e backups existentes, inclusive alternando formatos.
- [ ] Trocar a versão portátil e retornar à anterior quando o esquema for compatível;
      detectar claramente um estado de versão mais nova que não possa ser lido.
- [ ] Publicar requisitos, instruções de extração, limpeza e checksum junto ao arquivo.

## Matriz de validação compartilhada

| Cenário | Fase 1 | Fase 2 | Fase 3 |
| --- | --- | --- | --- |
| Deepin limpo, usuário novo, recursos opcionais ausentes | Obrigatório | Obrigatório | Obrigatório |
| Migração da instalação Ansible atual | Obrigatório | Obrigatório | Obrigatório |
| Atualização com ajustes ativos e backups pendentes | Obrigatório | Obrigatório | Obrigatório |
| Unidade, wrapper ou launcher personalizado | Preservar | Preservar | Preservar |
| Recurso incompatível, sem impedir a GUI de abrir | Obrigatório | Obrigatório | Obrigatório |
| Solid ativo | Obrigatório | Obrigatório | Obrigatório |
| Remoção da GUI com ajustes ativos | Obrigatório | Obrigatório | Obrigatório |
| Qt da calculadora diferente do Qt da GUI | Verificar ABI | Verificar ABI | Verificar ABI |
| Sessão Wayland | Informar limites | Informar limites | Informar limites |
| Pastas/container de origem indisponíveis | Após remover pacote | Após remover container | Após mover ou apagar pasta |

## Decisões pendentes e próxima entrega

O mantenedor escolheu MIT e autorizou `eduardo.r.luz@gmail.com` como e-mail
público do pacote. `LICENSE` e os metadados correspondentes já foram preparados
na implementação local, ainda sem commit na data desta passagem.

Também permanecem para validação: versões mínimas exatas, ambiente de CI Deepin,
versão de Base/Runtime Linyaps e composição final das bibliotecas portáteis.
Essas definições não impedem iniciar D1, mas fazem parte do aceite das releases.

A implementação local já inclui build comum, staging, resolução de caminhos,
migração/ativação de integrações e um `.deb` validado em imagem limpa e em VM
com sessão gráfica completa. A próxima entrega é o commit/push do candidato
1.1.0-3 e a execução do workflow no GitHub. A revisão da ABI do plugin da
calculadora permanece como condição para ampliar plataformas (referência
testada: Qt 6.8 do Deepin 25). A fase 2 só avança após o aceite da fase 1;
a fase 3 segue a fase 2.
