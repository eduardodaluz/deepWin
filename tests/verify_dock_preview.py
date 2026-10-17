#!/usr/bin/python3
"""Teste visual com duas janelas GTK descartáveis e rollback automático.

Requer DeepWin instalado, sessão X11 desbloqueada e prévia ao clicar desativada.
Recarrega o dde-shell, cria uma entrada de aplicativo temporária e restaura
somente este recurso ao terminar. Não interage com documentos do usuário.
"""
from pathlib import Path
import json,os,re,subprocess,sys,tempfile,time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'gui'))
from backend import Manager


def xdo(*args):
    return subprocess.check_output(['xdotool',*map(str,args)],text=True,timeout=6).strip()

def geometry(wid):
    result=subprocess.run(['xprop','-id',str(wid),'_NET_WM_ICON_GEOMETRY'],capture_output=True,text=True)
    if '=' not in result.stdout:return None
    values=re.findall(r'\d+',result.stdout.split('=',1)[1])
    return tuple(map(int,values)) if len(values)==4 else None

def windows(pid):
    result=subprocess.run(['xdotool','search','--onlyvisible','--pid',str(pid)],capture_output=True,text=True)
    return set(result.stdout.split())

def shell_pid():
    return int(subprocess.check_output(['systemctl','--user','show','-p','MainPID','--value','dde-shell@DDE.service'],text=True))

locked=subprocess.run(['xdotool','search','--onlyvisible','--class',r'^org\.deepin\.dde\.lock$'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
assert not locked,'Desbloqueie a sessão para o teste.'
manager=Manager()
assert 'dock_preview' not in manager.load_state(),'Há uma alteração anterior de prévias pendente.'
original=manager.capture('dock_preview')
assert not original['enabled'],'Teste requer comportamento padrão inicialmente.'
pointer=dict(line.split('=',1) for line in xdo('getmouselocation','--shell').splitlines())
active=xdo('getactivewindow')
app_id='org.deepwin.DockPreviewTest'
desktop=Path.home()/'.local/share/applications'/f'{app_id}.desktop'
assert not desktop.exists(),'Arquivo de teste já existe.'
process=None
changed=False
try:
 with tempfile.TemporaryDirectory(prefix='deepwin-preview-visual-') as directory:
    work=Path(directory)
    child=work/'windows.py'
    child.write_text('''import gi,json,signal,sys
from pathlib import Path
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib
GLib.set_prgname('org.deepwin.DockPreviewTest')
GLib.set_application_name('Teste de miniaturas DeepWin')
windows=[]
for index in range(2):
 window=Gtk.Window(title='Teste de miniaturas DeepWin — '+str(index+1))
 window.set_wmclass('org.deepwin.DockPreviewTest','org.deepwin.DockPreviewTest')
 window.set_default_size(420,220)
 label=Gtk.Label(label='Janela descartável '+str(index+1)+'\\nTeste de clique no dock')
 window.add(label)
 window.show_all()
 windows.append(window)
Path(sys.argv[1]).write_text(json.dumps([window.get_window().get_xid() for window in windows]))
signal.signal(signal.SIGTERM,lambda *args:Gtk.main_quit())
Gtk.main()
''')
    desktop.write_text('[Desktop Entry]\nType=Application\nName=Teste de miniaturas DeepWin\nExec=/usr/bin/python3 '+str(child)+' '+str(work/'ready.json')+'\nIcon=applications-utilities\nStartupWMClass='+app_id+'\nTerminal=false\n')
    time.sleep(1)
    process=subprocess.Popen(['/usr/bin/python3',str(child),str(work/'ready.json')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    deadline=time.monotonic()+12
    ids=[]
    while time.monotonic()<deadline:
        if (work/'ready.json').exists():
            ids=json.loads((work/'ready.json').read_text())
            geometries=[geometry(wid) for wid in ids]
            if all(geometries) and geometries[0]==geometries[1]:break
        time.sleep(.2)
    else: raise RuntimeError('As janelas de teste não foram agrupadas pelo dock.')
    print('PASS duas janelas descartáveis reconhecidas no mesmo grupo',flush=True)
    changed=True
    manager.change('dock_preview',True)
    time.sleep(1.2)
    assert manager.feature_status('dock_preview')['enabled']
    assert subprocess.run(['systemctl','--user','is-active','--quiet','dde-shell@DDE.service']).returncode==0
    pid=shell_pid()
    existing=windows(pid)
    icon=geometry(ids[0])
    assert icon, 'Geometria do ícone ausente após recarga.'
    xdo('windowactivate','--sync',ids[-1])
    before=xdo('getactivewindow')
    x,y,w,h=icon
    xdo('mousemove','--sync',x+w//2,y+h//2,'click',1)
    deadline=time.monotonic()+2
    popup=None
    while time.monotonic()<deadline:
        for candidate in windows(pid)-existing:
            geo=dict(line.split('=',1) for line in xdo('getwindowgeometry','--shell',candidate).splitlines())
            if int(geo['WIDTH'])>150 and int(geo['HEIGHT'])>70:
                popup=(candidate,geo)
                break
        if popup:break
        time.sleep(.05)
    assert popup, 'O clique não abriu a prévia nativa.'
    assert xdo('getactivewindow')==before,'O clique ativou outra janela antes da escolha.'
    print('PASS clique no grupo abre a prévia nativa sem trocar a janela ativa',flush=True)
    candidate,geo=popup
    xdo('mousemove','--window',candidate,int(geo['WIDTH'])//4,int(geo['HEIGHT'])*2//3,'click',1)
    time.sleep(.3)
    assert int(xdo('getactivewindow')) in ids
    print('PASS clique na miniatura seleciona uma das janelas do grupo',flush=True)
finally:
    if changed:
        if 'dock_preview' in manager.load_state():manager.restore('dock_preview')
        else:manager.restore_value('dock_preview',original)
        print('PASS rollback para o comportamento original do dock',flush=True)
    if process is not None:
        process.terminate()
        try:process.wait(timeout=3)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
    desktop.unlink(missing_ok=True)
    xdo('mousemove',pointer['X'],pointer['Y'])
    try:xdo('windowactivate',active)
    except subprocess.SubprocessError:pass
