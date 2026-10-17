# DeepWin: GUI nativa para as configurações pessoais

## Análise antes da implementação — 17/10/2026

O SDK visual solicitado é o DTK do Deepin. O sistema tem os runtimes DTK 6 e
Qt 6, mas não os headers de desenvolvimento. A implementação escolhida é
C++ com DTK Widgets (`DApplication`, `DMainWindow`, `DSwitchButton` e os
componentes de diálogo e layout do Deepin). Isso usa o SDK e o tema nativos.
Os headers podem ser extraídos dos pacotes oficiais para um diretório de build
local, sem instalar ou atualizar bibliotecas do sistema.

DTK Declarative/QML também está presente, mas seus launchers de desenvolvimento
não estão disponíveis. Para este painel de configurações, DTK Widgets oferece
uma integração direta com as bibliotecas instaladas e não exige um runtime web
nem bindings Python/Qt adicionais.

## Inventário e comportamento dos controles

| Recurso | Estado observado | Habilitar / desabilitar |
| --- | --- | --- |
| Colar ao confirmar no histórico | Serviço ativo e habilitado | Iniciar e habilitar / parar e desabilitar o serviço do usuário |
| Próxima área de trabalho | Ctrl+Win+→ | Adicionar / remover apenas esse acelerador pela API KGlobalAccel |
| Área de trabalho anterior | Ctrl+Win+← | Adicionar / remover apenas esse acelerador pela API KGlobalAccel |
| Janela no próximo monitor | Shift+Win+→ | Adicionar / remover apenas esse acelerador pela API KGlobalAccel |
| Janela no monitor anterior | Shift+Win+← | Adicionar / remover apenas esse acelerador pela API KGlobalAccel |
| Captura de área | Win+Shift+S | Sincronizar o acelerador no daemon do Deepin e no GSettings |
| Paisagem automática | Timer do usuário ativo e habilitado, a cada hora | Iniciar e habilitar / parar e desabilitar o timer; manter a imagem atual |
| Comando zclaude | Wrapper instalado e executável | Disponibilizar / guardar o wrapper para desativar o comando |

O `zclaude` é um comando opcional, não uma configuração global do Claude.
O controle representa a disponibilidade desse comando. A chave de API não
precisa ser lida, exibida, alterada ou apagada pelo painel.

A rotação de imagens do Deepin também está ativa. Ela é independente do timer
de download do Unsplash. O painel informa essa diferença na seção Aparência e
limita seu switch ao download configurado neste workspace.

O backup antigo `kglobalshortcutsrc.before-deepin-shortcuts` não está presente.
Por isso, desativar um atalho significa remover somente a combinação listada,
preservando outras atribuições da mesma ação. O painel não deve inventar um
estado anterior nem reescrever todo o arquivo de atalhos.

## Integração e reversão

- Usar as APIs nativas de KGlobalAccel e do daemon de atalhos do Deepin.
  A aplicação dos atalhos pode ser imediata, sem reiniciar o KWin ou a sessão.
- Usar systemd `--user` para os serviços já instalados, sem permissões de root.
- Ler o estado real a cada atualização; não apresentar preferências fictícias.
- Guardar o estado original de cada recurso antes de sua primeira alteração
  pelo painel. Permitir restaurar essas alterações individualmente no backend
  e em conjunto pela interface.
- Separar a GUI DTK do controlador de configurações. A GUI usa QProcess
  assíncrono; o controlador usa Python/D-Bus, já disponíveis no sistema.
- Preservar atalhos alternativos, conferir conflitos e verificar as alterações.
- Instalar a GUI como aplicativo do usuário, com entrada no menu do Deepin.
  Remover a GUI não deve desativar recursos nem apagar backups de restauração.

## Validação realizada

- Compilação contra DTK 6/Qt 6 e verificação das bibliotecas carregadas.
- 43 testes automatizados, incluindo os testes anteriores da colagem.
- Desativação e restauração reais dos quatro atalhos KWin, do atalho de captura,
  do serviço de colagem e do wrapper zclaude.
- A API de captura não aceita uma lista vazia em ModifyHotkeys. O controlador
  usa Disable para esse caso e consulta a associação real para ignorar o rótulo
  traduzido de atalho ausente, independentemente do idioma.
- A movimentação do wrapper funciona também quando o backup está em outro
  sistema de arquivos, preservando conteúdo, permissões e links simbólicos.
- Interface instalada aberta na sessão real; os oito recursos foram consultados.
- Teste gráfico do switch de colagem e do diálogo DTK de restauração.
- Estado inicial dos oito recursos confirmado ao final. O timer de paisagens
  foi testado com adaptador simulado, evitando disparar downloads nos testes.
- Entrada no menu validada com desktop-file-validate.

Os testes reais restauraram os valores anteriores em blocos finally, inclusive
quando uma verificação falhou durante o desenvolvimento.

## Identidade do aplicativo

O nome do projeto e da janela é DeepWin; o comando é `deepwin`. O identificador
do aplicativo/pacote é `devedu.deepin-configs`, também usado na entrada `.desktop`,
no controle de instância única e no diretório de estado. O instalador migra os
backups da identidade anterior antes de remover os arquivos antigos da GUI.

## Referências do SDK

- [DTK Widgets oficial](https://github.com/linuxdeepin/dtkwidget)
- [DTK Declarative oficial](https://github.com/linuxdeepin/dtkdeclarative)
