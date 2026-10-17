# Correção: erro 1210 no `zclaude`/Claude Code usando GLM (Z.AI) no Deepin

**Erro:** `API Error: 400 [1210][Invalid API parameter, please check the documentation.]`
**Sintoma de referência:** o erro ocorre no Claude Code **interativo** (TUI) com GLM, enquanto `zclaude -p "..."` (não-interativo) pode funcionar. Compare os dois modos para auxiliar no diagnóstico.

---

## Contexto do contorno

Este guia registra um contorno para relatos de **incompatibilidade entre determinadas versões do Claude Code e o endpoint da Z.AI**: algumas requisições interativas podem combinar **sem streaming (`stream: false`) com `tools`**, combinação rejeitada pelo endpoint Anthropic da Z.AI com o código 1210. Isso é evidência de comunidade/captura de requisições, não uma confirmação oficial da causa pela Z.AI.

A versão de contorno registrada neste arquivo é a **2.1.263**. Essa referência não significa que uma instalação nova precise de downgrade. Confirme que o problema se reproduz no seu ambiente antes de aplicar o procedimento. O auto-update pode substituir o binário pinado, por isso ele deve ser desativado nessa instância.

Referências: [relato no Reddit r/ZaiGLM](https://www.reddit.com/r/ZaiGLM/comments/1sejzvz/started_getting_api_error_400/), [linux.do (downgrade 2.1.263)](https://linux.do/t/topic/2877603), [códigos de erro da Z.AI](https://docs.z.ai/api-reference/api-code), [instalação do Claude Code](https://code.claude.com/docs/en/installation) e [pacote publicado no npm](https://www.npmjs.com/package/@anthropic-ai/claude-code?activeTab=versions).

## Seleção pela interface

Com DeepWin instalado, use **Ferramentas → Versão do Claude para zclaude** para
escolher uma versão específica ou voltar ao canal Stable. **Desfazer última
troca** recupera a seleção anterior. O procedimento manual abaixo se aplica ao
comportamento legado, antes de existir uma seleção ativa na GUI; instalar uma
cópia em `claude-glm` não substitui uma versão selecionada pelo painel.

## Procedimento manual no Deepin

O procedimento instala a versão de contorno em um **diretório separado**, preservando o Claude principal. O wrapper `bin/zclaude`, instalado pelo playbook `zclaude.yml`, usa essa cópia quando disponível. A chave é obtida de `~/.config/zai/api_key` ou das variáveis documentadas no README.

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
    "DISABLE_AUTOUPDATER": "1"
  }
}
```

> A chave não deve ser gravada neste JSON. O `zclaude` já a lê de `~/.config/zai/api_key` (ou de `ZAI_API_KEY`). O `DISABLE_AUTOUPDATER=1` impede que a versão pinada se auto-atualize.

### 3. Fazer o `zclaude` usar a cópia pinada

O wrapper `bin/zclaude` escolhe automaticamente `~/.local/share/claude-glm/bin/claude` quando ele existir. Caso contrário, usa o `claude` principal. A partir da pasta em que você clonou o DeepWin, instale ou atualize o wrapper:

```bash
ansible-playbook -i localhost, -c local zclaude.yml
```

### 4. Validar

Abra um terminal **novo** e:

```bash
zclaude --version      # deve mostrar 2.1.263
zclaude                # abre o TUI interativo
```

No TUI, envie uma mensagem de teste e confira se o erro 1210 deixou de ocorrer.

## Observações

- **Não faça** `npm install -g @anthropic-ai/claude-code@2.1.263` sem `--prefix`: isso pode rebaixar ou sobrescrever a instalação principal. O diretório separado resolve esse problema.
- O procedimento preserva a versão e a autenticação do Claude principal.
- **Quando voltar a uma versão nova:** quando a z.ai aceitar requisições não-streaming com tools (ou uma versão do Claude Code corrigir a regressão), atualize o pino com:
  `npm install -g --prefix "$HOME/.local/share/claude-glm" @anthropic-ai/claude-code@<versao>`
- Para avaliar a remoção do pino, compare o envio de mensagens no **TUI interativo** e no modo `zclaude -p "ola"` com a versão que pretende usar.
- O exemplo não fixa modelos. Se configurar modelos explicitamente, escolha os identificadores disponíveis para sua conta na Z.AI.
