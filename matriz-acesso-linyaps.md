# Matriz de acesso Linyaps — prova L1 do DeepWin

Entrega da L1 do [plano de distribuição](plano-distribuicao-deepwin.md): decidir,
com evidência, entre acesso direto do container à sessão hospedeira ou uma ponte.
Referência de ambiente: linyaps 1.14.3 em Deepin 25 (amd64), a mesma versão
presente no Deepin 25.2 de aceite.

## Método

1. Leitura do código-fonte do linyaps na tag 1.14.3 (`container_cfg_builder.cpp`,
   `container_builder.cpp`, `run_context.cpp`, gerador de unidades de usuário) e
   cruzamento com a documentação oficial 1.14.x.
2. Sonda descartável executada em 18/10/2026 dentro de um sandbox real
   (`ll-cli run org.deepin.calculator -- bash`), com verificação no host e limpeza
   completa. Todos os vereditos empíricos abaixo foram observados, não inferidos.

## Veredito de acesso do container ao host

| # | Acesso | Veredito | Evidência |
| --- | --- | --- | --- |
| 1 | D-Bus de sessão do host (socket cru, sem filtro) | Confirmado | `busctl --user` de dentro lista `org.deepin.dde.Appearance1`, `Clipboard1`, `ca.desrt.dconf` e os serviços DDE |
| 2 | Chamar serviços de sessão (kglobalaccel, Keybinding1, Appearance1, ApplicationManager1) | Confirmado | Conexão direta ao bus do host; fallback documentado na FAQ oficial |
| 3 | Possuir nome no bus de sessão | Confirmado | `RequestName` retornou `PRIMARY_OWNER`; nome morre com o container |
| 4 | `systemctl --user` controlando o manager do host | Confirmado | Sem `/run/user/1000/systemd` no container, o `systemctl` cai para o bus: listou unidades do host, leu unidade fornecida por app linyaps (`dde-calendar.service`) e aceitou `daemon-reload` |
| 5 | Escrever no `$HOME` real (`~/.config`, `~/.local/share`, `~/.local/bin`) | Confirmado | 4 arquivos-probe e um drop-in `systemd` criados de dentro existiram no host com os mesmos caminhos e timestamps |
| 6 | Unidades `--user` fornecidas pelo pacote visíveis ao manager do host | Confirmado | `$PREFIX/lib/systemd/user` → `/var/lib/linglong/entries/lib/systemd/user` → carregadas pelo systemd do host (`ExecStart` reescrito para `ll-cli run`); `com.dde.calendarserver.calendar.timer` ativa nesta máquina |
| 7 | GSettings/dconf de leitura e escrita | Confirmado | `gsettings get` de dentro; socket do dconf-service e `~/.config/dconf` montados |
| 8 | Ler o sistema do host | Confirmado | `/run/host/rootfs` (raiz, somente leitura); `usr/share/dde-shell/org.deepin.ds.dock.taskmanager/` com o QML da taskmanager legível |
| 9 | X11 | Parcial | Socket `X0` e `XAUTHORITY` expostos; conexão efetiva não provada pela sonda (sem `xdpyinfo` no runtime). Todo app GUI linyaps desta máquina abre janela no host, então a GUI é segura por observação; a verificação fina (xdotool/ctypes do helper de colagem) fica para o aceite em VM |
| 10 | Rede do host | Confirmado | Compartilhada por padrão, sem namespace |
| 11 | Escalação de privilégio | Bloqueado | Sem SUID/capabilities; grupos suplementares do usuário não entram no container — irrelevante ao DeepWin, que nunca usa root |

## O que o sandbox esconde (irrelevante ou aceito)

- `~/.ssh` e `~/.gnupg` do usuário são mascarados; `~/.linglong` é invisível de
  dentro. O DeepWin não depende de nenhum dos três.
- `XDG_RUNTIME_DIR` do app é privado por aplicativo: o `deepin-clipboard-autopaste`
  enxerga um `/run/user/1000` só seu. O lock dele funciona igual; nada do painel
  pressupõe conteúdo compartilhado nesse diretório.
