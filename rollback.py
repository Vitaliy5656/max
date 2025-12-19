"""
Rollback script for MAX transformation phases.
Provides easy rollback to any completed phase.
"""
import subprocess
import sys
import argparse


def get_phase_commits():
    """Get all phase completion commits."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--all"],
            capture_output=True, text=True, check=True
        )
        commits = []
        for line in result.stdout.split('\n'):
            if 'Phase' in line and 'complete' in line:
                commits.append(line)
        return commits
    except subprocess.CalledProcessError:
        return []


def get_phase_tags():
    """Get all phase tags."""
    try:
        result = subprocess.run(
            ["git", "tag", "-l", "phase-*"],
            capture_output=True, text=True, check=True
        )
        return [t.strip() for t in result.stdout.split('\n') if t.strip()]
    except subprocess.CalledProcessError:
        return []


def rollback_to_phase(phase_id: str):
    """Rollback to specific phase."""
    tag = f"phase-{phase_id}-complete"
    
    print(f"[~] Rolling back to Phase {phase_id}...")
    
    try:
        subprocess.run(["git", "reset", "--hard", tag], check=True)
        print(f"[OK] Rolled back to Phase {phase_id}")
    except subprocess.CalledProcessError as e:
        print(f"[X] Rollback failed: {e}")
        print(f"    Tag '{tag}' may not exist. Available tags:")
        for t in get_phase_tags():
            print(f"      - {t}")
        sys.exit(1)


def rollback_to_commit(commit_hash: str):
    """Rollback to specific commit."""
    print(f"[~] Rolling back to commit {commit_hash}...")
    
    try:
        subprocess.run(["git", "reset", "--hard", commit_hash], check=True)
        print(f"[OK] Rolled back to {commit_hash}")
    except subprocess.CalledProcessError as e:
        print(f"[X] Rollback failed: {e}")
        sys.exit(1)


def show_status():
    """Show current status and available rollback points."""
    print("\n=== MAX Rollback Status ===\n")
    
    # Current branch
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, check=True
        )
        print(f"Current branch: {result.stdout.strip()}")
    except subprocess.CalledProcessError:
        pass
    
    # Phase tags
    tags = get_phase_tags()
    if tags:
        print(f"\nAvailable phase tags ({len(tags)}):")
        for tag in tags:
            print(f"  - {tag}")
    else:
        print("\nNo phase tags found (no phases completed yet)")
    
    # Recent commits
    commits = get_phase_commits()
    if commits:
        print(f"\nPhase completion commits:")
        for commit in commits[:5]:
            print(f"  {commit}")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description="MAX Phase Rollback Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rollback.py status           # Show available rollback points
  python rollback.py --phase 0        # Rollback to Phase 0
  python rollback.py --commit abc123  # Rollback to specific commit
        """
    )
    parser.add_argument("action", nargs="?", default="status",
                       choices=["status", "rollback"],
                       help="Action to perform")
    parser.add_argument("--phase", "-p", help="Phase ID to rollback to")
    parser.add_argument("--commit", "-c", help="Commit hash to rollback to")
    
    args = parser.parse_args()
    
    if args.action == "status" or (not args.phase and not args.commit):
        show_status()
    elif args.phase:
        rollback_to_phase(args.phase)
    elif args.commit:
        rollback_to_commit(args.commit)


if __name__ == "__main__":
    main()
