#include <DApplication>
#include <DComboBox>
#include <DFrame>
#include <DLabel>
#include <DMainWindow>
#include <DDialog>
#include <DPushButton>
#include <DSpinner>
#include <DSwitchButton>
#include <DTitlebar>
#include <QCloseEvent>
#include <QCompleter>
#include <QButtonGroup>
#include <QCommandLineParser>
#include <QDateTime>
#include <QDir>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QIcon>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QScrollArea>
#include <QSignalBlocker>
#include <QTimer>
#include <QVBoxLayout>
#include <cstdio>

DWIDGET_USE_NAMESPACE

struct FeatureRow {
    DFrame *frame;
    DLabel *status;
    DLabel *note;
    DSwitchButton *toggle;
    QString category;
    bool available = false;
};

class SettingsWindow : public DMainWindow {
public:
    SettingsWindow(QString controller, bool smoke, QString screenshot, int section)
        : backend(std::move(controller)), screenshotPath(std::move(screenshot)), smokeTest(smoke) {
        currentCategory = section;
        setWindowTitle("DeepWin");
        setWindowIcon(QIcon::fromTheme("preferences-system"));
        setMinimumSize(800, 620);
        resize(1020, 790);
        titlebar()->setTitle("DeepWin");
        titlebar()->setIcon(QIcon::fromTheme("preferences-system"));

        auto *sidebar = new QWidget;
        auto *sideLayout = new QVBoxLayout(sidebar);
        sideLayout->setContentsMargins(12, 20, 12, 16);
        auto *sideTitle = new DLabel("MEUS AJUSTES");
        sideTitle->setForegroundRole(Dtk::Gui::DPalette::TextTips);
        sideLayout->addWidget(sideTitle);
        auto *navigation = new QButtonGroup(this);
        navigation->setExclusive(true);
        const QStringList names = {"Visão geral", "Produtividade", "Aparência", "Ferramentas"};
        const QStringList icons = {"preferences-system", "preferences-desktop-keyboard-shortcuts",
                                   "preferences-desktop-wallpaper", "applications-utilities"};
        for (int i = 0; i < names.size(); ++i) {
            auto *button = new DPushButton(names[i]);
            button->setIcon(QIcon::fromTheme(icons[i]));
            button->setCheckable(true);
            button->setChecked(i == section);
            button->setFixedHeight(44);
            navigation->addButton(button);
            sideLayout->addWidget(button);
            connect(button, &DPushButton::clicked, this, [this, i] {
                currentCategory = i;
                filterRows();
            });
        }
        sideLayout->addStretch(1);
        auto *sideFoot = new DLabel("Seus ajustes,\nno seu Deepin.");
        sideFoot->setForegroundRole(Dtk::Gui::DPalette::TextTips);
        sideLayout->addWidget(sideFoot);
        setSidebarWidget(sidebar);
        setSidebarWidth(225);
        setSidebarVisible(true);

        auto *central = new QWidget;
        central->setAutoFillBackground(true);
        auto *layout = new QVBoxLayout(central);
        layout->setContentsMargins(24, 24, 24, 16);
        layout->setSpacing(16);
        auto *heading = new QHBoxLayout;
        auto *titles = new QVBoxLayout;
        pageTitle = new DLabel("Seus recursos");
        QFont titleFont = pageTitle->font();
        titleFont.setPointSize(titleFont.pointSize() + 8);
        titleFont.setWeight(QFont::DemiBold);
        pageTitle->setFont(titleFont);
        summary = new DLabel("Consultando suas configurações…");
        summary->setForegroundRole(Dtk::Gui::DPalette::TextTips);
        titles->addWidget(pageTitle);
        titles->addWidget(summary);
        heading->addLayout(titles, 1);
        spinner = new DSpinner;
        spinner->setFixedSize(24, 24);
        heading->addWidget(spinner);
        refreshButton = new DPushButton("Atualizar");
        refreshButton->setIcon(QIcon::fromTheme("view-refresh"));
        heading->addWidget(refreshButton);
        layout->addLayout(heading);

        auto *intro = new DLabel("Ative e desative seus ajustes. As alterações são aplicadas imediatamente.");
        intro->setWordWrap(true);
        layout->addWidget(intro);
        auto *scroll = new QScrollArea;
        scroll->setBackgroundRole(QPalette::Window);
        scroll->setFrameShape(QFrame::NoFrame);
        scroll->setWidgetResizable(true);
        scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        auto *content = new QWidget;
        content->setAutoFillBackground(true);
        content->setBackgroundRole(QPalette::Window);
        rowsLayout = new QVBoxLayout(content);
        rowsLayout->setContentsMargins(0, 0, 6, 0);
        rowsLayout->setSpacing(12);
        rowsLayout->addStretch();
        makeClaudeControls();
        scroll->setWidget(content);
        layout->addWidget(scroll, 1);

        message = new DLabel("Você pode restaurar os valores anteriores depois de fazer alterações.");
        message->setWordWrap(true);
        message->setForegroundRole(Dtk::Gui::DPalette::TextTips);
        message->setAccessibleName("Resultado da última operação");
        layout->addWidget(message);
        auto *footer = new QHBoxLayout;
        updated = new DLabel;
        updated->setForegroundRole(Dtk::Gui::DPalette::TextTips);
        footer->addWidget(updated, 1);
        restoreButton = new DPushButton("Restaurar alterações");
        restoreButton->setEnabled(false);
        footer->addWidget(restoreButton);
        layout->addLayout(footer);
        setCentralWidget(central);

        connect(refreshButton, &DPushButton::clicked, this, [this] { run({"status"}); });
        connect(restoreButton, &DPushButton::clicked, this, [this] {
            QStringList titles;
            for (const auto &value : model["restore_titles"].toArray()) titles << value.toString();
            DDialog dialog("Restaurar alterações do painel?",
                "Os recursos abaixo voltarão aos valores anteriores à primeira alteração:\n\n" +
                titles.join("\n"), this);
            dialog.setIcon(QIcon::fromTheme("preferences-system"));
            dialog.addButton("Cancelar");
            dialog.addButton("Restaurar", true, DDialog::ButtonRecommend);
            if (dialog.exec() == 1) run({"restore"});
        });
        connect(&process, &QProcess::finished, this, [this](int, QProcess::ExitStatus) { finished(); });
        connect(&process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
            if (error == QProcess::FailedToStart) {
                setBusy(false);
                message->setText("Não foi possível iniciar o controlador das configurações.");
                if (smokeTest) QCoreApplication::exit(1);
            }
        });
        deadline.setSingleShot(true);
        connect(&deadline, &QTimer::timeout, this, [this] {
            timedOut = true;
            process.kill();
        });
        refreshTimer.setInterval(5000);
        connect(&refreshTimer, &QTimer::timeout, this, [this] {
            if (process.state() == QProcess::NotRunning) run({"status"});
        });
        refreshTimer.start();
        QTimer::singleShot(0, this, [this] { run({"status"}); });
    }

