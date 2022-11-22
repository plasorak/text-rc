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
from textual.widgets import Button, Header, Footer, Static, Input
from textual.reactive import reactive, Reactive

import logging
from logging.handlers import QueueHandler, QueueListener
import queue
from anytree import RenderTree

logging.basicConfig(level=logging.DEBUG)


class TitleBox(Static):
    def __init__(self, title, **kwargs):
        super().__init__(Markdown(f'# {title}'))

class RunNumDisplay(Static): pass

# class RunTypeDisplay(Static): pass

class RunInfo(Static):
    runnum  = reactive('none')
    runtype = reactive('none')

    def __init__(self, rc, **kwargs):
        super().__init__(**kwargs)
        self.rcobj = rc
        self.runtext = Markdown('# Run info')
    
    def update_text(self):
        run_num_display = self.query_one(RunNumDisplay)
        
        if self.runnum != 0:
            self.runtext = Markdown(f'# Run info\n\nNumber: {self.runnum}\n\nType: {self.runtype}')
        else:
            self.runtext = Markdown('# Run info')

        self.change_colour(run_num_display)
        run_num_display.update(self.runtext)

    def change_colour(self, obj) -> None:
        #If the colour is correct then return
        if ('STOPPED' in self.runtype and obj.has_class("redtextbox")) or ('STOPPED' not in self.runtype and obj.has_class("greentextbox")):
            return 
        #Otherwise, swap to the other colour
        if obj.has_class("redtextbox"):
            obj.remove_class("redtextbox")
            obj.add_class("greentextbox")
        else:
            obj.remove_class("greentextbox")
            obj.add_class("redtextbox")

    def update_runnum(self) -> None:
        self.runnum = self.rcobj.runmgr.get_run_number()

    def update_runtype(self) -> None:
        self.runtype = self.rcobj.runmgr.get_run_type()

    def watch_runtype(self, run:str) -> None:
        self.update_text()

    def watch_runnum(self, run:str) -> None:
        self.update_text()

    def on_mount(self) -> None:
        self.set_interval(0.1, self.update_runnum)
        self.set_interval(0.1, self.update_runtype)

    def compose(self) -> ComposeResult:
        yield RunNumDisplay(classes="redtextbox")
        
class LogDisplay(Static):
    logs = reactive('')
    searched_logs = reactive('')

    def __init__(self, log_queue, **kwargs):
        super().__init__(**kwargs)
        self.log_queue = log_queue
        self.handler = RichHandler()
        self.search_mode = False
    
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

    def watch_logs(self, logs:str, searched_logs:str) -> None:
        if self.search_mode:
            self.update(searched_logs)
        else:
            self.update(logs)
    
    def delete_logs(self) -> None:
        self.logs = ""

    def save_logs(self) -> None:
        data = self.logs
        # self.delete_logs() # dont want to delete_logs here
        
        time = str(datetime.now())
        
        time = time[:-7]               # Times to the nearest second instead of microsecond
        time = "-".join(time.split())  # Joins date and time with a hyphen instead of a space
        time = time.replace(":","")    # chuck the weird ":"
        filename = f"logs_{time}"
        try: 
            with open(filename, "x") as f:
                f.write(data)
        except:
            pass
    
class Logs(Static):
    def __init__(self, log_queue, **kwargs):
        super().__init__(**kwargs)
        self.log_queue = log_queue
    
    def compose(self) -> ComposeResult:
        yield TitleBox('Logs')
        yield Input(placeholder='Search logs')
        yield Horizontal(
            Button("Save logs", id="save_logs"),
            Button("Clear logs", id="delete_logs"),
            classes='horizontalbuttonscontainer'
        )
        yield Vertical(
            LogDisplay(self.log_queue),
            id='verticallogs'
        )

    async def on_button_pressed (self, event: Button.Pressed) -> None:
        button_id = event.button.id
        logdisplay = self.query_one(LogDisplay)
        method = getattr(logdisplay, button_id)
        method()

    async def on_input_changed(self, message: Input.Changed) -> None:
        """A coroutine to handle a text changed message."""
        logdisplay = self.query_one(LogDisplay)
        if message.value:
            logdisplay.search_mode = True
            task = asyncio.create_task(self.filter_logs(logdisplay, message.value))
            logdisplay.searched_logs = await(task)
            logdisplay.update(logdisplay.searched_logs)
        else:
            logdisplay.search_mode = False
            logdisplay.update(logdisplay.logs)

    async def filter_logs(self, logdisplay, term: str):
        loglist = logdisplay.logs.split("\n")                                       #Splits the log string into a list of logs
        #Gets a list of all logs that contain term as a substring (case insensitive)
        searchedlist = [log for log in loglist if term.lower() in log.lower()]   
        return "\n".join(searchedlist)                                              #Reformats the list as a string with newlines



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
        nice_status = status.replace('_', ' ').capitalize()
        status_display.update(Markdown(f'# Status\n\n{nice_status}'))

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
        always_displayed = ['quit', 'abort']
        for button in self.query(Button):
            if button.id in self.commands or button.id in always_displayed:
                button.display=True
            else:
                button.display=False

            if button.id == 'abort':
                button.color = 'red'
        
    def compose(self) -> ComposeResult:
        yield TitleBox('Commands')
        commandlist = self.rcobj.get_all_commands()
        yield Vertical(
            Horizontal(
                *[Button(b.replace('_', ' ').capitalize(), id=b) for b in commandlist],
                classes='horizontalbuttonscontainer',
            ),
            Horizontal(
                Button('Quit', id='quit'),
                Button('Abort',variant='error', id='abort'),
                classes='horizontalbuttonscontainer',
            ),
            id = 'verticalbuttoncontainer'
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.button.id
        if button_id == 'quit':
            method = getattr(self.rcobj, "shutdown")
            task = asyncio.create_task(method())
            await task
            sys.exit(0)
        elif button_id == 'abort':
            sys.exit(0)
        else:
            method = getattr(self.rcobj, button_id) # We use the name of the button to find the right method of the Nanorc class
            task = asyncio.create_task(method())
            # await task
        

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
            RunInfo  (rc = self.rc, classes='container'),
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
