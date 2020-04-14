"""
Module to control SORACOM 3G module from Switch Science
License: Boost Software License 1.0
"""

import time
import machine
import network
import _thread

try:
    from mpy_builtins import machine, const
    from typing import Tuple, Callable, List, Dict, Optional, Union, Any
except:
    import machine

WriteableBufferType = None # type: Union[memoryview, bytearray]
BufferType = None          # type: Union[memoryview, bytearray, bytes]

class logging(object):
    class Logger(object):
        def __init__(self, tag:str):
            self.tag = tag
        def debug(self, fmt:str, *args):
            print('[DEBUG] ', end='')
            print(fmt % args)
        def info(self, fmt:str, *args):
            print('[INFO] ', end='')
            print(fmt % args)
        def warn(self, fmt:str, *args):
            print('[WARN] ', end='')
            print(fmt % args)
        def error(self, fmt:str, *args):
            print('[ERROR] ', end='')
            print(fmt % args)


class CancelledError(BaseException):
    def __init__(self):
        pass

cancelled_error = CancelledError()
stop_iteration = StopIteration()

class SleepAwaitable(object):
    def __init__(self):
        self.value = None # type:Optional[Union[float, BaseException]]
        
    def __call__(self, value: Optional[Union[float, BaseException]]):
        self.value = value
        return self
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.value is None:
            raise stop_iteration
        elif self.value is BaseException:
            raise self.value
        else:
            time.sleep(self.value)
            self.value = None
            return self

class asyncio(object):
    _sleep_awaitable = SleepAwaitable()

    @staticmethod
    def sleep_ms(duration_ms:int) -> SleepAwaitable:
        return asyncio._sleep_awaitable(duration_ms*1.0e-3)
    @staticmethod
    def sleep(duration:float) -> SleepAwaitable:
        return asyncio._sleep_awaitable(duration)

class WaitEvent(object):
    def __init__(self):
        self.__lock = _thread.allocate_lock()
        self.__value_lock = _thread.allocate_lock()
        self.__value = None
        self.__lock.acquire()

    def notify(self, value: Any):
        self.__value_lock.acquire()
        self.__value = value
        self.__value_lock.release()
        self.__lock.acquire(False)
        self.__lock.release()
    
    def wait(self, timeout: float = -1) -> Optional[Any]:
        while True:
            self.__value_lock.acquire()
            if self.__value is not None:
                value = self.__value
                self.__value = None
                self.__value_lock.release()
                return value
            else:
                self.__value_lock.release()
            if not self.__lock.acquire(True, timeout):
                return None

    def release(self):
        self.__lock = None

class GSMError(Exception):
    def __init__(self, message:str):
        super().__init__(message)

