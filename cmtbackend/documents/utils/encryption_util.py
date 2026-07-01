# from cryptography.fernet import Fernet
# from decouple import config
# import base64
# import os
# from cryptography.hazmat.primitives import hashes
# from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
# salt = os.urandom(16)
# kdf = PBKDF2HMAC(
#     algorithm=hashes.SHA256(),
#     length=32,
#     salt=salt,
#     iterations=390000,
# )

# key = config('ENCRYPTION_KEY')

# cipher_suite = Fernet(key)

# def encrypt_text(plain_text):
#     if plain_text is not None:
#         encrypted_text = cipher_suite.encrypt(plain_text.encode('utf-8'))
#         return encrypted_text.decode('utf-8')
#     return None

# def decrypt_text(encrypted_text):
#     if encrypted_text is not None:
#         try:
#             decrypted_text = cipher_suite.decrypt(encrypted_text.encode('utf-8'))
#             return decrypted_text.decode('utf-8')
#         except Exception as e:
#             return encrypted_text
#     return None


from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import hashlib
import os
import base64
from decouple import config

salt = os.urandom(16)
passphrase = config('ENCRYPTION_KEY').encode('utf-8')

# Function to derive a key using SHA-512
def derive_key(passphrase, salt):
    return hashlib.pbkdf2_hmac('sha512', passphrase, salt, 10000, dklen=32)

key = derive_key(passphrase, salt)

# Function to encrypt data
def encrypt_text(plaintext):
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(plaintext.encode()) + padder.finalize()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(salt + iv + ciphertext).decode('utf-8')

# Function to decrypt data
def decrypt_text(b64_ciphertext):
    try:
        ciphertext = base64.b64decode(b64_ciphertext)
        salt = ciphertext[:16]
        iv = ciphertext[16:32]
        actual_ciphertext = ciphertext[32:]
        
        # Derive the key from the passphrase using SHA-512
        key = derive_key(passphrase, salt)
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        padded_plaintext = decryptor.update(actual_ciphertext) + decryptor.finalize()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        return plaintext.decode()
    except:
        return b64_ciphertext

# Function to check if the text is already decrypted
def is_decrypted(text):
    # First check if the text is valid base64
    try:
        decoded = base64.b64decode(text)
        # Check if the decoded data has the expected structure (salt + iv + ciphertext)
        if len(decoded) < 48:  # 16 (salt) + 16 (iv) + at least 16 (ciphertext)
            return True
    except:
        return True
    
    # If it looks like encrypted data, try to decrypt it
    try:
        decrypt_text(text)
        return False  # If decryption succeeds, it was encrypted
    except Exception as e:
        print("e", e)
        return True  # If decryption fails, it was already decrypted
