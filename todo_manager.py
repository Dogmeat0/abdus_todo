import argparse
import json
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv, set_key

load_dotenv()

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
ASSETS_DIR = os.path.join(CURRENT_DIR, "assets")
JSON_FILE = os.path.join(ASSETS_DIR, "todo.json")
TXT_FILE = os.path.join(ASSETS_DIR, "todo.txt")

Path(ASSETS_DIR).mkdir(parents=True, exist_ok=True)

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
DISCORD_MESSAGE_ID = os.getenv('DISCORD_MESSAGE_ID')


def initialize_json(file_path):
    if not os.path.exists(file_path):
        initial_data = {"tasks": [], "last_id": 0}
        with open(file_path, 'w') as file:
            json.dump(initial_data, file, indent=2)
        print(f"Initialized '{JSON_FILE}' with an empty task list.")
    else:
        with open(file_path, 'r') as file:
            try:
                data = json.load(file)
                updated = False
                if "tasks" not in data:
                    data["tasks"] = []
                    updated = True
                if "last_id" not in data:
                    data["last_id"] = 0
                    updated = True
                if updated:
                    with open(file_path, 'w') as wf:
                        json.dump(data, wf, indent=2)
                    print(f"Updated '{JSON_FILE}' to include necessary fields.")
            except json.JSONDecodeError as exc:
                print(f"Error reading JSON file: {exc}")
                sys.exit(1)


def read_json(file_path):
    with open(file_path, 'r') as file:
        try:
            data = json.load(file)
            return data
        except json.JSONDecodeError as exc:
            print(f"Error reading JSON file: {exc}")
            sys.exit(1)


def write_json(file_path, data):
    with open(file_path, 'w') as file:
        try:
            json.dump(data, file, indent=2)
        except TypeError as exc:
            print(f"Error writing JSON file: {exc}")
            sys.exit(1)


def write_txt(file_path, data):
    def truncate(text, max_length):
        return (text[:max_length - 3] + '...') if len(text) > max_length else text

    with open(file_path, 'w') as file:
        file.write("TODO LIST:\n\n")
        file.write("ID  | Name                                          | Code Pointer          | Status\n")
        file.write("-----------------------------------------------------------------------------------------\n")
        for task in data.get("tasks", []):
            task_id = task.get('id', '')
            name = truncate(task.get('name', ''), 45)
            code_pointer = truncate(task.get('code_pointer', ''), 21)
            status = task.get('status', '')
            file.write(f"{task_id:<3} | {name:<45} | {code_pointer:<21} | {status}\n")
        file.write("\n")


def add_task(data, name, code_pointer="..."):
    data["last_id"] += 1
    new_task = {
        'id': data["last_id"],
        'name': name,
        'code_pointer': code_pointer,
        'status': ""
    }
    data["tasks"].append(new_task)
    print(f"Added task '{name}' with ID {data['last_id']}.")


def tick_task(data, task_id):
    for task in data["tasks"]:
        if task['id'] == task_id:
            if task['status'] == "✅DONE✅":
                print(f"Task ID {task_id} is already marked as DONE.")
                return
            task['status'] = "✅DONE✅"
            print(f"Ticked task ID {task_id} as DONE.")
            return
    print(f"Error: Task ID {task_id} not found.")
    sys.exit(1)


def untick_task(data, task_id):
    for task in data["tasks"]:
        if task['id'] == task_id:
            if task['status'] == "":
                print(f"Task ID {task_id} is already unticked.")
                return
            task['status'] = ""
            print(f"Unticked task ID {task_id}.")
            return
    print(f"Error: Task ID {task_id} not found.")
    sys.exit(1)


def delete_task(data, task_id):
    for task in data["tasks"]:
        if task['id'] == task_id:
            data["tasks"].remove(task)
            print(f"Deleted task ID {task_id}.")
            return
    print(f"Error: Task ID {task_id} not found.")
    sys.exit(1)


