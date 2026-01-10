import webview
from web import app



window = webview.create_window(
    'Discord Tokens Checker',
    app,
    resizable=False,
    frameless=True,
    text_select=False,
    transparent=True,
    easy_drag=True,
    width=850,
    height=630
)

webview.start(gui="qt")