protected:
    void closeEvent(QCloseEvent *event) override {
        if (busyAction && process.state() != QProcess::NotRunning) {
            message->setText("Aguarde a conclusão da alteração antes de fechar.");
            event->ignore();
            return;
        }
        if (process.state() != QProcess::NotRunning) { process.kill(); process.waitForFinished(1000); }
        DMainWindow::closeEvent(event);
    }

private:
    QString backend, screenshotPath;
    bool smokeTest, busyAction = false, busy = false, timedOut = false, firstResult = true;
    QProcess process;
    QTimer refreshTimer, deadline;
    QJsonObject model;
    QMap<QString, FeatureRow> rows;
    QVBoxLayout *rowsLayout;
    int currentCategory = 0;
    DLabel *pageTitle, *summary, *message, *updated;
    DPushButton *refreshButton, *restoreButton;
    DFrame *claudeFrame;
    DLabel *claudeStatus, *claudeNote;
    DComboBox *claudeChoice;
    DPushButton *claudeApply, *claudeFetch, *claudeUndo;
    bool catalogRequested = false;
    QString claudeSignature;
    DSpinner *spinner;

    void run(const QStringList &arguments) {
        if (process.state() != QProcess::NotRunning) return;
        busyAction = arguments[0] != "status" && arguments[0] != "claude-list";
        timedOut = false;
        if (busyAction) message->setText(arguments[0] == "claude-select" ?
            "Preparando a versão do Claude… Aguarde a conclusão do download e da instalação." : "Aplicando alteração…");
        else if (arguments[0] == "claude-list") message->setText("Consultando versões disponíveis…");
        setBusy(true);
        process.start("/usr/bin/python3", QStringList{backend} + arguments);
        deadline.start(arguments[0] == "claude-select" ? 300000 : 25000);
    }

    void setBusy(bool value) {
        busy = value;
        spinner->setVisible(value);
        if (value) spinner->start(); else spinner->stop();
        refreshButton->setEnabled(!value);
        restoreButton->setEnabled(!value && model["restore_count"].toInt() > 0);
        for (auto &row : rows) row.toggle->setEnabled(!value && row.available);
        const auto claude = model["claude"].toObject();
        const bool selectable = !value && !claude["override"].toBool() && !claude.contains("error");
        claudeChoice->setEnabled(selectable);
        claudeApply->setEnabled(selectable);
        claudeFetch->setEnabled(!value);
        claudeUndo->setEnabled(!value && claude["can_restore"].toBool());
    }

    void makeClaudeControls() {
        claudeFrame = new DFrame;
        claudeFrame->setFrameRounded(true);
        auto *layout = new QVBoxLayout(claudeFrame);
        layout->setContentsMargins(18, 16, 18, 16);
        auto *title = new DLabel("Versão do Claude para zclaude");
        QFont font = title->font(); font.setWeight(QFont::DemiBold); title->setFont(font);
        layout->addWidget(title);
        claudeStatus = new DLabel("Consultando versão…");
        claudeStatus->setWordWrap(true);
        layout->addWidget(claudeStatus);
        claudeNote = new DLabel;
        claudeNote->setWordWrap(true);
        claudeNote->setForegroundRole(Dtk::Gui::DPalette::TextTips);
        layout->addWidget(claudeNote);
        auto *choiceRow = new QHBoxLayout;
        claudeChoice = new DComboBox;
        claudeChoice->setObjectName("claude-version");
        claudeChoice->setAccessibleName("Canal ou versão do Claude");
        claudeChoice->setEditable(true);
        claudeChoice->setInsertPolicy(QComboBox::NoInsert);
        claudeChoice->setMaxVisibleItems(14);
        claudeChoice->setMinimumWidth(180);
        claudeChoice->completer()->setCompletionMode(QCompleter::PopupCompletion);
        claudeChoice->completer()->setFilterMode(Qt::MatchContains);
        choiceRow->addWidget(claudeChoice, 1);
        claudeApply = new DPushButton("Aplicar");
        claudeApply->setObjectName("claude-apply");
        choiceRow->addWidget(claudeApply);
        layout->addLayout(choiceRow);
        auto *actions = new QHBoxLayout;
        claudeFetch = new DPushButton("Buscar versões");
        claudeUndo = new DPushButton("Desfazer última troca");
        claudeUndo->setObjectName("claude-undo");
        actions->addWidget(claudeFetch);
        actions->addWidget(claudeUndo);
        actions->addStretch();
        layout->addLayout(actions);
        rowsLayout->insertWidget(rowsLayout->count() - 1, claudeFrame);
        connect(claudeFetch, &DPushButton::clicked, this, [this] { run({"claude-list"}); });
        connect(claudeUndo, &DPushButton::clicked, this, [this] { run({"claude-restore"}); });
        connect(claudeApply, &DPushButton::clicked, this, [this] {
            const auto text = claudeChoice->currentText().trimmed();
            const auto choice = text == claudeChoice->itemText(claudeChoice->currentIndex()) ?
                claudeChoice->currentData().toString() : text;
            if (choice == "legacy" || choice.isEmpty()) {
                message->setText("Selecione Stable, Claude do sistema ou um número de versão.");
                return;
            }
            run({"claude-select", choice});
        });
    }

    void renderClaude() {
        const auto claude = model["claude"].toObject();
        const auto mode = claude["mode"].toString();
        const auto version = claude["version"].toString();
        const auto stable = claude["stable"].toString();
        const auto desired = mode == "pinned" ? version : mode;
        const QString signature = mode + ":" + version + ":" + stable + ":" +
            QString::fromUtf8(QJsonDocument(claude["versions"].toArray()).toJson(QJsonDocument::Compact));
        if (signature != claudeSignature) {
            claudeSignature = signature;
            // Preservar a escolha e o texto digitado durante a atualização periódica.
            const auto pendingText = claudeChoice->currentText();
            const auto pendingChoice = claudeChoice->currentData().toString();
            const bool edited = pendingText != claudeChoice->itemText(claudeChoice->currentIndex());
            const bool first = claudeChoice->count() == 0;
            const QSignalBlocker blocker(claudeChoice);
            claudeChoice->clear();
            if (mode == "legacy") claudeChoice->addItem("Configuração anterior" +
                (version.isEmpty() ? QString() : " · " + version), "legacy");
            claudeChoice->addItem(stable.isEmpty() ? "Stable · atualização automática" :
                "Stable · " + stable + " · atualização automática", "stable");
            claudeChoice->addItem("Claude do sistema", "system");
            for (const auto &value : claude["versions"].toArray())
                claudeChoice->addItem(value.toString(), value.toString());
            if (mode == "pinned" && claudeChoice->findData(version) < 0)
                claudeChoice->addItem(version, version);
            int index = claudeChoice->findData(first ? desired : pendingChoice);
            if (index < 0) index = claudeChoice->findData(desired);
            if (index >= 0) claudeChoice->setCurrentIndex(index);
            if (!first && edited && !pendingText.isEmpty()) claudeChoice->setEditText(pendingText);
        }
        QString label;
        if (mode == "stable") label = "Canal Stable · instalada: " + version;
        else if (mode == "pinned") label = "Versão fixa: " + version;
        else if (mode == "system") label = "Usando o Claude do sistema";
        else label = version.isEmpty() ? "Usando a configuração anterior do zclaude" : "Configuração anterior · " + version;
        claudeStatus->setText(claude.contains("error") ? claude["error"].toString() : label);
        QString note = "A mudança vale ao abrir o zclaude novamente. Stable verifica atualizações em segundo plano uma vez por dia; versões fixas permanecem selecionadas.";
        if (claude["override"].toBool()) note = "ZCLAUDE_CLAUDE_BIN está definido no ambiente. Remova essa substituição para selecionar pela interface.";
        if (!claude["update_error"].toString().isEmpty()) note += "\nA última atualização falhou; a versão instalada foi mantida.";
        claudeNote->setText(note);
    }

    void makeRow(const QJsonObject &feature) {
        const QString id = feature["id"].toString();
        auto *frame = new DFrame;
        frame->setFrameRounded(true);
        auto *layout = new QHBoxLayout(frame);
        layout->setContentsMargins(18, 16, 18, 16);
        layout->setSpacing(16);
        auto *text = new QVBoxLayout;
        text->setSpacing(5);
        auto *title = new DLabel(feature["title"].toString());
        title->setWordWrap(true);
        QFont font = title->font(); font.setWeight(QFont::DemiBold); title->setFont(font);
        auto *description = new DLabel(feature["description"].toString());
        description->setWordWrap(true);
        description->setForegroundRole(Dtk::Gui::DPalette::TextTips);
        auto *status = new DLabel;
        auto *note = new DLabel;
        note->setWordWrap(true);
        note->setForegroundRole(Dtk::Gui::DPalette::TextTips);
        text->addWidget(title);
        text->addWidget(description);
        text->addWidget(status);
        text->addWidget(note);
        layout->addLayout(text, 1);
        auto *toggle = new DSwitchButton;
        toggle->setObjectName(id);
        toggle->setAccessibleName(feature["title"].toString());
        layout->addWidget(toggle);
        rowsLayout->insertWidget(rowsLayout->indexOf(claudeFrame), frame);
        rows.insert(id, {frame, status, note, toggle, feature["category"].toString(), false});
        connect(toggle, &QAbstractButton::clicked, this, [this, id](bool checked) {
            run({"set", id, checked ? "on" : "off"});
        });
    }

    void render() {
        int count = 0, active = 0;
        for (const auto &value : model["features"].toArray()) {
            const auto feature = value.toObject();
            const auto id = feature["id"].toString();
            if (!rows.contains(id)) makeRow(feature);
            auto &row = rows[id];
            const QSignalBlocker blocker(row.toggle);
            row.available = feature["available"].toBool();
            row.toggle->setChecked(feature["enabled"].toBool());
            row.toggle->setEnabled(row.available && !busy);
            row.status->setText(feature["status"].toString());
            if (feature["enabled"].toBool()) row.status->setForegroundRole(QPalette::Link);
            else row.status->setForegroundRole(Dtk::Gui::DPalette::TextTips);
            const auto note = feature.value(row.available ? "note" : "error").toString();
            row.note->setText(note);
            row.note->setVisible(!note.isEmpty());
            ++count;
            if (feature["enabled"].toBool()) ++active;
        }
        summary->setText(QString("%1 de %2 recursos ativos").arg(active).arg(count));
        const int restorable = model["restore_count"].toInt();
        restoreButton->setText(restorable ? QString("Restaurar alterações (%1)").arg(restorable) : "Restaurar alterações");
        restoreButton->setEnabled(!busy && restorable > 0);
        updated->setText("Atualizado às " + QDateTime::currentDateTime().toString("HH:mm:ss"));
        renderClaude();
        filterRows();
    }

    void filterRows() {
        const int selected = currentCategory;
        const QStringList titles = {"Seus recursos", "Produtividade", "Aparência", "Ferramentas"};
        pageTitle->setText(titles.value(selected, titles[0]));
        claudeFrame->setVisible(selected == 0 || selected == 3);
        if (selected == 3 && !smokeTest && !catalogRequested && !busy) {
            catalogRequested = true;
            QTimer::singleShot(0, this, [this] { run({"claude-list"}); });
        }
        for (auto &row : rows) row.frame->setVisible(selected == 0 ||
            (selected == 1 && (row.category == "Produtividade" || row.category == "Atalhos")) ||
            (selected == 2 && row.category == "Aparência") ||
            (selected == 3 && row.category == "Ferramentas"));
    }

    void finished() {
        deadline.stop();
        QJsonParseError error;
        const auto result = QJsonDocument::fromJson(process.readAllStandardOutput(), &error).object();
        const bool ok = !timedOut && error.error == QJsonParseError::NoError && result["ok"].toBool();
        if (ok) {
            model = result;
            if (!result["message"].toString().isEmpty()) message->setText(result["message"].toString());
        } else {
            message->setText(timedOut ? "A operação demorou mais que o esperado. Atualize o painel para conferir o estado." :
                result["message"].toString("Não foi possível consultar as configurações da sessão."));
        }
        setBusy(false);
        render();
        if (firstResult) {
            firstResult = false;
            if (smokeTest || !screenshotPath.isEmpty()) {
                QTimer::singleShot(600, this, [this, ok] {
                    bool valid = ok && rows.size() == 8 &&
                        claudeChoice->findData("stable") >= 0 && claudeChoice->findData("system") >= 0;
                    for (const auto &row : rows) valid = valid && row.available;
                    if (!screenshotPath.isEmpty()) valid = grab().save(screenshotPath) && valid;
                    if (smokeTest) {
                        std::printf("%s GUI DTK: %lld recursos consultados\n", valid ? "PASS" : "FAIL", static_cast<long long>(rows.size()));
                        QCoreApplication::exit(valid ? 0 : 1);
                    }
                });
            }
        }
    }
};

