import requests
import threading
import os
import json
from time import sleep
import subprocess


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

    def start_scan(self):
        """Starts the scan, it run indefinetly. to stop it press Ctrl-C"""
        junk = os.listdir(self.wd + "tmp/")
        for file in junk:
            os.remove(self.wd + "tmp/" + file)
    
        subprocess.run("docker container prune -f", shell=True)
        self.update_transactions()
        print(f"Starting {self.THREADS} threads with execution time: {self.TIME//60} min")
        for t in self.threads:
            t.start()
        
        self.watchdog()

    def watchdog(self):
        """Every minute checks if some thread has finish, if so it recreates it and start it. If a thread crashes it won't cause any problem"""
        while True:
            sleep(60)
            subprocess.run("docker container prune -f", shell=True, capture_output=True)
            if self.stopped: 
                [t.join() for t in self.threads]
                break
            for i  in range(self.THREADS):
                if not self.threads[i].is_alive(): 
                    self.threads[i] = threading.Thread(target= self.__thread_func, args= [i], name= i)
                    self.threads[i].start()

    
    def update_transactions(self):
        """Downloads new transactions from the latest block"""
        while True:
            block = int(self.get_latest_block_number()[2:], 16) # 0x2131 -> in int
            if block == self.prev_block:
                print("Waiting for a new block...")
                sleep(60)
                continue
            self.prev_block = block
            break

        txs = self.get_block_by_number(block)["transactions"]
        for t in txs:
            self.transactions.append(t["from"])
            self.transactions.append(t["to"])
    
    def get_fields(self):
        """Function called by a thread to receive a bytecode and it's address if never checked before """
        with self.lock:
            
            while True:
                if len(self.transactions) == 0: self.update_transactions()
                address = self.transactions.pop()
                if address in self.history: continue

                bytecode = self.get_code(address)
                if bytecode == "0x": 
                    self.history[address] = False
                    continue

                self.history[address] = True 
                with open(self.wd + "history.json","w") as file:
                    json.dump(self.history, file, indent = 4)
                return (address, bytecode)


    def get_code(self, address: str):
        """returns '0x' if not a contract, else a string with the hex bytecode"""
        # if not _check_addr(address): return None
        response = requests.get("https://api.etherscan.io/api?module=proxy&action=eth_getCode&address={}&tag=latest&apikey={}".format(address, self.API_KEY))
        if response.status_code != 200: 
            print(response.reason)
            exit()
        
        payload = response.json()
        if "status" in payload: 
            print(payload)
            exit()
        
        return payload["result"]


    def get_block_by_number(self, n:int = -1):
        """Specify n for a specific block, leave -1 to get the last one created"""
    
        latest_block = self.get_latest_block_number() if n >= 0 else hex(n)
        response = requests.get("https://api.etherscan.io/api?module=proxy&action=eth_getBlockByNumber&tag={}&boolean=true&apikey={}".format(latest_block, self.API_KEY))
        if response.status_code != 200: 
            # HTTP Error
            print(response.reason)
            exit()

        payload = response.json()
        if "status" in payload: 
            # Bad API request
            print(payload)
            exit()

        return payload["result"]
    
    def get_latest_block_number(self) -> str:
        response = requests.get("https://api.etherscan.io/api?module=proxy&action=eth_blockNumber&apikey={}".format(self.API_KEY))        
        if response.status_code != 200: 
            """http error"""
            print(response.reason)
            exit()

        payload = response.json()
        if "status" in payload: 
            """bad api request"""
            print(payload)
            exit()

        return payload["result"]


    def __thread_func(self, thread_n):
        """Function runned by threads, it stores the bytecode into <workdir>/tmp/ and pass it to myth docker container. After the analysis the file get removed"""
        
        address, bytecode = self.get_fields()
        print(f"TH-{thread_n} is Scanning {address}")
        with open(self.wd + "/tmp/" + address, "w") as file:
            file.write(bytecode)
    
        p = subprocess.run("docker run -v {}:/tmp mythril/myth a -f /tmp/tmp/{} --execution-timeout {}".format(self.wd, address, self.TIME), shell=True, capture_output=True)
        with open(self.wd + "/data/" + address, "w") as file:
            file.writelines(p.stdout.decode())
        
        os.remove(self.wd + "/tmp/" + address)
        print(f"TH-{thread_n} is Done")