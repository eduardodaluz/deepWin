# Plano da correção do atalho de captura (daemon antigo de keybinding)

Design completo para implementação futura da correção definitiva da
regressão do atalho de captura na geração antiga do serviço de atalhos do
Deepin (`dde-session-daemon`). O diagnóstico já foi executado e está
resumido aqui com evidência; o que falta é implementar, testar e aceitar em
VM. Estimativa: meia sessão de implementação + aceite.

## O problema

No Deepin 25.2.0 (geração antiga — `org.deepin.dde.Keybinding1` servido pelo
`dde-session-daemon`, identificador curto `screenshot`), ao ativar o recurso
de captura o painel substitui `<Control><Alt>A` por `<Shift><Super>S` via
`ModifiedAccel`. Funciona na sessão corrente, mas **no login seguinte o
serviço retorna `['<Control><Alt>A', '<Shift><Super>S']`** — o padrão volta
e a combinação do painel fica acumulada (as duas ativas).

O adendo da fase 1 de 18/10/2026 previa "voltar à combinação anterior"; o
observado na VM de aceite em 19/10/2026 é a união das duas.

## Diagnóstico (evidência coletada em 19/10/2026, VM Deepin 25.2.0)

1. `gsettings get com.deepin.dde.keybinding.system screenshot` reflete o
   runtime. Experimento: gravar manualmente `['<Shift><Super>S']` no
   dsettings e reiniciar a sessão → o daemon volta com o padrão **somado**.
   O dconf é **aditivo** para este serviço: só soma, nunca remove.
2. `~/.config/deepin/dde-daemon/keybinding/custom.ini` só registra atalhos
   customizados (entradas UOS AI na VM); não há registro de modificação de
   built-ins.
3. Superfície D-Bus inspecionada (`Introspect`): `ModifiedAccel(id, tipo,
   tecla, adicionar)` é runtime-only; `EnableSystemShortcut(lista, ativo,
   isPersistente)` desabilita atalhos de sistema, não reescreve acels;
   `AddShortcutKeystroke`/`DeleteShortcutKeystroke`/`ClearShortcutKeystrokes`
   operam em atalhos customizados; não há API de remoção persistente para
   built-ins.
4. Detecção de geração: `GetShortcut(SCREENSHOT_ID)` (identificador longo)
   levanta `TypeError` do dbus-python na geração antiga (assinatura `si`) —
   mecanismo já usado por `gui/backend.py:133` (`screenshot_keys`).

Conclusão: dentro do contrato observável do daemon, a persistência de
remoção é impossível; a correção é **re-aplicar a convergência a cada
sessão**, no padrão que o projeto já usa para o clipboard
(`deepin-clipboard-autopaste.service`).

## O que já está no código (não repetir)

- `gui/backend.py` `set_screenshot`: grava no dsettings a lista **escolhida**
  (`value['active']`) em vez do valor anterior (`value['saved']`), e
  atualiza `value['saved']` antes da re-checagem final. Necessária (registra
  a intenção que a unidade vai converger) e **insuficiente** sozinha.
- `tests/test_packaged_resources.py`: dois testes de regressão
  (`test_set_screenshot_persists_chosen_keys_over_previous_value`,
  `test_set_screenshot_disable_persists_empty_key_list`). Suíte: 144.

## Desenho da correção

### 1. Helper `bin/deepin-shortcut-reapply` (novo)

Script Python executado pelo systemd uma vez por sessão. Somente stdlib no
topo; `dbus`/`gi` importados depois do bootstrap (o helper roda via systemd
no **host** no mundo Linyaps, onde as cópias beige podem ser necessárias):

```python
#!/usr/bin/python3
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'gui'))
import backend
backend.bootstrap_runtime_python()
import dbus
```

Contrato de comportamento:

- `DESTINATION/OBJECT_PATH/INTERFACE = org.deepin.dde.Keybinding1` e
  `/org/deepin/dde/Keybinding1` (mesmos de `Native.interface` no backend).
- `desired_keys()`: via `Gio.SettingsSchemaSource.get_default()`; schema
  ausente → `None` (sai 0, no-op). Retorna
  `[str(k) for k in Gio.Settings.new('com.deepin.dde.keybinding.system').get_strv('screenshot')]`.
