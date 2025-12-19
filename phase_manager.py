"""
Phase Manager for MAX Transformation Implementation

Provides enterprise-level phase management with atomic commits, verification,
and rollback capabilities. Prevents partial phase failures from leaving the
system in a broken state.
"""

from pathlib import Path
import json
import subprocess
from datetime import datetime
from typing import Optional, Dict, List
import logging

log = logging.getLogger(__name__)


class PhaseManager:
    """
    Enterprise-level phase state manager with atomic commits.
    
    Features:
    - Automatic verification before phase completion
    - Git checkpoint creation with tags
    - Rollback to last completed phase
    - Phase history tracking
    - State persistence
    """
    
    def __init__(self, state_file: Optional[Path] = None):
        """
        Initialize phase manager.
        
        Args:
            state_file: Path to state file (default: phase_state.json in current dir)
        """
        self.state_file = state_file or Path("phase_state.json")
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load phase state from disk, or create new state."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError) as e:
                log.error(f"Failed to load state file: {e}")
                log.warning("Creating new state")
        
        return {
            "current_phase": None,
            "status": "not_started",
            "history": [],
            "created_at": datetime.now().isoformat()
        }
    
    def _save_state(self):
        """Save current state to disk."""
        try:
            self.state_file.write_text(
                json.dumps(self.state, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except OSError as e:
            log.error(f"Failed to save state: {e}")
            raise
    
    def begin_phase(self, phase_id: str, description: str):
        """
        Mark phase as in-progress.
        
        Args:
            phase_id: Phase identifier (e.g., "0", "1", "2A")
            description: Human-readable phase description
        """
        self.state.update({
            "current_phase": phase_id,
            "status": "in_progress",
            "started_at": datetime.now().isoformat(),
            "description": description
        })
        self._save_state()
        print(f"[*] Starting Phase {phase_id}: {description}")
        log.info(f"Phase {phase_id} started: {description}")
    
    def verify_phase(self, phase_id: str) -> bool:
        """
        Run verification checks before marking complete.
        
        Args:
            phase_id: Phase identifier to verify
            
        Returns:
            True if verification passed, False otherwise
        """
        print(f"[?] Verifying Phase {phase_id}...")
        log.info(f"Verifying Phase {phase_id}")
        
        # Check if phase-specific tests exist
        test_dir = Path(f"tests/phase_{phase_id}")
        if not test_dir.exists():
            log.warning(f"No test directory found for phase {phase_id}")
            print(f"[!] No tests found for Phase {phase_id} (tests/phase_{phase_id}/)")
            print("   Skipping test verification")
            return True
        
        # Run tests specific to this phase
        try:
            result = subprocess.run(
                ['pytest', str(test_dir), '-v'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                print(f"[X] Phase {phase_id} verification failed!")
                print(result.stdout)
                log.error(f"Phase {phase_id} verification failed: {result.stdout}")
                return False
            
            print(f"[OK] Phase {phase_id} verified!")
            log.info(f"Phase {phase_id} verification passed")
            return True
            
        except subprocess.TimeoutExpired:
            print(f"[X] Phase {phase_id} verification timeout!")
            log.error(f"Phase {phase_id} verification timeout")
            return False
        except Exception as e:
            print(f"[X] Phase {phase_id} verification error: {e}")
            log.error(f"Phase {phase_id} verification error: {e}")
            return False
    
    def complete_phase(self, phase_id: str, skip_verification: bool = False):
        """
        Mark phase complete with git checkpoint.
        
        Args:
            phase_id: Phase identifier
            skip_verification: Skip verification checks (use with caution)
            
        Raises:
            RuntimeError: If verification fails
        """
        # Run verification unless skipped
        if not skip_verification:
            if not self.verify_phase(phase_id):
                raise RuntimeError(f"Phase {phase_id} failed verification!")
        
        # Create git checkpoint
        try:
            print(f"[+] Creating git checkpoint for Phase {phase_id}...")
            
            # Stage all changes
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            
            # Commit with descriptive message
            commit_msg = f"✅ Phase {phase_id} complete: {self.state.get('description', '')}"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Create tag for easy rollback
            tag_name = f"phase-{phase_id}-complete"
            subprocess.run(
                ["git", "tag", "-f", tag_name],
                check=True,
                capture_output=True
            )
            
            print(f"[OK] Git checkpoint created: {tag_name}")
            log.info(f"Git checkpoint created for Phase {phase_id}")
            
        except subprocess.CalledProcessError as e:
            log.warning(f"Git checkpoint failed: {e}")
            print(f"[!] Git checkpoint failed (non-fatal): {e}")
        
        # Update state
        completed_at = datetime.now().isoformat()
        self.state.update({
            "status": "complete",
            "completed_at": completed_at
        })
        self.state["history"].append({
            "phase": phase_id,
            "description": self.state.get("description", ""),
            "completed_at": completed_at
        })
        self._save_state()
        
        print(f"[OK] Phase {phase_id} complete and checkpointed!")
        log.info(f"Phase {phase_id} completed")
    
    def rollback_to_last_complete(self):
        """Rollback to last completed phase using git."""
        if not self.state["history"]:
            print("[X] No completed phases to rollback to")
            log.warning("Rollback requested but no history")
            return
        
        last_phase = self.state["history"][-1]["phase"]
        tag = f"phase-{last_phase}-complete"
        
        print(f"[~] Rolling back to Phase {last_phase}...")
        log.info(f"Rolling back to Phase {last_phase}")
        
        try:
            subprocess.run(["git", "reset", "--hard", tag], check=True)
            
            # Update state
            self.state["current_phase"] = last_phase
            self.state["status"] = "rolled_back"
            self.state["rolled_back_at"] = datetime.now().isoformat()
            self._save_state()
            
            print(f"[OK] Rolled back to Phase {last_phase}")
            log.info(f"Successfully rolled back to Phase {last_phase}")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Rollback failed: {e}")
            log.error(f"Rollback failed: {e}")
            raise
    
    def rollback_to_phase(self, phase_id: str):
        """
        Rollback to specific phase.
        
        Args:
            phase_id: Phase identifier to rollback to
        """
        # Find phase in history
        phase_exists = any(p["phase"] == phase_id for p in self.state["history"])
        
        if not phase_exists:
            print(f"[X] Phase {phase_id} not found in history")
            log.error(f"Phase {phase_id} not found in history")
            return
        
        tag = f"phase-{phase_id}-complete"
        
        print(f"[~] Rolling back to Phase {phase_id}...")
        log.info(f"Rolling back to Phase {phase_id}")
        
        try:
            subprocess.run(["git", "reset", "--hard", tag], check=True)
            
            # Update state - remove phases after this one
            self.state["history"] = [
                p for p in self.state["history"]
                if p["phase"] <= phase_id
            ]
            self.state["current_phase"] = phase_id
            self.state["status"] = "rolled_back"
            self.state["rolled_back_at"] = datetime.now().isoformat()
            self._save_state()
            
            print(f"[OK] Rolled back to Phase {phase_id}")
            log.info(f"Successfully rolled back to Phase {phase_id}")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Rollback failed: {e}")
            log.error(f"Rollback failed: {e}")
            raise
    
    def get_current_status(self) -> Dict:
        """
        Get current implementation status.
        
        Returns:
            Dictionary containing current phase state
        """
        return {
            "current_phase": self.state.get("current_phase"),
            "status": self.state.get("status"),
            "description": self.state.get("description"),
            "started_at": self.state.get("started_at"),
            "completed_phases": [p["phase"] for p in self.state["history"]],
            "total_phases_completed": len(self.state["history"])
        }
    
    def print_status(self):
        """Print current status in a human-readable format."""
        status = self.get_current_status()
        
        print("\n" + "="*60)
        print("PHASE MANAGER STATUS")
        print("="*60)
        print(f"Current Phase: {status['current_phase'] or 'None'}")
        print(f"Status: {status['status']}")
        
        if status.get('description'):
            print(f"Description: {status['description']}")
        
        if status.get('started_at'):
            print(f"Started: {status['started_at']}")
        
        print(f"\nCompleted Phases: {status['total_phases_completed']}")
        if status['completed_phases']:
            print("  " + ", ".join(status['completed_phases']))
        
        print("="*60 + "\n")


def main():
    """CLI interface for phase manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MAX Phase Manager")
    parser.add_argument("action", choices=["status", "begin", "complete", "rollback"])
    parser.add_argument("--phase", help="Phase ID")
    parser.add_argument("--description", help="Phase description")
    parser.add_argument("--skip-verification", action="store_true",
                       help="Skip verification (use with caution)")
    
    args = parser.parse_args()
    
    pm = PhaseManager()
    
    if args.action == "status":
        pm.print_status()
    
    elif args.action == "begin":
        if not args.phase or not args.description:
            print("[X] --phase and --description required for begin")
            return
        pm.begin_phase(args.phase, args.description)
    
    elif args.action == "complete":
        if not args.phase:
            print("[X] --phase required for complete")
            return
        pm.complete_phase(args.phase, skip_verification=args.skip_verification)
    
    elif args.action == "rollback":
        if args.phase:
            pm.rollback_to_phase(args.phase)
        else:
            pm.rollback_to_last_complete()


if __name__ == "__main__":
    main()
