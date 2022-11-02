from rc import RC
from textual import log
from textual.app import App, ComposeResult
from textual.containers import Container, Content
from textual.widgets import Button, Header, Footer, Static
from textual.reactive import reactive

class LogDisplay(Static):
    pass

class LogBox(Static):
    def __init__(self, rc, **kwargs):
        super().__init__(**kwargs)
        self.rc = rc


class StatusDisplay(Static):
    pass


class Status(Static):
    rc = reactive(RC)
    
    def __init__(self, rc, **kwargs):
        super().__init__(**kwargs)
        self.rcobj = rc

    def update_status(self) -> None:
        status_display = self.query_one(StatusDisplay)
        status_display.update(self.rcobj.state)
        
    def watch_rcobj(self) -> None:
        self.update_status()
        
    def on_mount(self) -> None:
        self.update_status()

    def compose(self) -> ComposeResult:
        yield StatusDisplay()
        yield Button('Update status', id='update_status', variant='primary')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        if event.button.id == "update_status":
            self.update_status()

class TreeView(Static):
    def __init__(self, rc, **kwargs):
        super().__init__(**kwargs)
        self.rc = rc

    def update_tree(self) -> None:
        import json
        self.update(json.dumps(self.rc.tree, indent=2))

    def on_mount(self) -> None:
        self.update_tree()

class StateBox(Static):
    def __init__(self, rc, **kwargs):
        super().__init__(**kwargs)
        self.rc = rc
    
    def compose(self) -> ComposeResult:
        #Creates the initial set of buttons

        for c in self.rc.get_available_commands():
            yield Button(c, id=c, variant="primary")
        
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.button.id
        method = getattr(self.rc, button_id)    #We use the name of the button to find the right method of the Nanorc class
        method()

class TUIApp(App):
    CSS_PATH = "tui.css"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def __init__(self, rc, **kwargs):
        super().__init__(**kwargs)
        self.rc = rc

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield TreeView(rc=self.rc)
        yield Status(rc=self.rc)
        yield StateBox(rc=self.rc)
        yield LogBox(rc=self.rc)
        yield Header()
        yield Footer()
        

if __name__ == "__main__":
    rc = RC()
    app = TUIApp(rc)
    app.run()
