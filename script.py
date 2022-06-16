"""
Requires a file .env in the folder of the script with the etherscan api key:
======
API_KEY=xxxxx
======
"""

"""
Get source code <available only for 5k contracts in file.csv>
https://api.etherscan.io/api
   ?module=contract
   &action=getsourcecode
   &address=0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413
   &apikey=YourApiKeyToken 
"""

from lib.Manager import Manager

from dotenv import load_dotenv
import os

wd = os.path.dirname(os.path.realpath(__file__))+"/"
load_dotenv()
# INFURA_ID = os.getenv("INFURA_ID")
API_KEY = os.getenv("API_KEY")
THREADS = 12
TIME = 60 * 30 # 30 minutes

def main():
    try:    
        man = Manager(API_KEY, THREADS, TIME)
        man.start_scan()
    except KeyboardInterrupt:
        print(f"\nGracefully stopping...\n[it can take up to {TIME//60} min]\nPress again Ctrl-C to hard stop!")
        man.stopped = True

if __name__ == "__main__":
    main()


