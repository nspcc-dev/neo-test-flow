#!/usr/bin/env python3
import sys
from neo.Implementations.Wallets.peewee.UserWallet import UserWallet
from neo.Wallets.utils import to_aes_key

WALLET_PWD = "nspcc"
WALLET_AES_PWD = to_aes_key(WALLET_PWD)
WALLET_PATH = "/wallets/wallet%d"
WALLET_DB_PATH = "/wallets/db.log"

def main():
    if len(sys.argv) != 2:
        print("USAGE: ./wallet-gen.py <NUM>")
        return

    db = []
    for i in range(int(sys.argv[1])):
        wallet = UserWallet.Create(WALLET_PATH % i, WALLET_AES_PWD)
        contract = wallet.GetDefaultContract()
        db.append(contract.Address)
        print(i, contract.Address)
        wallet.Close()

    with open(WALLET_DB_PATH, 'w') as writer:
        for addr in db:
            writer.write("%s\n" % addr)

if __name__ == "__main__":
    main()
