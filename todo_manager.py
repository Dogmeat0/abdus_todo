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
DISCORD_MESSAGE_ID = os.getenv('DISCORD_MESSAGE_ID')  # Tasks Message ID
DISCORD_DONE_MESSAGE_ID = os.getenv('DISCORD_DONE_MESSAGE_ID')  # Done Message ID


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
                if "done_tasks" not in data:
                    data["done_tasks"] = []
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


def write_txt(data):
    def truncate(text, max_length):
        return (text[:max_length - 3] + '...') if len(text) > max_length else text

    tasks_content = "TODO LIST - PENDING:\n\n"
    tasks_content += "ID  | Name                                          | Code Pointer          | Status\n"
    tasks_content += "-----------------------------------------------------------------------------------------\n"
    for task in data.get("tasks", []):
        if task['status'] == "":
            task_id = task.get('id', '')
            name = truncate(task.get('name', ''), 45)
            code_pointer = truncate(task.get('code_pointer', ''), 21)
            status = task.get('status', '')
            tasks_content += f"{task_id:<3} | {name:<45} | {code_pointer:<21} | {status}\n"
    tasks_content += "\n"

    done_content = "TODO LIST - DONE:\n\n"
    done_content += "ID  | Name                                          | Code Pointer          | Status\n"
    done_content += "-----------------------------------------------------------------------------------------\n"
    for task in data.get("tasks", []):
        if task['status'] == "✅DONE✅":
            task_id = task.get('id', '')
            name = truncate(task.get('name', ''), 45)
            code_pointer = truncate(task.get('code_pointer', ''), 21)
            status = task.get('status', '')
            done_content += f"{task_id:<3} | {name:<45} | {code_pointer:<21} | {status}\n"
    done_content += "\n"

    # Write to todo.txt
    with open(TXT_FILE, 'w') as file:
        file.write(tasks_content + done_content)

    return {'tasks': tasks_content, 'done': done_content}


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


def edit_task(data, task_id, name, code_pointer):
    for task in data["tasks"]:
        if task['id'] == task_id:
            task['name'] = name
            task['code_pointer'] = code_pointer
            print(f"Edited task ID {task_id}.")
            return
    print(f"Error: Task ID {task_id} not found.")
    sys.exit(1)


def setup_discord(webhook_link):
    global DISCORD_WEBHOOK_URL, DISCORD_MESSAGE_ID, DISCORD_DONE_MESSAGE_ID
    if not webhook_link.startswith("https://discord.com/api/webhooks/"):
        print("Error: Invalid Discord webhook URL.")
        sys.exit(1)
    DISCORD_WEBHOOK_URL = webhook_link

    # Prepare initial contents
    if os.path.exists(TXT_FILE):
        with open(TXT_FILE, 'r') as file:
            content = file.read()
    else:
        content = "No tasks available."

    # Send Tasks Message
    tasks_payload = {
        "content": f"```yaml\n{content.split('TODO LIST - DONE:')[0]}```",
    }

    tasks_response = requests.post(DISCORD_WEBHOOK_URL, json=tasks_payload)
    if tasks_response.status_code == 204:
        print("Successfully sent tasks TODO list to Discord.")
    else:
        print(f"Failed to send tasks message to Discord. Status Code: {tasks_response.status_code}")
        sys.exit(1)

    # Since Discord webhook response does not provide message ID, prompt user
    tasks_message_id = input("Enter the Discord message ID for tasks where the TODO list was sent: ")
    DISCORD_MESSAGE_ID = tasks_message_id

    # Send Done Message
    done_payload = {
        "content": f"```yaml\n{content.split('TODO LIST - DONE:')[1]}```",
    }

    done_response = requests.post(DISCORD_WEBHOOK_URL, json=done_payload)
    if done_response.status_code == 204:
        print("Successfully sent done TODO list to Discord.")
    else:
        print(f"Failed to send done message to Discord. Status Code: {done_response.status_code}")
        sys.exit(1)

    done_message_id = input("Enter the Discord message ID for done tasks where the TODO list was sent: ")
    DISCORD_DONE_MESSAGE_ID = done_message_id

    # Save to .env file
    set_key(Path('.env'), 'DISCORD_WEBHOOK_URL', DISCORD_WEBHOOK_URL)
    set_key(Path('.env'), 'DISCORD_MESSAGE_ID', DISCORD_MESSAGE_ID)
    set_key(Path('.env'), 'DISCORD_DONE_MESSAGE_ID', DISCORD_DONE_MESSAGE_ID)
    print("Discord webhook URL, tasks message ID, and done message ID have been saved to .env.")


