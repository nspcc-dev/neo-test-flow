#!/usr/bin/env python3
from time import sleep
import threading
import traceback
import sys
import argparse

from logzero import logger
from neocore.Fixed8 import Fixed8
from neocore.UInt256 import UInt256
from neocore.UInt160 import UInt160
from twisted.internet import reactor, task

from neo.Core.Blockchain import Blockchain
from neo.Core.CoinReference import CoinReference
from neo.Core.TX.Transaction import TransactionOutput, ContractTransaction, TXFeeError
from neo.Core.TX.TransactionAttribute import TransactionAttribute, TransactionAttributeUsage
from neo.Implementations.Blockchains.LevelDB.LevelDBBlockchain import LevelDBBlockchain
from neo.Implementations.Wallets.peewee.UserWallet import UserWallet
from neo.Network.NodeLeader import NodeLeader
from neo.Prompt.Commands import Send, Wallet
from neo.Prompt.Utils import get_asset_id, lookup_addr_str, get_asset_amount
from neo.Settings import settings
from neo.SmartContract.ContractParameterContext import ContractParametersContext
from neo.Wallets.utils import to_aes_key

WALLET_PWD = "nspcc"
WALLET_PATH = "/wallets/wallet"
MASTER_WALLET_PWD = "coz"
MASTER_WALLET_PATH = "/neo-python/neo-privnet.wallet"
WALLET_DB_PATH = "/wallets/db.log"
BLOCK_AMOUNT = 10

# user defined params
TX_FILE = "/root/raw.txs"
PREMADE_NEO = 10
PREMADE_GAS = 2.0
TX_NEO = 3
TX_GAS = 1.0
TOTAL_AMOUNT = 1000


def read_wallet_db():
    with open(WALLET_DB_PATH, 'r') as f:
          database = f.read().splitlines()
    return database

def write_raw_db(hashes, path):
    with open(path, 'w') as f:
        for hash in hashes:
            f.write(hash.decode("ascii")+"\n")

def process_transaction(wallet, contract_tx, scripthash_from=None, scripthash_change=None, fee=None, owners=None, user_tx_attributes=None):
    try:
        tx = wallet.MakeTransaction(tx=contract_tx,
                                    change_address=scripthash_change,
                                    fee=fee,
                                    from_addr=scripthash_from)
    except ValueError:
        print("Insufficient funds. No unspent outputs available for building the transaction.\n"
              "If you are trying to sent multiple transactions in 1 block, then make sure you have enough 'vouts'\n."
              "Use `wallet unspent` and `wallet address split`, or wait until the first transaction is processed before sending another.")
        raise Exception('oh no')
    except TXFeeError as e:
        print(e)
        raise Exception('oh no')

    if tx is None:
        print("Insufficient funds")
        raise Exception('oh no')

    try:
        input_coinref = wallet.FindCoinsByVins(tx.inputs)[0]
        source_addr = input_coinref.Address
        for order in tx.outputs:
            dest_addr = order.Address
            value = order.Value.ToString()  # fixed8
            if order.AssetId == Blockchain.Default().SystemShare().Hash:
                asset_name = 'NEO'
            else:
                asset_name = 'GAS'

            if source_addr != dest_addr:
                print(f"Sending {value} {asset_name} from {source_addr} to {dest_addr}")
            else:
                print(f"Returning {value} {asset_name} as change to {dest_addr}")
        print(" ")

        standard_contract = wallet.GetStandardAddress()

        if scripthash_from is not None:
            signer_contract = wallet.GetContract(scripthash_from)
        else:
            signer_contract = wallet.GetContract(standard_contract)

        if not signer_contract.IsMultiSigContract and owners is None:
            data = standard_contract.Data
            tx.Attributes = [TransactionAttribute(usage=TransactionAttributeUsage.Script,
                                                  data=data)]

        # insert any additional user specified tx attributes
        tx.Attributes = tx.Attributes + user_tx_attributes

        context = ContractParametersContext(tx, isMultiSig=signer_contract.IsMultiSigContract)
        wallet.Sign(context)

        if context.Completed:
            tx.scripts = context.GetScripts()
            relayed = NodeLeader.Instance().Relay(tx)

            if relayed:
                wallet.SaveTransaction(tx)
                return tx
            else:
                print("Could not relay tx %s " % tx.Hash.ToString())
                raise Exception('oh no')

        else:
            print("Transaction initiated, but the signature is incomplete. Use the `sign` command with the information below to complete signing.")
            print(json.dumps(context.ToJson(), separators=(',', ':')))
            raise Exception('oh no')

    except Exception as e:
        print("Could not send: %s " % e)
        traceback.print_stack()
        traceback.print_exc()

    return

