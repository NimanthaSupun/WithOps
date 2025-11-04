import time
import jwt

current_time = int(time.time())
iat_time = current_time - 60
exp_time = current_time + 300

payload = {
    'iat': iat_time,
    'exp': exp_time,
    'iss': '1510017'
}

print(f"Current Unix Time: {current_time}")
print(f"IAT (Issued At): {iat_time}")
print(f"EXP (Expiration): {exp_time}")
print(f"Token Lifetime: {exp_time - iat_time} seconds ({(exp_time - iat_time) / 60} minutes)")
print(f"\nPayload: {payload}")

token = jwt.encode(payload, "test-key", algorithm="HS256")
print(f"\nToken: {token}")

decoded = jwt.decode(token, options={"verify_signature": False})
print(f"\nDecoded: {decoded}")