int main(int argc, char **argv) {
    DApplication app(argc, argv);
    app.setOrganizationName("devedu");
    app.setApplicationName("deepwin");
    app.setDesktopFileName("devedu.deepin-configs");
    app.setApplicationDisplayName("DeepWin");
    app.setApplicationVersion("1.0.0");
    app.setProductName("DeepWin");
    app.setApplicationDescription("Controle seus ajustes pessoais do Deepin.");
    app.setWindowIcon(QIcon::fromTheme("preferences-system"));
    app.loadTranslator();
    QCommandLineParser parser;
    parser.addHelpOption();
    parser.addVersionOption();
    parser.addOption({"backend", "Caminho do controlador Python.", "arquivo"});
    parser.addOption({"smoke-test", "Consultar recursos, validar a GUI e sair, sem alterar configurações."});
    parser.addOption({"section", "Seção inicial: overview, productivity, appearance ou tools.", "seção", "overview"});
    parser.addOption({"screenshot", "Salvar uma captura da janela.", "arquivo"});
    parser.process(app);
    if (!parser.isSet("backend")) parser.showHelp(1);
    if (!parser.isSet("smoke-test") && !app.setSingleInstance("devedu.deepin-configs")) return 0;
    const QStringList sections = {"overview", "productivity", "appearance", "tools"};
    const int section = sections.indexOf(parser.value("section"));
    if (section < 0) parser.showHelp(1);
    SettingsWindow window(parser.value("backend"), parser.isSet("smoke-test"), parser.value("screenshot"), section);
    QObject::connect(&app, &DApplication::newInstanceStarted, &window, [&window] {
        window.showNormal(); window.raise(); window.activateWindow();
    });
    window.show();
    return app.exec();
}
