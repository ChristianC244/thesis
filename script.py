"""
Get Latest Block Number
    https://api.etherscan.io/api
    ?module=proxy
    &action=eth_blockNumber
    &apikey=YourApiKeyToken

Get block by number
    https://api.etherscan.io/api
   ?module=proxy
   &action=eth_getBlockByNumber
   &tag=0x10d4f
   &boolean=true
   &apikey=YourApiKeyToken

Get code (only if it is a contract)
    https://api.etherscan.io/api
   ?module=proxy
   &action=eth_getCode
   &address=0xf75e354c5edc8efed9b59ee9f67a80845ade7d0c
   &tag=latest
   &apikey=YourApiKeyToken

docekr run mythril/myth a
-m DELEGATECALL,
[depre]-a ADDRESS
-c BYTECODE
--execution-timeout EXECUTION_TIMEOUT
--statespace-json OUTPUT_FILE
--infura_id INFURA_ID

"""

from time import sleep
from warnings import catch_warnings
from dotenv import load_dotenv
import os
import requests
import json
import subprocess
import threading

wd = os.path.dirname(os.path.realpath(__file__))+"/"
load_dotenv()
INFURA_ID = os.getenv("INFURA_ID")
API_KEY = os.getenv("API_KEY")
THREADS = 6
TIME = 60 * 30 # 30 minutes


def main():

    threads_list = list()
    clear_tmp()
    history = {}
    if os.path.exists(wd + "history.json"): 
        with open(wd + "history.json") as file:
            history = json.load(file)
    else: 
        with open(wd + "history.json","w") as file:
            None
        
    prev_block = 0

    try: 
        while True:
            block = get_block_by_number()
            if block == prev_block:
                print("Waiting for a new block...")
                sleep(60)
                continue
            prev_block = block
            

            for transaction in block["transactions"]:
                sender = transaction["from"]
                receiver = transaction["to"]

                if sender not in history: 
                    res = get_code(sender)
                    if res == "0x": history[sender]=False
                    else:
                        history[sender]=True

                        print("Scanning ",sender)
                        t = threading.Thread(target=myth, args=[res, sender])
                        threads_list.append(t)
                        t.start()
                        # myth(res, sender)
                
                if receiver not in history: 
                    res = get_code(receiver)
                    if res == "0x": history[receiver]=False
                    else:
                        history[receiver]=True

                        print("Scanning ",receiver)
                        t = threading.Thread(target=myth, args=[res, receiver])
                        threads_list.append(t)
                        t.start()
                        
                        # myth(res, receiver)

                if len(threads_list) >= THREADS:
                    print("History updated")
                    with open(wd + "history.json","w") as file:
                        json.dump(history, file, indent = 4)

                    for t in threads_list:
                        t.join()
                    threads_list = list()
                    clear_tmp()
    except KeyboardInterrupt:
        print(f"Carefully stopping...[it can take up to {TIME//60} min]")
        for t in threads_list:
            t.join()

        print("History updated")
        with open(wd + "history.json","w") as file:
            json.dump(history, file, indent = 4)
        
        clear_tmp()
        print("Stopped succesfully!")



def myth(bytecode: str, address: str):
    # print("Should check ", bytecode)
    MODULES = "DELEGATECALL,dependence_on_predictable_vars,ether_thief,external_calls,state_change_external_calls,unchecked_retval,user_assertions"
    
    with open(wd + "/tmp/" + address, "w") as file:
        file.write(bytecode)
    

    p = subprocess.run("docker run -v {}:/tmp mythril/myth a -f /tmp/tmp/{} --execution-timeout {}".format(wd, address, TIME), shell=True, capture_output=True)
    with open(wd + "/data/" + address, "w") as file:
        file.writelines(p.stdout.decode())
    
    # print(p.stderr.decode())


def clear_tmp():
    junk = os.listdir(wd + "tmp/")
    for file in junk:
        os.remove(wd + "tmp/" + file)
    
    subprocess.run("docker container prune -f", shell=True)
    

def get_block_by_number():
    
    latest_block = _get_latest_block_number()
    if latest_block == "": return None

    response = requests.get("https://api.etherscan.io/api?module=proxy&action=eth_getBlockByNumber&tag={}&boolean=true&apikey={}".format(latest_block, API_KEY))
    if response.status_code != 200: 
        print(response.reason)
        return None

    payload = response.json()
    if "status" in payload: 
        print(payload)
        exit()

    return payload["result"]

def get_code(address: str):
    """returns '0x' if not a contract, else a string with the hex bytecode. None if errors in address format or if the http request went wrong"""
    # if not _check_addr(address): return None
    response = requests.get("https://api.etherscan.io/api?module=proxy&action=eth_getCode&address={}&tag=latest&apikey={}".format(address, API_KEY))
    if response.status_code != 200: 
        print(response.reason)
        return None
    
    payload = response.json()
    if "status" in payload: 
        print(payload)
        exit()
    
    return payload["result"]

def _get_latest_block_number() -> str:

    response = requests.get("https://api.etherscan.io/api?module=proxy&action=eth_blockNumber&apikey={}".format(API_KEY))
    
    if response.status_code != 200: 
        print(response.reason)
        return ""

    payload = response.json()
    if "status" in payload: 
        print(payload)
        exit()

    return payload["result"]

def _check_addr(addr: str) -> bool:
    if len(addr) != 42: return False
    try:
        int(addr, 16)
    except:
        return False

    return True


if __name__ == "__main__":
    main()


