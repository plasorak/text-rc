import sys
import asyncio
from rc import RC
from textual import log
from rich.logging import RichHandler
from rich.text import Text
from rich.json import JSON
from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Content, Container, Vertical

from textual.widgets import Button, Header, Footer, Static
from textual.reactive import reactive
import logging
from logging.handlers import QueueHandler, QueueListener
import queue

logging.basicConfig(level=logging.DEBUG)


class TitleBox(Static):
    def __init__(self, title, **kwargs):
        super().__init__(Markdown(f'# {title}'))

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
                self.logs += f'{text}\n'
            except:
                break

    def watch_logs(self, logs:str) ->None:
        self.update(logs)
        
class Logs(Static):
    def __init__(self, log_queue, **kwargs):
        super().__init__(**kwargs)
        self.log_queue = log_queue
    
    def compose(self) -> ComposeResult:
        yield TitleBox('Logs')
        yield Vertical(LogDisplay(self.log_queue), id='verticallogs')
        

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
        tree_display.update(JSON(json.dumps(tree)))

    def on_mount(self) -> None:
        self.set_interval(0.1, self.update_rctree)

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
            Status  (rc = self.rc, classes='container'),
            Command (rc = self.rc, classes='container', id='command'),
            TreeView(rc = self.rc, classes='container', id='tree'),
            Logs    (log_queue=self.log_queue, classes='container', id='log'),
            id = 'app-grid'
        )
        
        yield Header(show_clock=True)
        yield Footer()


if __name__ == "__main__":
    rc = RC()
    app = NanoRCTUI(rc)
    app.run()
