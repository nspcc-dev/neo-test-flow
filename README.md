# neo-bench

This is a repository with automated scripts to prepare environment for stress testing
of neo-cli nodes. Based on CoZ's [neo-local](https://github.com/CityOfZion/neo-local).
For more details read here. 

## Description

This repository contains docker environment to work with several neo-cli nodes running 
in consensus mode. You can specify neo-cli image in `.env` file

```
$ cat .env
# Docker Compose supports declaring default environment variables in a file named `.env`.
# https://docs.docker.com/compose/env-file/

PRIVNET_IMAGE=cityofzion/neo-local-privatenet:2.9.4_6kBlocks
```

### Creating wallets
Automated scripts allow you to create several wallets. To do this start 
environment and connect to the `neo-python` container

```
$ make up

Start environment

Creating network "neo-bench_inside" with the default driver
Creating network "neo-bench_host-exposed" with driver "bridge"
Creating neo-cli-privatenet-1 ... done
Creating neo-cli-privatenet-4 ... done
Creating neo-cli-privatenet-3 ... done
Creating neo-cli-privatenet-2 ... done
Creating neo-python           ... done

$ make connect
Connect to neo-python
root@ce8ab230ec2c:/neo-python# 
```

Go to the `scripts` directory and run `wallet-get.py`.
Script takes one argument - number of wallets.
Wallets will be placed in shared `/wallets` directory.

```
root@ce8ab230ec2c:/neo-python# cd scripts/
root@ce8ab230ec2c:/neo-python/scripts# ./wallet-gen.py 20  
0 ARvsNf422pmPZ8rG9qCW8pfmBuWvFNwkza
1 ALS6xvzkwqMMJcWeYP6eup25zE3P21zCHW
 . . . 
19 AWDkHKRsZ828xsPsstbRHXRSBWjYNUEUiR
root@ce8ab230ec2c:/neo-python# 
```

### Generating transactions
Script `tx-gen.py` fills wallets with assets and generate required number of transactions. 
Be aware, that **X** transactions requires **2X** wallets.

```
root@ce61ea096a0c:/neo-python/scripts# ./tx-gen.py -h                
usage: tx-gen.py [-h] [-n N] [--walletneo WALLETNEO] [--walletgas WALLETGAS]
                 [--txneo TXNEO] [--txfee TXFEE] [-f F]

optional arguments:
  -h, --help            show this help message and exit
  -n N                  total amount of transactions
  --walletneo WALLETNEO
                        premade NEO in wallet
  --walletgas WALLETGAS
                        premade GAS in wallet
  --txneo TXNEO         amount of sending NEO
  --txfee TXFEE         tx fee
  -f F                  file to save raw transactions

root@ce61ea096a0c:/neo-python/scripts# ./tx-gen.py -n 10 -f ./raw.txs                                                
Privatenet useragent '/Neo:2.9.4/', nonce: 2064273488                                         
[I 190319 10:23:07 Settings:331] Created 'Chains' directory at /root/.neopython/Chains                               
[I 190319 10:23:07 LevelDBBlockchain:112] Created Blockchain DB at /root/.neopython/Chains/privnet
[I 190319 10:23:07 tx-gen:215] ...awaits 0/0
[I 190319 10:24:56 tx-gen:215] ...awaits 6335/6491
[I 190319 10:24:58 tx-gen:221] Syncronized. Height 6492 Now open wallet:
[I 190319 10:24:58 tx-gen:231] Wallet opened                                                                         
[I 190319 10:25:03 tx-gen:131] Constructing NEO : 0-9
Sending 10.0 NEO from AK2nJJpJr6o664CWJKi1QRXjqeic2zRp8y to AVbJNxd7s5H8PimmgRTWgysLcToBAv8Qha                       
 . . .
Sending 10.0 NEO from AK2nJJpJr6o664CWJKi1QRXjqeic2zRp8y to AQ4QNSF6TJv7Z9hXEgvbQxdqtHbnUZYtfc
Returning 99999900.0 NEO as change to AK2nJJpJr6o664CWJKi1QRXjqeic2zRp8y                                             
[I 190319 10:25:03 Transaction:619] Verifying transaction: b'4fb06c6da3150a6e882d315064dc80a01a019601a4605ae50bce60bb702ef6aa'

[I 190319 10:25:06 tx-gen:131] Constructing GAS : 0-9
Sending 2.0 GAS from AK2nJJpJr6o664CWJKi1QRXjqeic2zRp8y to AVbJNxd7s5H8PimmgRTWgysLcToBAv8Qha                        
 . . .
Sending 2.0 GAS from AK2nJJpJr6o664CWJKi1QRXjqeic2zRp8y to AQ4QNSF6TJv7Z9hXEgvbQxdqtHbnUZYtfc
Returning 20132.0 GAS as change to AK2nJJpJr6o664CWJKi1QRXjqeic2zRp8y

[I 190319 10:25:12 tx-gen:278] Generating raw transactions
[E 190319 10:25:12 Wallet:126] Could not load height data invalid literal for int() with base 10: b'\x00\x00\x00\x00'
[I 190319 10:25:12 tx-gen:203] Rawed transaction 0
 . . .
[E 190319 10:25:12 Wallet:126]  b'\x00\x00\x00\x00'
[I 190319 10:25:12 tx-gen:203] Rawed transaction 9
[I 190319 10:25:12 tx-gen:346] Shutting down.

```

Ignore `Could not load height data invalid literal for int() with base 10:` errors. 

### Watching on blocks
You can watch on amount of transaction in blocks without starting neo-scan instances.
To do that you can run script `getblock.py` on your host environment 
(not in neo-python container ). Script takes one argument - number of block. 
Script shows you number of block, number of transactions in block, 
time to generate for required and 50 extra blocks.

```
$ ./scripts/getblock.py 100
100 1 
101 1 18
102 1 16
103 1 18
104 1 17
105 1 17
106 1 17
 . . .
148 1 18
149 1 18
150 1 16
```