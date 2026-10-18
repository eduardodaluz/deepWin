# Espelho do builder Linyaps

`bin/build-uab` usa o builder oficial 1.13.8 amd64, fixado em:

```text
registry.cn-hangzhou.aliyuncs.com/linyaps/builder@sha256:1ef5b6244f3a7f8b2227e88d171bd0b6cda7cb7c4310a609a70a70e35f08b85b
```

O registro Aliyun falhou repetidamente nos runners do GitHub, antes da
compilação. O espelho deve conter a mesma imagem; não há necessidade de
reconstruir o builder ou copiar o cache de Base/Runtime do volume local.

O espelho publicado em 18/10/2026 tem a referência:

```text
ghcr.io/eduardodaluz/linyaps-builder@sha256:9170f635112d5068ef815d6e55d6bd3969e668151bd31a33ca48086f53fd372a
```

O digest do manifesto no destino difere do original; o ID da imagem deve
permanecer igual. O pull anônimo pelo digest foi confirmado, e o workflow
usa esse espelho por padrão.

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

O workflow já define o espelho acima como padrão. Para selecionar outra
imagem, no GitHub, em Settings → Secrets and variables → Actions → Variables,
defina `DEEPWIN_BUILDER_IMAGE` como, por exemplo,
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
build, smoke tests e exportação do artefato. Remover a variável restaura o
espelho padrão no GHCR. Para usar a origem oficial na CI, configure a
variável com a referência Aliyun do início deste documento.
A publicação do builder não publica um Release do DeepWin.

## Namespaces no runner Ubuntu

O job usa `ubuntu-24.04`. Além de Docker `--privileged`, o builder executado
como usuário `builder` precisa criar user namespaces. A restrição AppArmor
do Ubuntu pode impedir essa operação com `clone failed: Operation not
permitted`, antes de compilar qualquer fonte.

Durante o passo de build, o workflow salva o valor de
`kernel.apparmor_restrict_unprivileged_userns`, ajusta-o para `0` e registra
um trap `EXIT` que restaura o valor original, inclusive se o build falhar.
Isso ocorre somente na VM descartável do GitHub; `bin/build-uab` não altera
configurações do kernel da máquina de desenvolvimento.
A restrição está descrita nas
[notas oficiais do Ubuntu 24.04](https://github.com/ubuntu/ubuntu-release-notes/blob/main/docs/24.04/index.md).

Falhas são publicadas em uma anotação por arquivo de log, com quebras de
linha escapadas. Isso preserva o diagnóstico do build quando o download
produz muitas linhas de progresso.

## Propriedade do staging

O usuário do runner pode ter UID 1001, enquanto o `builder` da imagem tem
UID 1000. Um staging pertencente ao runner impede o builder de preparar o
projeto (`stage prepare error`).

`bin/build-uab` inicia um wrapper como root no container somente para dar ao
`builder` a propriedade da cópia temporária dos fontes. A compilação,
os smoke tests e a exportação executam como `builder`, via `runuser`.
Um trap restaura o UID/GID original do staging ao sair, inclusive em erro.
O `chown -hR` não segue links; o checkout e a pasta pessoal não são montados.
