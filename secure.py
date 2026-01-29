import os
import base64
import zlib
import marshal
import codecs
from random import randint
from colorama import init, Fore, Style

init()  # Initialize colorama

def print_banner():
    banner = f"""
{Fore.CYAN}╭──────────────────────────────────────╮
│  {Fore.YELLOW}🔒 Python Code Encryptor/Decryptor {Fore.CYAN} │
│     {Fore.GREEN}Created by @GodxBots{Fore.CYAN}           │
╰──────────────────────────────────────╯{Style.RESET_ALL}
"""
    print(banner)

def get_file_path():
    while True:
        path = input(f"{Fore.YELLOW}📁 Enter Python file path: {Style.RESET_ALL}").strip()
        if os.path.exists(path) and path.endswith('.py'):
            return path
        print(f"{Fore.RED}❌ Invalid file path! Please enter a valid .py file{Style.RESET_ALL}")

def get_operation():
    while True:
        print(f"\n{Fore.CYAN}Choose operation:")
        print(f"{Fore.GREEN}1. 🔒 Encrypt")
        print(f"{Fore.BLUE}2. 🔓 Decrypt{Style.RESET_ALL}")
        choice = input(f"\n{Fore.YELLOW}Enter choice (1/2): {Style.RESET_ALL}").strip()
        if choice in ['1', '2']:
            return choice
        print(f"{Fore.RED}❌ Invalid choice! Please enter 1 or 2{Style.RESET_ALL}")

def encrypt_code(source_code):
    try:
        # Simple but effective encryption
        encoded = base64.b85encode(zlib.compress(source_code.encode())).decode()
        
        encrypted_code = f'''
# Encrypted by @GodxBots
import base64
import zlib
import codecs

def decrypt(encrypted_data):
    return zlib.decompress(base64.b85decode(encrypted_data)).decode()

exec(decrypt("{encoded}"))
'''
        return encrypted_code
    except:
        return None

def decrypt_code(encrypted_code):
    try:
        # Find the encrypted data
        start = encrypted_code.find('exec(decrypt("') + 13
        end = encrypted_code.find('"))', start)
        encrypted_data = encrypted_code[start:end]
        
        # Decrypt
        decrypted = zlib.decompress(base64.b85decode(encrypted_data)).decode()
        return decrypted
    except:
        return None

def main():
    print_banner()
    
    # Get file path
    file_path = get_file_path()
    
    # Get operation
    operation = get_operation()
    
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if operation == '1':  # Encrypt
            # Generate output filename
            base_name = os.path.splitext(file_path)[0]
            output_file = f"{base_name}-enc.py"
            
            # Encrypt
            print(f"\n{Fore.YELLOW}🔄 Encrypting...{Style.RESET_ALL}")
            encrypted = encrypt_code(content)
            
            if encrypted:
                # Save encrypted file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(encrypted)
                print(f"\n{Fore.GREEN}✅ Encryption successful!")
                print(f"📁 Encrypted file saved as: {output_file}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}❌ Encryption failed!{Style.RESET_ALL}")
                
        else:  # Decrypt
            # Generate output filename
            base_name = os.path.splitext(file_path)[0]
            output_file = f"{base_name}-dec.py"
            
            # Decrypt
            print(f"\n{Fore.YELLOW}🔄 Decrypting...{Style.RESET_ALL}")
            decrypted = decrypt_code(content)
            
            if decrypted:
                # Save decrypted file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(decrypted)
                print(f"\n{Fore.GREEN}✅ Decryption successful!")
                print(f"📁 Decrypted file saved as: {output_file}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}❌ Decryption failed!{Style.RESET_ALL}")
                
    except Exception as e:
        print(f"\n{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}")
    
    input(f"\n{Fore.CYAN}Press Enter to exit...{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
