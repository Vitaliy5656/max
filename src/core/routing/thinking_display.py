"""
Thinking Display for MAX AI.

Formats plan progress for display in chat UI.
Creates expandable thinking blocks with step indicators.

Features:
    - Collapsible thinking blocks
    - Step progress indicators
    - Timing display
    - Status icons
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from ..logger import log


class ThinkingStyle(Enum):
    """Display styles for thinking blocks."""
    MINIMAL = "minimal"      # Just dots: ...
    COMPACT = "compact"      # Single line progress
    EXPANDED = "expanded"    # Full step details
    STREAMING = "streaming"  # Real-time updates


@dataclass
class ThinkingBlock:
    """A formatted thinking block for UI."""
    header: str
    steps: List[str]
    footer: str
    is_complete: bool
    html: str
    markdown: str


class ThinkingDisplay:
    """
    Formats thinking/planning progress for chat display.
    """
    
    # Status icons
    ICONS = {
        "pending": "○",
        "running": "◐",
        "completed": "●",
        "failed": "✗",
        "skipped": "◌"
    }
    
    # Colors for HTML
    COLORS = {
        "pending": "#9ca3af",
        "running": "#3b82f6",
        "completed": "#22c55e",
        "failed": "#ef4444",
        "skipped": "#6b7280"
    }
    
    def __init__(self, style: ThinkingStyle = ThinkingStyle.COMPACT):
        self.style = style
        log.debug(f"ThinkingDisplay initialized (style={style.value})")
    
    def format_plan_start(self, goal: str, steps: List[Dict]) -> str:
        """Format plan start message."""
        if self.style == ThinkingStyle.MINIMAL:
            return f"⏳ {goal}..."
        
        step_list = " → ".join(s.get("icon", "•") for s in steps)
        return f"🎯 **{goal}**\n{step_list}"
    
    def format_step_progress(
        self,
        step_title: str,
        step_icon: str,
        status: str,
        elapsed_ms: float = 0
    ) -> str:
        """Format single step progress."""
        icon = self.ICONS.get(status, "•")
        
        if self.style == ThinkingStyle.MINIMAL:
            return f"{icon}"
        
        time_str = f" ({elapsed_ms:.0f}ms)" if elapsed_ms > 0 else ""
        
        if status == "running":
            return f"{step_icon} {step_title}...{time_str}"
        elif status == "completed":
            return f"✓ {step_title}{time_str}"
        elif status == "failed":
            return f"✗ {step_title} (ошибка)"
        else:
            return f"○ {step_title}"
    
    def format_plan_complete(
        self,
        goal: str,
        total_steps: int,
        completed_steps: int,
        total_time_ms: float
    ) -> str:
        """Format plan completion message."""
        if self.style == ThinkingStyle.MINIMAL:
            return "✓"
        
        return f"✅ Готово! ({completed_steps}/{total_steps} шагов, {total_time_ms:.0f}ms)"
    
    def format_thinking_block(
        self,
        plan_updates: List[Dict]
    ) -> ThinkingBlock:
        """
        Format a complete thinking block from plan updates.
        
        Returns both markdown and HTML versions.
        """
        if not plan_updates:
            return ThinkingBlock(
                header="",
                steps=[],
                footer="",
                is_complete=False,
                html="",
                markdown=""
            )
        
        # Extract info from updates
        goal = ""
        steps_text = []
        is_complete = False
        total_time = 0
        
        for update in plan_updates:
            if update.get("type") == "plan_start":
                goal = update.get("goal", "")
            elif update.get("type") == "step_start":
                step = update.get("step", {})
                steps_text.append(self.format_step_progress(
                    step.get("title", ""),
                    step.get("icon", "•"),
                    "running"
                ))
            elif update.get("type") == "step_complete":
                step = update.get("step", {})
                # Replace last step with completed version
                if steps_text:
                    steps_text[-1] = self.format_step_progress(
                        step.get("title", ""),
                        step.get("icon", "•"),
                        "completed",
                        step.get("elapsed_ms", 0)
                    )
            elif update.get("type") == "plan_complete":
                is_complete = True
                total_time = update.get("total_time_ms", 0)
        
        # Build blocks
        header = f"🧠 **Thinking:** {goal}" if goal else "🧠 **Thinking...**"
        footer = f"✅ Done ({total_time:.0f}ms)" if is_complete else ""
        
        # Markdown version
        md_steps = "\n".join(f"  {s}" for s in steps_text)
        markdown = f"{header}\n{md_steps}"
        if footer:
            markdown += f"\n{footer}"
        
        # HTML version (collapsible)
        html = self._build_html(header, steps_text, footer, is_complete)
        
        return ThinkingBlock(
            header=header,
            steps=steps_text,
            footer=footer,
            is_complete=is_complete,
            html=html,
            markdown=markdown
        )
    
    def _build_html(
        self,
        header: str,
        steps: List[str],
        footer: str,
        is_complete: bool
    ) -> str:
        """Build HTML for thinking block."""
        steps_html = "".join(f'<div class="thinking-step">{s}</div>' for s in steps)
        
        state = "complete" if is_complete else "running"
        
        return f'''
<div class="thinking-block thinking-{state}">
    <div class="thinking-header">{header}</div>
    <div class="thinking-steps">{steps_html}</div>
    {f'<div class="thinking-footer">{footer}</div>' if footer else ''}
</div>
'''
    
    def get_css(self) -> str:
        """Get CSS styles for thinking blocks."""
        return '''
<style>
.thinking-block {
    background: rgba(59, 130, 246, 0.1);
    border-left: 3px solid #3b82f6;
    padding: 12px 16px;
    margin: 8px 0;
    border-radius: 0 8px 8px 0;
    font-size: 14px;
}
.thinking-block.thinking-complete {
    border-left-color: #22c55e;
    background: rgba(34, 197, 94, 0.1);
}
.thinking-header {
    font-weight: 600;
    margin-bottom: 8px;
}
.thinking-step {
    padding: 4px 0;
    color: #6b7280;
}
.thinking-step:last-child {
    color: #374151;
}
.thinking-footer {
    margin-top: 8px;
    font-size: 12px;
    color: #22c55e;
}
@keyframes thinking-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
.thinking-running .thinking-header {
    animation: thinking-pulse 1.5s infinite;
}
</style>
'''


# Global instance
_display: Optional[ThinkingDisplay] = None


def get_thinking_display(style: ThinkingStyle = ThinkingStyle.COMPACT) -> ThinkingDisplay:
    """Get or create global display."""
    global _display
    if _display is None:
        _display = ThinkingDisplay(style)
    return _display


def format_as_thinking(plan_updates: List[Dict]) -> str:
    """Quick helper to format plan updates as thinking block."""
    return get_thinking_display().format_thinking_block(plan_updates).markdown
