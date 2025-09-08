import secrets


# Generate a 32-byte (256-bit) secret
secret_bytes = secrets.token_bytes(32)

# Encode to hexadecimal
secret_key_hex = secret_bytes.hex()
print(f"Hexadecimal Secret Key: {secret_key_hex}")

