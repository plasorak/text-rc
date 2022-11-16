import sys
import asyncio
from datetime import datetime
from rc import RC

from rich import print
from rich.align import Align
from rich.box import DOUBLE
from rich.logging import RichHandler
from rich.panel import Panel
from rich.text import Text
from rich.json import JSON
from rich.console import RenderableType
from rich.markdown import Markdown
from rich.style import Style

from textual import log, events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Content, Container, Vertical
from textual.widget import Widget
from textual.widgets import Button, Header, Footer, Static
from textual.reactive import reactive, Reactive

import logging
from logging.handlers import QueueHandler, QueueListener
import queue
from anytree import RenderTree

logging.basicConfig(level=logging.DEBUG)


class TitleBox(Static):
    def __init__(self, title, **kwargs):
        super().__init__(Markdown(f'# {title}'))

class RunDisplay(Static): pass

class RunInfo(Static):
    runnum = reactive('none')

    def __init__(self, rc, **kwargs):
        super().__init__(**kwargs)
        self.rcobj = rc

    def update_runnum(self) -> None:
        self.runnum = self.rcobj.run_num_mgr.get_run_number()

    def watch_runnum(self, run:str) -> None:
        run_display = self.query_one(RunDisplay)
        run_display.update(Markdown(f'# Run Number: {self.runnum}'))

    def on_mount(self) -> None:
        self.set_interval(0.1, self.update_runnum)

    def compose(self) -> ComposeResult:
        yield RunDisplay()
'''
class InputText(Widget):

    title: Reactive[RenderableType] = Reactive("")
    content: Reactive[RenderableType] = Reactive("")
    mouse_over: Reactive[RenderableType] = Reactive(False)

    def __init__(self, title: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title

    def on_enter(self) -> None:
        self.mouse_over = True

    def on_leave(self) -> None:
        self.mouse_over = False

    def on_key(self, event: events.Key) -> None:
        if self.mouse_over == True:
            if event.key == "ctrl+h":
                self.content = self.content[:-1]
            else:
                self.content += event.key

    def validate_title(self, value) -> None:
        try:
            return value.lower()
        except (AttributeError, TypeError):
            raise AssertionError("title attribute should be a string.")

    def render(self) -> RenderableType:
        renderable = None
        if self.title.lower() == "password":
            renderable = "".join(map(lambda char: "*", self.content))
        else:
            renderable = Align.left(Text(self.content, style="bold"))
        return Panel(
            renderable,
            title=self.title,
            title_align="center",
            height=3,
            style="bold white on rgb(50,57,50)",
            border_style=Style(color="green"),
            box=DOUBLE,
        )
'''

class LogDisplay(Static):
    logs = reactive('')

    def __init__(self, log_queue, **kwargs):
        super().__init__(**kwargs)
        self.log_queue = log_queue
        self.handler = RichHandler()
    
    def on_mount(self) -> None:
        self.set_interval(0.1, self.update_logs) # execute update_logs every second
    
    def update_logs(self) -> None:
        while True: # drain the queue of logs
            try:
                record = self.log_queue.get(block=False)
                text = self.handler.render_message(record, record.msg)
                self.logs = f'{text}\n' + self.logs
            except:
                break

    def watch_logs(self, logs:str) -> None:
        self.update(logs)
    
    def delete_logs(self) -> None:
        self.logs = ""

    def save_logs(self) -> None:
        data = self.logs
        self.delete_logs()
        time = str(datetime.now())
        time = time[:-3]                     #Times to the nearest millisecond instead of microsecond
        time = "-".join(time.split())       #Joins date and time with a hyphen instead of a space
        filename = f"logs{time}"
        f = open(filename, "x")
        f.write(data)
        f.close()
    
class Logs(Static):
    searchtext: Reactive[RenderableType] = Reactive("")

    def __init__(self, log_queue, **kwargs):
        super().__init__(**kwargs)
        self.log_queue = log_queue
    
    def compose(self) -> ComposeResult:
        yield TitleBox('Logs')
        yield Button("Save logs to file", id="save_logs")
        yield Button("Clear logs", id="delete_logs")
        yield Vertical(LogDisplay(self.log_queue), id='verticallogs')

    async def on_button_pressed (self, event: Button.Pressed) -> None:
        button_id = event.button.id
        logdisplay = self.query_one(LogDisplay)
        method = getattr(logdisplay, button_id)
        method()

class StatusDisplay(Static): pass

class Status(Static):
    rcstatus = reactive('none')

    def __init__(self, rc, **kwargs):
        super().__init__(**kwargs)
        self.rcobj = rc

    def update_rcstatus(self) -> None:
        self.rcstatus = self.rcobj.state

    def watch_rcstatus(self, status:str) -> None:
        status_display = self.query_one(StatusDisplay)
        status_display.update(Markdown(f'# Status: {status}'))

    def on_mount(self) -> None:
        self.set_interval(0.1, self.update_rcstatus)

    def compose(self) -> ComposeResult:
        # yield TitleBox("Status {}")
        yield StatusDisplay()

