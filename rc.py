import asyncio
import logging
logging.basicConfig(level=logging.INFO)
import queue

class RunManager:
    '''A VERY basic run manager that just stores a number and type'''
    def __init__(self):
        self.run_num = 0
        self.run_type = "STOPPED"

    def get_run_number(self):
        return self.run_num
    
    def get_run_type(self):
        return self.run_type

    def new_run(self):
        self.run_num += 1
        self.run_type = "TEST"          #All runs are tests
    
    def end_run(self):
        self.run_type = "STOPPED"

class RC:
    def __init__(self, timeout:int=1):
        self.runmgr = RunManager()
        self.timeout = timeout # s
        self.log = logging.getLogger("RC")
        # log_handle = logging.FileHandler("rc.log")
        # self.log.addHandler(log_handle)

        self.state = 'none'
        self.none_state_tree = {
            'np04_coldbox': {
                'state': 'none',
                'children': [
                    {
                        'wibs': {
                            'state': 'none',
                            'children': []
                        }
                    },
                    {
                        'daq': {
                            'state': 'none',
                            'children': []
                        }
                    },
                    
                ]
            }
        } # type: dict[str, dict]
        self.tree = self.none_state_tree
        self.paramdict = {
            'boot': ["timeout"],
            'start_run': ["timeout", "new_rate"],
            'conf': ["timeout"],
            'terminate': ["timeout"],
            'shutdown': ["timeout", "some", "more", "arguments"],
            'scrap': ["timeout"],
            'start': ["timeout"],
            'enable_trigger': ["timeout", "new_rate"],
            'disable_trigger': ["timeout"],
            'drain_dataflow': ["timeout"],
            'stop_trigger_sources': ["timeout"],
            'stop': ["timeout"],



        }

    def get_available_commands(self) -> list[str]:
        if   self.state == 'none':                    return ['boot']
        elif self.state == 'initialised':             return ['start_run', 'conf', 'terminate', 'shutdown']
        elif self.state == 'configured':              return ['start_run', 'scrap', 'shutdown', 'start']
        elif self.state == 'ready':                   return ['enable_trigger', 'drain_dataflow', 'shutdown']
        elif self.state == 'trigger_enabled':         return ['disable_trigger', 'shutdown']
        elif self.state == 'dataflow_drained':        return ['stop_trigger_sources', 'shutdown']
        elif self.state == 'trigger_sources_stopped': return ['stop', 'shutdown']
        else: return []

    def get_all_commands(self) -> list[str]:
        return [
            'boot',
            'start_run',
            'conf',
            'terminate',
            'shutdown',
            'scrap',
            'start',
            'enable_trigger',
            'disable_trigger',
            'drain_dataflow',
            'stop_trigger_sources',
            'stop',
        ]

    
    def update_app_status(self,out_state) -> None:
        self.tree = {
            'np04_coldbox': {
                'state': out_state,
                'children': [
                    {
                        'wibs': {
                            'state': out_state,
                            'children': [
                                {
                                    f'wib_00{i}': {
                                        'state': out_state
                                    }
                                    for i in range(8)
                                }
                            ]
                        }
                    },
                    {
                        'daq': {
                            'state': out_state,
                            'children': [
                                {
                                    f'runp04srv0{i}': {
                                        'state': out_state
                                    }
                                    for i in range(24,28)
                                },
                                {
                                    f'dqmrunp04srv0{i}': {
                                        'state': out_state
                                    }
                                    for i in range(24,28)
                                },
                                {
                                    'dfo': {
                                        'state': out_state
                                    }
                                },
                                {
                                    'trigger': {
                                        'state': out_state
                                    }
                                },
                                {
                                    f'dataflow{i}': {
                                        'state': out_state
                                    }
                                    for i in range(4)
                                },
                                {
                                    f'dqmdf{i}': {
                                        'state': out_state
                                    }
                                    for i in range(4)
                                }
                            ]
                        }
                    },
                    
                ]
            }
        } # type: dict[str, dict]
    '''    
    def update_single_app(self, out_state:str, nodepath:str topnode:str, apptype:str, app:str) -> None:
        nodepath = nodepath.split["/"]              #Nodepath should be formatted like np04_coldbox/daq/dataflow2
        topnode = nodepath[0]
        apptype = nodepath[1]
        app = nodepath[2]                           #There is probably a better way of doing that

        typelist = self.tree[topnode]['children']
        for item in typelist:                       #Searches the list to find the dict with the right name
            typecheck = list(item.keys())[0]
            if typecheck == apptype:
                typedict = item
        applist = typedict[apptype]['children']
        for item in applist:                        #Same but for apps
            appcheck = list(item.keys())[0]
            if appcheck == app:
                appdict = item
        appdict[app]['state'] = out_state
    '''
    def get_required_params(self, command:str) -> list:
        return(self.paramdict[command])
        
    async def send_command(self, command:str, in_state:str, out_state:str, **kwargs) -> None:
        import time
        from rich.progress import track
        
        if self.state != in_state:
            raise RuntimeError(f'Cannot send {command} from \'{self.state}\'')
        
        self.state = command+'ing'
        words = ""
        for key in kwargs:
            words += f"{key}: {kwargs[key]}\n"

        self.log.info(f'Preparing to send \'{command}\'')
        self.log.info(f'\nProvided parameters:\n{words}')
        for i in track(range(self.timeout*10), description=f"Sending {command}..."):
            self.log.info(f'Plenty of logs for the command \'{command}\'...')
            await asyncio.sleep(0.01)  # Simulate work being done

        if command == 'start':
            self.runmgr.new_run()

        if command == 'drain_dataflow':
            self.runmgr.end_run()

        if command == 'terminate':
            self.tree = self.none_state_tree
        else:
            self.update_app_status(out_state)
        
        self.state = out_state
        self.log.info(f'Sent \'{command}\'')

    async def boot(self, **kwargs) -> None:
        await self.send_command('boot', 'none', 'initialised', **kwargs)
        
    async def conf(self, **kwargs) -> None:
        await self.send_command('conf', 'initialised', 'configured', **kwargs)

    async def start(self, **kwargs) -> None:
        await self.send_command('start', 'configured', 'ready', **kwargs)
        
    async def enable_trigger(self, **kwargs) -> None:
        await self.send_command('enable_trigger', 'ready', 'trigger_enabled', **kwargs)

    async def disable_trigger(self, **kwargs) -> None:
        await self.send_command('disable_trigger', 'trigger_enabled', 'ready', **kwargs)

    async def drain_dataflow(self, **kwargs) -> None:
        await self.send_command('drain_dataflow', 'ready', 'dataflow_drained', **kwargs)

    async def stop_trigger_sources(self, **kwargs) -> None:
        await self.send_command('stop_trigger_sources', 'dataflow_drained', 'trigger_sources_stopped', **kwargs)
    
    async def stop(self, **kwargs) -> None:
        await self.send_command('stop', 'trigger_sources_stopped', 'configured', **kwargs)
        
    async def scrap(self, **kwargs) -> None:
        await self.send_command('scrap', 'configured', 'initialised', **kwargs)
        
    async def terminate(self, **kwargs) -> None:
        await self.send_command('terminate', 'initialised', 'none', **kwargs)


    async def execute_maybe(self, cmd, in_state, out_state, **kwargs):
        try:
            await self.send_command(cmd, in_state, out_state, **kwargs)
        except:
            pass
            
    async def shutdown(self, **kwargs) -> None:
        await self.execute_maybe('disable_trigger',      'trigger_enabled',         'ready'                  )
        await self.execute_maybe('drain_dataflow',       'ready',                   'dataflow_drained'       )
        await self.execute_maybe('stop_trigger_sources', 'dataflow_drained',        'trigger_sources_stopped')
        await self.execute_maybe('stop',                 'trigger_sources_stopped', 'configured'             )
        await self.execute_maybe('scrap',                'configured',              'initialised'            )
        await self.execute_maybe('terminate',            'initialised',             'none'                  )
        
    async def start_run(self, **kwargs) -> None:
        await self.execute_maybe('conf',           'initialised', 'configured'     )
        await self.execute_maybe('start',          'configured',  'ready'          )
        await self.execute_maybe('enable_trigger', 'ready',       'trigger_enabled')
            
        
        


async def main():
    from rich.logging import RichHandler
    import logging

    # logging.basicConfig(
    #     level="INFO",
    #     format="%(filename)s:%(lineno)d %(message)s",
    #     datefmt="[%X]",
    #     handlers=[RichHandler(rich_tracebacks=True)]
    # )

    # log = logging.getLogger("main")
    rc = RC(timeout=4)
    log_queue = queue.Queue(-1)
    queue_handler = QueueHandler(queue)
    log.addHandler(QueueHandler(queue))

    
    # log.info(f'RC state: \'{rc.state}\', available commands: {rc.get_available_commands()}')
    import json
    # log.info(f'RC tree: {json.dumps(rc.tree, indent=2)}')
    await rc.start()
    # log.info(f'RC state: \'{rc.state}\', available commands: {rc.get_available_commands()}')
    # log.info(f'RC tree: {json.dumps(rc.tree, indent=2)}')
    await rc.stop()
    # log.info(f'RC state: \'{rc.state}\', available commands: {rc.get_available_commands()}')
    # log.info(f'RC tree: {json.dumps(rc.tree, indent=2)}')


if __name__ == '__main__':
    asyncio.run(main())