- Conexão com retentativas: `dbus.SessionBus()` +
  `get_object` + `Interface`, até 12 tentativas com pausa de 2 s
  (`dbus.exceptions.DBusException` → novo attempt); esgotadas → mensagem e
  exit 1.
- Sonda de geração: `GetShortcut(SCREENSHOT_ID, timeout=3)`; `TypeError` →
  geração antiga (continua); sucesso → exit 0 (geração nova persiste no
  próprio serviço; unidade é inútil).
- Loop de convergência (até 12 tentativas, pausa 1 s):
  1. Ler accels atuais: `GetShortcut(SCREENSHOT_LEGACY_ID, 0)` → JSON
     → `Accels` (mesmo parse de `screenshot_keys` no backend; resposta
     inválida → exit 1).
  2. Iguais ao desejado → exit 0.
  3. Remover: para cada accel fora do desejado,
     `ModifiedAccel(LEGACY_ID, 0, key, False)`.
  4. Adicionar: para cada desejado ausente,
     `ModifiedAccel(LEGACY_ID, 0, key, True)`.
  5. Dormir 1 s e reler.
- Esgotou sem convergir → mensagem e exit 1 (o systemd registra; a unidade
  não tem `Restart` — a próxima sessão tenta de novo).

Testes (sem D-Bus real): funções puras do helper testadas com API falsa —
convergência remove/adiciona na ordem certa, estado já igual sai sem
chamadas, resposta JSON inválida falha. Espelhar o estilo das
`LegacyScreenshotTests` (falsos em `tests/test_packaged_resources.py`).

### 2. Template `packaging/systemd/deepin-shortcut-reapply.service` (novo)

```ini
# Gerenciado pelo DeepWin
[Unit]
Description=Sincronizar o atalho de captura do Deepin com a escolha do painel
After=dde-session-initialized.target
PartOf=dde-session-initialized.target
StartLimitIntervalSec=120
StartLimitBurst=3

[Service]
Type=oneshot
ExecCondition=/bin/sh -c 'test "$XDG_SESSION_TYPE" = x11 && test -n "$DISPLAY"'
ExecStart=@SHORTCUT_EXEC@
TimeoutStartSec=90
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=dde-session-initialized.target
```

Mesma estrutura do template do clipboard (que é a referência de estilo).

### 3. `gui/user_services.py`

- `SERVICE_FILES['screenshot'] = ('deepin-shortcut-reapply.service',)`.
- `prepare()`: acrescentar
  `text = text.replace('@SHORTCUT_EXEC@', command_path(runtime / 'bin/deepin-shortcut-reapply'))`
  ao lado das substituições existentes (replace em substring ausente é
  no-op — seguro para os templates das outras features).

### 4. `gui/backend.py` — três pontos de cabeamento

**`capture()`** (ramo `if feature == 'screenshot'`, hoje
`return self.native.screenshot()`): passar a devolver o estado + snapshot
da unidade, espelhando o ramo `SERVICES`:

```python
value = self.native.screenshot()
value['files'] = self.user_services.snapshot('screenshot')
if not self.user_services.existing('screenshot'):
    value['absent'] = True
return value
```

Chaves extras no dicionário são toleradas por `set_screenshot` (só lê
`active`/`saved`) e pelo status da GUI (lê `active`/`saved`/`enabled`).

**`apply()`** (ramo `elif feature == 'screenshot'`): após
`self.native.set_screenshot(values)`:

```python
# A unidade de re-sincronização só existe para o daemon antigo:
# na geração nova o próprio serviço persiste a combinação.
if self.native.screenshot_generation(self.native.keybindings()) == 'legacy':
    self.user_services.prepare('screenshot')
    self.native.call(['systemctl', '--user', 'enable',
                      'deepin-shortcut-reapply.service'])
```

Sem `start`: o runtime já converge no próprio `set_screenshot`
(`ModifiedAccel`); a unidade é para o login seguinte. Desativar o recurso
mantém a unidade habilitada — desejado vazio (`[]`) converge para "sem
atalho", mesmo contrato do `Disable` atual.

**`restore_value()`** (ramo `elif feature == 'screenshot'`, hoje só
`set_screenshot(value)`): tratar `absent`/`files` como o ramo `SERVICES`
faz, com as mesmas proteções de unidade personalizada:

