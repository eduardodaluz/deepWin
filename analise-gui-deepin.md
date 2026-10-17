# DeepWin: arquitetura da interface nativa

## SDK e compilação

A interface usa C++ com DTK 6 Widgets (`DApplication`, `DMainWindow`,
`DSwitchButton` e os componentes de diálogo e layout do Deepin), com integração
ao tema nativo. O controlador de configurações é separado da janela e usa
Python/D-Bus.

A escolha de DTK Widgets permite usar os componentes de desktop do Deepin sem
um runtime web ou bindings Python/Qt. A compilação requer os headers DTK/Qt e
os runtimes compatíveis. O script `bin/build-deepwin` usa o SDK instalado ou
extrai headers de pacotes oficiais para um cache local, sem instalar ou
atualizar bibliotecas do sistema.

## Recursos e controles

Os estados são consultados na sessão do usuário. A lista abaixo descreve as
integrações; ela não indica que os recursos estejam instalados ou habilitados.

| Recurso | Integração | Habilitar / desabilitar |
| --- | --- | --- |
| Colar ao confirmar no histórico | `deepin-clipboard-autopaste.service` | Iniciar e habilitar / parar e desabilitar o serviço do usuário |
| Próxima área de trabalho | KGlobalAccel, Ctrl+Win+→ | Adicionar / remover apenas essa combinação |
| Área de trabalho anterior | KGlobalAccel, Ctrl+Win+← | Adicionar / remover apenas essa combinação |
| Janela no próximo monitor | KGlobalAccel, Shift+Win+→ | Adicionar / remover apenas essa combinação |
| Janela no monitor anterior | KGlobalAccel, Shift+Win+← | Adicionar / remover apenas essa combinação |
| Captura de área | API de atalhos do Deepin e GSettings, Win+Shift+S | Sincronizar a combinação ativa e a configuração salva |
| Prévia ao clicar em grupos | Pacote QML de usuário do `dde-shell` | Usar a prévia nativa para duas ou mais janelas; remover o ajuste ao desabilitar |
| Paisagem automática | `deepin-wallpaper.timer` | Iniciar e habilitar / parar e desabilitar o timer; manter a imagem atual |
| Comando zclaude | Wrapper do Claude Code para Z.AI | Disponibilizar / guardar o wrapper para desativar o comando |

O `zclaude` é opcional. Seu controle representa a disponibilidade do comando;
a chave de API não precisa ser lida, exibida, alterada ou apagada pelo painel.

A rotação nativa de imagens do Deepin e o timer de download são independentes.
Quando a rotação nativa está ativa, o painel apresenta uma observação na seção
Aparência. O switch controla somente o timer de download. A frequência depende
da configuração desse timer; as unidades precisam existir previamente, pois o
playbook de papel de parede faz apenas uma troca de imagem por chamada.

Desativar um atalho remove somente a combinação listada, preservando outras
atribuições da mesma ação. A restauração usa o estado capturado pelo painel
antes da primeira alteração; ela não pressupõe a existência de um backup antigo
do arquivo de atalhos.

## Integração e reversão

- As APIs de KGlobalAccel e do daemon de atalhos do Deepin aplicam os atalhos
  imediatamente, preservando combinações alternativas e verificando conflitos.
- Os serviços são controlados pelo systemd do usuário, sem permissões de root.
- A GUI usa QProcess assíncrono para consultar ou alterar configurações; ela
  não instala um serviço permanente.
- O estado original de cada recurso é guardado antes da primeira alteração
  pelo painel. O backend permite restaurar um recurso; a interface permite
  restaurar o conjunto de alterações.
- Remover a GUI preserva os recursos e os backups de restauração.

A API de captura é desativada com `Disable` quando não há combinação. A consulta
confere a associação real para ignorar rótulos traduzidos de atalho ausente.
Ao guardar ou recuperar o wrapper, o controlador preserva conteúdo, permissões
e links simbólicos, inclusive entre sistemas de arquivos diferentes.

## Versões do Claude para zclaude

A seção Ferramentas inclui um seletor DTK de canal ou versão. O controlador
consulta as versões finais publicadas no registro oficial npm, ordenadas da
mais recente para a mais antiga. Uma versão é instalada em um diretório
separado, validada por `--version` e só então ativada por uma seleção JSON
atômica. Um bloqueio de arquivo serializa instalações, atualizações e rollback.

Stable é resolvido pelo tag `stable`, sem confundi-lo com `latest`. O wrapper
agenda uma verificação em segundo plano ao ser iniciado, no máximo uma vez por
dia. As atualizações preservam o último executável funcional e a seleção de
rollback. Versões fixas não recebem essas atualizações. As cópias gerenciadas
executam com o atualizador próprio do Claude desabilitado.

O botão de desfazer restaura a seleção anterior. Ele é separado da restauração
dos switches. A instalação principal, a chave da Z.AI e os arquivos de
configuração do Claude não são reescritos. Downloads e verificações usam um
ambiente sem as variáveis de credenciais. Remover a GUI preserva o helper e os
executáveis usados pelo `zclaude`.

## Verificação

Os testes unitários cobrem decisões de colagem, atalhos, backups, restauração,
migração de estado e movimentação do wrapper. Eles usam adaptadores simulados
para as configurações do sistema. Os comandos estão no README.

O modo `--smoke-test` consulta os nove recursos sem alterá-los; seu resultado
depende de essas integrações estarem disponíveis na sessão. O teste gráfico
`tests/verify_configs_gui.py` exige sessão desbloqueada, GUI fechada, colagem
ativa e nenhum backup pendente. Ele desativa a colagem e usa o diálogo de
restauração, preservando o estado original em um bloco `finally`.

A imagem `gui/preview.png` é uma prévia ilustrativa da interface. Os estados
exibidos nela não representam os valores iniciais de uma nova instalação.

## Identidade do aplicativo

O nome do projeto e da janela é DeepWin; o comando é `deepwin`. O identificador
do aplicativo/pacote é `devedu.deepin-configs`, também usado na entrada `.desktop`,
no controle de instância única e no diretório de estado. O instalador migra os
backups da identidade anterior antes de remover os arquivos antigos da GUI.

## Referências do SDK

- [DTK Widgets oficial](https://github.com/linuxdeepin/dtkwidget)
- [DTK Declarative oficial](https://github.com/linuxdeepin/dtkdeclarative)
