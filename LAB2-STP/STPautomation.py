import os
import yaml
from netmiko import ConnectHandler

def load_inventory(filepath="inventorey.yaml"):
    with open(filepath, "r") as f:
        return yaml.safe_load(f)

# Global STP commands for brand-new switches
STP_COMMANDS = [
    "spanning-tree mode rapid-pvst",
    "spanning-tree portfast default",
    "spanning-tree portfast bpduguard default"
]

def main():
    inventory = load_inventory()
    
    for device in inventory:
        if device.get("role") != "switch":
            continue

        hostname = device.get("hostname")
        env_var = device.get("password_env")
        password = os.environ.get(env_var) if env_var else None

        if not password:
            print(f"[SKIP] Password environment variable '{env_var}' not set for {hostname}.")
            continue

        netmiko_device = {
            "device_type": device.get("device_type", "cisco_ios"),
            "host": device.get("host"),
            "username": device.get("username"),
            "password": password,
        }

        print(f"[*] Connecting to {hostname} ({device.get('host')})...")
        try:
            connection = ConnectHandler(**netmiko_device)
            output = connection.send_config_set(STP_COMMANDS)
            print(f"--- Configuration Output: {hostname} ---")
            print(output)
            
            connection.save_config()
            connection.disconnect()
            print(f"[+] STP configured successfully on {hostname}.\n")
        except Exception as e:
            print(f"[-] Connection failed for {hostname}: {e}\n")

if __name__ == "__main__":
    main()