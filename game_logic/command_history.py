# game_logic/command_history.py
from typing import List, Optional
from .commands import Command

class CommandHistory:
    def __init__(self):
        self._history: List[Command] = []
        self._current_index: int = -1 # Points to the last executed command

    def execute_command(self, command: Command) -> bool:
        """Executes a new command and adds it to the history."""
        if command.execute():
            # Discard redo history if new command is executed after undo
            if self._current_index < len(self._history) - 1:
                print(f"Discarding redo history from index {self._current_index + 1}")
                self._history = self._history[:self._current_index + 1]

            self._history.append(command)
            self._current_index += 1
            print(f"Command '{command.get_description()}' executed. History size: {len(self._history)}, Index: {self._current_index}")
            return True
        else:
            print(f"Command '{command.get_description()}' failed execution.")
            return False

    def undo(self) -> bool:
        """Undoes the last executed command."""
        if self._current_index >= 0:
            command_to_undo = self._history[self._current_index]
            print(f"Attempting to undo command at index {self._current_index}: '{command_to_undo.get_description()}'")
            if command_to_undo.undo():
                self._current_index -= 1
                print(f"Undo successful. Current index: {self._current_index}")
                return True
            else:
                print("Undo failed for the command.")
                return False
        else:
            print("Nothing to undo.")
            return False

    def redo(self) -> bool:
        """Redoes the last undone command."""
        if self._current_index < len(self._history) - 1:
            self._current_index += 1
            command_to_redo = self._history[self._current_index]
            print(f"Attempting to redo command at index {self._current_index}: '{command_to_redo.get_description()}'")
            # Re-execute the command's execute logic
            if command_to_redo.execute():
                print("Redo successful.")
                return True
            else:
                print("Redo failed (command execution failed). Undoing index change.")
                self._current_index -= 1 # Revert index if redo fails
                return False
        else:
            print("Nothing to redo.")
            return False

    def can_undo(self) -> bool:
        return self._current_index >= 0

    def can_redo(self) -> bool:
        return self._current_index < len(self._history) - 1

    def clear(self):
         """Clears the command history."""
         self._history = []
         self._current_index = -1

    def clear_redo_history(self):
        """Discards commands after the current index (prevents redo)."""
        if self._current_index < len(self._history) - 1:
            print(f"Clearing redo history from index {self._current_index + 1}")
            self._history = self._history[:self._current_index + 1]
            # Index remains pointing to the last valid command executed/undone to

    # Optional: Get description of last command for UI feedback
    def get_last_action_description(self) -> Optional[str]:
         if self._current_index >= 0:
              return self._history[self._current_index].get_description()
         return None

    def get_command_to_redo(self) -> Optional[Command]:
        """Returns the next command available for redo, if any."""
        if self._current_index < len(self._history) - 1:
             return self._history[self._current_index + 1]
        return None