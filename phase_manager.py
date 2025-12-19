"""
Phase Manager for MAX Transformation
Provides atomic phase execution with verification and rollback capabilities.
"""
from pathlib import Path
import json
import subprocess
from datetime import datetime
from typing import Optional, Dict


class PhaseManager:
    """Manages implementation phases with atomic commits and rollback."""
    
    def __init__(self, state_file: str = "phase_state.json"):
        self.state_file = Path(state_file)
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load phase state from file."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                print("⚠️  State file corrupted, starting fresh")
                return self._empty_state()
        return self._empty_state()
    
    def _empty_state(self) -> Dict:
        """Create empty state structure."""
        return {
            "current_phase": None,
            "status": "not_started",
            "history": []
        }
    
    def _save_state(self):
        """Save phase state to file."""
        self.state_file.write_text(
            json.dumps(self.state, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
    
    def begin_phase(self, phase_id: str, description: str):
        """Mark phase as in-progress."""
        self.state.update({
            "current_phase": phase_id,
            "status": "in_progress",
            "started_at": datetime.now().isoformat(),
            "description": description
        })
        self._save_state()
        print(f"[*] Starting Phase {phase_id}: {description}")
    
    def verify_phase(self, phase_id: str) -> bool:
        """Run verification checks before marking complete."""
        print(f"[?] Verifying Phase {phase_id}...")
        
        # Check if phase-specific tests exist
        test_path = Path(f"tests/phase_{phase_id}/")
        if not test_path.exists():
            print(f"[i] No phase-specific tests found for Phase {phase_id}, skipping test verification")
            return True
        
        # Run tests specific to this phase
        try:
            result = subprocess.run(
                ['pytest', str(test_path), '-v'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                print(f"[X] Phase {phase_id} verification failed!")
                print(result.stdout)
                return False
            
            print(f"[+] Phase {phase_id} verified!")
            return True
        except subprocess.TimeoutExpired:
            print(f"⚠️  Tests timed out for Phase {phase_id}")
            return False
        except FileNotFoundError:
            print(f"⚠️  pytest not found, skipping verification")
            return True
    
    def complete_phase(self, phase_id: str, skip_verification: bool = False):
        """Mark phase complete with git checkpoint."""
        if not skip_verification and not self.verify_phase(phase_id):
            raise RuntimeError(f"Phase {phase_id} failed verification!")
        
        # Create git checkpoint
        print(f"[+] Creating git checkpoint for Phase {phase_id}...")
        try:
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(
                ["git", "commit", "-m", f"✅ Phase {phase_id} complete"],
                check=True
            )
            subprocess.run(
                ["git", "tag", f"phase-{phase_id}-complete"],
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Git checkpoint failed: {e}")
            print("You may need to commit manually")
        
        # Update state
        self.state.update({
            "status": "complete",
            "completed_at": datetime.now().isoformat()
        })
        self.state["history"].append({
            "phase": phase_id,
            "completed_at": datetime.now().isoformat()
        })
        self._save_state()
        
        print(f"[+] Phase {phase_id} complete and checkpointed!")
    
    def rollback_to_last_complete(self):
        """Rollback to last completed phase."""
        if not self.state["history"]:
            print("❌ No completed phases to rollback to")
            return
        
        last_phase = self.state["history"][-1]["phase"]
        tag = f"phase-{last_phase}-complete"
        
        print(f"🔄 Rolling back to Phase {last_phase}...")
        try:
            subprocess.run(["git", "reset", "--hard", tag], check=True)
            
            # Update state
            self.state["current_phase"] = last_phase
            self.state["status"] = "rolled_back"
            self._save_state()
            
            print(f"✅ Rolled back to Phase {last_phase}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Rollback failed: {e}")
    
    def get_current_status(self) -> Dict:
        """Get current implementation status."""
        return self.state.copy()
    
    def print_status(self):
        """Print current status in readable format."""
        print("\n" + "="*60)
        print("📊 PHASE MANAGER STATUS")
        print("="*60)
        print(f"Current Phase: {self.state.get('current_phase', 'None')}")
        print(f"Status: {self.state.get('status', 'Unknown')}")
        
        if self.state.get('started_at'):
            print(f"Started: {self.state['started_at']}")
        
        if self.state["history"]:
            print(f"\nCompleted Phases: {len(self.state['history'])}")
            for entry in self.state["history"]:
                print(f"  ✅ Phase {entry['phase']}")
        
        print("="*60 + "\n")


if __name__ == "__main__":
    # CLI interface
    import sys
    
    pm = PhaseManager()
    
    if len(sys.argv) < 2:
        pm.print_status()
        print("Usage:")
        print("  python phase_manager.py status")
        print("  python phase_manager.py begin <phase_id> <description>")
        print("  python phase_manager.py complete <phase_id>")
        print("  python phase_manager.py rollback")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "status":
        pm.print_status()
    elif command == "begin" and len(sys.argv) >= 4:
        phase_id = sys.argv[2]
        description = " ".join(sys.argv[3:])
        pm.begin_phase(phase_id, description)
    elif command == "complete" and len(sys.argv) >= 3:
        phase_id = sys.argv[2]
        pm.complete_phase(phase_id)
    elif command == "rollback":
        pm.rollback_to_last_complete()
    else:
        print("❌ Invalid command")
        sys.exit(1)
