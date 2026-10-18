cmake_minimum_required(VERSION 3.20)
file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/VERSION" DEEPWIN_VERSION LIMIT_COUNT 1)
project(DeepWin VERSION "${DEEPWIN_VERSION}" LANGUAGES CXX)
include(GNUInstallDirs)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(Dtk6Widget REQUIRED)

add_executable(deepwin-ui gui/main.cpp)
target_link_libraries(deepwin-ui PRIVATE Dtk6::Widget Qt6::Widgets)
target_compile_definitions(deepwin-ui PRIVATE DEEPWIN_VERSION="${PROJECT_VERSION}")
target_compile_options(deepwin-ui PRIVATE -Wall -Wextra)
add_library(deepwin-calculator MODULE gui/calculator_decimal.cpp)
target_link_libraries(deepwin-calculator PRIVATE Qt6::Gui Qt6::Core)
set_target_properties(deepwin-calculator PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/qt6/plugins/generic")

# Um único layout privado é usado pelo .deb e pelo runtime por usuário.
set(DEEPWIN_RESOURCE_DIR "${CMAKE_INSTALL_LIBDIR}/deepwin" CACHE STRING "Diretório privado do DeepWin")
install(TARGETS deepwin-ui RUNTIME DESTINATION "${DEEPWIN_RESOURCE_DIR}")
install(TARGETS deepwin-calculator LIBRARY DESTINATION "${DEEPWIN_RESOURCE_DIR}/qt6/plugins/generic")
install(DIRECTORY gui/ DESTINATION "${DEEPWIN_RESOURCE_DIR}/gui" FILES_MATCHING PATTERN "*.py")
install(PROGRAMS bin/zclaude bin/deepwin-calculator bin/deepin-clipboard-autopaste
    bin/refresh-deepin-wallpaper bin/deepwin-restore DESTINATION "${DEEPWIN_RESOURCE_DIR}/bin")
install(DIRECTORY packaging/systemd/ DESTINATION "${DEEPWIN_RESOURCE_DIR}/systemd")
install(FILES VERSION LICENSE resources.json DESTINATION "${DEEPWIN_RESOURCE_DIR}")
# Extrações beige (python3-dbus/gi) presentes apenas no build Linyaps; no
# .deb as dependências Python continuam vindo por Depends.
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/pydeps")
    install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/pydeps/"
            DESTINATION "${DEEPWIN_RESOURCE_DIR}/pydeps" USE_SOURCE_PERMISSIONS)
endif()
configure_file(packaging/deepwin.in deepwin @ONLY)
install(PROGRAMS "${CMAKE_CURRENT_BINARY_DIR}/deepwin" DESTINATION "${CMAKE_INSTALL_BINDIR}")
install(FILES packaging/devedu.deepin-configs.desktop DESTINATION "${CMAKE_INSTALL_DATADIR}/applications")
install(FILES packaging/devedu.deepin-configs.metainfo.xml DESTINATION "${CMAKE_INSTALL_DATADIR}/metainfo")

include(CTest)
if(BUILD_TESTING)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_test(NAME python-tests COMMAND "${Python3_EXECUTABLE}" -m unittest discover -s "${CMAKE_CURRENT_SOURCE_DIR}/tests" -q)
    set_tests_properties(python-tests PROPERTIES ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1;DEEPWIN_BUILD_DIR=${CMAKE_CURRENT_BINARY_DIR}")
    add_executable(calculator-decimal-test tests/calculator_decimal_qt.cpp)
    target_link_libraries(calculator-decimal-test PRIVATE Qt6::Widgets)
    add_test(NAME calculator-qt COMMAND calculator-decimal-test "${CMAKE_CURRENT_BINARY_DIR}/qt6/plugins")
    set_tests_properties(calculator-qt PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
endif()
