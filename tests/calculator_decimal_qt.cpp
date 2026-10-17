#include <QApplication>
#include <QFile>
#include <QKeyEvent>
#include <QLineEdit>
#include <QTemporaryDir>
#include <cstdio>

class InputEdit : public QLineEdit { Q_OBJECT };

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    QTemporaryDir temporary;
    const QString flag = temporary.filePath("enabled");
    QFile file(flag);
    if (!file.open(QIODevice::WriteOnly)) return 2;
    file.close();
    qputenv("QT_QPA_PLATFORM", "offscreen");
    qputenv("QT_PLUGIN_PATH", argv[1]);
    qputenv("QT_QPA_GENERIC_PLUGINS", ("deepwin-calculator:" + flag).toUtf8());
    QApplication app(argc, argv);
    QCoreApplication::setApplicationName("deepin-calculator");
    InputEdit editor;
    QLineEdit other;
    auto type = [](QLineEdit &edit, int key, Qt::KeyboardModifiers modifiers, const QString &text) {
        QKeyEvent press(QEvent::KeyPress, key, modifiers, text);
        QCoreApplication::sendEvent(&edit, &press);
        QKeyEvent release(QEvent::KeyRelease, key, modifiers, text);
        QCoreApplication::sendEvent(&edit, &release);
    };
    bool ok = true;
    auto check = [&ok](const char *name, bool condition) {
        std::printf("%s %s\n", condition ? "PASS" : "FAIL", name);
        ok &= condition;
    };
    type(editor, Qt::Key_1, Qt::NoModifier, "1");
    type(editor, Qt::Key_Comma, Qt::NoModifier, ",");
    type(editor, Qt::Key_5, Qt::NoModifier, "5");
    check("Qt: decimal 1,5 interpretado como 1.5", editor.text() == "1.5");
    editor.clear();
    type(editor, Qt::Key_Comma, Qt::KeypadModifier, ",");
    check("Qt: virgula do teclado numerico", editor.text() == ".");
    type(other, Qt::Key_Comma, Qt::NoModifier, ",");
    check("Qt: outro campo permanece intacto", other.text() == ",");
    editor.clear();
    type(editor, Qt::Key_Less, Qt::ShiftModifier, "<");
    type(editor, Qt::Key_Period, Qt::NoModifier, ".");
    check("Qt: Shift e ponto nativo preservados", editor.text() == "<.");
    editor.clear();
    for (int i = 0; i < 1000; ++i) {
        type(editor, Qt::Key_1, Qt::NoModifier, "1");
        type(editor, Qt::Key_Comma, Qt::NoModifier, ",");
        type(editor, Qt::Key_5, Qt::NoModifier, "5");
    }
    check("Qt: 3000 teclas sem perda ou reordenacao", editor.text() == QString("1.5").repeated(1000));
    editor.clear();
    QCoreApplication::setApplicationName("other-application");
    type(editor, Qt::Key_Comma, Qt::NoModifier, ",");
    check("Qt: outro aplicativo permanece intacto", editor.text() == ",");
    QCoreApplication::setApplicationName("deepin-calculator");
    file.remove();
    editor.clear();
    type(editor, Qt::Key_Comma, Qt::NoModifier, ",");
    check("Qt: rollback imediato sem reiniciar janela", editor.text() == ",");
    return ok ? 0 : 1;
}
#include "calculator_decimal_qt.moc"
