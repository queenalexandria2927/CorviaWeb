import sys, os, json, subprocess, importlib
from PyQt5.QtWidgets import (QApplication,QMainWindow,QWidget,QLineEdit,QVBoxLayout,QHBoxLayout,
                             QTabWidget,QPushButton,QToolButton,QAction,QMessageBox,QInputDialog,
                             QScrollArea,QSizePolicy,QFrame,QTextEdit,QMenu)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtCore import QUrl, Qt

def ensure_package(p):
    try: importlib.import_module(p)
    except ImportError: subprocess.check_call([sys.executable,"-m","pip","install",p])
ensure_package("PyQt5")
ensure_package("PyQtWebEngine")

try:
    import downloads
except ImportError:
    class downloads:
        LOG_FILE="downloads.log"
        @staticmethod
        def log_download(url,path):
            with open(downloads.LOG_FILE,"a",encoding="utf-8") as f: f.write(f"Downloaded {url} to {path}\n")

CONFIG_FILE, BOOKMARKS_FILE, HISTORY_FILE, THEMES_FILE = ".corvia_config.json","bookmarks.json","history.json","themes.json"

def load_json(f, default): 
    try: return json.load(open(f,"r",encoding="utf-8"))
    except: return default
def save_json(f,d): json.dump(d, open(f,"w",encoding="utf-8"), indent=2)
load_config = lambda: load_json(CONFIG_FILE,{})
save_config = lambda c: save_json(CONFIG_FILE,c)
load_bookmarks = lambda: load_json(BOOKMARKS_FILE,[])
save_bookmarks = lambda b: save_json(BOOKMARKS_FILE,b)
load_history = lambda: load_json(HISTORY_FILE,[])
save_history = lambda h: save_json(HISTORY_FILE,h)
load_themes = lambda: load_json(THEMES_FILE, {
    "Light": {"background":"#ffffff","text":"#000000","link":"#0000ee"},
    "Dark": {"background":"#121212","text":"#eeeeee","link":"#3399ff"}
})
save_themes = lambda t: save_json(THEMES_FILE,t)

class BookmarksBar(QWidget):
    def __init__(self,parent_tab):
        super().__init__()
        self.parent_tab = parent_tab
        self.setFixedHeight(34)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5,0,5,0)
        self.layout.setSpacing(3)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setFixedHeight(30)
        self.inner = QWidget()
        self.inner_layout = QHBoxLayout(self.inner)
        self.inner_layout.setContentsMargins(0,0,0,0)
        self.inner_layout.setSpacing(4)
        self.scroll.setWidget(self.inner)
        self.layout.addWidget(self.scroll)
        self.load_bookmarks()

    def load_bookmarks(self):
        for i in reversed(range(self.inner_layout.count())):
            w=self.inner_layout.itemAt(i).widget()
            if w: w.setParent(None)
        for bm in load_bookmarks():
            self.add_bookmark_button(bm["title"],bm["url"])

    def add_bookmark_button(self,title,url):
        btn=QPushButton(title)
        btn.setToolTip(url)
        btn.setFixedHeight(24)
        btn.setFixedWidth(100)
        btn.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        btn.clicked.connect(lambda _,u=url:self.parent_tab.web_view.setUrl(QUrl(u)))
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(lambda pos,b=btn,u=url,t=title:self.open_context_menu(b,u,t))
        self.inner_layout.addWidget(btn)

    def open_context_menu(self,button,url,title):
        menu=QMenu()
        del_act=menu.addAction("Remove Bookmark")
        act=menu.exec_(button.mapToGlobal(button.rect().bottomLeft()))
        if act==del_act:
            bms = load_bookmarks()
            bms = [b for b in bms if not(b["url"]==url and b["title"]==title)]
            save_bookmarks(bms)
            button.setParent(None)