class _GSM(object):
    "Controls u-blox GSM Module"
    CR = const(0x0d)
    LF = const(0x0a)

    SOCKET_TCP = const(0)
    SOCKET_UDP = const(1)

    MAX_CONNECT_ID = const(12)
    MAX_SOCKET_DATA_SIZE = const(1460)

    def __init__(self, uart: machine.UART):
        self.__l = logging.Logger('GSM')
        self.__uart = uart
        self.__urcs = None #type: Optional[List[bytes]]
        self.__ppp = None #type: network.PPP
        self.__buffer = bytearray(1024)

    def initialize(self) -> None:
        "Initialize I/O ports and peripherals to communicate with the module."
        self.__l.debug('initialize')
        
        self.__uart.init(baudrate=115200, timeout=30)

    async def reset(self) -> bool:
        "Turn on or reset the module and wait until the LTE commucation gets available."
        self.__urcs = []

        self.write_command(b'~+++')
        if not await self.write_command_wait(b'AT', b'OK'):    # Check if the module can accept commands.
            self.__l.info("The module did not respond.")
            return False
        if not await self.write_command_wait(b'ATZ', b'OK'):  # Reset module.
            self.__l.info("Failed to reset the module.")
            return False
        await asyncio.sleep_ms(100)
        if not await self.write_command_wait(b'ATE0', b'OK'):  # Disable command echo
            self.__l.info("Failed to disable command echo.")
            return False
        if not await self.write_command_wait(b'AT+CFUN=1', b'OK'):  # Enable RF.
            self.__l.info("Failed to enable RF.")
            return False
        
        buffer = bytearray(1024)
        
        self.__l.info('Waiting SIM goes active...')
        while True:
            result, responses = await self.execute_command(b'AT+CPIN?', buffer, timeout=1000)
            self.__l.info('AT+CPIN result={0}, response={1}'.format(result, len(responses)))
            if len(responses) == 0: return False
            if result: 
                return True

    async def get_IMEI(self) -> Optional[str]:
        "Gets International Mobile Equipment Identity (IMEI)"
        response = await self.execute_command_single_response(b'AT+GSN')
        return str(response, 'utf-8') if response is not None else None
    
    async def get_IMSI(self) -> Optional[str]:
        "Gets International Mobile Subscriber Identity (IMSI)"
        response = await self.execute_command_single_response(b'AT+CIMI')
        return str(response, 'utf-8') if response is not None else None

    async def get_phone_number(self) -> Optional[str]:
        "Gets phone number (subscriber number)"
        response = await self.execute_command_single_response(b'AT+CNUM', b'+CNUM:')
        return str(response[6:], 'utf-8') if response is not None else None

    async def get_RSSI(self) -> Optional[Tuple[int,int]]:
        "Gets received signal strength indication (RSSI)"
        response = await self.execute_command_single_response(b'AT+CSQ', b'+CSQ:')
        if response is None:
            return None
        try:
            s = str(response[5:], 'utf-8')
            rssi, ber = s.split(',', 2)
            return (int(rssi), int(ber))
        except ValueError:
            return None
    
    async def activate(self, access_point:str, user:str, password:str, timeout:int=None) -> bool:
        self.__l.info("Activating network...")
        while True:
            # Read network registration status.
            response = await self.execute_command_single_response(b'AT+CGREG?', b'+CGREG:', timeout)
            if response is None:
                raise GSMError('Failed to get registration status.')
            s = str(response, 'utf-8')
            self.__l.debug('AT+CGREG?:%s', s)
            n, stat = s.split(',')[:2]
            if stat == '4':  # Not registered and not searching (0), or unknown (4).
                raise GSMError('Invalid registration status.')
            elif stat == '0':
                await asyncio.sleep_ms(1)
            elif stat == '1' or stat == '5': # Registered.
                break
        # No action
        if not await self.write_command_wait(b'AT&D0', b'OK', timeout):
            return False
        
        # Enable verbose error
        if not await self.write_command_wait(b'AT+CMEE=2', b'OK', timeout):
            return False

        # Define a PDP context
        command = bytes('AT+CGDCONT=1,"IP","{0}"'.format(access_point), 'utf-8')
        if not await self.write_command_wait(command, b'OK', timeout):
            return False
        
        # Activate a PDP context
        if not await self.write_command_wait(b'AT+CGACT=1', b'OK', timeout):
            return False
        if not await self.write_command_wait(b'AT+CGACT?', b'OK', timeout):
            return False
        
        # Enter to PPP mode
        if not await self.write_command_wait(b'AT+CGDATA="PPP",1', b'CONNECT', timeout):
            return False

        # Construct PPP
        self.__l.info("Initializing PPP...")
        self.__ppp = network.PPP(self.__uart)

        # Activate PPP
        self.__l.info("Activating PPP...")
        self.__ppp.active(True)

        # Connect
        self.__l.info("Connecting PPP...")
        self.__ppp.connect(authmode=self.__ppp.AUTH_PAP, username=user, password=password)
        
        self.__l.info("PPP Connected.")
        return True
    

    def write(self, s:bytes) -> None:
        self.__l.debug('<- ' + str(s, 'utf-8'))
        self.__uart.write(s)
    
    def read(self, length:int) -> bytes:
        return self.__uart.read(length)
    
    def write_command(self, command:bytes) -> None:
        self.__l.debug('<- %s', command)
        self.__uart.write(command)
        self.__uart.write(b'\r')

    async def write_command_wait(self, command:bytes, expected_response:bytes, timeout:int=None) -> bool:
        self.write_command(command)
        return await self.wait_response(expected_response, timeout=timeout) is not None


    async def read_response_into(self, buffer:WriteableBufferType, offset:int=0, timeout:Optional[int]=None) -> Optional[int]:
        while True:
            length = await self.__read_response_into(buffer=buffer, offset=offset, timeout=timeout)
            mv = memoryview(buffer)
            if length is not None and length >= 8 and mv[0:8] == b"+QIURC: ":
                #self.__l.info("URC: {0}".format(str(mv[:length], 'utf-8')))
                if length > 17 and mv[8:16] == b'"closed"':
                    connect_id = int(str(mv[17:length], 'utf-8'))
                    self.__l.info("Connection {0} closed".format(connect_id))
                    self.__urcs.append( ("closed", connect_id) )
                    continue
            
            return length
    

    async def __read_response_into(self, buffer:WriteableBufferType, offset:int=0, timeout:int=None) -> Optional[int]:
        buffer_length = len(buffer)
        response_length = 0
        state = 0
        start_time_ms = time.ticks_ms()
        cb = bytearray(1)
        while True:
            n = self.__uart.readinto(cb) #type: int
            if n == 0:
                if timeout is not None and (time.ticks_ms()-start_time_ms) >= timeout:
                    return None
                try:
                    await asyncio.sleep_ms(1)
                except asyncio.CancelledError:
                    return None
                continue
            c = cb[0]

            #self.__l.debug('S:%d R:%c', state, c)
            if state == 0 and c == _GSM.CR:
                state = 1
            elif state == 1 and c == _GSM.LF:
                state = 2
            elif state == 1 and c == _GSM.CR:
                state = 1
            elif state == 1 and c != _GSM.LF:
                response_length = 0
                state = 0
            elif state == 2 and c == _GSM.CR:
                if response_length == 0:
                    state = 1   # Maybe there is another corresponding CR-LF followed by actual response data. So we have to return to state 1.
                else:
                    state = 4
            elif state == 2 and c != _GSM.CR:
                buffer[offset+response_length] = c
                response_length += 1
                if offset+response_length == buffer_length:
                    state = 3
            elif state == 3 and c == _GSM.CR:
                state = 4
            elif state == 4 and c == _GSM.LF:
                return response_length
    
    async def wait_response(self, expected_response:bytes, max_response_size:int=1024, timeout:Optional[int]=None) -> Optional[WriteableBufferType]:
        self.__l.debug('wait_response: target=%s', expected_response)
        response = memoryview(self.__buffer) if len(self.__buffer) <= max_response_size else bytearray(max_response_size)
        expected_length = len(expected_response)
        while True:
            length = await self.read_response_into(response, timeout=timeout)
            if length is None: return None
            self.__l.debug("wait_response: response=%s", str(response[:length], 'utf-8'))
            if length >= expected_length and response[:expected_length] == expected_response:
                return response[:length]
    
    async def wait_response_into(self, expected_response:bytes, response_buffer:bytearray, timeout:Optional[int]=None) -> Optional[WriteableBufferType]:
        self.__l.debug('wait_response_into: target=%s', expected_response)
        expected_length = len(expected_response)
        mv = memoryview(response_buffer)
        while True:
            length = await self.read_response_into(response_buffer, timeout=timeout)
            if length is None: return None
            self.__l.debug("wait_response_into: response=%s", str(mv[:length], 'utf-8'))
            if length >= expected_length and mv[:expected_length] == expected_response:
                return mv[:length]

    async def wait_prompt(self, expected_prompt:bytes, timeout:Optional[int]=None) -> bool:
        prompt_length = len(expected_prompt)
        index = 0
        start_time_ms = time.ticks_ms()
    
        while True:
            c = self.__uart.readchar()
            if c < 0:
                if time.ticks_ms() - start_time_ms > timeout:
                    return False
                await asyncio.sleep_ms(1)
                continue
            if expected_prompt[index] == c:
                index += 1
                if index == prompt_length:
                    return True
            else:
                index = 0
        
    async def execute_command(self, command:bytes, response_buffer:bytearray, index:int=0, expected_response_predicate:Callable[[memoryview],bool]=None, expected_response_list:List[bytes]=[b'OK'], timeout:int=None) -> Tuple[bool, List[memoryview]]:
        assert expected_response_predicate is not None or expected_response_list is not None
        if expected_response_predicate is None:
            expected_response_predicate = lambda mv: mv in expected_response_list 
        self.write_command(command)
        responses = []
        mv = memoryview(response_buffer)
        while True:
            length = await self.read_response_into(response_buffer, index, timeout=timeout)
            if length is None:
                return (False, responses)
            response = mv[index:index+length]
            responses.append(response)
            if expected_response_predicate(response):
                return (True, responses)
            index += length

    async def execute_command_single_response(self, command:bytes, starts_with:bytes=None, timeout:Optional[int]=None) -> Optional[BufferType]:
        result, responses = await self.execute_command(command, self.__buffer, timeout=timeout)
        if not result: return None
        starts_with_length = len(starts_with) if starts_with is not None else 0

        for response in responses:
            if starts_with_length == 0 and len(response) > 0:
                response = bytes(response)
                self.__l.debug('-> %s', response)
                return response
            if starts_with_length > 0 and len(response) >= starts_with_length and response[:starts_with_length] == starts_with:
                response = bytes(response)
                self.__l.debug('-> %s', response)
                return response
        return None



