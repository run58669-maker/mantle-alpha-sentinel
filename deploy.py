#!/usr/bin/env python3
"""Deploy AlertRegistry contract to Mantle Sepolia testnet."""
import json
import os
import subprocess
import sys
from pathlib import Path
from web3 import Web3

RPC = "https://rpc.sepolia.mantle.xyz"
CHAIN_ID = 5003

def load_wallet():
    wallet_file = Path(__file__).parent / ".wallet"
    data = {}
    for line in wallet_file.read_text().strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data["ADDRESS"], data["PRIVATE_KEY"]

def compile_contract():
    sol_path = Path(__file__).parent / "contracts" / "AlertRegistry.sol"
    source = sol_path.read_text()

    from solcx import compile_source, install_solc
    install_solc("0.8.19")
    compiled = compile_source(source, output_values=["abi", "bin"], solc_version="0.8.19")
    contract_id, contract_interface = list(compiled.items())[0]
    return contract_interface["abi"], contract_interface["bin"]

def deploy():
    address, private_key = load_wallet()
    print(f"Deployer: {address}")

    w3 = Web3(Web3.HTTPProvider(RPC))
    if not w3.is_connected():
        print("ERROR: Cannot connect to Mantle Sepolia RPC")
        sys.exit(1)

    balance = w3.eth.get_balance(address)
    print(f"Balance: {w3.from_wei(balance, 'ether')} MNT")
    if balance == 0:
        print("ERROR: No MNT balance. Get testnet MNT from a faucet first.")
        print("  -> https://www.hackquest.io/faucets  (4 MNT, needs login)")
        print(f"  -> Wallet address: {address}")
        sys.exit(1)

    print("Compiling contract...")
    abi, bytecode = compile_contract()

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    nonce = w3.eth.get_transaction_count(address)
    gas_price = w3.eth.gas_price

    tx = contract.constructor().build_transaction({
        "chainId": CHAIN_ID,
        "from": address,
        "nonce": nonce,
        "gasPrice": gas_price,
    })

    tx["gas"] = w3.eth.estimate_gas(tx)
    print(f"Estimated gas: {tx['gas']}, gas price: {gas_price}")

    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"TX sent: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    contract_address = receipt["contractAddress"]
    print(f"Contract deployed at: {contract_address}")
    print(f"Explorer: https://sepolia.mantlescan.xyz/address/{contract_address}")

    # Save deployment info
    deploy_info = {
        "contract_address": contract_address,
        "deployer": address,
        "chain_id": CHAIN_ID,
        "tx_hash": tx_hash.hex(),
        "abi": abi,
    }
    info_path = Path(__file__).parent / "deployment.json"
    info_path.write_text(json.dumps(deploy_info, indent=2))
    print(f"Deployment info saved to {info_path}")

    return contract_address

if __name__ == "__main__":
    deploy()
