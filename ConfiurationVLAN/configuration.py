import argparse
import os
from pathlib import Path

import yaml
from jinja2 import Template
from netmiko import ConnectHandler


BASE_DIR = Path(__file__).resolve().parent


def load_yaml(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


def render_template(template_file, data):
    with open(BASE_DIR / template_file, 'r', encoding='utf-8') as file:
        template = Template(file.read())
    rendered = template.render(data)
    return [
        line.strip()
        for line in rendered.splitlines()
        if line.strip() and not line.lstrip().startswith('!')
    ]


def build_deployment_plan(inventory):
    plan = []
    for device in inventory['devices']:
        template_by_role = {'switch': 'Switch.j2', 'router': 'Router.j2'}
        template_file = template_by_role.get(device['role'])
        if template_file is None:
            raise ValueError(f"Unsupported role {device['role']!r} for {device['hostname']}")

        password_env = device.get('password_env')
        password = os.environ.get(password_env) if password_env else device.get('password')
        if not password:
            raise ValueError(
                f"Set the {password_env} environment variable for {device['hostname']}"
            )

        plan.append({
            'device': device,
            'commands': render_template(template_file, device),
            'password': password,
        })
    return plan


def run_automation(apply=False):
    inventory = load_yaml(BASE_DIR / 'inventorey.yaml')
    plan = build_deployment_plan(inventory)

    for item in plan:
        device = item['device']
        print(f"\n==========================================")
        print(f"Deploying Configuration to {device['hostname']} ({device['host']})")
        print(f"==========================================")

        print("Generated Commands to push:")
        for cmd in item['commands']:
            print(f"  {cmd}")

    if not apply:
        print("\nPreview only; no device connections were made. Use --apply to deploy.")
        return

    confirmation = input("Type APPLY to send these commands to the listed devices: ")
    if confirmation != 'APPLY':
        print("Deployment cancelled.")
        return

    for item in plan:
        device = item['device']
        connection_params = {
            'device_type': device['device_type'],
            'host': device['host'],
            'username': device['username'],
            'password': item['password'],
        }

        net_connect = None
        try:
            print(f"\n[+] Establishing SSH session to {device['host']}...")
            net_connect = ConnectHandler(**connection_params)
            output = net_connect.send_config_set(item['commands'])
            print("\n--- Command Output ---")
            print(output)

            net_connect.save_config()
            print(f"[✓] Deployment completed for {device['hostname']}")

        except Exception as err:
            print(f"[X] Connection Error on {device['hostname']}: {err}")
        finally:
            if net_connect is not None:
                net_connect.disconnect()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Configure the HR and IT switch VLANs.')
    parser.add_argument(
        '--apply',
        action='store_true',
        help='connect to devices and apply the generated configuration',
    )
    run_automation(apply=parser.parse_args().apply)