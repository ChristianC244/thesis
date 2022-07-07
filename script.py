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
import argparse

# Parse args
parser = argparse.ArgumentParser()
parser.add_argument("-t", "--threads", type=int, help="Set how many threads", default=8)
parser.add_argument("-e", "--execution", type=int, help="Maximum execution time in MINUTES for each analysis", default=30)
args = parser.parse_args()
# Load dir
wd = os.path.dirname(os.path.realpath(__file__))+"/"
load_dotenv()
# INFURA_ID = os.getenv("INFURA_ID")
API_KEY = os.getenv("API_KEY")
threads = args.threads
time = 60 * args.execution 

def main():
    try:
        man = Manager(API_KEY, threads, time)
        man.start_scan()
    except KeyboardInterrupt:
        print(f"\nGracefully stopping...\n[it can take up to {time//60} min]\nPress again Ctrl-C to hard stop!")
        man.stopped = True

if __name__ == "__main__":
    main()


