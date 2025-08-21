import copy
import csv
from datetime import datetime
import gzip
import json
from pymongo import MongoClient, errors
import random
import os
import sys

EVALMAP = os.path.join(os.path.dirname(__file__), "dodgem_eval.json.gz")
MAX_DEPTH = [20, 30, 50]
# min_depth, min_remain, max_side
EVAL3 = (10, 7, 5)  # 803 / 1963 positions
EVAL4 = (15, 12, 10)  # 113,065 / 393,900 positions
EVAL5 = (30, 15, 2)  # 879,830 / 164,308,067 positions


class Dodgem():
    def __init__(self, n=4, evalmap=EVALMAP):
        """Construct a Dodgem engine, load the evalmap, and initialize game state.

        Initializes core parameters (board size, depth bounds, repetition rule,
        evaluation constants, MongoDB configuration, display settings), loads
        the evalmap for the requested board size, and sets the initial position.

        Args:
            n (int, optional): Board size, one of 3, 4, or 5. Defaults to 4.
            evalmap (str, optional): Path to a gzipped JSON evalmap file.
                Defaults to the packaged EVALMAP path.

        Returns:
            None

        Raises:
            OSError: If the evalmap file cannot be opened/read.
            KeyError: If the evalmap does not contain data for the given board size.
        """
        self.n = n
        self.draw_repetition = 3  # Draw if the same position repeats this count
        self.max_depth = self.calc_max_depth(n)
        self.max_remain = n * (n-1) * 2
        self.eval_win = 100
        self.refresh_evalmap = False
        self.document_url = 'https://sekika.github.io/dodgem-py/'
        self.mongo_server = 'mongodb://localhost:27017/'
        self.db_name = 'dodgem_db'
        self.database_status = None
        self.warning_issued = []
        self.server_timeout_ms = 3000
        self.client = None
        self.verbose = 1
        self.chars = '▷▲'
        self.evalmap_path = evalmap
        self.load_evalmap()
        self.start()

    # Level definition

    def set_level(self):
        """Configure per-move search source and depth from the current player's level.

        This method consults self.level[turn] and the current game phase
        (move count and remain metric) to set:
        - self.use_mongo: whether to rely on MongoDB (Level 4) or in-memory search.
        - self.eval_map: in-memory memo/evalmap to use or refresh.
        - self.depth: the maximum search depth for this move.

        It may reload the evalmap when refresh_evalmap is True or for n=5.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If self.level[turn] is not in the supported range.
        """
        remain = self.remain(self.pieces)
        moves = len(self.move_history)
        match self.level[self.turn]:
            case 1:
                self.use_mongo = False
                self.eval_map = {}
                self.depth = random.randint(1, 7)
            case 2:
                self.use_mongo = False
                match self.n:
                    case 3:
                        self.eval_map = {}
                        self.depth = random.randint(6, 10)
                    case 4:
                        if moves < 8:
                            self.depth = 1
                            if self.refresh_evalmap:
                                self.load_evalmap()
                            return
                        self.eval_map = {}
                        if remain > 12:
                            self.depth = random.randint(6, 11)
                            return
                        self.depth = 30
                    case 5:
                        self.load_evalmap()
                        if moves < 10:
                            self.depth = 1
                        elif remain < 15:
                            self.depth = 10
                        else:
                            self.depth = 4
            case 3:
                self.use_mongo = False
                if self.refresh_evalmap or self.n == 5:
                    self.load_evalmap()
                match self.n:
                    case 3:
                        self.depth = 5
                    case 4:
                        if moves < 3:
                            self.depth = 1
                        if remain < 15:
                            self.depth = 40
                        else:
                            self.depth = random.randint(12, 18)
                    case 5:
                        if moves < 3:
                            self.depth = 1
                        elif remain < 15:
                            self.depth = 40
                        else:
                            self.depth = 13 - int(remain / 5)
            case 4:
                self.use_mongo = True
                self.depth = 1
            case _:
                raise Exception('Level not defined')

    # Playing games

    def play_games(self, repetition):
        """Play multiple games in a row and return the aggregate results.

        Starts/plays 'repetition' games back-to-back, optionally opening
        MongoDB for high verbosity or Level 4, and prints progress and a
        summary according to self.verbose.

        Args:
            repetition (int): Number of games to play.

        Returns:
            tuple[int, int, int]: (wins_by_first, wins_by_second, draws)

        Raises:
            SystemExit: If MongoDB is required and cannot be opened.
        """
        if max(self.level) == 4 or self.verbose > 3:
            self.open_mongodb()
        if self.verbose > 0:
            print(f'{self.n}x{self.n} board: start {repetition} games')
        sente = gote = draw = 0
        for i in range(repetition):
            self.start()
            self.play_game()
            if self.draw:
                draw += 1
            else:
                if self.win == 0:
                    sente += 1
                else:
                    gote += 1
            if self.verbose > 0:
                print(f'{i+1} plays: 1st player {sente} win {gote} loss {draw} draw')
        if self.verbose > 0:
            print(
                f'{self.n}x{self.n} L{self.level[0]}-L{self.level[1]} {i+1} plays: 1st player {sente} win {gote} loss {draw} draw')
        return (sente, gote, draw)

    def play_game(self):
        """Play a single game until termination, printing updates if verbose.

        Initializes per-game flags, loops moves until a win or draw is reached,
        and prints the final result at the end.

        Args:
            None

        Returns:
            None
        """
        self.finished = False
        self.draw = False
        self.win_determined = -1
        self.move_count = 0
        self.show_move()
        while not self.finished:
            self.set_level()
            self.play_comp()
            self.show_move()
        self.show_result()

    def show_move(self):
        """Print a move header and optional board state depending on verbosity.

        Increments the move counter, optionally prints database status and the
        current position, and shows any known early win/loss prediction.

        Args:
            None

        Returns:
            None
        """
        self.move_count += 1
        if self.move_count < 3:
            self.win_declared = False
        if self.win_determined < 0 or self.win_declared:
            eval = ''
        else:
            eval = f'({['First','Second'][self.win_determined]} player is winning) '
            self.win_declared = True
        if self.verbose > 3:
            print('move: ', end='')
            print(f'{self.make_key(self.pieces, self.turn)}')
        if self.verbose > 1:
            if len(self.move_history) < 2:
                if self.database_status:
                    status = f' ({self.database_status})'
                else:
                    status = ''
                print(
                    f'Dodgem {self.n}x{self.n} {self.chars[0]}{self.player_name(0)} {self.chars[1]}{self.player_name(1)}{status}')
            elif self.verbose < 4:
                print(f'{self.last_move(self.move_history)} {eval}', end='')
        if self.verbose > 2:
            print()
            self.show_position(self.pieces)
        if self.verbose > 1:
            print(f'{self.move_count}.', end='', flush=True)
        if self.verbose > 3:
            print()

    def player_name(self, turn):
        """Return a human-readable name for the given side based on level.

        Args:
            turn (int): 0 for First, 1 for Second.

        Returns:
            str: "Human" if level==0 for the side, otherwise "CPU L{level}".
        """
        if self.level[turn] == 0:
            return 'Human'
        else:
            return f'CPU L{self.level[turn]}'

    def show_result(self):
        """Print the outcome of the game according to verbosity.

        Prints "Draw" or announces the winning side. Does not return a value.

        Args:
            None

        Returns:
            None
        """
        if self.verbose > 1:
            if self.draw:
                print('Draw')
            else:
                print(
                    f'{["First","Second"][self.win]} player wins')

    def last_move(self, moves):
        """Derive a human-readable last move from two adjacent position keys.

        Given a list of at least two canonical position keys (before and after),
        detect the moved or removed piece and format as "from-to" or "from-X"
        (X indicates the piece exited the board).

        Args:
            moves (list[str]): A history list of canonical position keys
                (JSON strings). The last two entries are used.

        Returns:
            str: A move string such as "5-6" or "3-X".
        """
        prev = json.loads(moves[-2])
        current = json.loads(moves[-1])
        if prev[0] == current[0]:
            prev_pos = prev[1]
            current_pos = current[1]
        else:
            prev_pos = prev[0]
            current_pos = current[0]
        if len(prev_pos) > len(current_pos):
            for i in prev_pos:
                if i not in current_pos:
                    return f'{i}-X'
        for i in prev_pos:
            if i not in current_pos:
                move_from = i
        for i in current_pos:
            if i not in prev_pos:
                move_to = i
        return f'{move_from}-{move_to}'

    # Main thinking functions

    def play_comp(self):
        """Select and play a move for the side to move using search and eval data.

        Enumerates all legal next positions, evaluates them using a blend of
        depth-limited search, the in-memory evalmap, and (optionally) MongoDB,
        applies repetition/draw handling, and updates the game state.

        Side effects:
        - Updates self.pieces, self.turn, self.move_history.
        - Sets self.finished/draw when repetition threshold is reached.
        - Sets self.win_determined if a forced win/loss is found.

        Args:
            None

        Returns:
            None
        """
        pos = self.next_positions(self.pieces, self.turn)
        min_eval = self.eval_win + 2
        p = []

        # Evaluate all the possible moves
        for i in range(len(pos)):
            e = self.evaluate(pos[i], 1 - self.turn, self.depth)
            key = self.make_key(pos[i], 1 - self.turn)
            if self.depth == 1 and abs(e) < self.eval_win:
                e = self.remain(pos[i])
            if self.verbose > 3:
                result = self.collection.find_one({"_id": key})
                if result and "value" in result:
                    eval = f'{result["value"]}'
                else:
                    eval = 'none'
                if key in self.eval_map:
                    evalmap = self.eval_map[key][0]
                else:
                    evalmap = 'none'
                print(
                    f'candidate: {key} = {e} DB {eval} evalmap {evalmap}')
            if e < min_eval:
                p = [pos[i]]
                min_eval = e
            elif e == min_eval:
                p.append(pos[i])

        # Select move that is not in the history. If not available, judge it as draw.
        p_diff = [pos for pos in p if self.make_key(
            pos, self.turn) not in self.move_history]

        if len(p_diff) < len(pos):
            if len(p_diff) == 0:
                count = {}
                for pos in p:
                    c = self.move_history.count(self.make_key(pos, self.turn))
                    if c not in count:
                        count[c] = []
                    count[c].append(pos)
                min_count = min(count.keys())
                p = count[min_count]
                if min_count >= self.draw_repetition - 1:
                    self.finished = True
                    self.draw = True
            else:
                p = p_diff

        # Win determined
        if min_eval <= -self.eval_win:
            self.win_determined = self.turn

        # Lost determined
        if min_eval >= self.eval_win:
            self.win_determined = 1 - self.turn
            p = self.min_remain(p)

        if self.verbose > 4:
            print(f'p = {p}\np_diff = {p_diff}')

        self.pieces = random.choice(p)
        self.move_history.append(self.make_key(self.pieces, self.turn))

        if self.is_finished():
            self.finished = True

        self.turn = 1 - self.turn

    def evaluate(self, pieces, turn, depth):
        """Evaluate a position via depth-limited negamax with memoization and DB.

        Uses:
        - Terminal checks for empty side or no legal moves.
        - Depth-limited negamax; at leaf depth, uses a heuristic based on remain().
        - In-memory eval_map as a transposition table.
        - Optional MongoDB lookups when enabled.

        Args:
            pieces (list[list[int]]): Position as [list_of_first, list_of_second].
            turn (int): Side to move, 0 for First, 1 for Second.
            depth (int): Remaining search depth. At 0, heuristic evaluation is used.

        Returns:
            int: Evaluation in negamax convention from the current side's perspective.
                 Values ≥ +eval_win indicate a forced win; ≤ -eval_win indicate a forced loss;
                 0 can indicate forced draw.

        Raises:
            None
        """
        key = self.make_key(pieces, turn)
        if self.use_mongo:
            result = self.collection.find_one({"_id": key})
            if result and 'value' in result:
                return result["value"]

        if key in self.eval_map and self.eval_map[key][1] >= depth:
            return self.eval_map[key][0]

        if len(pieces[turn]) == 0:
            return self.eval_win
        if len(pieces[1 - turn]) == 0:
            return -self.eval_win
        pos = self.next_positions(pieces, turn)
        if len(pos) == 0:
            return self.eval_win + 1

        if depth < 1:
            remain = 0
            for piece in pieces[1]:
                remain -= 1 + piece // self.n
                if (piece - self.n) in pieces[0]:
                    remain -= 1
            for piece in pieces[0]:
                remain += self.n - (piece % self.n)
                if (piece % self.n < self.n - 1) and ((piece + 1) in pieces[1]):
                    remain += 1
            return 1 - 2 * remain if turn == 0 else 1 + 2 * remain

        min_eval = self.eval_win + 1
        for p in pos:
            key = self.make_key(p, 1 - turn)

            if key in self.eval_map and self.eval_map[key][1] >= depth - 1:
                e = self.eval_map[key][0]
            else:
                e = self.evaluate(p, 1 - turn, depth - 1)
                self.eval_map[key] = [e, depth - 1]

            if e <= -self.eval_win:
                return -e
            min_eval = min(min_eval, e)

        return -min_eval

    # Evalmap

    def load_evalmap(self):
        """Load the evalmap from a gzipped JSON file and select the current board size.

        Loads the entire evalmap file, then assigns the dictionary for the
        current self.n to self.eval_map.

        Args:
            None

        Returns:
            None

        Raises:
            OSError: If the file cannot be opened/read.
            KeyError: If the evalmap lacks an entry for self.n.
        """
        with gzip.open(self.evalmap_path, 'rt', encoding='utf-8') as f:
            self.eval_map = json.load(f)[str(self.n)]

    def create_evalmap(self):
        """Build an evalmap from MongoDB and write it as gzipped JSON.

        Connects to MongoDB, selects subsets for n=3..5 using predefined
        thresholds (EVAL3/EVAL4/EVAL5), merges them into a single dictionary,
        and writes to self.evalmap_path as gzip-compressed JSON.

        Args:
            None

        Returns:
            None

        Raises:
            SystemExit: If MongoDB cannot be connected.
            OSError: If writing the evalmap fails.
        """
        self.connect_mongodb()
        self.db = self.client[self.db_name]
        self.eval_map = {}
        self.eval_map['3'] = self.select_evalmap(3, *EVAL3)
        self.eval_map['4'] = self.select_evalmap(4, *EVAL4)
        self.eval_map['5'] = self.select_evalmap(5, *EVAL5)
        if self.verbose > 0:
            print(
                f'3: {len(self.eval_map["3"])} 4: {len(self.eval_map["4"])} 5: {len(self.eval_map["5"])}')
        with gzip.open(self.evalmap_path, 'wt') as f:
            json.dump(self.eval_map, f, separators=(",", ":"))

    def select_evalmap(self, n, min_depth, min_remain, max_side):
        """Select evalmap entries from MongoDB using filter thresholds.

        Applies depth, remain, and a frontier constraint (depth - remain)
        and returns a mapping of canonical keys to [value, depth]. For n=3,
        known forced-draw positions are also added with maximal depth to
        protect them from being overwritten.

        Args:
            n (int): Board size to export.
            min_depth (int): Minimum search depth to include.
            min_remain (int): Minimum remain threshold to include.
            max_side (int): Frontier offset used to constrain depth - remain.

        Returns:
            dict[str, list[int, int]]: Mapping key -> [value, depth].
                Keys are canonical position JSON strings.

        Raises:
            None
        """
        if not f"eval_{self.n}" in self.db.list_collection_names():
            return {}
        self.collection = self.db[f"eval_{n}"]
        diff = self.calc_max_depth(n) - n * (n-1) * 2 - max_side
        query = {
            "depth": {"$gte": min_depth},
            "remain": {"$gte": min_remain},
            "value": {"$ne": 0},
            "$expr": {"$gte": [{"$subtract": ["$depth", "$remain"]}, diff]}
        }
        projection = {"_id": 1, "value": 1, "depth": 1, "remain": 1}
        result = self.collection.find(query, projection)
        data_dict = {doc["_id"]: [doc["value"], doc["depth"]]
                     for doc in result}
        if n == 3:
            # See comment in resolve_draw()
            # Depth is set to the highest value to prevent overwriting
            for key in self.force_draw_positions():
                data_dict[key] = [0, self.calc_max_depth(3)]
        return data_dict
    
    # Functions on the database

    def show_status(self):
        """Print MongoDB database status and distribution summaries.

        Opens MongoDB, iterates over depth and remain buckets, and prints
        aggregate counts according to the current verbosity. At verbosity 4,
        outputs CSV rows of (depth, remain, count) to stdout.

        Args:
            None

        Returns:
            None

        Raises:
            SystemExit: If MongoDB cannot be opened or database is missing.
        """
        self.open_mongodb()

        count = 0

        if self.verbose == 4:
            csv_writer = csv.writer(sys.stdout)
            csv_writer.writerow(["depth", "remain", "count"])

        for depth in range(0, self.max_depth + 1):
            countd = 0
            for remain in range(1, self.max_remain + 1):
                try:
                    countr = len(self.get_keys_dr(depth, remain))
                    countd += countr
                except:
                    countr = 0

                if countr > 0:
                    if self.verbose == 3:
                        print(f'  depth {depth} remain {remain}: {countr}')
                    if self.verbose == 4:
                        csv_writer.writerow([depth, remain, countr])
            count += countd
            if self.verbose > 1 and countd > 0 and self.verbose != 4:
                print(f'depth {depth}: {countd} positions')

        if self.verbose != 4:
            print(f'{count} positions in n={self.n}')

    def traverse(self, key, history):
        """Interactively traverse the move tree starting from a given key.

        Prints the current node, shows child moves with MongoDB/evalmap info,
        and accepts user input to navigate deeper or back. If key == "ini",
        starts from the initial position.

        Args:
            key (str): Canonical position key "[[...],[...],turn]" or "ini".
            history (list[str]): A traversal history list; the current key is appended.

        Returns:
            None

        Raises:
            SystemExit: If the user enters an empty line to quit.
        """
        self.open_mongodb()
        self.load_evalmap()
        if key == 'ini':
            self.start()
            p = self.pieces
            turn = self.turn
            key = self.make_key(p, turn)
        history.append(key)
        while True:
            j = json.loads(key)
            p = [j[0], j[1]]
            turn = j[2]
            result = self.collection.find_one({"_id": key})
            print(f'{['First', 'Second'][turn]} to move: {key} {self.show_mongo_eval(result, turn)}')
            self.show_position(p)
            pos = self.next_positions(p, turn)
            num = 1
            for p in pos:
                key2 = self.make_key(p, 1-turn)
                result2 = self.collection.find_one({"_id": key2})
                move = self.last_move([key, key2])
                print(
                    f'({num}) {move} {key2} {self.show_mongo_eval(result2, 1-turn)} {self.show_evalmap(self.eval_map, key2)}')
                num += 1
            print('(0) Back')
            i = len(pos) + 1
            while i > len(pos):
                i = input('> ')
                if i == '':
                    sys.exit()
                i = int(i)
                if i == 0:
                    return
            key2 = self.make_key(pos[i-1], 1-turn)
            self.traverse(key2, copy.deepcopy(history))

    def show_eval(self, pieces, turn):
        """Print the MongoDB evaluation of a given position if present.

        Args:
            pieces (list[list[int]]): Position as [first_list, second_list].
            turn (int): Side to move, 0 (First) or 1 (Second).

        Returns:
            None
        """
        key = self.make_key(pieces, turn)
        result = self.collection.find_one({"_id": key})
        if result:
            print(
                f'Eval: {pieces} {["First","Second"][turn]} eval = {result["value"]} depth = {result["depth"]}')
        else:
            print(f'Eval: {pieces} {["First","Second"][turn]} not found')

    def show_mongo_eval(self, result, turn):
        """Format a MongoDB record into a human-readable evaluation string.

        Args:
            result (dict|None): MongoDB document for the position, or None.
            turn (int): Side to move, 0 (First) or 1 (Second).

        Returns:
            str: A summary string indicating value and who is winning/draw,
                 or 'No data' / 'No eval' when appropriate.
        """
        if result:
            if 'value' in result:
                x = result['value'] * (0.5 - turn)
                match x:
                    case 0:
                        return '0 (Draw)'
                    case  _ if x > 0:
                        return f'MongoDB: {result["value"]} (First wins)'
                    case _:
                        return f'MongoDB: {result["value"]} (Second wins)'
            else:
                return 'No eval'
        else:
            return f'No data'

    def show_evalmap(self, evalmap, key):
        """Return a compact string showing the evalmap entry for a key.

        Args:
            evalmap (dict): The in-memory evalmap dictionary for self.n.
            key (str): Canonical position key.

        Returns:
            str: "evalmap: {value}" if present, otherwise an empty string.
        """
        if key in evalmap:
            return f'evalmap: {evalmap[key][0]}'
        else:
            return ''

    def open_mongodb(self):
        """Open MongoDB client and set collection handles for the current board size.

        Ensures that:
        - self.client is connected (connect_mongodb if needed).
        - self.db and per-size collections (eval_n, depth_n) exist.
        - database_status is updated if the initial position is missing.

        Args:
            None

        Returns:
            None

        Raises:
            SystemExit: If MongoDB is not reachable or the DB/collections are missing.
        """
        if self.client is None:
            self.connect_mongodb()
        if self.db_name in self.client.list_database_names():
            self.db = self.client[self.db_name]
        else:
            print("Evaluation database of MongoDB does not exist.")
            self.no_database_error()
        if f"depth_{self.n}" in self.db.list_collection_names():
            self.collection_depth = self.db[f"depth_{self.n}"]
        else:
            print(f"Evaluation database for n={self.n} does not exist.")
            self.no_database_error()
        self.collection = self.db[f"eval_{self.n}"]
        # Check if the database has initial position
        self.start()
        key = self.make_key(self.pieces, self.turn)
        if self.collection.find_one({"_id": key}) is None:
            if self.n not in self.warning_issued:
                print(
                    f'Warning: Evaluation database for n={self.n} is not complete.')
                self.warning_issued.append(self.n)
            self.database_status = 'Partial database'
        else:
            self.database_status = None

    def no_database_error(self):
        """Print guidance for creating the database and exit the program.

        Args:
            None

        Returns:
            NoReturn
        """
        print(f"Create database by running: dodgem -c -n {self.n}")
        print(f"For more information, see {self.document_url}database.html'")
        sys.exit(1)

    def connect_mongodb(self):
        """Connect to the MongoDB server and verify connectivity with ping.

        Uses self.mongo_server and self.server_timeout_ms for connection
        settings and stores the client in self.client.

        Args:
            None

        Returns:
            None

        Raises:
            SystemExit: If connection fails or ping fails.
        """
        try:
            self.client = MongoClient(
                self.mongo_server, serverSelectionTimeoutMS=self.server_timeout_ms)
            self.client.admin.command("ping")
        except errors.ConnectionFailure as e:
            print(f"MongoDB connection failed: {e}")
            print(
                f'For more information, see {self.document_url}database.html')
            sys.exit(1)

    def create_database(self):
        """Create and fill the evaluation database by increasing remain/depth buckets.

        Pipeline:
        1) Initialize the depth/remain buckets via create_depth_database().
        2) For remain = 1..max_remain:
           - Evaluate all positions per depth with evaluate_remain_depth().
           - Accumulate undetermined nodes and re-search them with
             increasing depth limits (evaluate_simple).
           - Store forced wins/losses as ±eval_win and forced draws as 0.
           - Update roll-up stats under documents with _id 'r{remain}'.
        3) Apply resolve_draw() to mark special 3x3 repetitions as draws.

        Args:
            None

        Returns:
            None

        Raises:
            SystemExit: If MongoDB cannot be opened or is unavailable.
        """
        self.evaluate_start = datetime.now()
        if self.verbose > 0:
            print(f'n={self.n} computation start {self.evaluate_start}', flush=True)
        self.create_depth_database(self.init_pos(self.n), 0)
        for remain in range(1, self.max_remain + 1):
            p = self.collection.find_one({"_id": f'r{remain}'})
            if p and 'positions' in p and 'win' in p:
                self.total_p = p['positions']
                self.total_win = p['win']
                forced_draw = ''
            else:
                self.total_win = 0
                self.total_p = 0
                self.not_determined = set()
                for depth in range(self.max_depth + 1):
                    self.evaluate_remain_depth(remain, depth)
                if len(self.not_determined) < 5000:
                    search_depth = (2, 2, 2, 3, 3, 3, 5, 5, 7, 9)
                elif len(self.not_determined) < 10000:
                    search_depth = (2, 2, 2, 3, 3, 3, 5, 5, 7)
                elif len(self.not_determined) < 100000:
                    search_depth = (2, 2, 2, 3, 3, 3, 5, 5)
                elif len(self.not_determined) < 500000:
                    search_depth = (2, 2, 3, 3, 3, 4, 4)
                elif len(self.not_determined) < 700000:
                    search_depth = (2, 2, 3, 3, 3, 4)
                else:
                    search_depth = (2, 2, 3)
                for depth in search_depth:
                    if self.verbose > 1 and len(self.not_determined) > 0:
                        print(
                            f'{datetime.now().strftime("%m-%d %H:%M:%S")} remain {remain} undetermined {len(self.not_determined)} re-search depth = {depth}           ', flush=True)
                    for p in tuple(self.not_determined):
                        a, b, turn = json.loads(p)
                        e = self.evaluate_simple([a, b], turn, depth, [])
                        if e != -1:
                            self.not_determined.remove(p)
                            result = self.collection.find_one({"_id": p})
                            remain = self.remain([a, b])
                            self.collection.update_one(
                                {"_id": p},
                                {"$set": {"value": e,
                                          "depth": result['depth'], "remain": remain}},
                                upsert=True
                            )
                            if abs(e) >= self.eval_win:
                                self.total_win += 1
                for p in self.not_determined:
                    result = self.collection.find_one({"_id": p})
                    self.collection.update_one(
                        {"_id": p},
                        {"$set": {"value": 0,
                                  "depth": result['depth'], "remain": remain}},
                        upsert=True
                    )
                self.collection.update_one(
                    {"_id": f'r{remain}'},
                    {"$set": {"positions": self.total_p, "win": self.total_win}},
                    upsert=True
                )
                forced_draw = f' forced draws {len(self.not_determined)}'
            if self.verbose > 1:
                print(
                    f'{datetime.now().strftime("%m-%d %H:%M:%S")} remain {remain} positions {self.total_p} forced win {self.total_win}{forced_draw}', flush=True)
        self.resolve_draw()
        end = datetime.now()
        if self.verbose > 0:
            print(
                f'n={self.n} computation finished {end} elapsed: {end - self.evaluate_start}')

    def resolve_draw(self):
        """Mark specific 3x3 positions as draws to avoid repetition in perfect play.

        Purpose:
            On a 3x3 board, even with complete analysis data, short cycles
            with threefold repetition can arise. To avoid these artificial
            draws during DB-backed play, certain positions are explicitly
            rewritten to draw (value = 0).

        Called from:
            create_database()

        Args:
            None

        Returns:
            None
        """
        for p in self.force_draw_positions():
            self.rewrite_database(3, p, 0)
    
    def force_draw_positions(self):
        """Return canonical keys that should be treated as draws on 3x3.

        These positions are enforced as draws to break repetition cycles.
        See resolve_draw() for details.

        Args:
            None

        Returns:
            list[str]: Canonical position keys to be recorded as draws.
        """
        return ['[[3,8],[4,6],1]', '[[2,3],[4,6],1]', '[[2,3],[4,8],1]']

    def rewrite_database(self, n, key, value):
        """Rewrite a specific position document in MongoDB with a new value.

        If the current engine board size does not match n, do nothing.

        Args:
            n (int): Board size for which the rewrite applies.
            key (str): Canonical position key to update.
            value (int): New evaluation value (e.g., 0 for draw).

        Returns:
            None
        """
        if self.n != n:
            return
        result = self.collection.find_one({"_id": key})
        self.collection.update_one(
            {"_id": key},
            {"$set": {"value": value,
                      "depth": result['depth'], "remain": result['remain']}},
            upsert=True
        )

    def create_depth_database(self, pieces, turn):
        """Build depth/remain index buckets in MongoDB for candidate positions.

        Seeds the top-level depth bucket with the initial position, then walks
        backward in depth, generating candidate positions adjacent to the prior
        depth, and stores them grouped by remain. For large buckets, splits them
        into subdocuments to avoid the MongoDB document size limit.

        Args:
            pieces (list[list[int]]): Initial position [first_list, second_list].
            turn (int): Initial side to move (0 or 1).

        Returns:
            None
        """
        key = self.make_key(pieces, turn)
        self.open_mongodb()
        depth = self.max_depth
        remain = self.remain(self.pieces)
        self.collection_depth.update_one(
            {"_id": f'd{depth}r{remain}'},
            {"$set": {"key": [key,]}},
            upsert=True
        )
        total = 0
        for depth in range(self.max_depth - 1, -1, -1):
            p = self.collection_depth.find_one(
                {"_id": f'd{depth}r{self.max_remain}'})
            if not p:
                pos = set()  # Candidate positions = next to previous positions
                prev_positions = self.get_keys(depth + 1)
                for pp in prev_positions:
                    a, b, turn = json.loads(pp)
                    if len(a) > 0 and len(b) > 0:
                        for next in self.next_positions([a, b], turn):
                            pos.add(self.make_key(next, 1 - turn))
                n = {}
                for remain in range(1, self.max_remain + 1):
                    n[remain] = []
                for p in pos:
                    result = self.collection.find_one({"_id": p})
                    if result:
                        if result['depth'] > depth:
                            if self.verbose > 3:
                                print(
                                    f'Skip {p} depth {depth} in database {result["depth"]}')
                        elif result['depth'] < depth:
                            if self.verbose > 3:
                                print(
                                    f'Update {p} depth {depth} in database {result["depth"]}')
                            if result['value']:
                                self.collection.update_one(
                                    {"_id": result['_id']},
                                    {"$set": {
                                        "value": result['value'], "depth": depth, "remain": result['remain']}},
                                    upsert=True
                                )
                            else:
                                self.collection.update_one(
                                    {"_id": result['_id']},
                                    {"$set": {
                                        "depth": depth, "remain": result['remain']}},
                                    upsert=True
                                )
                            n[result['remain']].append(p)
                        else:
                            a, b, turn = json.loads(p)
                            remain = self.remain([a, b])
                            n[remain].append(p)
                    else:
                        if self.verbose > 3:
                            print(f'{p} not found')
                        a, b, turn = json.loads(p)
                        remain = self.remain([a, b])
                        self.collection.update_one(
                            {"_id": p},
                            {"$set": {"depth": depth, "remain": remain}},
                            upsert=True
                        )
                        n[remain].append(p)
                batch_size = 300000
                for remain in range(1, self.max_remain + 1):
                    if len(n[remain]) < batch_size:
                        self.collection_depth.update_one(
                            {"_id": f'd{depth}r{remain}'},
                            {"$set": {"key": n[remain]}},
                            upsert=True
                        )
                    else:
                        self.collection_depth.update_one(
                            {"_id": f'd{depth}r{remain}'},
                            {"$set": {"large": 1}},
                            upsert=True
                        )
                        for i in range(0, len(n[remain]), batch_size):
                            sublist = n[remain][i:i + batch_size]
                            index = i // batch_size
                            self.collection_depth.update_one(
                                {"_id": f'd{depth}r{remain}i{index}'},
                                {"$set": {"dr": f'd{depth}r{remain}',
                                          "index": index,
                                          "key": sublist}},
                                upsert=True
                            )
            p = self.collection_depth.find_one(f'd{depth}')
            if p and 'positions' in p:
                sum = p['positions']
            else:
                sum = 0
                for remain in range(1, self.max_remain + 1):
                    keys = self.get_keys_dr(depth, remain)
                    if self.verbose > 2:
                        print(
                            f'depth {depth} remain {remain} keys {len(keys)}')
                    sum += len(keys)
                self.collection_depth.update_one(
                    {"_id": f'd{depth}'},
                    {"$set": {"positions": sum}},
                    upsert=True
                )
            if self.verbose > 1:
                print(
                    f'{datetime.now().strftime("%m-%d %H:%M:%S")} depth {depth} {sum} positions', flush=True)
            total += sum
        if self.verbose > 0:
            print(
                f'{datetime.now().strftime("%m-%d %H:%M:%S")} n={self.n} Depth DB build complete positions {total}', flush=True)

    def get_keys(self, depth):
        """Return all canonical keys at a given depth across every remain.

        Args:
            depth (int): Depth bucket.

        Returns:
            list[str]: A list of canonical position keys at that depth.
        """
        keys = []
        for remain in range(1, self.max_remain + 1):
            keys.extend(self.get_keys_dr(depth, remain))
        return keys

    def get_keys_dr(self, depth, remain):
        """Return keys for a specific depth/remain bucket from MongoDB.

        For large buckets, concatenates keys from sharded subdocuments.

        Args:
            depth (int): Depth bucket.
            remain (int): Remain bucket.

        Returns:
            list[str]: A list of canonical position keys for the bucket.
        """
        keys = []
        p = self.collection_depth.find_one(
            {"_id": f'd{depth}r{remain}'})
        if p:
            if 'large' in p:
                query = {"dr": f'd{depth}r{remain}'}
                projection = {"_id": 1}
                cursor = self.collection_depth.find(query, projection)
                for id in [doc["_id"] for doc in cursor]:
                    p = self.collection_depth.find_one(
                        {"_id": id})
                    keys.extend(p['key'])
            else:
                keys.extend(p['key'])
        return keys

    def evaluate_remain_depth(self, remain, depth, same_remain_depth=2):
        """Evaluate all positions in a remain/depth bucket, with quick local recursion.

        For each key in the given bucket, attempts a shallow fixed-depth search
        (evaluate_simple). If undetermined, records the position for later
        re-search; otherwise, writes the evaluation to MongoDB and updates stats.

        Args:
            remain (int): Remain bucket to process.
            depth (int): Depth bucket to process.
            same_remain_depth (int, optional): Depth used for the initial quick
                recursion within the same remain layer. Defaults to 2.

        Returns:
            None
        """
        pos = self.get_keys_dr(depth, remain)
        win = 0
        num = 0
        for p in pos:
            num += 1
            if self.verbose > 2 and num % 1000 == 0:
                print(
                    f'remain {remain} depth {depth} computing {num} / {len(pos)}               \r', end='')
            result = self.collection.find_one({"_id": p})
            if not result or 'value' not in result:
                a, b, turn = json.loads(p)
                e = self.evaluate_simple(
                    [a, b], turn, same_remain_depth, [])
                if e == -1:
                    self.collection.update_one(
                        {"_id": p},
                        {"$set": {"depth": depth, "remain": remain}},
                        upsert=True
                    )
                    self.not_determined.add(p)
                else:
                    remain = self.remain([a, b])
                    self.collection.update_one(
                        {"_id": p},
                        {"$set": {"value": e, "depth": depth, "remain": remain}},
                        upsert=True
                    )
                    if abs(e) >= self.eval_win:
                        win += 1
                    else:
                        if self.verbose > 3:
                            self.show_eval([a, b], turn)
                            self.show_position([a, b])
            else:
                if abs(result['value']) >= self.eval_win:
                    win += 1
        if self.verbose > 2 and len(pos) > 0:
            print(
                f'remain {remain} depth {depth} positions {len(pos)} forced win {win}      \r', end='')
        self.total_win += win
        self.total_p += len(pos)

    def evaluate_simple(self, pieces, turn, depth, history):
        """Evaluate a position with a shallow recursion and cycle detection.

        This simplified evaluator:
        - Returns 0 for repetitions found in the current recursion path.
        - Returns -1 if not determined within the given depth limit.
        - Uses terminal checks and negamax-style propagation otherwise.

        Args:
            pieces (list[list[int]]): Position as [first_list, second_list].
            turn (int): Side to move (0 or 1).
            depth (int): Remaining depth to explore; negative means "undetermined".
            history (list[str]): Path of visited keys for repetition detection.

        Returns:
            int: One of:
                 - self.eval_win or greater: forced win for side to move.
                 - -self.eval_win or less: forced loss for side to move.
                 - self.eval_win + 1: opponent has no moves (special terminal).
                 - 0: repetition detected (treated as draw).
                 - -1: not determined within remaining depth; needs deeper search.
        """
        key_org = self.make_key(pieces, turn)
        if key_org in history:
            return 0
        if depth < 0:
            return -1  # Not determined
        history.append(key_org)
        if len(pieces[turn]) == 0:
            return self.eval_win
        if len(pieces[1 - turn]) == 0:
            return -self.eval_win

        pos = self.next_positions(pieces, turn)
        if len(pos) == 0:
            return self.eval_win + 1

        min_eval = self.eval_win + 2
        for p in pos:
            key = self.make_key(p, 1 - turn)
            result = self.collection.find_one({"_id": key})

            if result and 'value' in result:
                e = result["value"]
            else:
                e = self.evaluate_simple(
                    p, 1 - turn, depth - 1, copy.deepcopy(history))
            if e < min_eval:
                min_eval = e
        if min_eval == -1:
            return -1
        return -min_eval

    # Basic calculation functions

    def remain(self, pieces):
        """Compute the 'remain' heuristic for both sides combined.

        The measure estimates distance to exit for the Second's pieces (row
        distance to top) and for the First's pieces (column distance to right).

        Args:
            pieces (list[list[int]]): Position as [first_list, second_list].

        Returns:
            int: The combined remain score (non-increasing along actual play).
        """
        remain = 0

        for value in pieces[1]:
            remain += 1 + value // self.n

        for value in pieces[0]:
            remain += self.n - (value % self.n)

        return remain

    def next_positions(self, pieces, turn):
        """Generate all legal successor positions for the side to move.

        For each movable piece of the given side, enumerates legal targets
        including exits (denoted by -1), and produces the resulting positions.

        Args:
            pieces (list[list[int]]): Current position as [first_list, second_list].
            turn (int): Side to move, 0 (First) or 1 (Second).

        Returns:
            list[list[list[int]]]: A list of successor positions, each in
                the same format [first_list, second_list].
        """
        pos = []
        for piece in pieces[turn]:
            moves = self.move_available(pieces, piece, turn)
            for m in moves:
                if m < 0:
                    pos.append([
                        [item for item in sub_array if item != piece]
                        for sub_array in pieces
                    ])
                else:
                    pos.append([
                        [m if item == piece else item for item in sub_array]
                        for sub_array in pieces
                    ])
        return pos

    def move_available(self, pieces, i, turn):
        """Return legal target squares for a given piece and side.

        For exits, the move is represented as -1. Otherwise, targets are
        board indices that are empty.

        Args:
            pieces (list[list[int]]): Current position [first_list, second_list].
            i (int): The current square index of the piece.
            turn (int): Side to move, 0 (First) or 1 (Second).

        Returns:
            list[int]: List of target squares (or -1 for exit).
        """
        place = []

        if turn == 1:
            if i < self.n:
                place.append(-1)
            elif self.is_empty(pieces, i - self.n):
                place.append(i - self.n)

            if i % self.n > 0 and self.is_empty(pieces, i - 1):
                place.append(i - 1)

            if i % self.n < self.n - 1 and self.is_empty(pieces, i + 1):
                place.append(i + 1)

            return place

        if i % self.n == self.n - 1:
            place.append(-1)
        elif self.is_empty(pieces, i + 1):
            place.append(i + 1)

        if i >= self.n and self.is_empty(pieces, i - self.n):
            place.append(i - self.n)

        if i < self.n * (self.n - 1) and self.is_empty(pieces, i + self.n):
            place.append(i + self.n)

        return place

    def is_empty(self, pieces, i):
        """Check if a board square is empty.

        Args:
            pieces (list[list[int]]): Position [first_list, second_list].
            i (int): Board index to test.

        Returns:
            bool: True if no piece occupies index i, False otherwise.
        """
        return i not in pieces[0] and i not in pieces[1]

    def make_key(self, pos, turn):
        """Create a canonical JSON key for a position and side to move.

        The key has sorted piece lists, no spaces, and includes the turn.

        Args:
            pos (list[list[int]]): Position as [first_list, second_list].
            turn (int): Side to move, 0 or 1.

        Returns:
            str: Canonical JSON string "[[...],[...],turn]".
        """
        return json.dumps([sorted(pos[0]), sorted(pos[1]), turn]).replace(' ', '')

    def is_finished(self):
        """Check whether the game has finished and set the winner accordingly.

        Termination rules:
        - If one side has no pieces, the opponent wins.
        - If the opponent has no legal moves, the current player loses.

        Side effects:
        - Sets self.win to 0 (First) or 1 (Second) when finished.

        Args:
            None

        Returns:
            bool: True if finished (win condition reached), False otherwise.
        """
        if len(self.pieces[0]) == 0:
            self.win = 0
            return True
        if len(self.pieces[1]) == 0:
            self.win = 1
            return True

        # When opponent cannot move, you lose
        for piece in self.pieces[1 - self.turn]:
            if len(self.move_available(self.pieces, piece, 1 - self.turn)) > 0:
                return False

        self.win = 1 - self.turn
        return True

    def min_remain(self, pos):
        """Filter positions to those with the minimal remain() value.

        Args:
            pos (list[list[list[int]]]): Candidate positions.

        Returns:
            list[list[list[int]]]: Subset of positions with minimal remain score.
        """
        remain_values = [self.remain(item) for item in pos]
        min_value = min(remain_values)
        return [item for item, value in zip(pos, remain_values) if value == min_value]

    def show_position(self, pos):
        """Render the board to stdout using box characters.

        Uses self.chars for the two sides. Intended for debugging or verbose
        output paths.

        Args:
            pos (list[list[int]]): Position as [first_list, second_list].

        Returns:
            None
        """
        hor = '・' + '━・' * self.n
        print(hor)
        for i in range(self.n):
            print('┃', end='')
            for j in range(self.n):
                k = i * self.n + j
                if k in pos[0]:
                    print(self.chars[0], end='')
                elif k in pos[1]:
                    print(self.chars[1], end='')
                else:
                    print('　', end='')
                print('┃', end='')
            print()
            print(hor)

    def start(self):
        """Reset the engine to the initial position and set the first player to move.

        Also initializes the move history with the initial key.

        Args:
            None

        Returns:
            None
        """
        self.pieces = self.init_pos(self.n)
        self.turn = 0
        self.move_history = [self.make_key(self.pieces, self.turn)]

    def init_pos(self, n):
        """Return the initial piece lists for a given board size.

        First's pieces start on the leftmost column (except top-left),
        and Second's pieces on the bottom row (except bottom-left).

        Args:
            n (int): Board size (3, 4, or 5).

        Returns:
            list[list[int]]: [first_list, second_list] initial positions.
        """
        piece = []
        piece2 = []
        for i in range(n - 1):
            piece.append(n * i)
            piece2.append(n * (n - 1) + 1 + i)
        return [piece, piece2]

    def calc_max_depth(self, n):
        """Return the configured maximum search depth for the given board size.

        The depth values are defined by the MAX_DEPTH constant and indexed by (n-3).

        Args:
            n (int): Board size (3, 4, or 5).

        Returns:
            int: Maximum depth for that board size.
        """
        return MAX_DEPTH[n-3]
