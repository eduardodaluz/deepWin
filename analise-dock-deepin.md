# Miniaturas ao clicar em grupos do dock

## Integração nativa

O dock fornecido pelo `dde-shell` usa `AppItem.qml` para tratar cada ícone.
A implementação de referência é a versão 2.0.52. Nela, o hover inicia um timer
que chama `taskmanager.Applet.requestPreview(...)`, enquanto o clique chama
`TaskManager.requestActivate(index)`. As configurações de agrupamento não
oferecem uma chave para trocar essas ações.

A alteração insere uma condição no clique: para duas ou mais janelas, preparar
as coordenadas com `onEntered()`, interromper a espera do timer e disparar sua
prévia imediatamente. O clique não solicita a ativação de uma janela do grupo.
O próprio Deepin continua responsável pelas miniaturas e pela seleção.

A prévia ao passar o mouse, o clique em uma única janela, o lançamento de um
aplicativo e o menu de contexto mantêm seus fluxos nativos. A mudança não usa
interceptação global de mouse, posição fixa de ícones ou captura própria das
janelas.

## Instalação e reversão

O carregador do `dde-shell` procura pacotes nas localizações de dados XDG e
prioriza o pacote do usuário. O DeepWin gera a personalização a partir do pacote
instalado do sistema, preservando seus componentes, recursos e traduções. O
repositório contém somente o código que gera e valida a alteração.

O switch em Aparência cria ou remove esse pacote e recarrega
`dde-shell@DDE.service`. O estado inicial é integrado ao backup e à restauração
do painel. Personalizações locais desconhecidas e mudanças manuais no pacote
ou no drop-in são preservadas e impedem a sobrescrita automática.

Um `ExecStartPre` de usuário verifica os arquivos nativos a cada inicialização
do shell e regenera a cópia quando eles mudam. Se os pontos de integração
ficarem incompatíveis, remove somente a personalização gerada e permite que o
shell carregue o pacote original. O prefixo de tolerância a erro no drop-in
impede que uma falha do helper bloqueie a inicialização da barra.

O helper e o drop-in usam os diretórios XDG de dados e configuração do usuário.
Remover somente a interface do DeepWin preserva essa integração; desativar seu
switch remove o ajuste e o drop-in.

## Validação

Os testes cobrem as decisões de clique, conflitos com personalizações,
atualizações compatíveis e incompatíveis, falhas de recarga e rollback. A
precedência do pacote de usuário pode ser verificada com o próprio carregador
em uma sessão D-Bus privada, sem iniciar outro dock visível.

`tests/verify_dock_preview.py` cria duas janelas GTK descartáveis, verifica seu
agrupamento, habilita o recurso e confirma que o clique abre a prévia sem mudar
a janela ativa. Depois seleciona uma miniatura e restaura o estado original em
um bloco `finally`. Esse teste exige sessão X11 desbloqueada e DeepWin instalado.
A compatibilidade visual em Wayland precisa de validação específica.

## Código de referência

- [Descoberta e precedência de pacotes](https://github.com/linuxdeepin/dde-shell/blob/2.0.52/frame/pluginloader.cpp)
- [Hover e clique em AppItem.qml](https://github.com/linuxdeepin/dde-shell/blob/2.0.52/panels/dock/taskmanager/package/AppItem.qml)
- [Filtragem e solicitação da prévia nativa](https://github.com/linuxdeepin/dde-shell/blob/2.0.52/panels/dock/taskmanager/taskmanager.cpp)
