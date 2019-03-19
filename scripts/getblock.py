#!/usr/bin/env python3

import urllib.request
import sys
import json
import ast

URL = 'http://127.0.0.1:30334/'
EXTRA_BLOCKS = 50

def main():
    if len(sys.argv) != 2:
        print("USAGE: ./getblock.py <NUM>")
        return

    start = int(sys.argv[1])
    end = start+EXTRA_BLOCKS
    t = None
    while start <= end:
        t = get_tx(start, t)
        start +=1 
    

def get_tx(block, time):
    params = { "jsonrpc": "2.0", "method": "getblock", "params": [block, 1], "id": 1 }
    data = json.dumps(params).encode('utf-8')
    req = urllib.request.Request(URL, data=data)
    req.add_header('Content-Type', 'application/json')
    response = urllib.request.urlopen(req)
    answer = ast.literal_eval(response.read().decode('utf-8'))
    
    if "error" in answer:
        print(block, 'error')
        return None
    else:
        new_time = answer['result']['time']
        if time is not None:
            t = int(new_time) - int(time)
        else:
            t = ''
        print(block, len(answer['result']['tx']), t)
        return new_time



if __name__ == '__main__':
    main()
    