class GSM(object):
    "Wrapper of GSM to run GSM process in background thread"
    STATE_ERROR        = const(-1)
    STATE_INITIALIZING = const(0)
    STATE_ACTIVATING   = const(1)
    STATE_CONNECTING   = const(2)
    STATE_CONNECTED    = const(3)
    
    @staticmethod
    def __thread_proc(obj: GSM) -> None:
        runner = obj.__run() # type: SleepAwaitable
        try:
            while True:
                next(runner)
                runner.send(None)
        except StopIteration:
            pass
        print('GSM thread stopped')

    def __init__(self, uart: machine.UART):
        self.__lock = _thread.allocate_lock()
        self.__thread = None
        self.__gsm = _GSM(uart)
        self.__state = GSM.STATE_INITIALIZING
        self.__ifconfig = None # type: Optional[Tuple[str,str,str,str]]
        self.__l = logging.Logger('GSM')
        self.__wait = WaitEvent()
    
    def start(self, apn:str, user:str, password:str, timeout:int=30000) -> None:
        self.__apn = apn
        self.__user = user
        self.__password = password
        self.__timeout = timeout
        self.__gsm.initialize()
        self.__thread = _thread.start_new_thread(GSM.__thread_proc, (self,))

    
    def state(self) -> int:
        self.__lock.acquire()
        value = self.__state
        self.__lock.release()
        return value
    
    def __make_values(self) -> Dict[str, Union[Optional[Tuple[str,str,str,str]],int]]:
        return {
            'ifconfig': self.__ifconfig,
            'state': self.__state,
        }
    def __notify_values(self) -> None:
        values = self.__make_values()
        self.__wait.notify(values)
    
    def __set_state(self, state: int) -> None:
        self.__lock.acquire()
        self.__state = state
        self.__notify_values()
        self.__lock.release()
    
    def values(self) -> Dict[str, Union[Optional[Tuple[str,str,str,str]],int]]:
        self.__lock.acquire()
        values = self.__make_values()
        self.__lock.release()
        return values
    
    def is_connected(self) -> bool:
        v = self.values()
        return v is not None and v['ifconfig'] is not None
    
    def ifconfig(self) -> Optional[Tuple[str,str,str,str]]:
        v = self.values()
        return v['ifconfig'] if v is not None else None
    
    def wait_values(self, timeout: float = -1) -> Optional[Dict[str, Union[str,int]]]:
        return self.__wait.wait()
    
    async def __run(self):
        while True:
            if not await self.__gsm.reset():
                self.__l.error('Failed to reset GSM module.')
                self.__ifconfig = None
                self.__set_state(GSM.STATE_ERROR)
                await asyncio.sleep(1)
                continue
            self.__set_state(GSM.STATE_ACTIVATING)
        
            if not await self.__gsm.activate(self.__apn, self.__user, self.__password, self.__timeout):
                self.__l.error('Failed to activae network.')
                self.__set_state(GSM.STATE_ERROR)
                await asyncio.sleep(1)
                continue
            self.__set_state(GSM.STATE_CONNECTING)
            
            while not self.__gsm.__ppp.isconnected():
                await asyncio.sleep(1)
            self.__ifconfig = self.__gsm.__ppp.ifconfig()
            self.__set_state(GSM.STATE_CONNECTED)

            while True:    
                await asyncio.sleep(1)

def Soracom3G(uart: Optional[machine.UART]=None) -> GSM:
    if uart is None:
        uart = machine.UART(2, tx=17, rx=16, baudrate=115200)
    return GSM(uart)
