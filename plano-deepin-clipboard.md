# Plano: Enter para selecionar e colar no histórico do Deepin

Status: implementação criada em 16/10/2026. Instalação e validações descritas
no README. A implementação usa o monitor nativo do Deepin pelo D-Bus e
libX11/libXfixes via ctypes, dispensando a dependência de python-xlib prevista
inicialmente. O prazo foi ajustado para 1,5 segundo porque o próprio Deepin
aplica a seleção após cerca de 500 ms.

## Resultado esperado

Com um campo de texto em foco, abrir o histórico com Win+V, escolher um item
com as setas e pressionar Enter deve selecionar esse item, fechar o histórico
e executar uma única colagem no aplicativo de origem.

O Enter continua sendo entregue ao Deepin para realizar a seleção normalmente.
Escape, fechamento por clique e troca de aplicativo cancelam a colagem pendente.

## Ambiente confirmado

- Deepin 25, sessão X11 e pacote `dde-clipboard` versão `1:6.1.33`.
- Python 3, `xdotool`, `xprop` e Ansible já instalados.
- `python-xlib` não é necessário na arquitetura implementada.
- Não foi encontrada opção de colagem automática nos metadados de configuração
  instalados do histórico.
- O diagnóstico e os testes gráficos foram executados na sessão do usuário
  com acesso fora do sandbox.

## 1. Confirmar os eventos antes de implementar

Criar um modo de diagnóstico que registre apenas identificadores de janelas,
mudanças de foco e eventos relevantes de confirmação/cancelamento. Não registrar
texto digitado nem conteúdo da área de transferência.

Validar na sessão real:

1. Identificar a janela do histórico por `WM_CLASS` e sua relação com o processo
   `dde-clipboard`, sem depender do título traduzido da janela.
2. Verificar se a janela aparece como ativa em `_NET_ACTIVE_WINDOW`, se mantém
   o foco em uma janela filha ou se usa captura de teclado.
3. Confirmar se Enter e Enter numérico selecionam o item e fecham o histórico.
4. Medir a sequência entre confirmação, atualização da seleção CLIPBOARD,
   fechamento do histórico e retorno do foco.
5. Verificar o comportamento com a lista vazia, diálogos e campos de busca,
   se existirem, para não tratar qualquer Enter dentro do processo como seleção.

Decisão após o diagnóstico: usar o monitor de eventos org.deepin.dde.XEventMonitor1,
o sinal clipboardVisibleChanged e as notificações XFIXES de alteração de
CLIPBOARD. Não capturar nem bloquear globalmente o Enter. Não é necessário
usar a extensão RECORD.

Critério para avançar: distinguir confirmação de item e cancelamento, além de
identificar com segurança o destino da colagem. Se os eventos externos não
permitirem isso, revisar a abordagem antes de ativar qualquer automação.

## 2. Implementar o fluxo

O script proposto é `bin/deepin-clipboard-autopaste`, executado continuamente
na sessão do usuário e orientado a eventos, sem consultar o teclado em um loop
de comandos shell.

Fluxo: inativo → histórico aberto → confirmação pendente → colar → inativo.

- Ao abrir o histórico, guardar a janela que estava ativa imediatamente antes.
  Se não houver um destino válido, não armar a colagem.
- Ao detectar Enter confirmando um item, deixar o Deepin processar a tecla.
  Aceitar uma única confirmação por abertura e ignorar repetição da tecla.
- Esperar o histórico fechar, a seleção ficar disponível e o Enter ser solto.
  Aguardar também a liberação dos modificadores que alterariam Ctrl+V.
- Confirmar que a janela de origem continua existindo e recuperou o foco.
  Cancelar se o usuário escolher outra janela ou clicar para mudar o destino.
- Enviar Ctrl+V nos aplicativos comuns ou Ctrl+Shift+V nos terminais reconhecidos,
  uma única vez com `xdotool`, depois da última verificação de
  foco. Não forçar a ativação de uma janela que o usuário acabou de abandonar.