class BrowserView(QWebEngineView):
    def __init__(self, tabs):
        super().__init__()
        self.tabs = tabs
        self.urlChanged.connect(self.update_url_bar)
        self.titleChanged.connect(self.update_tab_title)
        self.loadFinished.connect(self.log_history)
    def createWindow(self,_type):
        tab = self.tabs.add_browser_tab()
        return tab.web_view
    def update_url_bar(self,qurl):
        idx=self.tabs.currentIndex()
        if idx>=0:
            tab=self.tabs.widget(idx)
            tab.url_bar.setText(qurl.toString())
    def update_tab_title(self,title):
        idx=self.tabs.currentIndex()
        if idx>=0:
            self.tabs.setTabText(idx,title if title else "New Tab")
    def log_history(self):
        url=self.url().toString()
        h=load_history()
        if url and (not h or h[-1]!=url):
            h.append(url)
            save_history(h)

class BrowserTab(QWidget):
    def __init__(self,tabs):
        super().__init__()
        self.tabs = tabs
        nav = QHBoxLayout()
        self.back = QPushButton("⬅️"); self.forward = QPushButton("➡️")
        self.reload = QPushButton("🔄"); self.bookmark = QPushButton("⭐")
        for b in [self.back,self.forward,self.reload,self.bookmark]: b.setFixedSize(30,24)
        self.back.clicked.connect(lambda:self.web_view.back())
        self.forward.clicked.connect(lambda:self.web_view.forward())
        self.reload.clicked.connect(lambda:self.web_view.reload())
        self.bookmark.clicked.connect(self.add_bookmark)
        self.url_bar=QLineEdit()
        self.url_bar.returnPressed.connect(self.load_url)
        for w in [self.back,self.forward,self.reload,self.bookmark,self.url_bar]: nav.addWidget(w)
        self.web_view = BrowserView(tabs)
        self.web_view.setUrl(QUrl.fromLocalFile(os.path.abspath("newtab.html")))
        self.web_view.settings().setAttribute(QWebEngineSettings.JavascriptEnabled,True)
        self.web_view.urlChanged.connect(lambda q:self.url_bar.setText(q.toString()))
        self.bookmarks_bar = BookmarksBar(self)
        layout=QVBoxLayout(self)
        layout.addLayout(nav)
        layout.addWidget(self.bookmarks_bar)
        layout.addWidget(self.web_view)
    def go_back(self): self.web_view.back()
    def go_forward(self): self.web_view.forward()
    def refresh_page(self): self.web_view.reload()
    def load_url(self):
        url=self.url_bar.text()
        if not url.startswith("http"): url="https://"+url
        self.web_view.setUrl(QUrl(url))
    def add_bookmark(self):
        url=self.web_view.url().toString()
        if not url: return
        title,ok=QInputDialog.getText(self,"Add Bookmark","Bookmark name:")
        if ok and title.strip():
            bms=load_bookmarks()
            if not any(b.get("url")==url and b.get("title")==title for b in bms):
                bms.append({"title":title.strip(),"url":url})
                save_bookmarks(bms)
                self.bookmarks_bar.add_bookmark_button(title.strip(),url)

