# Smart Contract Analyzer

Small script that interacts with Etherscan API tp download the bytecode of recently interacted Smart Contracts.
Then uses [Mythril](https://github.com/ConsenSys/mythril) in docker containers with more than 1 thread to analyze them.

Requires a file .env in the folder of the script with the etherscan api key:
API_KEY=xxxxx