- Usar prazo máximo de espera de 1,5 segundo, ajustável após os
  testes. Ao expirar, cancelar a operação e voltar ao estado inativo.

Não depender apenas de um atraso fixo ou de uma mudança no conteúdo do clipboard:
o usuário pode selecionar novamente o mesmo item. O diagnóstico deve indicar
qual sinal de conclusão é utilizável nessa versão do Deepin.

A colagem usa Ctrl+V nos aplicativos comuns. Terminais conhecidos são identificados
pelos nomes exatos de WM_CLASS e recebem Ctrl+Shift+V. Atalhos personalizados e
terminais embutidos em outros aplicativos dependem de uma regra específica.
O foco de uma janela não identifica sozinho o campo interno de um aplicativo;
essa limitação e a pequena corrida entre verificar o foco e enviar a tecla devem
ser avaliadas nos testes.

## 3. Testar antes da ativação permanente

Primeiro executar em modo de simulação: informar quando colaria e em qual
janela, sem enviar teclas. Depois testar a colagem em um editor com conteúdo
descartável.

Casos de aceitação:

- Texto simples, acentos, várias linhas e seleção de um item antigo.
- Selecionar o mesmo item duas vezes em aberturas consecutivas.
- Enter principal e numérico; segurar Enter não deve duplicar a colagem.
- Escape, lista vazia, diálogos e fechamento sem confirmação não colam.
- Alt+Tab, clique fora ou fechamento do destino durante a espera cancelam.
- Enter em outros aplicativos mantém seu comportamento habitual.
- Testar um editor, um navegador e o aplicativo em que o recurso será usado.
- Imagens e arquivos: verificar separadamente em destinos compatíveis.
- Falha ao acessar X11 e reinício do histórico geram recuperação controlada.

Criar testes automatizados para as decisões de estado, principalmente eventos
fora de ordem, cancelamentos, repetição e tempo esgotado. Complementar com os
testes gráficos: testes de estado sozinhos não comprovam foco ou colagem real.

## 4. Instalar e permitir reversão

Após os testes, criar `deepin-clipboard.yml` para instalar o script e um serviço
`systemd --user` associado à sessão gráfica. Confirmar que o serviço recebe
DISPLAY e a autorização X11 da sessão, sem valores fixos.

O serviço deve impedir instâncias duplicadas, registrar apenas informações de
operação e tolerar o reinício do histórico. Manter Win+V com sua configuração
atual, caso o diagnóstico confirme que isso é suficiente.

Documentar instalação, consulta de status, parada e desativação. Parar o serviço
deve restaurar imediatamente o comportamento original. Só habilitar o início
automático depois da validação na sessão real.

## Validação realizada

- 18 testes automatizados das decisões de colagem, cancelamento e escolha
  do atalho por classe de janela passaram.
- Teste gráfico com editor GTK: acentos e várias linhas, Enter numérico,
  mesmo item novamente, item antigo, Escape, troca de janela, Enter fora do
  histórico e Enter segurado. Quatro colagens autorizadas, sem duplicação.
- Instalação em simulação e reaplicação idempotente: nenhuma alteração na
  segunda execução.
- Rollback executado: serviço parado e arquivos instalados removidos.
- O serviço recebe DISPLAY e XAUTHORITY da sessão, sem valores fixos.
- Deepin Terminal, Kitty e Alacritty validados com Win+V e Enter usando Ctrl+Shift+V, com um
  leitor de bytes temporário que não executa o texto colado.
- Navegadores, imagens e arquivos continuam dependendo de validação específica.

## Referências técnicas

- [Confirmação e atraso da seleção na versão instalada](https://github.com/linuxdeepin/dde-clipboard/blob/6.1.33/dde-clipboard/itemwidget.cpp)
- [Sinais de visibilidade do histórico](https://github.com/linuxdeepin/dde-clipboard/blob/6.1.33/dde-clipboard/mainwindow.cpp)
- [Monitor de eventos nativo](https://github.com/linuxdeepin/dde-daemon/blob/master/x_event_monitor1/manager.go)
