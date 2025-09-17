"""
TUI Session Replay Application

This module provides an interactive terminal application for replaying
recorded MiniTel-Lite sessions with keyboard navigation.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich import box

from ..minitel.session import SessionLoader


class SessionReplayTUI:
    """
    Interactive TUI for replaying MiniTel-Lite sessions.
    
    Keybindings:
    - N/n: Next step
    - P/p: Previous step
    - Q/q: Quit
    """
    
    def __init__(self, session_file: str):
        self.session_file = session_file
        self.console = Console()
        self.interactions: List[Dict[str, Any]] = []
        self.current_step = 0
        self.session_data: Dict[str, Any] = {}
        self.load_session()
    
    def load_session(self) -> None:
        """Load session data from file."""
        try:
            self.session_data = SessionLoader.load_session(self.session_file)
            self.interactions = self.session_data.get("interactions", [])
            
            if not self.interactions:
                self.console.print("[red]No interactions found in session file[/red]")
                sys.exit(1)
                
        except FileNotFoundError:
            self.console.print(f"[red]Session file not found: {self.session_file}[/red]")
            sys.exit(1)
        except json.JSONDecodeError:
            self.console.print(f"[red]Invalid JSON in session file: {self.session_file}[/red]")
            sys.exit(1)
    
    def create_header_panel(self) -> Panel:
        """Create the header panel with session information."""
        session_id = self.session_data.get("session_id", "Unknown")
        start_time = self.session_data.get("start_time", 0)
        duration = self.session_data.get("duration", 0)
        total_interactions = self.session_data.get("total_interactions", 0)
        
        start_time_str = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
        
        header_text = Text()
        header_text.append("NORAD MINITEL-LITE SESSION REPLAY\n", style="bold red")
        header_text.append(f"Session ID: {session_id}\n", style="cyan")
        header_text.append(f"Start Time: {start_time_str}\n", style="white")
        header_text.append(f"Duration: {duration:.2f}s\n", style="white")
        header_text.append(f"Total Interactions: {total_interactions}", style="white")
        
        return Panel(header_text, title="Session Information", border_style="blue")
    
    def create_navigation_panel(self) -> Panel:
        """Create the navigation panel with current step info."""
        total_steps = len(self.interactions)
        
        nav_text = Text()
        nav_text.append(f"Step {self.current_step + 1} of {total_steps}\n", style="bold yellow")
        nav_text.append("\nControls:\n", style="bold")
        nav_text.append("N/n - Next step\n", style="green")
        nav_text.append("P/p - Previous step\n", style="green")
        nav_text.append("Q/q - Quit", style="red")
        
        return Panel(nav_text, title="Navigation", border_style="green")
    
    def create_interaction_panel(self) -> Panel:
        """Create the panel showing the current interaction."""
        if not self.interactions or self.current_step >= len(self.interactions):
            return Panel("No interaction to display", title="Interaction", border_style="red")
        
        interaction = self.interactions[self.current_step]
        
        # Create interaction table
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="white")
        
        # Add interaction details
        timestamp = interaction.get("timestamp", 0)
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3]
        
        table.add_row("Timestamp", time_str)
        table.add_row("Relative Time", f"{interaction.get('relative_time', 0):.3f}s")
        table.add_row("Type", interaction.get("type", "unknown"))
        
        if interaction.get("type") in ["request", "response"]:
            table.add_row("Direction", interaction.get("direction", ""))
            table.add_row("Command", interaction.get("command", ""))
            table.add_row("Command Code", interaction.get("command_code", ""))
            table.add_row("Nonce", str(interaction.get("nonce", "")))
            table.add_row("Payload Length", str(interaction.get("payload_length", 0)))
            
            payload = interaction.get("payload", "")
            if payload:
                # Truncate long payloads
                if len(payload) > 100:
                    payload = payload[:97] + "..."
                table.add_row("Payload", payload)
            
            table.add_row("Frame Length", str(interaction.get("raw_frame_length", 0)))
            
        elif interaction.get("type") == "event":
            table.add_row("Event Type", interaction.get("event_type", ""))
            
            details = interaction.get("details", {})
            if details:
                details_str = ", ".join([f"{k}: {v}" for k, v in details.items()])
                if len(details_str) > 100:
                    details_str = details_str[:97] + "..."
                table.add_row("Details", details_str)
        
        description = interaction.get("description", "")
        if description:
            table.add_row("Description", description)
        
        # Determine panel color based on interaction type
        border_color = "white"
        if interaction.get("type") == "request":
            border_color = "blue"
        elif interaction.get("type") == "response":
            border_color = "green"
        elif interaction.get("type") == "event":
            event_type = interaction.get("event_type", "")
            if "error" in event_type.lower():
                border_color = "red"
            else:
                border_color = "yellow"
        
        return Panel(table, title="Current Interaction", border_style=border_color)
    
    def create_timeline_panel(self) -> Panel:
        """Create a timeline panel showing interaction sequence."""
        timeline_text = Text()
        
        # Show a window of interactions around the current step
        window_size = 10
        start_idx = max(0, self.current_step - window_size // 2)
        end_idx = min(len(self.interactions), start_idx + window_size)
        
        for i in range(start_idx, end_idx):
            interaction = self.interactions[i]
            
            # Format the timeline entry
            time_offset = interaction.get("relative_time", 0)
            interaction_type = interaction.get("type", "unknown")
            
            if interaction_type in ["request", "response"]:
                command = interaction.get("command", "UNKNOWN")
                direction = "→" if interaction_type == "request" else "←"
                entry = f"{time_offset:6.2f}s {direction} {command}"
            else:
                event_type = interaction.get("event_type", "event")
                entry = f"{time_offset:6.2f}s • {event_type}"
            
            # Highlight current step
            if i == self.current_step:
                timeline_text.append(f"► {entry}\n", style="bold yellow on blue")
            else:
                style = "white"
                if interaction_type == "request":
                    style = "blue"
                elif interaction_type == "response":
                    style = "green"
                elif "error" in interaction.get("event_type", "").lower():
                    style = "red"
                
                timeline_text.append(f"  {entry}\n", style=style)
        
        return Panel(timeline_text, title="Timeline", border_style="magenta")
    
    def create_layout(self) -> Layout:
        """Create the main layout for the TUI."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=8),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right", ratio=2)
        )
        
        layout["left"].split_column(
            Layout(name="navigation", size=10),
            Layout(name="timeline")
        )
        
        # Populate layouts
        layout["header"].update(self.create_header_panel())
        layout["navigation"].update(self.create_navigation_panel())
        layout["timeline"].update(self.create_timeline_panel())
        layout["right"].update(self.create_interaction_panel())
        
        # Footer with instructions
        footer_text = Text("Use N/n (next), P/p (previous), Q/q (quit) to navigate", 
                          style="bold white on black", justify="center")
        layout["footer"].update(Panel(footer_text, border_style="white"))
        
        return layout
    
    def next_step(self) -> bool:
        """Move to the next step. Returns True if moved, False if at end."""
        if self.current_step < len(self.interactions) - 1:
            self.current_step += 1
            return True
        return False
    
    def previous_step(self) -> bool:
        """Move to the previous step. Returns True if moved, False if at beginning."""
        if self.current_step > 0:
            self.current_step -= 1
            return True
        return False
    
    def run(self) -> None:
        """Run the interactive TUI."""
        try:
            import termios
            import tty
            
            # Save terminal settings
            old_settings = termios.tcgetattr(sys.stdin)
            
            with Live(self.create_layout(), refresh_per_second=10, screen=True) as live:
                try:
                    tty.setraw(sys.stdin.fileno())
                    
                    while True:
                        # Read a single character
                        char = sys.stdin.read(1).lower()
                        
                        if char in ['q']:
                            break
                        elif char in ['n']:
                            self.next_step()
                        elif char in ['p']:
                            self.previous_step()
                        
                        # Update the display
                        live.update(self.create_layout())
                        
                finally:
                    # Restore terminal settings
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                    
        except ImportError:
            # Fallback for systems without termios (Windows)
            self.console.print("[yellow]Warning: Advanced keyboard input not available on this system[/yellow]")
            self.console.print("Using simple input mode. Press Enter after each command.")
            
            while True:
                self.console.clear()
                self.console.print(self.create_layout())
                
                command = input("\nCommand (n/p/q): ").lower().strip()
                
                if command == 'q':
                    break
                elif command == 'n':
                    if not self.next_step():
                        self.console.print("[yellow]Already at the last step[/yellow]")
                        input("Press Enter to continue...")
                elif command == 'p':
                    if not self.previous_step():
                        self.console.print("[yellow]Already at the first step[/yellow]")
                        input("Press Enter to continue...")


