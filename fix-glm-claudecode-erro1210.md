# Correção: erro 1210 no `zclaude`/Claude Code usando GLM (Z.AI) no Deepin

**Erro:** `API Error: 400 [1210][Invalid API parameter, please check the documentation.]`
**Sintoma:** aparece ao enviar qualquer mensagem no Claude Code **interativo** (TUI) com a GLM configurada. O comando `zclaude -p "..."` (não-interativo) funciona normalmente — isso é uma dica rápida de que é este problema.

---

## Causa raiz (resumo)

Não parece ser problema de chave, configuração ou shell. Há relatos de uma **incompatibilidade nas versões do Claude Code posteriores à 2.1.263**: algumas requisições interativas podem combinar **sem streaming (`stream: false`) com `tools`**, combinação rejeitada pelo endpoint Anthropic da Z.AI com o código 1210. Isso é evidência de comunidade/captura de requisições, não uma confirmação oficial da causa pela Z.AI.

A versão de contorno documentada neste arquivo é a **2.1.263**. O auto-update pode substituir o binário pinado, por isso ele deve ser desativado nessa instância.

Referências: [relato no Reddit r/ZaiGLM](https://www.reddit.com/r/ZaiGLM/comments/1sejzvz/started_getting_api_error_400/), [linux.do (downgrade 2.1.263)](https://linux.do/t/topic/2877603), [códigos de erro da Z.AI](https://docs.z.ai/api-reference/api-code), [instalação do Claude Code](https://code.claude.com/docs/en/installation) e [pacote publicado no npm](https://www.npmjs.com/package/@anthropic-ai/claude-code?activeTab=versions).

## Solução no Deepin

Instalar a versão 2.1.263 num **diretório separado**, sem mexer no Claude principal. Nesta máquina, o comando público é `zclaude`, instalado por `~/dev/src/deepWin/zclaude.yml`; o wrapper continuará lendo a chave de `~/.config/zai/api_key`.

### 1. Instalar a versão pinada

No terminal do Deepin, com Node.js/npm disponíveis, rode:

```bash
PIN_ROOT="$HOME/.local/share/claude-glm"
mkdir -p "$PIN_ROOT"
npm install -g --prefix "$PIN_ROOT" @anthropic-ai/claude-code@2.1.263
```

Confira: `"$PIN_ROOT/bin/claude" --version` → deve mostrar `2.1.263`.

> O instalador nativo oficial do Claude Code é recomendado para instalações novas, mas não é usado aqui porque instalar uma segunda cópia nativa no caminho padrão poderia substituir o `claude` principal. O npm é usado somente para manter esta cópia isolada.

### 2. Criar a configuração da instância GLM

Crie o arquivo `~/.claude-glm/settings.json` (se ainda não existir):

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5.3[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-5.3-flash[1m]",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-4.7[1m]",
    "DISABLE_AUTOUPDATER": "1"
  }
}
```

> A chave não deve ser gravada neste JSON. O `zclaude` já a lê de `~/.config/zai/api_key` (ou de `ZAI_API_KEY`). O `DISABLE_AUTOUPDATER=1` impede que a versão pinada se auto-atualize.

### 3. Fazer o `zclaude` usar a cópia pinada

A fonte do wrapper (`~/dev/src/deepWin/bin/zclaude`) já foi ajustada para escolher automaticamente `~/.local/share/claude-glm/bin/claude` quando ele existir. Caso contrário, ela mantém o comportamento anterior e usa o `claude` principal. Reaplique o wrapper:

```bash
ansible-playbook -i localhost, -c local ~/dev/src/deepWin/zclaude.yml
```

### 4. Validar

Abra um terminal **novo** e:

```bash
zclaude --version      # deve mostrar 2.1.263
zclaude                # abre o TUI interativo
```

No TUI, envie "ola" — deve responder normalmente, sem erro 1210.

## Observações

- **Não faça** `npm install -g @anthropic-ai/claude-code@2.1.263` sem `--prefix`: isso pode rebaixar ou sobrescrever a instalação principal. O diretório separado resolve esse problema.
- O Claude principal (login Anthropic) continua na última versão e não é afetado.
- **Quando voltar a uma versão nova:** quando a z.ai aceitar requisições não-streaming com tools (ou uma versão do Claude Code corrigir a regressão), atualize o pino com:
  `npm install -g --prefix "$HOME/.local/share/claude-glm" @anthropic-ai/claude-code@<versao>`
- Como conferir se já pode sair do pino: `zclaude -p "ola"` sempre funcionou; o teste que importa é mandar mensagem no **TUI interativo** na versão nova.
- A lista de modelos pode mudar; confirme os nomes disponíveis no endpoint `GET /v1/models` antes de trocar os valores do JSON.
