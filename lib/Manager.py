import requests
import threading
import os
import json
from time import sleep, time, strftime, gmtime
import subprocess

import logging
logging.basicConfig(filename='scanner.log', filemode='w', format='%(asctime)s | %(levelname)s | %(threadName)s | %(message)s',level=logging.DEBUG)

class Manager:
    
    def __init__(self, api_key: str, n_threads: int, time: int):
        """
        Parameters:
            api_key: a string containing the etherscan api key
            n_threads: how many threads to launch
            time: max execution time for each thread
        """
        self.API_KEY = api_key
        self.THREADS = n_threads
        self.TIME = time
        self.threads = [threading.Thread(target= self.__thread_func, name=i, args= [i]) for i in range(self.THREADS)]
        self.transactions = list()    
        self.wd = os.path.dirname(os.path.realpath(__file__))+"/../"
        self.prev_block = 0
        self.lock = threading.Lock()
        self.stopped = False


        self.history = {}
        if os.path.exists(self.wd + "history.json"): 
            with open(self.wd + "history.json") as file:
                self.history = json.load(file)
        else: 
            with open(self.wd + "history.json","w") as file:
                None
        logging.debug("Manager class initiated")
        logging.info(f"Loaded hystory file with: {len(self.history)} entries")

    def start_scan(self):
        """Starts the scan, it run indefinetly. to stop it press Ctrl-C"""
        junk = os.listdir(self.wd + "tmp/")
        for file in junk:
            os.remove(self.wd + "tmp/" + file)
        logging.debug("'tmp/' folder cleared")
        while True:
            p = subprocess.run("docker container prune -f", shell=True, capture_output=True)
            if p.stderr != b"": 
                print("Docker deamon not running... Retry in 30s")
                logging.warning("Docker deamon not running... Retry in 30s")
                sleep(30)
                continue
            print(p.stdout.decode())
            break
        
        self.update_transactions()
        print(f"Starting {self.THREADS} threads with execution time: {self.TIME//60} min")
        logging.info(f"Starting {self.THREADS} threads with execution time: {self.TIME//60} min")
        for t in self.threads:
            t.start()
        
        self.watchdog()

    def watchdog(self):
        """Every minute checks if some thread has finish, if so it recreates it and start it. If a thread crashes it won't cause any problem"""
        while True:
            sleep(60)
            if self.stopped: 
                logging.warning("Ctrl-C Pressed... Waiting for threads to terminate")
                [t.join() for t in self.threads]
                subprocess.run("docker container prune -f", shell=True, capture_output=True)
                break
            subprocess.run("docker container prune -f", shell=True, capture_output=True)
            for i  in range(self.THREADS):
                if not self.threads[i].is_alive(): 
                    logging.debug(f"Starting thread {i}")
                    self.threads[i] = threading.Thread(target= self.__thread_func, args= [i], name= i)
                    self.threads[i].start()

    
    def update_transactions(self):
        """Downloads new transactions from the latest block"""
        while True:
            block = int(self.get_latest_block_number()[2:], 16) # 0x2131 -> in int
            if block == self.prev_block:
                print("Waiting for a new block...")
                logging.warning("Waiting for a new block...")
                sleep(60)
                continue
            self.prev_block = block
            break

        txs = self.get_block_by_number(block)["transactions"]
        for t in txs:
            self.transactions.append(t["from"])
            self.transactions.append(t["to"])
        print(f"Added {len(self.transactions)} new addresses from block: {hex(block)}")
        logging.info(f"Added {len(self.transactions)} new addresses from block: {hex(block)}")
    
    def get_fields(self):
        """Function called by a thread to receive a bytecode and it's address if never checked before """
        with self.lock:
            while True:

                if len(self.transactions) == 0: 
                    self.update_transactions()
                    continue

                address = self.transactions.pop()
                if address in self.history: 
                    logging.debug(f"{address} already in history")
                    continue

                bytecode = self.get_code(address)
                if bytecode == "0x": 
                    self.history[address] = False
                    logging.debug(f"{address} is not a Smart Contract")
                    continue

                self.history[address] = True 
                with open(self.wd + "history.json","w") as file:
                    json.dump(self.history, file, indent = 4)
                logging.debug(f"{address} is a valid Smart Contract")
                return (address, bytecode)


    def get_code(self, address: str):
        """returns '0x' if not a contract, else a string with the hex bytecode"""
        # if not _check_addr(address): return None
        response
        try:
            response = requests.get("http://api.etherscan.io/api?module=proxy&action=eth_getCode&address={}&tag=latest&apikey={}".format(address, self.API_KEY), timeout=10)
        except Exception as e:
            print("Exception in getting URL Content")
            logging.error(e)
        if response.status_code != 200: 
            print(response.reason)
            logging.error(response.reason)
            exit()
        
        payload = response.json()
        if "status" in payload: 
            print(payload)
            logging.error(payload)
            exit()
        
        return payload["result"]


    def get_block_by_number(self, n:int = -1):
        """Specify n for a specific block, leave -1 to get the last one created"""
    
        latest_block = self.get_latest_block_number() if n >= 0 else hex(n)
        response
        try: 
            response = requests.get("http://api.etherscan.io/api?module=proxy&action=eth_getBlockByNumber&tag={}&boolean=true&apikey={}".format(latest_block, self.API_KEY), timeout=10)
        except Exception as e:
            print("Exception in getting URL Content")
            logging.error(e)
        if response.status_code != 200: 
            # HTTP Error
            print(response.reason)
            logging.error(response.reason)
            exit()

        payload = response.json()
        if "status" in payload: 
            # Bad API request
            print(payload)
            logging.error(payload)
            exit()

        return payload["result"]
    
    def get_latest_block_number(self) -> str:
        response
        try:
            response = requests.get("http://api.etherscan.io/api?module=proxy&action=eth_blockNumber&apikey={}".format(self.API_KEY), timeout=10)
        except Exception as e:
            print("Exception in getting URL Content")
            logging.error(e)
        if response.status_code != 200: 
            """http error"""
            print(response.reason)
            logging.error(response.reason)
            exit()

        payload = response.json()
        if "status" in payload: 
            """bad api request"""
            print(payload)
            logging.error(payload)
            exit()

        return payload["result"]


    def __thread_func(self, thread_n):
        """Function runned by threads, it stores the bytecode into <workdir>/tmp/ and pass it to myth docker container. After the analysis the file get removed"""
        
        address, bytecode = self.get_fields()
        if self.stopped: 
            logging.warn(f"Dropping contract at {address}")
            
            return
        _start = time()
        print(f"TH-{thread_n} is Scanning {address}")
        logging.info(f"Start Scanning {address}")
        with open(self.wd + "/tmp/" + address, "w") as file:
            file.write(bytecode)
    
        p = subprocess.run("docker run -v {}:/tmp mythril/myth a -f /tmp/tmp/{} --execution-timeout {}".format(self.wd, address, self.TIME), shell=True, capture_output=True)
        with open(self.wd + "/data/" + address, "w") as file:
            file.writelines(p.stdout.decode())
        logging.info(f"Done Scanning {address}")
        
        os.remove(self.wd + "/tmp/" + address)
        _stop = time()
        print(log_output(thread_n, len(bytecode[2:]), _stop - _start))
        logging.info(log_output(thread_n, len(bytecode[2:]), _stop - _start))
    
def log_output(n_thread: int, bytecode_len: int, delta_time: float):
    
    s = f"TH-{n_thread} has analyzed "

    # Correct unit of byte
    u = ["GB", "MB", "kB", "B"]
    i = 0
    k = 1_000_000_000 #GB
    while k > 0:
        if bytecode_len / k > 1:
            s += f"{(bytecode_len / k):.3f} {u[i]} "
            break
        k //= 1000
        i += 1
    
    # Correct unit of time
    t = strftime("%H:%M:%S", gmtime(delta_time))
    s += f"in {t}s"

    return s

