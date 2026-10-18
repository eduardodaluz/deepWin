# Espelho do builder Linyaps

`bin/build-uab` usa o builder oficial 1.13.8 amd64, fixado em:

```text
registry.cn-hangzhou.aliyuncs.com/linyaps/builder@sha256:1ef5b6244f3a7f8b2227e88d171bd0b6cda7cb7c4310a609a70a70e35f08b85b
```

O registro Aliyun falhou repetidamente nos runners do GitHub, antes da
compilação. O espelho deve conter a mesma imagem; não há necessidade de
reconstruir o builder ou copiar o cache de Base/Runtime do volume local.

## Publicar a imagem validada

Em uma máquina que alcance o registro de origem, com Docker autenticado no
GHCR da conta mantenedora:

```bash
docker login ghcr.io -u eduardodaluz
docker pull registry.cn-hangzhou.aliyuncs.com/linyaps/builder@sha256:1ef5b6244f3a7f8b2227e88d171bd0b6cda7cb7c4310a609a70a70e35f08b85b
docker tag registry.cn-hangzhou.aliyuncs.com/linyaps/builder@sha256:1ef5b6244f3a7f8b2227e88d171bd0b6cda7cb7c4310a609a70a70e35f08b85b ghcr.io/eduardodaluz/linyaps-builder:1.13.8_amd64
docker push ghcr.io/eduardodaluz/linyaps-builder:1.13.8_amd64
```

O login local requer um token pessoal clássico com `write:packages`,
conforme a [documentação do GHCR](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
Informe o token apenas ao prompt do Docker; não o grave no projeto.

Após o push, registre o digest informado pelo GHCR e torne o pacote público
nas configurações do pacote. Publicar a partir de um repositório público
não torna a imagem pública automaticamente. Confirme o pull sem credenciais
usando uma configuração Docker temporária:

```bash
deepwin_docker_config=$(mktemp -d)
docker --config "$deepwin_docker_config" pull ghcr.io/eduardodaluz/linyaps-builder:1.13.8_amd64
rmdir "$deepwin_docker_config"
```

Compare o ID da imagem de origem e o da imagem espelhada com
`docker image inspect --format '{{.Id}}' REFERENCIA`. Eles devem ser iguais.

## Selecionar o espelho

No GitHub, em Settings → Secrets and variables → Actions → Variables,
defina `DEEPWIN_BUILDER_IMAGE` como
`ghcr.io/eduardodaluz/linyaps-builder@sha256:DIGEST_DO_PUSH`.
Use o digest efetivamente retornado pelo destino. O workflow usa essa
variável tanto no passo de download quanto em `bin/build-uab`.

Para reproduzir o build localmente:

```bash
DEEPWIN_BUILDER_IMAGE=ghcr.io/eduardodaluz/linyaps-builder:1.13.8_amd64 ./bin/build-uab --offline
```

`--offline` requer o cache local de Base/Runtime já preparado; no primeiro
build, omita essa opção. O override troca somente a origem da imagem, sem
alterar os slots em `linglong.yaml`.

Execute novamente o workflow **Linyaps package** e confirme download,
build, smoke tests e exportação do artefato. Até o espelho estar acessível,
a CI mantém a origem oficial como padrão. Remover a variável restaura esse
padrão. A publicação do builder não publica um Release do DeepWin.
