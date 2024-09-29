import argparse
import json
import os
import sys

JSON_FILE = 'todo.json'
TXT_FILE = 'todo.txt'

VALID_STATUSES = ['DONE', 'PENDING', 'CURRENT']


def initialize_json(file_path):
    if not os.path.exists(file_path):
        initial_data = {status: [] for status in VALID_STATUSES}
        with open(file_path, 'w') as file:
            json.dump(initial_data, file, indent=2)
        print(f"Initialized '{JSON_FILE}' with empty statuses.")
    else:
        with open(file_path, 'r') as file:
            try:
                data = json.load(file)
                updated = False
                for status in VALID_STATUSES:
                    if status not in data:
                        data[status] = []
                        updated = True
                if updated:
                    with open(file_path, 'w') as wf:
                        json.dump(data, wf, indent=2)
                    print(f"Updated '{JSON_FILE}' to include all valid statuses.")
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
    with open(file_path, 'w') as file:
        for status in VALID_STATUSES:
            file.write(f"{status}:\n")
            file.write("  Task                                             | Code Pointer           | Details\n")
            file.write("  ---------------------------------------------------------------------------------------------------------\n")
            for task in data.get(status, []):
                task_name = task.get('Task', '')
                code_pointer = task.get('Code Pointer', '')
                details = task.get('Details', '')
                file.write(f"  - {task_name:<50} | {code_pointer:<22} | {details}\n")
            file.write("\n")


def add_task(data, status, task, code_pointer, details):
    if status not in VALID_STATUSES:
        print(f"Error: Invalid status '{status}'. Valid statuses are: {', '.join(VALID_STATUSES)}.")
        sys.exit(1)
    for s in VALID_STATUSES:
        for t in data[s]:
            if t['Task'].lower() == task.lower():
                print(f"Error: Task '{task}' already exists in status '{s}'.")
                sys.exit(1)
    new_task = {
        'Task': task,
        'Code Pointer': code_pointer,
        'Details': details
    }
    data[status].append(new_task)
    print(f"Added task '{task}' to status '{status}'.")


def delete_task(data, task):
    found = False
    for status in VALID_STATUSES:
        for t in data[status]:
            if t['Task'].lower() == task.lower():
                data[status].remove(t)
                print(f"Deleted task '{task}' from status '{status}'.")
                found = True
                break
        if found:
            break
    if not found:
        print(f"Error: Task '{task}' not found.")
        sys.exit(1)


def move_task(data, task, new_status):
    if new_status not in VALID_STATUSES:
        print(f"Error: Invalid status '{new_status}'. Valid statuses are: {', '.join(VALID_STATUSES)}.")
        sys.exit(1)
    found = False
    for status in VALID_STATUSES:
        for t in data[status]:
            if t['Task'].lower() == task.lower():
                data[status].remove(t)
                data[new_status].append(t)
                print(f"Moved task '{task}' from '{status}' to '{new_status}'.")
                found = True
                break
        if found:
            break
    if not found:
        print(f"Error: Task '{task}' not found.")
        sys.exit(1)


def clear_tasks(data, target):
    target = target.upper()
    if target == 'ALL':
        for status in VALID_STATUSES:
            data[status].clear()
        print("Cleared all tasks from all statuses.")
    elif target in VALID_STATUSES:
        data[target].clear()
        print(f"Cleared all tasks from status '{target}'.")
    else:
        print(f"Error: Invalid target '{target}'. Valid targets are: all, done, pending, current.")
        sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description='Manage TODO List with JSON mediator and TXT output.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Add command
    parser_add = subparsers.add_parser('add', help='Add a new task')
    parser_add.add_argument('status', type=str, help='Status of the task (DONE, PENDING, CURRENT)')
    parser_add.add_argument('task', type=str, help='Name of the task')
    parser_add.add_argument('code_pointer', type=str, help='Code pointer for the task')
    parser_add.add_argument('details', type=str, nargs='?', default='', help='Details about the task')

    # Delete command
    parser_delete = subparsers.add_parser('delete', help='Delete an existing task')
    parser_delete.add_argument('task', type=str, help='Name of the task to delete')

    # Move command
    parser_move = subparsers.add_parser('move', help='Move a task to a different status')
    parser_move.add_argument('task', type=str, help='Name of the task to move')
    parser_move.add_argument('status', type=str, help='New status for the task (DONE, PENDING, CURRENT)')

    # Clear command
    parser_clear = subparsers.add_parser('clear', help='Clear tasks from a status or all')
    parser_clear.add_argument('target', type=str, help='Target to clear (all, done, pending, current)')

    return parser.parse_args()


def main():
    args = parse_args()
    if not args.command:
        print("Error: No command provided. Use -h for help.")
        sys.exit(1)

    initialize_json(JSON_FILE)

    data = read_json(JSON_FILE)

    if args.command == 'add':
        add_task(data, args.status.upper(), args.task, args.code_pointer, args.details)
    elif args.command == 'delete':
        delete_task(data, args.task)
    elif args.command == 'move':
        move_task(data, args.task, args.status.upper())
    elif args.command == 'clear':
        clear_tasks(data, args.target)
    else:
        print(f"Error: Unknown command '{args.command}'.")
        sys.exit(1)

    write_json(JSON_FILE, data)

    write_txt(TXT_FILE, data)

    print(f"TODO list updated successfully. See '{TXT_FILE}' for the formatted list.")


if __name__ == '__main__':
    main()