def setup_discord(webhook_link):
    global DISCORD_WEBHOOK_URL, DISCORD_MESSAGE_ID
    if not webhook_link.startswith("https://discord.com/api/webhooks/"):
        print("Error: Invalid Discord webhook URL.")
        sys.exit(1)
    DISCORD_WEBHOOK_URL = webhook_link

    if os.path.exists(TXT_FILE):
        with open(TXT_FILE, 'r') as file:
            content = file.read()
    else:
        content = "No tasks available."

    data = {
        "content": f"```yaml\n{content}\n```",
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if response.status_code == 204:
        print("Successfully sent initial TODO list to Discord.")
    else:
        print(f"Failed to send message to Discord. Status Code: {response.status_code}")
        sys.exit(1)

    message_id = input("Enter the Discord message ID where the TODO list was sent: ")
    DISCORD_MESSAGE_ID = message_id

    set_key(Path('.env'), 'DISCORD_WEBHOOK_URL', DISCORD_WEBHOOK_URL)
    set_key(Path('.env'), 'DISCORD_MESSAGE_ID', DISCORD_MESSAGE_ID)
    print("Discord webhook URL and message ID have been saved to .env.")


def sync_discord():
    if not DISCORD_WEBHOOK_URL or not DISCORD_MESSAGE_ID:
        print("Error: Discord webhook URL or message ID not set. Please run the setup command first.")
        sys.exit(1)

    if os.path.exists(TXT_FILE):
        with open(TXT_FILE, 'r') as file:
            content = file.read()
    else:
        content = "No tasks available."

    payload = {
        "content": f"```yaml\n{content}\n```",
    }

    try:
        parts = DISCORD_WEBHOOK_URL.split('/')
        webhook_id = parts[-2]
        webhook_token = parts[-1]
    except IndexError:
        print("Error: Invalid Discord webhook URL format.")
        sys.exit(1)

    edit_url = f"https://discord.com/api/webhooks/{webhook_id}/{webhook_token}/messages/{DISCORD_MESSAGE_ID}"

    response = requests.patch(edit_url, json=payload)
    if response.status_code == 200:
        print("Successfully synced TODO list to Discord.")
    else:
        print(f"Failed to sync message to Discord. Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description='Manage TODO List with JSON mediator and TXT output.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Setup command
    parser_setup = subparsers.add_parser('setup', help='Setup Discord webhook')
    parser_setup.add_argument('webhook_url', type=str, help='Discord webhook URL for sending TODO list')

    # Sync command
    parser_sync = subparsers.add_parser('sync', help='Sync the TODO list to Discord')

    # Add command
    parser_add = subparsers.add_parser('add', help='Add a new task')
    parser_add.add_argument('name', type=str, help='Name of the task')
    parser_add.add_argument('code_pointer', type=str, nargs='?', default='...', help='Code pointer for the task')

    # Tick command
    parser_tick = subparsers.add_parser('tick', help='Mark a task as DONE')
    parser_tick.add_argument('task_id', type=int, help='ID of the task to tick')

    # Untick command
    parser_untick = subparsers.add_parser('untick', help='Mark a task as not DONE')
    parser_untick.add_argument('task_id', type=int, help='ID of the task to untick')

    # Delete command
    parser_delete = subparsers.add_parser('del', help='Delete a task')
    parser_delete.add_argument('task_id', type=int, help='ID of the task to delete')

    # Positional argument for viewing tasks
    parser.add_argument('id', type=int, nargs='?', help='ID of the task to view')

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == 'setup':
        setup_discord(args.webhook_url)
        sys.exit(0)

    initialize_json(JSON_FILE)
    data = read_json(JSON_FILE)

    if args.command == 'add':
        add_task(data, args.name, args.code_pointer)
    elif args.command == 'tick':
        tick_task(data, args.task_id)
    elif args.command == 'untick':
        untick_task(data, args.task_id)
    elif args.command == 'del':
        delete_task(data, args.task_id)
    elif args.command == 'sync':
        sync_discord()
        sys.exit(0)
    elif args.id is not None:
        # View a specific task by ID
        task_found = False
        for task in data["tasks"]:
            if task['id'] == args.id:
                print(f"ID: {task['id']}")
                print(f"Name: {task['name']}")
                print(f"Code Pointer: {task['code_pointer']}")
                print(f"Status: {task['status']}")
                task_found = True
                break
        if not task_found:
            print(f"Error: Task ID {args.id} not found.")
            sys.exit(1)
        sys.exit(0)
    else:
        # No command and no ID: list all tasks
        write_txt(TXT_FILE, data)
        print("\nAll TODOs:")
        print("-------------------------")
        if not data["tasks"]:
            print("No tasks available.")
        else:
            for task in data["tasks"]:
                status = task['status'] if task['status'] else "(Pending)"
                print(f"ID: {task['id']} | Name: {task['name']} | Code Pointer: {task['code_pointer']} | Status: {status}")
        # Sync after listing all tasks
        sync_discord()
        sys.exit(0)

    write_json(JSON_FILE, data)
    write_txt(TXT_FILE, data)
    sync_discord()
    print(f"TODO list updated successfully. See '{TXT_FILE}' for the formatted list.")


if __name__ == '__main__':
    main()
