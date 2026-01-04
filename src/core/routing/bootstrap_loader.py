"""
Bootstrap Loader for Semantic Router.

Loads training examples from YAML and creates embeddings for vector search.
"""
import yaml
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass

# Path to training data (MAX/data/semantic_training.yaml)
TRAINING_DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "semantic_training.yaml"


@dataclass
class TrainingExample:
    """Single training example with text and intent."""
    text: str
    intent: str


def load_training_data() -> Dict[str, List[str]]:
    """
    Load bootstrap training data from YAML file.
    
    Returns:
        Dict mapping intent names to lists of example phrases
    """
    if not TRAINING_DATA_PATH.exists():
        raise FileNotFoundError(f"Training data not found: {TRAINING_DATA_PATH}")
    
    with open(TRAINING_DATA_PATH, 'r', encoding='utf-8') as f:
        # Skip the header comments
        content = f.read()
        # Find where YAML starts (first line without #)
        lines = content.split('\n')
        yaml_start = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('#'):
                yaml_start = i
                break
        
        yaml_content = '\n'.join(lines[yaml_start:])
        data = yaml.safe_load(yaml_content)
    
    return data or {}


def get_all_examples() -> List[TrainingExample]:
    """
    Get all training examples as flat list.
    
    Returns:
        List of TrainingExample objects
    """
    data = load_training_data()
    examples = []
    
    for intent, phrases in data.items():
        if isinstance(phrases, list):
            for phrase in phrases:
                examples.append(TrainingExample(text=phrase, intent=intent.lower()))
    
    return examples


def get_intent_examples(intent: str) -> List[str]:
    """
    Get examples for specific intent.
    
    Args:
        intent: Intent name (case insensitive)
        
    Returns:
        List of example phrases
    """
    data = load_training_data()
    return data.get(intent.upper(), [])


def count_examples() -> Dict[str, int]:
    """
    Count examples per intent.
    
    Returns:
        Dict mapping intent to count
    """
    data = load_training_data()
    return {intent: len(phrases) for intent, phrases in data.items()}


# Quick test
if __name__ == "__main__":
    print("Loading bootstrap training data...")
    counts = count_examples()
    total = sum(counts.values())
    print(f"\nTotal examples: {total}")
    print("\nPer intent:")
    for intent, count in sorted(counts.items()):
        print(f"  {intent}: {count}")
