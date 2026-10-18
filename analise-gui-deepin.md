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
| Vírgula decimal | Plugin Qt 6, filtro dentro da calculadora e sobreposição do launcher por usuário | Carregar na próxima abertura pelo menu / remover a flag e o launcher gerenciado |
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
da configuração desse timer. Em instalações novas, o painel prepara as unidades
com intervalo de uma hora; timers existentes são preservados. O playbook de
papel de parede faz apenas uma troca de imagem por chamada.

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

O modo `--smoke-test` verifica a abertura e a consulta dos dez recursos sem
alterá-los, permitindo integrações opcionais ausentes. Acrescentar
`--check-integrations` exige disponibilidade de todas as integrações. O teste gráfico
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

## Compatibilidade ABI do plugin da calculadora

Revisão antes de ampliar plataformas (referência testada: Qt 6.8 do Deepin 25):

- A superfície de API está restrita a contrato estável do Qt 6: `QGenericPlugin`,
  `QCoreApplication::installEventFilter/sendEvent/applicationName` e `QKeyEvent`.
  `nm -D` no `.so` não mostra símbolos privados; as dependências usam a tag
  pública `@Qt_6` e sonames major (`libQt6Core.so.6`), sem fixação de versão
  menor nas entradas ELF.
- Os metadados do plugin gravam Qt 6.8 (`.note.qt.metadata`, bytes `01 06 08`)
  e a referência `qt_version_tag@Qt_6.8`. O loader do Qt aceita plugins
  construídos em versão menor igual ou anterior à do runtime, e os runtimes Qt 6
  exportam as tags retroativas das versões menores anteriores. Portanto o plugin
  carrega em qualquer Qt ≥ 6.8; a série 25 é rolling e só avança.
- Recusa de carga (runtime anterior a 6.8 — fora do Deepin 25, ou runtime
  Linglong da calculadora mais antigo que o usado pela GUI) degrada sem quebrar:
  o Qt registra aviso e a calculadora abre com o teclado padrão. Limitação
  conhecida: o status do painel reflete a flag por usuário, não a carga efetiva
  do plugin, e não acusaria essa recusa.
- O teste Qt do CTest (`calculator-qt`) exercita a carga e a filtragem no Qt 6.8.

Conclusão: nenhuma garantia genérica é necessária agora, pois o alvo é Deepin 25.
Reavaliar se a série mudar de major do Qt ou se o pacote passar a visar
ambientes com Qt anterior a 6.8.

## Referências do SDK

- [DTK Widgets oficial](https://github.com/linuxdeepin/dtkwidget)
- [DTK Declarative oficial](https://github.com/linuxdeepin/dtkdeclarative)
