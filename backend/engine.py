import subprocess
import time
import os
import signal
import psutil
from datetime import datetime
from collections import deque
from sqlalchemy.orm import Session
from models import Run, Task, QualityMetric
from validators import validator_registry

class HardenedRunnerEngine:
    def __init__(self, session: Session):
        self.session = session
        self.active_processes = []

    def execute_dag(self, run_id: str, dag_json: dict):
        run = self.session.query(Run).filter_by(id=run_id).first()
        tasks = {t.node_id: t for t in run.tasks}
        
        # Dependency Mapping
        in_degree = {n["id"]: 0 for n in dag_json["nodes"]}
        adj = {n["id"]: [] for n in dag_json["nodes"]}
        for edge in dag_json["edges"]:
            adj[edge["source"]].append(edge["target"])
            in_degree[edge["target"]] += 1
        
        queue = deque([n_id for n_id, deg in in_degree.items() if deg == 0])
        
        try:
            while queue:
                node_id = queue.popleft()
                task = tasks[node_id]
                
                # Execute with supervision
                self._run_task_supervised(task, dag_json["node_map"][node_id])
                
                if task.status == "failed":
                    run.status = "failed"
                    self.session.commit()
                    return

                for neighbor in adj[node_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            
            run.status = "success"
            run.end_time = datetime.utcnow()
            self.session.commit()

        finally:
            self.cleanup_processes()

    def _run_task_supervised(self, task: Task, node_meta: dict):
        task.status = "running"
        task.start_time = datetime.utcnow()
        self.session.commit()

        start_perf = time.time()
        
        try:
            # Start process in a new session for group supervision
            proc = subprocess.Popen(
                task.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True
            )
            self.active_processes.append(proc)
            
            stdout, stderr = proc.communicate()
            self.active_processes.remove(proc)
            
            task.stdout = stdout
            task.stderr = stderr
            task.exit_code = proc.returncode
            
            # Initial Status
            if proc.returncode != 0:
                task.status = "failed"
            else:
                # SCIENTIFIC VALIDATION
                output_type = node_meta.get("output_type", "DEFAULT")
                output_path = node_meta.get("output_path") # Assumes command generates this
                
                if output_path:
                    validator = validator_registry.get(output_type)
                    res = validator.validate(output_path)
                    
                    task.validation_status = res.status
                    task.validation_messages = res.messages
                    
                    # Store metrics
                    for m_name, m_val in res.metrics.items():
                        metric = QualityMetric(task_id=task.id, name=m_name, value=m_val)
                        self.session.add(metric)
                    
                    # Override status if validation is suspicious/failed
                    if res.status == "failed":
                        task.status = "failed"
                    elif res.status == "suspicious":
                        task.status = "suspicious"
                    else:
                        task.status = "success"
                else:
                    task.status = "success"
            
        except Exception as e:
            task.status = "failed"
            task.stderr = str(e)
        
        task.end_time = datetime.utcnow()
        task.duration = time.time() - start_perf
        self.session.commit()

    def cleanup_processes(self):
        """Kills all active process groups to prevent zombies."""
        for proc in self.active_processes:
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGTERM)
                time.sleep(1)
                if proc.poll() is None:
                    os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception as e:
                print(f"Cleanup error: {e}")
        self.active_processes = []