def sync_discord(tasks_content, done_content):
    if not DISCORD_WEBHOOK_URL or not DISCORD_MESSAGE_ID or not DISCORD_DONE_MESSAGE_ID:
        print("Error: Discord webhook URL or message IDs not set. Please run the setup command first.")
        sys.exit(1)

    # Update Tasks Message
    tasks_payload = {
        "content": f"```yaml\n{tasks_content}```",
    }

    try:
        parts = DISCORD_WEBHOOK_URL.split('/')
        webhook_id = parts[-2]
        webhook_token = parts[-1]
    except IndexError:
        print("Error: Invalid Discord webhook URL format.")
        sys.exit(1)

    tasks_edit_url = f"https://discord.com/api/webhooks/{webhook_id}/{webhook_token}/messages/{DISCORD_MESSAGE_ID}"

    tasks_response = requests.patch(tasks_edit_url, json=tasks_payload)
    if tasks_response.status_code == 200:
        print("Successfully synced tasks TODO list to Discord.")
    else:
        print(f"Failed to sync tasks message to Discord. Status Code: {tasks_response.status_code}")
        print(f"Response: {tasks_response.text}")
        sys.exit(1)

    # Update Done Message
    done_payload = {
        "content": f"```yaml\n{done_content}```",
    }

    done_edit_url = f"https://discord.com/api/webhooks/{webhook_id}/{webhook_token}/messages/{DISCORD_DONE_MESSAGE_ID}"

    done_response = requests.patch(done_edit_url, json=done_payload)
    if done_response.status_code == 200:
        print("Successfully synced done TODO list to Discord.")
    else:
        print(f"Failed to sync done message to Discord. Status Code: {done_response.status_code}")
        print(f"Response: {done_response.text}")
        sys.exit(1)


def create_done_message(data):
    global DISCORD_MESSAGE_ID, DISCORD_DONE_MESSAGE_ID

    # Prepare done tasks content
    done_content = "TODO LIST - DONE:\n\n"
    done_content += "ID  | Name                                          | Code Pointer          | Status\n"
    done_content += "-----------------------------------------------------------------------------------------\n"
    for task in data.get("tasks", []):
        if task['status'] == "✅DONE✅":
            task_id = task.get('id', '')
            name = task.get('name', '')[:45]
            code_pointer = task.get('code_pointer', '')[:21]
            status = task.get('status', '')
            done_content += f"{task_id:<3} | {name:<45} | {code_pointer:<21} | {status}\n"
    done_content += "\n"

    # Send new done message
    done_payload = {
        "content": f"```yaml\n{done_content}```",
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json=done_payload)
    if response.status_code == 204:
        print("Successfully created a new done TODO list message on Discord.")
    else:
        print(f"Failed to create done message on Discord. Status Code: {response.status_code}")
        sys.exit(1)

    # Prompt user to input the new done message ID
    new_done_message_id = input("Enter the Discord message ID for the new done TODO list message: ")

    # Swap the message IDs
    old_tasks_message_id = DISCORD_MESSAGE_ID
    old_done_message_id = DISCORD_DONE_MESSAGE_ID

    DISCORD_MESSAGE_ID = new_done_message_id
    DISCORD_DONE_MESSAGE_ID = old_tasks_message_id

    # Update .env file
    set_key(Path('.env'), 'DISCORD_MESSAGE_ID', DISCORD_MESSAGE_ID)
    set_key(Path('.env'), 'DISCORD_DONE_MESSAGE_ID', DISCORD_DONE_MESSAGE_ID)
    print("Swapped tasks message ID with done message ID and updated .env accordingly.")