```python
if value.get('absent'):
    if self.user_services.existing('screenshot'):
        if not self.user_services.managed('screenshot'):
            raise ConfigError('Uma unidade personalizada apareceu após o backup. Preserve-a antes de restaurar.')
        self.native.call(['systemctl', '--user', 'disable',
                          'deepin-shortcut-reapply.service'])
    self.user_services.restore_files('screenshot', value['files'])
elif 'files' in value:
    owned = self.user_services.managed('screenshot')
    if not owned and self.user_services.existing('screenshot'):
        raise ConfigError('Uma unidade personalizada apareceu após o backup. Preserve-a antes de restaurar.')
    self.user_services.restore_files('screenshot', value['files'])
    self.native.call(['systemctl', '--user', 'enable',
                      'deepin-shortcut-reapply.service'])
self.native.set_screenshot(value)
```

Compatibilidade de estado: os 9 backups existentes na VM não têm
`files`/`absent` na entrada do screenshot — o ramo cai direto no
`set_screenshot(value)` de hoje (nenhuma migração necessária). `restore_files`
faz `daemon-reload`; habilitar/desabilitar remove/cria o symlink em
`dde-session-initialized.target.wants`.

### 5. `resources.json`

Acrescentar aos `files` distribuídos:

```json
"bin/deepin-shortcut-reapply",
"systemd/deepin-shortcut-reapply.service"
```

(o `systemd/` do manifesto corresponde a `packaging/systemd/`, como nas
unidades existentes.)

### 6. Testes

- Helper: convergência com API falsa (ordem das chamadas remove→adiciona,
  no-op quando igual, JSON inválido).
- `user_services.prepare('screenshot')` escreve a unidade com o caminho do
  runtime substituído em `ExecStart` e marcador de propriedade.
- `apply('screenshot', True)` com `FakeNative` **estendido** (hoje falta:
  `keybindings()` → retorna `self`; `screenshot_generation(api)` →
  `'legacy'`) afirma unidade escrita + `systemctl --user enable` em
  `native.commands`; geração nova (`'new'`) não cria unidade.
- `restore_value` com entrada nova `{'absent': True, 'files': ...}` remove
  unidade; entrada antiga (sem `files`) não toca unidade; unidade
  personalizada (marcador divergente) recusa sem sobrescrever.
- Desativar persiste lista vazia no dsettings (já coberto pelo teste
  existente do dsettings).

## Aceite em VM (após implementar)

1. Suíte Python completa verde (144 + novos).
2. `bin/build-deb` candidato novo (revisão 1.1.0-4 ou versão nova — **não**
   reusar `-3`, que é o instalador publicado).
3. Instalar na VM por `apt` via SSH (sudo NOPASSWD; a senha do usuário
   `deepwin` está vazia — NP — e o polkit gráfico não funciona na sessão de
   autologin sem regra temporária).
4. Ativar/desativar o recurso de captura pelo CLI/GUI e conferir: unidade
   escrita em `~/.config/systemd/user/`, habilitada
   (`dde-session-initialized.target.wants`), `ExecStart` apontando ao
   runtime persistente, dsettings com a lista escolhida.
5. **Reboot** e conferir pós-login: `GetShortcut('screenshot')` ==
   `['<Shift><Super>S']` (ou vazio se desativado), sem `<Control><Alt>A`.
6. Restauração real (`deepwin-restore screenshot`) volta ao padrão e o
   estado pós-login converge para o restaurado.
7. Unidade personalizada com hash divergente recusa restauração
   (proteção existente do `user_services`).
8. Registrar resultados no `continuidade-desenvolvimento.md` (novo adendo)
   e mover esta pendência para concluída na tabela do "Ponto de partida".

## Notas

- **Linyaps**: a unidade é escrita por usuário e o `ExecStart` aponta para
  a cópia persistente no home — o systemd do host executa o helper com o
  Python do host; daí o `bootstrap_runtime_python()` (pydeps beige) antes
  de `import dbus`. Na VM de aceite o host já tem `python3-dbus`/`gi`, mas
  não contar com isso.
- **Geração nova (dde-shell)**: sem unidade, sem helper ativo — o serviço
  persiste via `ModifyHotkeys` (caminho já aceito na fase 1).
- O esboço de implementação desta correção chegou a ser escrito em
  19/10/2026 e foi revertido no mesmo dia (interrupção a pedido do
  mantenedor) — não há resquício no código; este documento é a
  especificação completa.