def list_sessions_command(sessions_dir: str = "sessions") -> None:
    """List available session files."""
    console = Console()
    sessions = SessionLoader.list_sessions(sessions_dir)
    
    if not sessions:
        console.print(f"[yellow]No session files found in {sessions_dir}[/yellow]")
        return
    
    table = Table(title="Available Sessions", show_header=True, header_style="bold magenta")
    table.add_column("Session ID", style="cyan")
    table.add_column("Recorded At", style="white")
    table.add_column("Duration", style="green")
    table.add_column("Interactions", style="yellow")
    table.add_column("File", style="blue")
    
    for session in sessions:
        duration = session.get("duration", 0)
        duration_str = f"{duration:.2f}s" if duration else "Unknown"
        
        recorded_at = session.get("recorded_at", "Unknown")
        if recorded_at != "Unknown":
            try:
                dt = datetime.fromisoformat(recorded_at.replace('Z', '+00:00'))
                recorded_at = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        table.add_row(
            session.get("session_id", "Unknown"),
            recorded_at,
            duration_str,
            str(session.get("total_interactions", 0)),
            session.get("filename", "")
        )
    
    console.print(table)


def main():
    """Main entry point for the session replay TUI."""
    parser = argparse.ArgumentParser(description="MiniTel-Lite Session Replay TUI")
    parser.add_argument("--session", "-s", help="Session file to replay")
    parser.add_argument("--list", "-l", action="store_true", help="List available sessions")
    parser.add_argument("--sessions-dir", default="sessions", help="Directory containing session files")
    
    args = parser.parse_args()
    
    if args.list:
        list_sessions_command(args.sessions_dir)
        return 0
    
    if not args.session:
        console = Console()
        console.print("[red]Error: No session file specified[/red]")
        console.print("Use --session <file> to specify a session file")
        console.print("Use --list to see available sessions")
        return 1
    
    try:
        replay = SessionReplayTUI(args.session)
        replay.run()
        return 0
        
    except KeyboardInterrupt:
        print("\nReplay interrupted by user")
        return 1
    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