def setup_discord(webhook_link):
    global DISCORD_WEBHOOK_URL, DISCORD_MESSAGE_ID, DISCORD_DONE_MESSAGE_ID
    if not webhook_link.startswith("https://discord.com/api/webhooks/"):
        print("Error: Invalid Discord webhook URL.")
        sys.exit(1)
    DISCORD_WEBHOOK_URL = webhook_link

    # Prepare initial contents
    if os.path.exists(TXT_FILE):
        with open(TXT_FILE, 'r') as file:
            content = file.read()
    else:
        content = "No tasks available."

    # Split the content into tasks and done tasks
    try:
        tasks_content = content.split("TODO LIST - DONE:")[0]
        done_content = content.split("TODO LIST - DONE:")[1]
    except IndexError:
        tasks_content = content
        done_content = "No done tasks available."

    # Send Tasks Message
    tasks_payload = {
        "content": f"```yaml\n{tasks_content}```",
    }

    tasks_response = requests.post(DISCORD_WEBHOOK_URL, json=tasks_payload)
    if tasks_response.status_code == 204:
        print("Successfully sent tasks TODO list to Discord.")
    else:
        print(f"Failed to send tasks message to Discord. Status Code: {tasks_response.status_code}")
        sys.exit(1)

    # Since Discord webhook response does not provide message ID, prompt user
    tasks_message_id = input("Enter the Discord message ID for tasks where the TODO list was sent: ")
    DISCORD_MESSAGE_ID = tasks_message_id

    # Send Done Message
    done_payload = {
        "content": f"```yaml\n{done_content}```",
    }

    done_response = requests.post(DISCORD_WEBHOOK_URL, json=done_payload)
    if done_response.status_code == 204:
        print("Successfully sent done TODO list to Discord.")
    else:
        print(f"Failed to send done message to Discord. Status Code: {done_response.status_code}")
        sys.exit(1)

    done_message_id = input("Enter the Discord message ID for done tasks where the TODO list was sent: ")
    DISCORD_DONE_MESSAGE_ID = done_message_id

    # Save to .env file
    set_key(Path('.env'), 'DISCORD_WEBHOOK_URL', DISCORD_WEBHOOK_URL)
    set_key(Path('.env'), 'DISCORD_MESSAGE_ID', DISCORD_MESSAGE_ID)
    set_key(Path('.env'), 'DISCORD_DONE_MESSAGE_ID', DISCORD_DONE_MESSAGE_ID)
    print("Discord webhook URL, tasks message ID, and done message ID have been saved to .env.")


def sync_discord_with_contents(contents):
    tasks_content = contents['tasks']
    done_content = contents['done']
    sync_discord(tasks_content, done_content)


def create_done_message_command(data):
    create_done_message(data)


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

    # Edit command
    parser_edit = subparsers.add_parser('edit', help='Edit a task')
    parser_edit.add_argument('task_id', type=int, help='ID of the task to edit')
    parser_edit.add_argument('name', type=str, help='New name of the task')
    parser_edit.add_argument('code_pointer', type=str, nargs='?', default='...', help='New code pointer for the task')

    # Create Done Message command
    parser_create_done = subparsers.add_parser('create_done_message', help='Create a new done message to handle overflow')

    # Viewing by ID or listing all
    parser_view = parser.add_argument('view_id', type=int, nargs='?', help='ID of the task to view')

    return parser.parse_args()


def list_tasks(data):
    contents = write_txt(data)
    sync_discord_with_contents(contents)
    print("\nAll TODOs:")
    print("-------------------------")
    if not data["tasks"]:
        print("No tasks available.")
    else:
        for task in data["tasks"]:
            status = task['status'] if task['status'] else "(Pending)"
            print(f"ID: {task['id']} | Name: {task['name']} | Code Pointer: {task['code_pointer']} | Status: {status}")

    


def view_task(data, task_id):
    for task in data["tasks"]:
        if task['id'] == task_id:
            print(f"ID: {task['id']}")
            print(f"Name: {task['name']}")
            print(f"Code Pointer: {task['code_pointer']}")
            print(f"Status: {task['status'] if task['status'] else '(Pending)'}")
            print(f"See '{TXT_FILE}' for the formatted task.")
            return
    print(f"Error: Task ID {task_id} not found.")
    sys.exit(1)


def main():
    args = parse_args()

    # If no command and no view_id, list all tasks
    if args.command is None and args.view_id is None:
        initialize_json(JSON_FILE)
        data = read_json(JSON_FILE)
        list_tasks(data)
        sys.exit(0)
    # If no command but view_id is provided, view specific task
    elif args.command is None and args.view_id is not None:
        initialize_json(JSON_FILE)
        data = read_json(JSON_FILE)
        view_task(data, args.view_id)
        sys.exit(0)

    # Handle commands
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
    elif args.command == 'edit':
        edit_task(data, args.task_id, args.name, args.code_pointer)
    elif args.command == 'create_done_message':
        create_done_message(data)
    elif args.command == 'sync':
        contents = write_txt(data)
        sync_discord_with_contents(contents)
        print("Successfully synced TODO list to Discord.")
        sys.exit(0)
    else:
        print(f"Error: Unknown command '{args.command}'.")
        sys.exit(1)

    write_json(JSON_FILE, data)
    contents = write_txt(data)
    sync_discord_with_contents(contents)
    print(f"TODO list updated successfully. See '{TXT_FILE}' for the formatted list.")


if __name__ == '__main__':
    main()
