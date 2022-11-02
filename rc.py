

class RC:

    def __init__(self, timeout:int=10):
        self.timeout = timeout # s
        import logging
        self.log = logging.getLogger("RC")
        self.state = 'none'
        self.tree = {
            'whatever': {
                'whatever': None
            }
        } # type: dict[str, dict]

    def get_available_commands(self) -> list[str]:
        if self.state == 'none':
            return ['start']
        return ['stop']
        

    def send_command(self, command:str) -> None:
        import time
        from rich.progress import track
        self.log.info(f'Preparing to send \'{command}\'')
        for i in track(range(self.timeout), description=f"Sending {command}..."):
            time.sleep(1)  # Simulate work being done
        self.log.info(f'Sent \'{command}\'')


    def start(self) -> None:
        if self.state != 'none':
            raise RuntimeError('Cannot send start from \'started\'')
        self.send_command('start')
        self.state = 'started'
        self.tree = {
            'whatever': {
                'whatever1': {
                    "child1" : None,
                    "child2" : None,
                },
                'whatever2': {
                    "child1" : None,
                    "child2" : None,
                }
            }
        }


    def stop(self) -> None:
        if self.state != 'started':
            raise RuntimeError('Cannot send start from \'none\'')
        self.send_command('stop')
        self.state = 'stopped'
        self.tree = {
            'whatever': {
                'whatever': None
            }
        }

        

if __name__ == '__main__':
    from rich.logging import RichHandler
    import logging
    
    logging.basicConfig(
        level="INFO",
        format="%(filename)s:%(lineno)d %(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    
    log = logging.getLogger("main")
    rc = RC(timeout=4)
    log.info(f'RC state: \'{rc.state}\', available commands: {rc.get_available_commands()}')
    import json
    log.info(f'RC tree: {json.dumps(rc.tree, indent=2)}')
    rc.start()
    log.info(f'RC state: \'{rc.state}\', available commands: {rc.get_available_commands()}')
    log.info(f'RC tree: {json.dumps(rc.tree, indent=2)}')
    rc.stop()
    log.info(f'RC state: \'{rc.state}\', available commands: {rc.get_available_commands()}')
    log.info(f'RC tree: {json.dumps(rc.tree, indent=2)}')