def construct_send_many(wallet, outgoing, start, data, asset, amount):
    logger.info("Constructing %s : %d-%d" % (asset, start, start+outgoing-1))
    output = []
    for i in range(outgoing):
        try:
            assetId = get_asset_id(wallet, asset)
            address_to = data[start+i]
            scripthash_to = lookup_addr_str(wallet, address_to)
            if scripthash_to is None:
                logger.debug("invalid destination address")
                return
            f8amount = get_asset_amount(amount, assetId)
            if f8amount is False:
                logger.debug("invalid amount")
                return
            tx_output = TransactionOutput(AssetId=assetId, Value=f8amount, script_hash=scripthash_to)
            output.append(tx_output)
        except KeyboardInterrupt:
            print('Transaction cancelled')
            return
    contract_tx = ContractTransaction(outputs=output)

    scripthash_from = None
    scripthash_change = None
    owners = None
    user_tx_attributes = []
    fee = Fixed8.Zero()

    return [contract_tx, scripthash_from, scripthash_change, fee, owners, user_tx_attributes]

def create_raw_transaction(walletpath, source, dest, txidNeo, txidGas, n):
    # const for asset id
    gas_asset_id = Blockchain.SystemCoin().Hash
    neo_asset_id = Blockchain.SystemShare().Hash

    # open source wallet for later transaction signing
    wallet = UserWallet.Open(walletpath, to_aes_key(WALLET_PWD))

    source_script_hash = wallet.ToScriptHash(source)
    destination_script_hash = wallet.ToScriptHash(dest)

    contract_tx = ContractTransaction()
    contract_tx.raw_tx = True

    # here we creating vin
    input1 = CoinReference(prev_hash=UInt256.ParseString(txidNeo), prev_index=int(n))
    input2 = CoinReference(prev_hash=UInt256.ParseString(txidGas), prev_index=int(n))
    contract_tx.inputs = [input1, input2]

    # here we creating vout (src [10 NEO] -> { dst [3 NEO]; src [7 NEO] })
    send_to_destination_output1 = TransactionOutput(AssetId=neo_asset_id, Value=Fixed8.FromDecimal(TX_NEO), script_hash=destination_script_hash)
    return_change_output1 = TransactionOutput(AssetId=neo_asset_id, Value=Fixed8.FromDecimal(PREMADE_NEO-TX_NEO), script_hash=source_script_hash)
    return_change_output2 = TransactionOutput(AssetId=gas_asset_id, Value=Fixed8.FromDecimal(TX_GAS), script_hash=source_script_hash)
    contract_tx.outputs = [send_to_destination_output1, return_change_output1, return_change_output2]

    # time to sign
    context = ContractParametersContext(contract_tx)
    wallet.Sign(context)

    # confirmation scripts
    contract_tx.scripts = context.GetScripts()

    raw_tx = contract_tx.ToArray()
    return raw_tx

def construct_raw_many(outgoing, start, data, txidNeo, txidGas):
    output = []
    for i in range(outgoing):
        try:
            pos = start + i
            filename = WALLET_PATH + "%d" % pos
            tx = create_raw_transaction(filename, data[pos], data[pos + TOTAL_AMOUNT], txidNeo, txidGas, i)
            output.append(tx)
            logger.info("Rawed transaction %d" % pos)

        except KeyboardInterrupt:
            print('Transaction cancelled')
            return

    return output

