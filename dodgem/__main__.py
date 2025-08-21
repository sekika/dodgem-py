import argparse
import os
import sys
import json
from .dodgem import Dodgem, EVALMAP


def load_config():
    """Load config from ~/.dodgem or return defaults."""
    home = os.path.expanduser("~")
    cfg_file = os.path.join(home, ".dodgem")
    config = {
        "mongo_server": "mongodb://localhost:27017/",
        "evalmap_path": EVALMAP  # package default
    }
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r") as f:
                user_cfg = json.load(f)
            config.update(user_cfg)
        except Exception as e:
            print(f"Warning: failed to read config {cfg_file}: {e}")
    return config


def main():
    description = "Dodgem: play, analyze, and manage database/evalmap."
    config = load_config()

    parser = argparse.ArgumentParser(
        description=description
    )
    parser.add_argument('-c', '--create', action='store_true',
                        help='create MongoDB evaluation database')
    parser.add_argument('-e', '--evalmap', action='store_true',
                        help='create evalmap JSON.GZ from MongoDB')
    parser.add_argument('-l', '--level', type=int, default=3,
                        help='level for the first player (1-4)')
    parser.add_argument('-g', '--gote', type=int, default=None,
                        help='level for the second player (1-4)')
    parser.add_argument('-n', '--num', type=int,
                        default=4, help='board size (3-5)')
    parser.add_argument('-p', '--play', action='store_true', help='play games')
    parser.add_argument('-r', '--rep', type=int, default=10,
                        help='repetition count in play mode (default: 10)')
    parser.add_argument('-s', '--status', action='store_true',
                        help='show MongoDB status summary')
    parser.add_argument('-t', '--traverse', type=str, nargs='?', const='ini',
                        default=None, help='traverse MongoDB from key (default: ini)')
    parser.add_argument('-v', '--verbose', type=int,
                        default=1, help='verbose level (1-5)')
    parser.add_argument('--mongo-server', type=str,
                        default=config.get("mongo_server"), help='MongoDB server URI')
    parser.add_argument('--evalmap-path', type=str,
                        default=config.get("evalmap_path"), help='path to evalmap JSON.GZ')
    parser.add_argument('--gui', action='store_true', help='launch Tcl/Tk GUI')
    args = parser.parse_args()

    assert 3 <= args.num <= 5
    assert 0 <= args.level <= 4
    if args.gote:
        assert 0 <= args.gote <= 4
    else:
        args.gote = args.level
    assert 1 <= args.verbose <= 5

    if args.gui:
        from .gui import launch_gui
        launch_gui(args)
        return

    assert args.level * args.gote > 0
    d = Dodgem(args.num, evalmap=args.evalmap_path)
    d.mongo_server = args.mongo_server
    d.verbose = args.verbose

    if args.play:
        d.level = [args.level, args.gote]
        if d.level[0] != d.level[1]:
            d.refresh_evalmap = True
        d.play_games(args.rep)
        return
    if args.create:
        d.create_database()
        return
    if args.evalmap:
        d.create_evalmap()
        return
    if args.status:
        d.show_status()
        return
    if args.traverse is not None:
        d.traverse(args.traverse, [])
        return

    print(description)
    print('Run "dodgem -h" for a quick help.')
    print('Documentation: https://sekika.github.io/dodgem-py/')
    print('Play online: https://sekika.github.io/dodgem/')


if __name__ == "__main__":
    main()
