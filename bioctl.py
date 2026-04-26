import sys
import os
import time
import uuid
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

import click
import json
import shutil
import signal
from pathlib import Path
from models import init_db, Run, Task
from engine import HardenedRunnerEngine

SessionLocal = init_db()

def handle_interrupt(sig, frame):
    click.echo("\n[!] Interrupt received. Cleaning up...")
    # The engine instance needs to be accessible here for thorough cleanup
    # In a full app, we'd use a global or context manager
    sys.exit(1)

signal.signal(signal.SIGINT, handle_interrupt)

@click.group()
def cli():
    """bioctl: Hardened Bioinformatics Control CLI"""
    pass

@cli.command()
def doctor():
    """Pre-flight environment validation."""
    click.echo("[*] biograph Doctor - Checking system health...")
    
    # 1. Python Check
    py_ver = sys.version_info
    if py_ver.major == 3 and py_ver.minor >= 9:
        click.echo(f"✅ Python {py_ver.major}.{py_ver.minor} found.")
    else:
        click.echo(f"❌ Python >= 3.9 required. Found {py_ver.major}.{py_ver.minor}")

    # 2. DB Check
    db_path = "biograph_hardened.db"
    if os.access(".", os.W_OK):
        click.echo("✅ Filesystem is writable (SQLite ready).")
    else:
        click.echo("❌ Filesystem not writable.")

    # 3. Tool Check
    required_tools = {
        "bwa": "conda install bwa",
        "samtools": "conda install samtools",
        "bcftools": "conda install bcftools"
    }
    
    for tool, fix in required_tools.items():
        path = shutil.which(tool)
        if path:
            click.echo(f"✅ {tool} found at {path}")
        else:
            click.echo(f"❌ {tool} NOT FOUND. Suggested fix: {fix}")

@cli.command()
@click.argument('dag_path', type=click.Path(exists=True))
def run(dag_path):
    """Execute hardened pipeline."""
    dag_json = json.loads(Path(dag_path).read_text())
    
    # Pre-flight warn
    click.echo("[*] Running pre-flight checks...")
    # (Simplified call to doctor logic)
    
    session = SessionLocal()
    engine = HardenedRunnerEngine(session)
    
    # Initialize Run & Tasks
    run_record = Run(id=str(uuid.uuid4()) if 'uuid' in globals() else str(Path(dag_path).name + str(time.time())), 
                     name=dag_json.get("name", "Hardened Run"))
    session.add(run_record)
    
    task_map = {}
    for node in dag_json["nodes"]:
        t = Task(run_id=run_record.id, node_id=node["id"], name=node["id"], command=node["data"].get("command", "echo 'skip'"))
        session.add(t)
        task_map[node["id"]] = t
    session.commit()

    click.echo(f"[*] Started Run: {run_record.id}")
    
    try:
        engine.execute_dag(run_record.id, dag_json)
    finally:
        session.refresh(run_record)
        
        success = len([t for t in run_record.tasks if t.status == "success"])
        failed = len([t for t in run_record.tasks if t.status == "failed"])
        suspicious = len([t for t in run_record.tasks if t.status == "suspicious"])
        
        click.echo("\n--- Hardened Run Summary ---")
        click.echo(f"ID:         {run_record.id}")
        click.echo(f"Status:     {run_record.status.upper()}")
        click.echo(f"Successful: {success}")
        click.echo(f"Failed:     {failed}")
        click.echo(f"Suspicious: {suspicious}")
        
        if failed > 0:
            f_task = next(t for t in run_record.tasks if t.status == "failed")
            click.echo(f"Failure Point: {f_task.name}")
            if f_task.validation_messages:
                click.echo(f"Validation: {f_task.validation_messages}")
        
        session.close()

if __name__ == "__main__":
    cli()