def main_routine():
    # Here we awaiting local node to synchronize with private-net
    while True:
        if Blockchain.Default().Height != Blockchain.Default().HeaderHeight or Blockchain.Default().Height < 10:
            logger.info("...awaits %s/%s" % (Blockchain.Default().Height, Blockchain.Default().HeaderHeight))
            sleep(2)
        else:
            break

    bc_height = Blockchain.Default().Height
    logger.info("Syncronized. Height %s Now open wallet:" % bc_height)
    txsNeo = []
    txsGas = []
    hashes = []

    try:
        wallet = UserWallet.Open(MASTER_WALLET_PATH, to_aes_key(MASTER_WALLET_PWD))
        loop = task.LoopingCall(wallet.ProcessBlocks)
        loop.start(.5)

        logger.info("Wallet opened")

        wallet_db = read_wallet_db()

        sleep(5)
        # In this block we transfer NEO assets from master wallet to generated wallets
        for i in range(int(TOTAL_AMOUNT/BLOCK_AMOUNT)):
            pre_tx = construct_send_many(wallet, BLOCK_AMOUNT, i*BLOCK_AMOUNT, wallet_db, 'NEO', str(PREMADE_NEO))
            funds_source_script_hash = wallet.ToScriptHash(wallet.Addresses[0])
            tx = process_transaction(wallet, contract_tx=pre_tx[0], scripthash_from=funds_source_script_hash,
                                     scripthash_change=pre_tx[2], fee=pre_tx[3], owners=pre_tx[4],
                                     user_tx_attributes=pre_tx[5])
            if tx is None:
                continue
            tx_hash = tx.Hash.ToString()
            txsNeo.append(tx_hash)
            while True:
                # Try to find transaction in blockchain
                sleep(0.5)
                _tx, height = Blockchain.Default().GetTransaction(tx_hash)
                if height > 0:
                    break
            sleep(1)

        # In this block we transfer GAS assets from master wallet to generated wallets
        for i in range(int(TOTAL_AMOUNT/BLOCK_AMOUNT)):
            pre_tx = construct_send_many(wallet, BLOCK_AMOUNT, i*BLOCK_AMOUNT, wallet_db, 'GAS', str(PREMADE_GAS))
            funds_source_script_hash = wallet.ToScriptHash(wallet.Addresses[0])
            tx = process_transaction(wallet, contract_tx=pre_tx[0], scripthash_from=funds_source_script_hash,
                                     scripthash_change=pre_tx[2], fee=pre_tx[3], owners=pre_tx[4],
                                     user_tx_attributes=pre_tx[5])
            if tx is None:
                continue
            tx_hash = tx.Hash.ToString()
            txsGas.append(tx_hash)
            while True:
                # Try to find transaction in blockchain
                sleep(0.5)
                _tx, height = Blockchain.Default().GetTransaction(tx_hash)
                if height > 0:
                    break
            sleep(1)

        loop.stop()
        wallet.Close()
        logger.info("Wallet closed")
        sleep(2)
        logger.info("Generating raw transactions")

        # In this block we generating raw transactions
        for i in range(int(TOTAL_AMOUNT/BLOCK_AMOUNT)):
            hashes += construct_raw_many(BLOCK_AMOUNT, i*BLOCK_AMOUNT, wallet_db, txsNeo[i], txsGas[i])

        write_raw_db(hashes, TX_FILE)


    except Exception as ex:
        logger.info(ex)
        traceback.print_stack()
        traceback.print_exc()
        reactor.stop()
        return

    # After main_routine we stop application
    reactor.stop()
    return


def main():
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", help="total amount of transactions", type=int)
    parser.add_argument("--walletneo", help="premade NEO in wallet", type=int)
    parser.add_argument("--walletgas", help="premade GAS in wallet", type=int)
    parser.add_argument("--txneo", help="amount of sending NEO", type=int)
    parser.add_argument("--txfee", help="tx fee", type=float)
    parser.add_argument("-f", help="file to save raw transactions", type=str)
    args = parser.parse_args()

    global TOTAL_AMOUNT
    global PREMADE_GAS
    global PREMADE_NEO
    global TX_NEO
    global TX_FEE
    global TX_FILE

    if args.n:
        TOTAL_AMOUNT = args.n
    if args.walletgas:
        PREMADE_GAS = args.walletgas
    if args.walletneo:
        PREMADE_NEO = args.walletneo
    if args.txneo:
        TX_NEO = args.tx
    if args.txfee:
        TX_FEE = PREMADE_GAS - args.txfee
    if args.f:
        TX_FILE = args.f

    # Use TestNet
    settings.setup_privnet()

    # Setup the blockchain
    blockchain = LevelDBBlockchain(settings.chain_leveldb_path)
    Blockchain.RegisterBlockchain(blockchain)
    dbloop = task.LoopingCall(Blockchain.Default().PersistBlocks)
    dbloop.start(.5)
    NodeLeader.Instance().Start()

    d = threading.Thread(target=main_routine)
    d.setDaemon(True)
    d.start()

    # Awaiting exit here
    reactor.run()
    logger.info("Shutting down.")

if __name__ == "__main__":
    main()
