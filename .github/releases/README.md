# Publicação de versões do DeepWin

Cada release é descrito por um arquivo JSON neste diretório. O workflow
`release.yml` só publica por **dispatch manual** (`workflow_dispatch`) com o
nome do arquivo como entrada; pushes que tocam esta pasta ou os scripts de
publicação executam apenas os testes de validação. Um release já publicado é
**no-op**: o publicador confere a tag e sai sem alterar nada — nunca
reconstrói, edita ou substitui anexos de um release publicado.

## Anatomia da definição

```json
{
  "tag": "v1.2.0",            // tag git do release
  "title": "DeepWin 1.2.0",   // título exato do release
  "version": "1.2.0",         // deve casar com VERSION na raiz
  "tag_commit": "<40 hex>",   // commit apontado pela tag (docs/automação)
  "source": "<40 hex>",       // commit aceito pelos workflows de build
  "notes": "packaging/release-notes-1.2.0.md",
  "release_only": ["..."],    // arquivos que podem diferir entre source e HEAD
  "builds": [                 // um por formato: .deb, .uab, .tar.xz
    {"run": 1, "workflow": "deb.yml", "artifact": 2, "name": "deepwin-deb-amd64",
     "file": "devedu.deepin-configs_1.2.0-1_amd64.deb", "digest": "<sha256 do ZIP>"}
  ]
}
```

`digest` é o SHA-256 do **ZIP do artefato** (campo `digest` retornado pela API
`actions/artifacts/{id}`), não do instalador — o instalador é revalidado
contra o sidecar `.sha256` dentro do ZIP.

## Roteiro da próxima versão

1. **Bump de versão**: `VERSION`, `debian/changelog` (revisão nova, dia da
   semana correto), `linglong.yaml`, metainfo/desktop conforme aplicável.
   Sem alterar `packaging/release-notes-1.1.0.md` nem a definição v1.1.0.
2. **Aceite de código**: commit do código na `main`, três workflows verdes
   (Debian, Linyaps, portátil) **no mesmo commit** de código (`source`).
   Mudanças de aplicação exigem novo aceite em VM quando tocam comportamento
   validado em sessão (atalhos, serviços, migração, restauração).
3. **Registro**: criar `<tag>.json` aqui com os IDs de run/artefato e os
   digests dos ZIPs conferidos na API; `release_only` lista o que difere
   entre `source` e o commit da tag (notas, documentação, automação).
4. **Tag**: criar a tag no commit pós-documentação (`tag_commit`); a diferença
   entre `source` e a tag deve estar inteira em `release_only`.
5. **Notas**: escrever `packaging/release-notes-<versão>.md`.
6. **Publicação**: dispatch manual de `release.yml` com o nome da definição.
   O publicador confere proveniência dos runs, digests dos ZIPs e checksums
   dos instaladores, cria o rascunho, confere os sete anexos remotos e só
   então publica. Falha depois do rascunho: inspecionar o estado antes de
   reexecutar (o rascunho existente é retomado por ID e recusado se editado).

## Revalidação de ambiente (aceite)

- Mudança de **comportamento** da aplicação: repetir o aceite de VM nas
  áreas tocadas (ver `continuidade-desenvolvimento.md` para o histórico de
  falhas que só apareceram em sessão gráfica completa).
- Atualização de **Linyaps**: rever a matriz de acesso do sandbox
  (`matriz-acesso-linyaps.md`) e os diretórios XDG compartilhados.
- Mudança de **major do Qt** ou alvo com Qt < 6.8: revisar ABI do plugin da
  calculadora (ver `analise-gui-deepin.md`).
- O aceite publicado do 1.1.0 é Deepin 25 amd64/X11; outros alvos são
  entregas novas, não patches.