class TreeDisplay(Static): pass

class TreeView(Static):
    rctree = reactive('')
    
    def __init__(self, rc, **kwargs):
        super().__init__(**kwargs)
        self.rcobj = rc
        
    def compose(self) -> ComposeResult:
        yield TitleBox("Apps")
        yield Vertical(TreeDisplay(), id='verticaltree')
    
    def update_rctree(self) -> None:
        self.rctree = self.rcobj.tree

    def watch_rctree(self, tree:dict) -> None:
        tree_display = self.query_one(TreeDisplay)
        import json
        #T = JSON(json.dumps(tree))
        #tree_display.update(T)
        nicetree = self.render_json(tree)
        tree_display.update(nicetree)

    def on_mount(self) -> None:
        self.set_interval(0.1, self.update_rctree)

    def render_json(self, tree:dict):
        branch_extend = '│  '
        branch_mid    = '├─ '
        branch_last   = '└─ '
        spacing       = '   '
        rows = []
        last_cat = False
        last_app = False
        col1 = "[bold magenta]"
        col1end = "[/bold magenta]"
        col2 = "[royal_blue1]"
        col2end = "[/royal_blue1]"
        col3 = "[green]"
        col3end = "[/green]"

        for tl_key in tree:                                                                 #Loop over top level nodes
            tlvalue = tree[tl_key]
            typelist = tlvalue['children']
            text = f"{col1}{tl_key}: {tlvalue['state']}\n{col1end}"    
            rows.append(text)
            for i, typedict in enumerate(typelist):                                         #Loop over the dictionaries that correspond to a category
                last_cat = (i == len(typelist)-1)
                typename = list(typedict.keys())[0]    
                typedata = typedict[typename]                                               #Gets the subdictionary with state and children
                applist = typedata['children']
                if last_cat:                                                    #If we are at the end, use the right shape
                    c1 = branch_last
                else:
                    c1 = branch_mid               
                text = f"{col1}{c1}{col1end}{col2}{typename}: {typedata['state']}\n{col2end}"
                rows.append(text)
                for j, appdict in enumerate(applist):                                                     #Loop over the apps themselves
                    last_app = (j == len(applist)-1)
                    appname = list(appdict.keys())[0]
                    appdata = appdict[appname]                                              #Gets the subdictionary that contains the state
                    if last_cat:
                        a1 = spacing
                    else:
                        a1 = branch_extend
                    if last_app:
                        a2 = branch_last
                    else:
                        a2 = branch_mid
                    text = f"{col1}{a1}{col1end}{col2}{a2}{col2end}{col3}{appname}: {appdata['state']}\n{col3end}"
                    rows.append(text)

        return "".join(rows)


class Command(Static):
    commands = reactive([])
    
    def __init__(self, rc, **kwargs):
        super().__init__(**kwargs)
        self.rcobj = rc
        
    def on_mount(self) -> None:
        self.set_interval(0.1, self.update_buttons)

    def update_buttons(self) -> None:
        self.commands = self.rcobj.get_available_commands()
        
    def watch_commands(self, commands:list[str]) -> None:
        # for cmd self.rcobj.get_all_commands():
        for button in self.query(Button):
            if button.id in self.commands or button.id == "quit":
                button.display=True
            else:
                button.display=False
        
    def compose(self) -> ComposeResult:
        yield TitleBox('Commands')
        commandlist = self.rcobj.get_all_commands()
        commandlist.append("quit")
        yield Horizontal(
            *[Button(b, id=b) for b in commandlist],
            classes='buttonscontainer',
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.button.id
        if button_id != 'quit': 
            method = getattr(self.rcobj, button_id) # We use the name of the button to find the right method of the Nanorc class
            task = asyncio.create_task(method())
        else:
            method = getattr(self.rcobj, "shutdown")
            task = asyncio.create_task(method())
            await task
            sys.exit(0)


class NanoRCTUI(App):
    CSS_PATH = "tui.css"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def __init__(self, rc, **kwargs):
        super().__init__(**kwargs)
        self.rc = rc
        self.log_queue = queue.Queue(-1)
        self.queue_handler = QueueHandler(self.log_queue)
        self.rc.log.propagate = False
        self.rc.log.addHandler(self.queue_handler)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Container(
            RunInfo  (rc = self.rc, classes = 'container'),
            Status   (rc = self.rc, classes='container'),
            Command  (rc = self.rc, classes='container', id='command'),
            TreeView (rc = self.rc, classes='container', id='tree'),
            Logs     (log_queue=self.log_queue, classes='container', id='log'),
            id = 'app-grid'
        )
        
        yield Header(show_clock=True)
        yield Footer()

if __name__ == "__main__":
    rc = RC()
    app = NanoRCTUI(rc)
    app.run()
