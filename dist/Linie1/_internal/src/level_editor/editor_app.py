# src/level_editor/editor_app.py
import pygame
import sys
import os
import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
import pickle
import json

# Since 'src' is on the system path, we import from its subdirectories directly.
from level_editor.grid import Grid
from level_editor.sidebar import Sidebar
from common import constants as C
# from common.sound_manager import SoundManager

class EditorApp:
    def __init__(self):
        # self.sounds = sounds # Store the passed-in SoundManager instance
        
        self.tk_root = tk.Tk()
        self.tk_root.withdraw()
        rows = simpledialog.askinteger("Grid Size", "Enter PLAYABLE rows:", initialvalue=12, minvalue=3, maxvalue=50)
        cols = simpledialog.askinteger("Grid Size", "Enter PLAYABLE columns:", initialvalue=12, minvalue=3, maxvalue=50)
        self.tk_root.destroy()

        if not rows or not cols:
            sys.exit()

        # The pygame.init() call is now correctly in main.py
        self.editor_width, self.editor_height = 1600, 900
        self.screen = pygame.display.set_mode((self.editor_width, self.editor_height))
        pygame.display.set_caption("Linie 1: Level Editor")
        self.clock = pygame.time.Clock()

        self.sidebar = Sidebar(self.editor_height, self.editor_width)
        self.grid = Grid(rows, cols, self.sidebar.width, self.editor_width, self.editor_height)
        
        self.running = True
        self.current_orientation = 0

    def run(self):
        """The main loop of the editor."""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

          
    def handle_events(self):
        """Handles all user input, now correctly passing mouse position."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            sidebar_result = self.sidebar.handle_event(event)
            
            if sidebar_result == "ui_focus":
                continue # The sidebar is typing or scrolling, don't interact with the grid.
            elif sidebar_result == "Save": self.save_level()
            elif sidebar_result == "Load": self.load_level()
            elif sidebar_result == "Export": self.export_level()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.current_orientation = (self.current_orientation + 90) % 360
            
            if event.type == pygame.MOUSEWHEEL:
                self.sidebar.handle_event(event) # Pass the whole event for simplicity

            # --- START OF CHANGE: Correct the logic for mouse clicks ---
            # We handle the sidebar event first, and only if it doesn't consume the click
            # do we process it as a grid click.
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_result = self.sidebar.handle_event(event)

                if click_result == "stamp":
                    # A stamp was selected, which is all we need to do.
                    pass 
                elif click_result == "Save":
                    self.save_level()
                elif click_result == "Load":
                    self.load_level()
                elif click_result == "Export":
                    self.export_level()
                elif click_result == "Mute Music":
                    # self.sounds.toggle_mute()
                    return
                elif click_result == "Search":
                    self.search_for_stamp()
                elif click_result is None:
                    # If the sidebar didn't handle the click, it must be for the grid.
                    # We can safely get the mouse position from the event here.
                    mouse_pos = event.pos
                    selected_stamp = self.sidebar.get_selected_stamp()
                    if selected_stamp:
                        self.grid.handle_click(mouse_pos, selected_stamp, self.current_orientation)
            
            # Pass other mouse events to the sidebar for things like scrollbar dragging
            elif event.type == pygame.MOUSEBUTTONUP or event.type == pygame.MOUSEMOTION:
                self.sidebar.handle_event(event)
            # --- END OF CHANGE ---

    def update(self):
        """Update logic (not needed for Phase 1)."""
        pass

    def draw(self):
        """Draws all components to the screen."""
        self.screen.fill((20, 20, 30))
        self.grid.draw(self.screen)
        self.sidebar.draw(self.screen)
        self._draw_mouse_preview()
        pygame.display.flip()

    def _draw_mouse_preview(self):
        """Draws the currently selected stamp, rotated, under the cursor."""
        mouse_pos = pygame.mouse.get_pos()
        
        if self.grid.is_mouse_over(mouse_pos):
            # --- START OF CHANGE: Use the correct helper method ---
            stamp = self.sidebar.get_selected_stamp()
            # --- END OF CHANGE ---

            if not stamp: return

            # Preview for single tiles
            if stamp['type'] == 'tile':
                base_surf = self.grid.stamp_surfaces.get(stamp['name'])
                if base_surf:
                    rotated_surf = pygame.transform.rotate(base_surf, -self.current_orientation)
                    rotated_surf.set_alpha(150)
                    preview_rect = rotated_surf.get_rect(center=mouse_pos)
                    self.screen.blit(rotated_surf, preview_rect)
            
            # Preview for terminal pairs
            elif stamp['type'] == 'terminal_pair':
                curve_surf = self.grid.stamp_surfaces.get('Curve')
                if not curve_surf: return
                
                pair_configs = {
                    0:   [(0, 0, 90), (0, 1, 180)],
                    90:  [(0, 0, 180), (1, 0, 270)],
                    180: [(0, 0, 270), (0, -1, 0)],
                    270: [(0, 0, 0), (-1, 0, 90)],
                }
                config = pair_configs[self.current_orientation]

                rot1 = pygame.transform.rotate(curve_surf, -config[0][2])
                rot1.set_alpha(150)
                rect1 = rot1.get_rect(center=mouse_pos)
                self.screen.blit(rot1, rect1)

                pos2_x = mouse_pos[0] + (config[1][1] * self.grid.tile_size)
                pos2_y = mouse_pos[1] + (config[1][0] * self.grid.tile_size)
                rot2 = pygame.transform.rotate(curve_surf, -config[1][2])
                rot2.set_alpha(150)
                rect2 = rot2.get_rect(center=(pos2_x, pos2_y))
                self.screen.blit(rot2, rect2)

    def save_level(self):
        """Saves the current grid data to a .lvl file using pickle."""
        # --- START OF CHANGE: Re-initialize the Tk root for each dialog ---
        self.tk_root = tk.Tk()
        self.tk_root.withdraw()
        filepath = filedialog.asksaveasfilename(
            title="Save Level File",
            defaultextension=".lvl",
            filetypes=[("Level Files", "*.lvl")]
        )
        self.tk_root.destroy()
        # --- END OF CHANGE ---
        
        if filepath:
            try:
                with open(filepath, 'wb') as f:
                    pickle.dump(self.grid.get_grid_data(), f)
                messagebox.showinfo("Success", "Level saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save level: {e}")

    def load_level(self):
        """Loads grid data from a .lvl file using pickle."""
        self.tk_root = tk.Tk()
        self.tk_root.withdraw()
        filepath = filedialog.askopenfilename(
            title="Load Level File",
            filetypes=[("Level Files", "*.lvl")]
        )
        self.tk_root.destroy()

        if filepath:
            try:
                with open(filepath, 'rb') as f:
                    loaded_data = pickle.load(f)
                self.grid.set_grid_data(loaded_data)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load level: {e}")

    def export_level(self):
        """
        Exports the current grid data to a game-ready .json file,
        now without the extra name/author prompts.
        """
        grid_data = self.grid.get_grid_data()
        
        # 1. Transform and validate the data (this logic is correct from last time)
        building_coords = {}
        terminals_by_line = {i: [] for i in range(1, 7)}
        raw_terminals: List[Tuple[int, Tuple[int, int], int]] = []
        for r, row_data in enumerate(grid_data):
            for c, stamp in enumerate(row_data):
                if stamp:
                    if stamp['type'] == 'building': building_coords[stamp['name']] = [r, c]
                    elif stamp['type'] == 'terminal': raw_terminals.append((stamp['line_number'], (r,c), stamp['orientation']))
        
        for term in raw_terminals:
            line_num, pos, orient = term; is_paired = False
            for other_term in raw_terminals:
                if term == other_term: continue
                other_line, other_pos, other_orient = other_term
                if line_num == other_line and abs(pos[0] - other_pos[0]) + abs(pos[1] - other_pos[1]) == 1:
                    pair = tuple(sorted((term, other_term)))
                    if pair not in terminals_by_line[line_num]: terminals_by_line[line_num].append(pair)
                    is_paired = True; break
            if not is_paired:
                messagebox.showerror("Validation Error", f"Terminal for Line {line_num} at {pos} is unpaired."); return

        final_terminal_data = {}
        for line_num, pairs in terminals_by_line.items():
            if not pairs: continue
            if len(pairs) != 2:
                messagebox.showerror("Validation Error", f"Line {line_num} has {len(pairs)} terminal ends. Each line requires exactly two."); return
            pair1 = [ [list(p[1]), p[2]] for p in pairs[0] ]; pair2 = [ [list(p[1]), p[2]] for p in pairs[1] ]
            final_terminal_data[str(line_num)] = [ pair1, pair2 ]

        # 2. Prompt for save location
        self.tk_root = tk.Tk(); self.tk_root.withdraw()
        filepath = filedialog.asksaveasfilename(
            title="Export Level to JSON",
            initialdir=os.path.join(os.path.dirname(__file__), '..', 'levels'),
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")]
        )
        self.tk_root.destroy()
        if not filepath: return

        # 3. Auto-generate metadata from the filename
        base_name = os.path.basename(filepath)
        name_without_ext = os.path.splitext(base_name)[0]
        level_name = name_without_ext.replace('_', ' ').replace('-', ' ').title()
        author_name = "Level Editor"

        # 4. Create and write the final JSON object
        export_data = {
            "level_name": level_name, "author": author_name,
            "grid_rows": self.grid.total_rows, "grid_cols": self.grid.total_cols,
            "playable_rows": [1, self.grid.playable_rows], "playable_cols": [1, self.grid.playable_cols],
            "building_coords": building_coords, "terminal_data": final_terminal_data
        }
        try:
            with open(filepath, 'w') as f: json.dump(export_data, f, indent=2)
            messagebox.showinfo("Success", "Level exported successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export level: {e}")
    # --- END OF CHANGE ---

    def search_for_stamp(self):
        """Prompts the user for a search term and tells the sidebar to find it."""
        self.tk_root = tk.Tk(); self.tk_root.withdraw()
        search_term = simpledialog.askstring("Search Stamp", "Enter name of tile, building, or tool to find:")
        self.tk_root.destroy()
        
        if search_term:
            self.sidebar.search_and_select(search_term)