- `DISPLAY` pode ser renumerado e `XAUTHORITY` aponta para `/run/linglong/Xauthority`;
  o painel não interpreta esses valores.

## Decisão registrada (L1)

**Acesso direto aprovado.** A arquitetura atual do painel — backend na sessão do
usuário escrevendo em `$HOME`, unidades geradas na ativação, `systemctl --user` e
D-Bus de sessão — funciona dentro do sandbox sem ponte, conforme itens 1–8.
O mecanismo de unidades fornecidas pelo pacote (item 6) permanece registrado como
endurecimento futuro, não como requisito desta fase.

### Riscos registrados

1. **Privatização futura de XDG**: a FAQ oficial declara intenção de redirecionar
   `XDG_CONFIG_HOME` para `~/.linglong/<id>/config`; no código 1.14.3 o
   redirecionamento só ocorre se esse diretório existir. O empacotamento e a
   documentação devem garantir que nenhum fluxo crie `~/.linglong/<id>/config`.
   Reavaliar em cada major/minor do linyaps (1.15+).
2. **Binários de apoio no sandbox**: `xdotool`, `xdg-user-dir`, `curl`, `file`,
   `gsettings` e os módulos Python `dbus`/`gi` precisam existir dentro do
   container (via dependências do pacote) ou a checagem de disponibilidade
   declarará o recurso indisponível — o painel degrada sem quebrar, mas a meta é
   disponibilidade plena no Deepin 25.
3. **Seleção de versões do Claude dentro do container**: exige `node`/`npm` no
   sandbox; o wrapper `zclaude` em si roda no host (fora do sandbox) e não é
   afetado. Se `npm` não embarcar, o recurso degrada no painel e segue
   funcional pelo terminal — comportamento a documentar na página de download.

## Consequência por recurso

| Recurso | Veredito no sandbox | Ajuste necessário |
| --- | --- | --- |
| Colar ao confirmar | OK | Embarcar `xdotool` (ou fallback de resolução) para a checagem de disponibilidade |
| Vírgula decimal | OK | Nenhum — launcher e plugin já operam com calculadora linyaps (provado na fase 1) |
| Atalhos KGlobalAccel (4) | OK | Nenhum |
| Captura de área | OK | Nenhum |
| Prévia da dock | OK | Resolver o QML de `/run/host/rootfs/usr/share/dde-shell/...` quando `/usr/share/dde-shell` não existir |
| Paisagem automática | OK | Embarcar `curl`, `file`, `xdg-user-dir` se ausentes no Base |
| Comando zclaude | OK com ressalva | Decidir entre embarcar `npm` ou documentar degradação do seletor de versões |
| GUI (deepwin-ui + backend) | OK | Embarcar `python3-dbus`/`python3-gi` no prefixo e injetar `PYTHONPATH`/`GI_TYPELIB_PATH` no launcher |

## Pendências desta fase

- Spike de build: concluído. Os slots resolvem no repo estável
  (`org.deepin.base/25.2.2` → 25.2.2.8; `org.deepin.runtime.dtk/6.7.0` →
  6.7.0.50) e o builder oficial em Docker puxa sozinho os módulos develop,
  que trazem a toolchain completa — não há necessidade do truque
  `apt --download-only`. O apt dentro do sandbox de build não é confiável
  (indexes parciais), então as dependências Python (`python3-dbus`,
  `python3-gi`, `gir1.2-glib-2.0`, `libgirepository-1.0-1`, versões beige
  fixadas) são pré-baixadas do repo beige por `bin/build-uab` e extraídas no
  build sem rede, conforme a lista `files_optional` do manifesto de recursos.
  O candidato `devedu.deepin-configs_1.1.0.0_x86_64_main.uab` foi gerado com
  smoke de importação `dbus`/`gi` aprovado dentro do sandbox.
- Aceite em VM Deepin 25 limpa, incluindo a prova fina de X11 do helper de
  colagem (item 9) e a persistência de estado após reinício do container.
