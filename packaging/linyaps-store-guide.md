# Distribuição do DeepWin por repositório/loja Linyaps

Guia de preparação, submissão e aprovação para levar o pacote Linyaps do
DeepWin além da distribuição direta de `.uab` (que já é um canal oficialmente
reconhecido e é o que o [Release 1.1.0](https://github.com/eduardodaluz/deepWin/releases/tag/v1.1.0)
usa hoje). Submeter efetivamente é uma decisão do mantenedor; este guia
registra o processo verificado em outubro de 2026 nas fontes oficiais
citadas no fim. Nada aqui é pré-requisito do Release publicado.

## Decisão prévia obrigatória: o identificador do aplicativo

A spec oficial de empacotamento Linyaps exige `package.id` em **domínio
reverso comprovado**: quem submete precisa demonstrar controle sobre o
domínio que dá nome ao app. Para apps de terceiros hospedados no GitHub, a
spec recomenda `io.github.<usuário>.<aplicativo>` (sublinhado no lugar de
hífen). A spec admite remover do repositório um app cujo domínio não pode
ser comprovado.

`devedu.deepin-configs` não atende a isso hoje: `devedu` não é um domínio do
mantenedor (o prefixo `deepin` de grande marcas do projeto também não é de
terceiros). Consequências práticas para a submissão:

- A submissão por `devedu.deepin-configs` depende de exceção ou de comprovar
  um domínio próprio — até onde a documentação oficial vai, não há esse
  mecanismo para terceiros.
- A alternativa spec-conforme seria um novo ID (exemplo:
  `io.github.eduardodaluz.deepin_configs`). **Isso não é uma renomeação
  cosmética**: o identificador está em `linglong.yaml`, desktop entry, pasta
  de estado XDG (`~/.config/devedu.deepin-configs`, `~/.local/share/...`),
  nomes de `.deb`/`.uab` e runtime persistente. Uma mudança dessas exige
  plano de migração de estado e novo aceite das três fases.
- A distribuição direta de `.uab` (Release/GitHub) não passa por essa
  revisão de ID; a exigência é dos canais de repositório/loja.

**Decisão pendente do mantenedor**: manter distribuição direta, ou adotar
novo ID e migrar. Este guia segue com o processo, válido para qualquer um
dos dois caminhos.

## Os dois canais (e o erro comum)

Existem dois canais distintos de distribuição; confundi-los é o erro mais
comum:

1. **Ecossistema comunitário Linyaps**: repositório consumido por padrão
   pelo `ll-cli` (`stable`, `mirror-repo-linglong.deepin.com`) e a loja web
   da comunidade (store.linyaps.org.cn / store.linglong.dev), mantida pelo
   SIG de loja simples. A via de entrada é o
   [linglongdev/Repository-Manager](https://github.com/linglongdev/Repository-Manager),
   por pull request.
2. **Loja oficial UnionTech/deepin**: plataforma de desenvolvedor em
   appstore-dev.uniontech.com, que distribui no canal oficial das lojas
   deepin/UOS (o `deepin-app-store` do sistema aceita DEB e formato
   Linyaps). A via de entrada é upload do `.layer` pronto no console.

## Preparação

1. **CLA**: assinar o CLA do Linyaps (individual em linyaps.org.cn/icla;
   corporativo em /ccla). É pré-requisito da via comunitária. Para o canal
   UnionTech há CLA/certificação própria (identity.chinauos.com).
2. **Manifesto conforme a spec** (o `linglong.yaml` do repositório já existe;
   conferir contra a spec vigente antes de submeter):
   - `version: "1"` do schema; `package` com `id` (domínio reverso — ver
     decisão acima), `name`, `version` em quatro grupos numéricos
     (`1.1.0.0`), `kind: app`, `description`.
   - `base` fixada com três dígitos da série (ex. `org.deepin.base/25.2`);
     fixar quatro dígitos impede atualizações de base. O DeepWin usa
     `org.deepin.base/25.2.2` e `org.deepin.runtime.dtk/25.2.2` — para
     submissão, reavaliar contra a prática vigente do repositório.
   - `command` com caminho absoluto dentro do container.
   - Instalação inteira em `$PREFIX` (`/opt/apps/<id>/files`); nada fora de
     `$PREFIX` e `/source` no build. O pacote atual atende (o CMake instala
     em staging e o layer só carrega a árvore instalada).
   - Desktop entry nomeado com o próprio `id` em `files/share/applications/`
     e ícone em `files/share/icons/hicolor/` — mínimo um PNG 48×48 (MUST),
     SVG recomendado. `info.json` é gerado pela ferramenta; nunca editar.
   - Limitações estruturais: sem SUID/capabilities, sem unidades systemd de
     sistema, sem componentes do ambiente desktop. O DeepWin já opera assim
     (L1 decidiu acesso direto ao host; as unidades são por usuário).
3. **`.layer` para o canal UnionTech**: exportar com
   `ll-builder export` (o mesmo pipeline do `bin/build-uab` produz o
   `.uab`; o `.layer` é a variante de repositório). Para a via comunitária o
   layer é construído pelo CI do Repository-Manager — não se envia binário.
4. **Ativos de vitrine** (canal UnionTech): ícone quadrado 1:1 entre 96×96 e
   512×512 e pelo menos três capturas 3:2 entre 1050×700 e 1920×1280, mais
   textos. O `linglong.yaml` **não tem campo de screenshots/metainfo**; os
   ativos pertencem ao console da loja. Para a loja web comunitária os
   requisitos de vitrine não estão documentados publicamente.

## Submissão

### Via comunitária (Repository-Manager)

1. PR em <https://github.com/linglongdev/Repository-Manager> editando
   `repos.yaml`: entrada com `repo` (ID em domínio reverso), `info`
   (descrição) e `developer` (usuário GitHub). Repositório ativo (pushes em
   2026); após o merge o `repos.yaml` é resetado e o histórico vai para
   `history/repos_history.yaml`.
2. O merge cria automaticamente um repositório de app na org `linglongdev`.
3. PRs seguintes alteram o `linglong.yaml` do app nesse repositório; o
   webhook dispara build no Jenkins e **o bot cola na PR o link do
   `.layer`** gerado para teste.
4. Mudança de versão: PR que altera o campo `version`; o merge cria tag,
   o build de tag publica o layer no repositório online automaticamente.
5. `ll-builder push` existe e é documentado, mas não há fluxo público de
   emissão de credenciais de push do repo `stable` para terceiros — o
   caminho documentado de terceiros é o PR, não push direto. Não contar com
   push direto.

### Via loja UnionTech/deepin

1. Conta e certificação de desenvolvedor: identity.chinauos.com.
2. No console appstore-dev.uniontech.com: "应用分发" → "添加新应用";
   enviar o `.layer`; preencher nome, categoria, versão, arquiteturas
   (amd64, arm64, loongarch64) e versões de sistema alvo; enviar ícone,
   capturas e textos.
3. Observar as linhas vermelhas declaradas: cobrança maliciosa, coleta
   oculta de dados, abuso de permissões, scripts de fundo não autorizados.
   O DeepWin não coleta dados nem instala scripts de fundo; a documentação
   do painel deve deixar isso explícito no formulário.

## Aprovação

- **Comunitária**: revisão humana por administrador do SIG de empacotamento
  — baixa o layer da PR, testa e só então aprova. Não é merge automático;
  espere interações de revisão na PR.
- **UnionTech/deepin**: revisão humana com feedback para rejeição e
  ressubmissão. Critérios citados oficialmente: arquivos sob
  `/opt/apps/<id>/`, scripts de manutenção sem efeitos colaterais, execução
  sem crashes na versão alvo, ID único e legal, permissões mínimas, sem
  mexer em configuração do sistema. **Atenção específica do DeepWin**: o
  painel altera configurações do *usuário* (com backup e rollback), não do
  sistema; a descrição da submissão deve deixar essa distinção clara para
  não ser rejeitado pelo critério "sem mexer em config do sistema".
- **Assinatura**: nenhum requisito de assinatura de app está documentado nas
  fontes oficiais (o próprio repositório do cliente usa `gpg-verify=false`).
- **Licença**: sem política pública explícita encontrada; a spec espera
  `files/share/doc/copyright` no artefato (o pacote já carrega MIT).

## Instalação pelo usuário final

Repositório de terceiros (após aprovação, ou repo próprio para testes):

```bash
ll-cli repo add meurepo https://repo.exemplo.com   # registra um mirror
ll-cli repo show                                   # lista repos (padrão: stable)
ll-cli repo set-priority meurepo 200               # prioridade entre repos
ll-cli search deepwin --repo meurepo
ll-cli install <id> --repo meurepo
```

Canal direto já em produção neste projeto: `ll-cli install ./arquivo.uab`
(com `sudo`) ou clique duplo no gerenciador de arquivos; documentado em
`README.md` e reconhecido oficialmente como canal de distribuição UAB.

## Fontes verificadas (outubro de 2026)

- Guia oficial de contribuição: <https://linyaps.org.cn/packagecontribution>
- Repository-Manager: <https://github.com/linglongdev/Repository-Manager>
- Spec de empacotamento e manifests:
  <https://linyaps.org.cn/en/guide/building/linyaps_package_spec.md>,
  <https://linyaps.org.cn/en/guide/building/manifests.html>
- Publishing/repositórios/UAB:
  <https://linyaps.org.cn/en/guide/publishing/repositories.html>,
  <https://linyaps.org.cn/en/guide/publishing/uab.html>
- Comandos: `ll-builder push`, `ll-builder repo` (docs v1.14)
- Loja UnionTech/deepin: <https://www.deepin.org/zh/app-store-submission-listing-guide>,
  <https://appstore-dev.uniontech.com>
- Loja comunitária: <https://store.linyaps.org.cn>, <https://store.linglong.dev>
- Obsoleto/não usar: `linglongdev/repo` (morto desde 2023),
  linyaps.github.io (não existe).
