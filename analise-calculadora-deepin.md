# Vírgula decimal na calculadora Deepin

## Causa e integração

O tratamento de teclado dos modos básico e científico tem uma ação explícita
para `Qt::Key_Period`, que chama `enterPointEvent()`. Não há ação equivalente
para `Qt::Key_Comma`. A apresentação regional pode usar vírgula mesmo com essa
restrição no teclado. Alterar o idioma do sistema não adiciona o caso ausente.

O DeepWin fornece um `QGenericPlugin` Qt 6. O launcher da calculadora acrescenta
a pasta privada ao `QT_PLUGIN_PATH`, preservando os caminhos já definidos pelo
runtime, e solicita o plugin por `QT_QPA_GENERIC_PLUGINS`. Para Linglong, essas
variáveis são definidas dentro do container, após a preparação do runtime.
Não é necessário alterar arquivos do pacote instalado.

O filtro atua somente se `applicationName()` for `deepin-calculator`, no `InputEdit`
ou `MainWindow`, para a tecla vírgula sem modificadores ou com `KeypadModifier`.
Encaminha um `QKeyEvent` decimal à própria calculadora, na mesma chamada e na mesma
ordem. Preserva tipo, modificadores, repetição, contagem e timestamp. A tecla ponto,
os atalhos e os demais aplicativos seguem o tratamento original.

A flag é verificada em cada evento. Desativar remove a flag e a sobreposição de
launcher, permitindo rollback mesmo na janela que já carregou o plugin. Ativar
exige reabrir a calculadora pelo menu. O controlador integra esse estado ao backup
individual do painel e recusa remover sobreposições ou flags editadas pelo usuário.
O catálogo nativo é atualizado por `ApplicationManager1.ReloadApplications()`
para que menu e barra usem o novo comando. A configuração não injeta o plugin
globalmente na sessão.

A compatibilidade validada é com a calculadora Qt 6 distribuída como
`org.deepin.calculator` 6.5.35.1. Outros launchers oficiais de mesmo formato são
aceitos, mas mudanças nas classes de entrada ou de ABI podem exigir adaptação.
O modo programador não oferece entrada de números decimais.

## Validação

A suíte inclui teste do plugin compilado com Qt em modo offscreen: vírgula,
teclado numérico, 3.000 teclas sem intervalo, preservação de outros campos e
aplicativos, Shift/ponto e desativação sem reiniciar. Testes do controlador
verificam ownership do launcher, backups, falha parcial e rollback independente.
A calculadora real também foi usada em instância descartável para validar a soma
`1,5 + 0,5 = 2`. Os arquivos e as contas da instância do usuário são preservados.

Foi avaliada uma captura X11 por janela. Ela apresentou falhas no encaminhamento
de eventos rápidos ao Qt e foi descartada; não há daemon de teclado na solução.

## Referências

- [Tratamento básico oficial](https://github.com/linuxdeepin/deepin-calculator/blob/master/src/widgets/basicmodule.cpp)
- [Tratamento científico oficial](https://github.com/linuxdeepin/deepin-calculator/blob/master/src/widgets/scientificmodule.cpp)
- [QGenericPlugin](https://doc.qt.io/qt-6/qgenericplugin.html)
- [QObject::installEventFilter](https://doc.qt.io/qt-6/qobject.html#installEventFilter)
