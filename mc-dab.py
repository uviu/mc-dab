#!/usr/bin/env python3
from datetime import datetime
import logging
import os
import subprocess
import tarfile

#absolute path configs !change accordingly
CONTAINER_NAME = "your_minecraft_container"
DEFAULT_WORLD_PATH = "/home/luca/Documents/mc-docker-autobackup/minecraft-server/world/"
DEFAULT_BACKUP_DIR = "/home/luca/Documents/mc-docker-autobackup/backups/"
MAX_BACKUPS = 5

logging.basicConfig(
    #use absolute path for cron compatibility
    filename = "/home/luca/minecraft-server/mc-dab/backup_log.log",
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

def backup_world():
    """copies world from container volume to backup dir"""
    #disable autosave beforehand to prevent anomalies
    log_and_print("disabling autosave and forcing worldsave")
    run_minecraft_command("save-off")
    run_minecraft_command("save-all")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"mc_backup_{timestamp}.tar.gz"
    backup_path = os.path.join(DEFAULT_BACKUP_DIR, backup_filename)

    # ensure the backup directory exists
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)

    #compressing the world folder
    log_and_print(f"backing up world to {DEFAULT_BACKUP_DIR} !can take a while depending on world size and read/write speed")
    with tarfile.open(backup_path, "w:gz") as tar:
        tar.add(DEFAULT_WORLD_PATH, arcname="world")

    #reenable autosave between backups
    run_minecraft_command("save-on")
    log_and_print("reenabled autosave")

    cleanup_backups(DEFAULT_BACKUP_DIR)

def cleanup_backups(backup_dir):
    """deletes backups exeeding MAX_BACKUPS"""
    #sort the backups from newest to oldest
    backups = sorted([f for f in os.listdir(DEFAULT_BACKUP_DIR) if f.startswith("mc_backup_")], reverse=True)
    #delete backups with index > MAX_BACKUPS
    if len(backups) > MAX_BACKUPS:
        for old_backup in backups[MAX_BACKUPS:]:
            old_backup_path = os.path.join(DEFAULT_BACKUP_DIR, old_backup)
            log_and_print(f"deleting old backup: {old_backup_path}")
            os.remove(old_backup_path)

if __name__ == "__main__":
    backup_world()
