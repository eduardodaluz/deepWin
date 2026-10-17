// Filtro de eventos Qt: carregado somente pelo launcher da calculadora.
#include <QGenericPlugin>
#include <QCoreApplication>
#include <QKeyEvent>
#include <QFileInfo>
class DecimalFilter : public QObject {
public:
    // O Qt possui o objeto retornado pelo QGenericPlugin (sem parent adicional).
    explicit DecimalFilter(const QString &flag) : QObject(), flag(flag) {
        qApp->installEventFilter(this);
    }
protected:
    bool eventFilter(QObject *target, QEvent *event) override {
        if (event->type() != QEvent::KeyPress && event->type() != QEvent::KeyRelease &&
            event->type() != QEvent::ShortcutOverride) return false;
        if (QCoreApplication::applicationName() != QStringLiteral("deepin-calculator")) return false;
        if (!target->inherits("InputEdit") && !target->inherits("MainWindow")) return false;
        if (!QFileInfo::exists(flag)) return false;
        const auto key = static_cast<QKeyEvent *>(event);
        if (key->key() != Qt::Key_Comma || (key->modifiers() & ~Qt::KeypadModifier)) return false;
        QKeyEvent replacement(event->type(), Qt::Key_Period, key->modifiers(),
                              QStringLiteral("."), key->isAutoRepeat(), key->count());
        replacement.setTimestamp(key->timestamp());
        QCoreApplication::sendEvent(target, &replacement);
        event->setAccepted(replacement.isAccepted());
        return true;
    }
private:
    QString flag;
};
class DecimalPlugin : public QGenericPlugin {
    Q_OBJECT
    Q_PLUGIN_METADATA(IID "org.qt-project.Qt.QGenericPluginFactoryInterface" FILE "calculator_decimal.json")
public:
    QObject *create(const QString &key, const QString &specification) override {
        if (key != QStringLiteral("deepwin-calculator") || specification.isEmpty()) return nullptr;
        return new DecimalFilter(specification);
    }
};
#include "calculator_decimal.moc"
