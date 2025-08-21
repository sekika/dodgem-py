import tkinter as tk
from tkinter import ttk
from .dodgem import Dodgem


def launch_gui(args):
    root = tk.Tk()
    app = DodgemGUI(root, args)
    root.mainloop()


class DodgemGUI:
    def __init__(self, master, args):
        self.master = master
        self.master.title("Dodgem")
        self.game = Dodgem(evalmap=args.evalmap_path)
        self.game.level = [args.level, args.gote]
        self.game.mongo_server = args.mongo_server
        self.game.n = args.num
        self.game.verbose = args.verbose
        self.game.finished = True
        if self.game.level[0] != self.game.level[1]:
            self.game.refresh_evalmap = True
        self.initial = True
        self.selected_piece = None
        self.canvas_margin = 15
        self.after_id = None
        self.create_widgets()

    def create_widgets(self):
        # Settings frame
        self.settings_frame = tk.Frame(self.master)
        self.settings_frame.pack(pady=5)

        # Board size
        tk.Label(self.settings_frame, text="Board:").grid(row=0, column=0)
        self.size_var = tk.IntVar(value=self.game.n)
        size_menu = ttk.Combobox(
            self.settings_frame, textvariable=self.size_var,
            # read-only to prevent keyboard input
            values=[3, 4, 5], width=5, state='readonly'
        )
        size_menu.grid(row=0, column=1)
        size_menu.bind("<<ComboboxSelected>>", self.size_menu_change)

        # First and second player types
        self.players = {'Human': 0}
        for level in range(1, 5):
            self.players[f'CPU L{level}'] = level

        def label(i):
            return next((k for k, v in self.players.items() if v == self.game.level[i]), None)

        ttk.Label(self.settings_frame, text="First:").grid(
            row=1, column=0)
        self.first_player_var = tk.StringVar(value=label(0))
        first_menu = ttk.Combobox(
            self.settings_frame, textvariable=self.first_player_var,
            values=list(self.players.keys()), width=10,
        )
        first_menu.grid(row=1, column=1)

        ttk.Label(self.settings_frame, text="Second: ").grid(
            row=1, column=2)
        self.second_player_var = tk.StringVar(value=label(1))
        second_menu = ttk.Combobox(
            self.settings_frame, textvariable=self.second_player_var,
            values=list(self.players.keys()), width=10, state='readonly'
        )
        second_menu.grid(row=1, column=3)

        # Start button
        self.start_button = tk.Button(
            self.master, text="Start Game", command=self.start_game)
        self.start_button.pack(pady=5)

        # Status label
        self.status_label = tk.Label(
            self.master, text="Ready", font=("Arial", 12))
        self.status_label.pack(pady=5)

        # Canvas for board
        self.master.update_idletasks()
        self.canvas_size = self.master.winfo_width() - self.canvas_margin
        self.canvas = tk.Canvas(
            self.master, width=self.canvas_size, height=self.canvas_size, bg="white")
        self.canvas.pack()
        self.master.update_idletasks()
        self.init_board()
        self.canvas.bind("<Button-1>", self.on_click)

    def size_menu_change(self, event):
        if self.game.finished or self.initial:
            self.init_board()

    def init_board(self):
        self.game.n = self.size_var.get()
        self.game.level = [
            self.players[self.first_player_var.get()], self.players[self.second_player_var.get()]]
        self.cell_size = self.canvas_size // self.game.n
        self.game.start()
        self.update_board()

    def start_game(self):
        if self.after_id:
            self.master.after_cancel(self.after_id)
            self.after_id = None

        # Initialize board
        self.init_board()
        self.game.finished = False
        self.game.draw = False
        self.game.win_determined = -1
        self.game.move_count = 0
        if 4 in self.game.level or self.game.verbose > 3:
            self.game.open_mongodb()
        if self.game.level[0] != self.game.level[1]:
            self.game.refresh_evalmap = True
        self.game.load_evalmap()

        self.selected_piece = None
        self.initial = False
        self.update_board()
        self.update_status()
        self.game.show_move()
        if self.game.level[self.game.turn] > 0:
            self.after_id = self.master.after(500, self.do_step)
            self.after_id = None

    def update_board(self):
        canvas_size = self.master.winfo_width() - self.canvas_margin
        if self.canvas_size != canvas_size:
            self.canvas_size = canvas_size
            self.canvas.configure(width=canvas_size, height=canvas_size)
        self.canvas.delete("all")
        size = self.game.n
        self.cell_size = self.canvas_size // self.game.n

        # Draw grid
        for r in range(size):
            for c in range(size):
                x0, y0 = c*self.cell_size, r*self.cell_size
                x1, y1 = x0+self.cell_size, y0+self.cell_size
                self.canvas.create_rectangle(x0, y0, x1, y1)

        # Draw pieces
        for turn, pieces in enumerate(self.game.pieces):
            margin = self.cell_size // 6
            color = "blue" if turn == 0 else "red"
            for idx in pieces:
                row, col = idx // size, idx % size
                x0 = col*self.cell_size+margin
                y0 = row*self.cell_size+margin
                x1 = x0+self.cell_size-margin*2
                y1 = y0+self.cell_size-margin*2
                if self.selected_piece == idx:
                    outline = "yellow"
                else:
                    outline = "white" if self.game.finished else "black"
                if turn == 0:
                    # ▶ (right-pointing triangle)
                    points = [
                        x0, y0,             # top-left
                        x0, y1,             # bottom-left
                        x1, (y0 + y1) / 2   # middle-right
                    ]
                else:
                    # ▲ (up-pointing triangle)
                    points = [
                        (x0 + x1) / 2, y0,  # middle-top
                        x0, y1,             # bottom-left
                        x1, y1              # bottom-right
                    ]
                self.canvas.create_polygon(
                    points, fill=color, outline=outline, width=2
                )

        # Update status
        self.update_status()

    def update_status(self):
        if self.initial:
            return
        if self.game.finished:
            if self.game.draw:
                text = "Draw"
            else:
                winner = self.game.win
                if self.game.level[0] == self.game.level[1] == 0:
                    text = "First player won" if winner == 0 else "Second player won"
                elif self.game.level[0] * self.game.level[1] > 0:
                    text = "First player won" if winner == 0 else "Second player won"
                else:
                    result = 'won' if self.game.level[winner] == 0 else 'lost'
                    cpu_turn = 0 if self.game.level[1] == 0 else 1
                    cpu_level = self.game.level[cpu_turn]
                    text = f"You {result} against CPU level {cpu_level}"
        else:
            color = ['Blue', 'Red'][self.game.turn]
            if self.game.level[self.game.turn] == 0:
                text = f"{color} (human) to move"
            else:
                text = f"{color} (computer) is thinking"

        self.status_label.config(text=text)
        self.master.update_idletasks()

    def on_click(self, event):
        size = self.game.n
        c, r = event.x // self.cell_size, event.y // self.cell_size
        clicked_pos = r*size + c
        turn = self.game.turn

        if self.game.level[turn] > 0 or self.game.finished:
            return

        if self.selected_piece is None:
            # If piece is not selected
            if clicked_pos in self.game.pieces[turn]:
                self.selected_piece = clicked_pos
                self.update_board()
            return
        else:
            avail = self.game.move_available(
                self.game.pieces, self.selected_piece, turn)
            if clicked_pos == self.selected_piece and -1 in avail:
                # Remove a piece
                self.game.pieces[turn].remove(self.selected_piece)
            elif clicked_pos in avail:
                # Normal move
                self.game.pieces[turn].remove(self.selected_piece)
                self.game.pieces[turn].append(clicked_pos)
            elif clicked_pos in self.game.pieces[turn]:
                # Reselect a piece
                self.selected_piece = clicked_pos
                self.update_board()
                return
            else:
                return

        # There was a move
        self.selected_piece = None
        key = self.game.make_key(self.game.pieces, turn)
        self.game.move_history.append(key)
        repetition = self.game.move_history.count(key)
        if self.game.is_finished():
            self.game.finished = True
        if repetition >= self.game.draw_repetition:
            self.game.finished = True
            self.game.draw = True
        self.update_board()
        if self.game.finished:
            self.game.show_result()
            return
        self.game.turn = 1 - turn
        self.game.show_move()
        if self.game.level[self.game.turn] > 0:
            self.update_status()
            self.after_id = self.master.after(20, self.do_step)
            self.after_id = None

    def do_step(self):
        if self.game.finished:
            return

        turn = self.game.turn
        if self.game.level[turn] > 0:
            self.game.set_level()
            self.game.play_comp()
            self.update_board()
            if self.game.finished:
                self.game.show_result()
                return
            self.game.show_move()
            self.game.turn = 1-turn
            if self.game.level[self.game.turn] > 0:
                self.update_status()
                self.after_id = self.master.after(200, self.do_step)
                self.after_id = None