class TabWidget(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.plus_button=QToolButton()
        self.plus_button.setText("+")
        self.plus_button.setAutoRaise(True)
        self.plus_button.clicked.connect(self.new_tab)
        self.setCornerWidget(self.plus_button, Qt.TopRightCorner)
    def add_browser_tab(self):
        tab=BrowserTab(self)
        idx=self.addTab(tab,"New Tab")
        self.setCurrentIndex(idx)
        return tab
    def new_tab(self): self.add_browser_tab()
    def close_tab(self,idx):
        if self.count()>1:
            self.removeTab(idx)
            # Fix download handling connection on new current tab
            self.connect_download_handling()
    def connect_download_handling(self):
        if self.count()==0: return
        idx=self.currentIndex()
        tab = self.widget(idx)
        if not tab: return
        profile=tab.web_view.page().profile()
        profile.downloadRequested.connect(self.parent().handle_download)

class CorviaBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Corvia Browser (Qt5 Legacy)")
        self.setGeometry(100,100,1200,800)
        self.tabs=TabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.new_tab()
        self.create_menu_bar()
        self.downloads_window=None
        self.check_legacy()
        self.apply_theme(self.load_theme())
        self.tabs.currentChanged.connect(lambda _: self.tabs.connect_download_handling())
        self.tabs.connect_download_handling()
    def create_menu_bar(self):
        mb=self.menuBar()
        file_menu=mb.addMenu("File")
        file_menu.addAction(self.make_action("New Tab","Ctrl+T",self.tabs.new_tab))
        file_menu.addAction(self.make_action("Close Tab","Ctrl+W",lambda:self.tabs.close_tab(self.tabs.currentIndex())))
        file_menu.addSeparator()
        file_menu.addAction(self.make_action("Downloads","Ctrl+D",self.open_downloads_window))
        file_menu.addSeparator()
        file_menu.addAction(self.make_action("Exit","Ctrl+Q",self.close))
        theme_menu=mb.addMenu("Themes")
        theme_menu.addAction(self.make_action("Light Mode", None, lambda:self.set_theme("Light")))
        theme_menu.addAction(self.make_action("Dark Mode", None, lambda:self.set_theme("Dark")))
    def make_action(self,text,shortcut,callback):
        a=QAction(text,self)
        if shortcut: a.setShortcut(shortcut)
        a.triggered.connect(callback)
        return a
    def open_downloads_window(self):
        if not self.downloads_window:
            self.downloads_window=DownloadsWindow()
        self.downloads_window.show()
        self.downloads_window.raise_()
        self.downloads_window.activateWindow()
    def handle_download(self,download):
        suggested=download.suggestedFileName()
        dldir=os.path.join(os.path.expanduser("~"),"Downloads")
        os.makedirs(dldir,exist_ok=True)
        path=os.path.join(dldir,suggested)
        download.setPath(path)
        download.accept()
        download.finished.connect(lambda:self.log_download(download))
    def log_download(self,download):
        downloads.log_download(download.url().toString(), download.path())
        if self.downloads_window: self.downloads_window.load_log()
    def check_legacy(self):
        c=load_config()
        if not c.get("qt5_acknowledged",False):
            mb=QMessageBox(self)
            mb.setWindowTitle("Legacy Qt5 Mode Notice")
            mb.setIcon(QMessageBox.Warning)
            mb.setText("You are running the browser in Qt5 legacy mode.\nQt6 support coming soon.")
            mb.setStandardButtons(QMessageBox.Ok)
            if mb.exec()==QMessageBox.Ok:
                c["qt5_acknowledged"]=True
                save_config(c)
    def load_theme(self):
        c=load_config()
        tname = c.get("theme","Light")
        themes=load_themes()
        return themes.get(tname, themes["Light"])
    def apply_theme(self,t):
        style=f"""
        QMainWindow {{background:{t.get('background','#fff')}; color:{t.get('text','#000')}}}
        QLineEdit {{background:{t.get('background','#fff')}; color:{t.get('text','#000')}}}
        QPushButton {{background:{t.get('background','#fff')}; color:{t.get('text','#000')}}}
        QTabWidget::pane {{border:1px solid {t.get('text','#000')}}}
        """
        self.setStyleSheet(style)
    def set_theme(self,name):
        themes=load_themes()
        if name in themes:
            c=load_config()
            c["theme"]=name
            save_config(c)
            self.apply_theme(themes[name])

class DownloadsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Downloads")
        self.resize(600,400)
        self.text_area=QTextEdit()
        self.text_area.setReadOnly(True)
        l=QVBoxLayout(self)
        l.addWidget(self.text_area)
        self.load_log()
    def load_log(self):
        if os.path.exists(downloads.LOG_FILE):
            with open(downloads.LOG_FILE,"r",encoding="utf-8") as f:
                self.text_area.setPlainText(f.read())
        else: self.text_area.setPlainText("No downloads yet.")

def main():
    app=QApplication(sys.argv)
    win=CorviaBrowser()
    win.show()
    sys.exit(app.exec())

if __name__=="__main__":
    main()
else:   
    # For testing purposes, we can run the main function directly
    # without needing to create a separate script.
    main()              