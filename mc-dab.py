import argparse
from datetime import datetime
import logging
import os
import subprocess
import tarfile
import threading
import time 

#path configs
CONTAINER_NAME = "your_minecraft_container"
DEFAULT_WORLD_PATH = "/path/to/your/world"
DEFAULT_BACKUP_DIR = "/path/to/backup/folder"
MAX_BACKUPS = 5
BACKUP_INTERVAL_MINUTES = 60
LAST_BACKUP_TIMESTAMP = None

logging.basicConfig(
    filename = "backup_log.txt",
    level = logging.INFO,
    format = "%(asctime)s - %(levelname)s - %(message)s"
)

def log_and_print(message):
    """logs and prints a message"""
    logging.info(message)
    print(message)

def run_minecraft_command(command):
    """executes a command inside the minecraft server"""
    docker_cmd = f"docker exec {CONTAINER_NAME} rcon-cli {command}"
    subprocess.run(docker_cmd, shell=True)

def backup_world(world_path, backup_dir, manual=False):
    """copies world from container volume to backup dir"""
    #disable autosave beforehand to prevent anomalies
    log_and_print("disabling autosave and forcing worldsave")
    run_minecraft_command("save-off")
    run_minecraft_command("save-all")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    #if backup was triggered manually file gets a tag
    tag = "_manual" if manual else ""
    backup_filename = f"mc_backup_{timestamp}{tag}.tar.gz"
    backup_path = os.path.join(backup_dir, backup_filename)

    #compressing the world folder
    log_and_print(f"backing up world to {backup_path}")
    with tarfile.open(backup_path, "w:gz") as tar:
        tar.add(world_path, arcname="world")

    #reenable autosave between backups
    run_minecraft_command("save-on")
    log_and_print("reenabled autosave")

    LAST_BACKUP_TIMESTAMP = time.time()

    cleanup_backups(backup_dir)

def cleanup_backups(backup_dir):
    """deletes backups exeeding MAX_BACKUPS"""
    #sort the backups from newest to oldest
    backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("mc_backup_")], reverse=True)
    #delete backups with index > MAX_BACKUPS
    if len(backups) > MAX_BACKUPS:
        for old_backup in backups[MAX_BACKUPS:]:
            old_backup_path = os.path.join(backup_dir, old_backup)
            log_and_print(f"deleting old backup: {old_backup_path}")
            os.remove(old_backup_path)

def show_status():
    """shows the remaining time till the next backup"""
    log_and_print("status: periodical backup scheduled")
    if LAST_BACKUP_TIMESTAMP is None:
        log_and_print("no backup has been completed yet.")
    else:
        next_backup_time = LAST_BACKUP_TIMESTAMP + BACKUP_INTERVAL_MINUTES * 60
        time_left = next_backup_time - time.time()
        if time_left < 0:
            log_and_print("a backup is overdue!")
        else:
            log_and_print(f"next backup in {time_left / 60:.0f} minutes")

def schedule_backups(world_path, backup_dir):
    """waits for next backup timeslot and triggers backup"""
    log_and_print(f"Backup scheduled every {BACKUP_INTERVAL_MINUTES} minutes.")
    while True:
        time.sleep(BACKUP_INTERVAL_MINUTES * 60)  # wait for the next backup time
        backup_world(world_path, backup_dir)  # trigger the backup

def background_backup_thread(world_path, backup_dir):
    """Runs the backup scheduler in a background thread."""
    backup_thread = threading.Thread(target=schedule_backups, args=(world_path, backup_dir))
    backup_thread.daemon = True  # ensures thread stops when the main program exits
    backup_thread.start()

def main():
    parser = argparse.ArgumentParser(description="automatic world backup for minecraft docker container")
    parser.add_argument("--world-path", type=str, default=DEFAULT_WORLD_PATH, help="path to the minecraft world folder")
    parser.add_argument("--backup-dir", type=str, default=DEFAULT_BACKUP_DIR, help="path to store backups")
    parser.add_argument("--manual", action="store_true", help="trigger an out of schedule backup manually")
    parser.add_argument("--logs", action="store_true", help="show the last 10 log entries")
    parser.add_argument("--status", action="store_true", help="show information about upcoming backups")
    parser.add_argument("--run", action="store_true", help="start the autoamtic backup process")

    args = parser.parse_args()

    #create dir for backups if necessary
    os.makedirs(args.backup_dir, exist_ok=True)

    if args.manual:
        backup_world(args.world_path, args.backup_dir, manual=True)
    elif args.logs:
        with open("backup_log.txt", "r") as log_file:
            #show the last ten log entries
            logs = log_file.readlines()[-10:]  
            print("".join(logs))
    elif args.status:
        show_status()
    elif args.run:
        # start seperate thread to schedule backups
        background_backup_thread(args.world_path, args.backup_dir)
        # main program running continously to wait for new commands
        while True:
            time.sleep(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

