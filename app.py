from pyrogram import Client
from pyrogram.raw import functions

from pyrogram.raw.functions.phone import RequestCall, SendSignalingData
from pyrogram.raw.types import InputPhoneCall, PhoneCallProtocol, UpdatePhoneCall
from pyrogram.handlers import RawUpdateHandler
from pyrogram.raw.types.messages import DhConfigNotModified

from sympy import isprime
def get_protocol() -> PhoneCallProtocol:
    return PhoneCallProtocol(
        min_layer=92,
        max_layer=92,
        udp_p2p=True,
        udp_reflector=True,
        library_versions=['3.0.0'],
    )

class DHC:
    def __init__(self, dictionary):
        for key in dictionary:
            setattr(self, key, dictionary[key])
            
def is_safe_prime(p):
    return isprime(p) and isprime((p - 1) // 2)
def bytes_to_int(bytes_value):
    return int.from_bytes(bytes_value, 'big')

def is_valid_generator(g, p):
    if g == 2:
        return p % 8 == 7
    elif g == 3:
        return p % 3 == 2
    elif g == 4:
        return True  # No extra condition
    elif g == 5:
        return p % 5 in [1, 4]
    elif g == 6:
        return p % 24 in [19, 23]
    elif g == 7:
        return p % 7 in [3, 5, 6]
    else:
        return False
import redis

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def cache_p_g(p, g):
    r.set('dh_p', p)
    r.set('dh_g', g)

def get_cached_p_g():
    p = r.get('dh_p')
    g = r.get('dh_g')
    if p is None or g is None:
        return None, None
    print('cached in stock')
    return p,g

import secrets
import hashlib

def hash_g_a(p, g):
    a = secrets.randbelow(p-1) + 1
    g_a = pow(g, a, p)

    g_a_bytes = g_a.to_bytes((g_a.bit_length() + 7) // 8, 'big')
    g_a_hash = hashlib.sha256(g_a_bytes).digest()

    print("g_a (bytes):", g_a_bytes)
    print("SHA256 hash of g_a:", g_a_hash)
    return g_a_hash, g_a_bytes
# Usage
async def get_p_g(app):
    global dhc
    try:
        p, g = get_cached_p_g()
    except:
        p, g = None, None
    if p is None or g is None:
        async with app:
            dh_config = await app.invoke(
                functions.messages.GetDhConfig(
                    version=0,  # Replace with your cached version or 0 if not available
                    random_length=256  # Example length, adjust as needed
                )
            )
            # Check if the DhConfig is modified or not
            if hasattr(dh_config, 'p') and hasattr(dh_config, 'g'):
                p, g = bytes_to_int(dh_config.p), dh_config.g
                print('new', p, g)
                
            if is_safe_prime(p) and is_valid_generator(g, p):
                print(f"p and g are valid: p={p}, g={g}")
                cache_p_g(p, g)
                return p, g
            # Optionally cache p and g here
            else:
                print("Invalid p or g received")
                return
    else:
        return p, g

async def initiate_call(app, peer, g_a_hash):
    async with app:
        protocol =  get_protocol()
        print('invoking call')
        call = await app.invoke(RequestCall(
            user_id=peer,
            random_id=69,
            g_a_hash=g_a_hash,
            protocol=protocol
        ))
        print("call;\n", call)
    
from pyrogram.raw.functions.phone import ConfirmCall

async def confirm_call(app, peer,g_a, key_fingerprint):
    async with app:
        protocol = get_protocol()
        
        result = await app.invoke(ConfirmCall(
            peer=peer,
            g_a=g_a,
            key_fingerprint=key_fingerprint,
            protocol=protocol
        ))
        print("confirm call result:", result)
    

async def main():
    global dhc
    

    @app.on_raw_update()
    def handle_update_phone_call(client, update, users, chat):
        global dhc
        print(update)
        if isinstance(update, UpdatePhoneCall) and isinstance(update.phone_call, PhoneCallAccepted):
            dhc.g_b  = update.phone_call.g_b
            print("Received g_b:", g_b_value)
            # Compute the Diffie-Hellman key
            key = pow(g_b_value, a, p)  # 'a' and 'p' should be defined earlier in your code

            # Compute the key fingerprint
            key_fingerprint = int.from_bytes(hashlib.sha1(key.to_bytes(256, 'big')).digest()[-8:], 'big')
            print("Key fingerprint:", key_fingerprint)
            dhc.key_fingerprint = key_fingerprint
            g_b_received_event.set()
            
        elif isinstance(update, updatePhoneCallSignalingData):
            print("Phone call bytes:", update)
            client.invoke(SendPhoneCallSignalingData(
                peer=update.peer,
                data=update.data
            ))
            print("sent")
    
    p, g = await get_p_g(app)
    dhc.p, dhc.g = p, g
    print(p, g)
    dhc.g_a_hash, dhc.g_a_bytes = hash_g_a(int(p), int(g))

    # Request Call
    user_id = os.getenv('USER_ID')
    async with app:
        peer = await app.resolve_peer(user_id)

    await initiate_call(app, peer, dhc.g_a_hash)

    await g_b_received_event.wait()
    print("Confirming call :")
    await confirm_call(app, peer, dhc.g_a_bytes, dhc.key_fingerprint)
    

if __name__ == "__main__":
    import asyncio
    import uvloop
    import os
    dhc_dict = {"p": None, \
        "g": None,\
        "random_length": 256,\
        "version": 0,\
            "g_a": None,\
                "g_b": None,\
                    "g_a_hash": None,\
                        "g_a_bytes": None,\
                        "key_fingerprint": None,\
                            }
    dhc = DHC(dhc_dict)
    g_b_received_event = asyncio.Event()
    username = os.getenv('USERNAME')
    
    uvloop.install()
    app = Client(username)
    app.run(main())

    # asyncio.run(main())
    