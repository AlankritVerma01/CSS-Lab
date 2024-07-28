import os
import re
import json
import chess.pgn
from concurrent.futures import ProcessPoolExecutor, as_completed

def parse_pgn(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def extract_blunders(pgn_file):
    blunders = []

    with open(pgn_file) as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break

            headers = game.headers
            node = game
            move_number = 0

            while node.variations:
                next_node = node.variation(0)
                move_number += 1

                comment = next_node.comment
                eval_match = re.search(r'\[%eval (-?\d+\.\d+)\]', comment)
                eval_match_prev = re.search(r'\[%eval (-?\d+\.\d+)\]', node.comment)
                if eval_match and eval_match_prev:
                    eval_score = float(eval_match.group(1))
                    eval_score_prev = float(eval_match_prev.group(1))
                else:
                    eval_score = None
                    eval_score_prev = None

                if re.search(r'\b[Bb]lunder\b', comment):
                    before_blunder = node.board().fen()
                    after_blunder = next_node.board().fen()

                    better_move_match = re.search(r'Blunder\.\s*(.*?)\s*was best\.', comment)
                    if better_move_match:
                        better_move = better_move_match.group(1)
                    else:
                        better_move = None

                    eval_diff = None
                    if eval_score is not None and eval_score_prev is not None:
                        eval_diff = eval_score - eval_score_prev

                    blunder_info = {
                        "Event": headers.get("Event", "Unknown"),
                        "Site": headers.get("Site", "Unknown"),
                        "Date": headers.get("Date", "Unknown"),
                        "Round": headers.get("Round", "Unknown"),
                        "White Player": headers.get("White", "Unknown"),
                        "Black Player": headers.get("Black", "Unknown"),
                        "Result": headers.get("Result", "Unknown"),
                        "UTCDate": headers.get("UTCDate", "Unknown"),
                        "UTCTime": headers.get("UTCTime", "Unknown"),
                        "Variant": headers.get("Variant", "Standard"),
                        "ECO": headers.get("ECO", "Unknown"),
                        "Opening": headers.get("Opening", "Unknown"),
                        "Move Number": move_number,
                        "Player": headers.get("White", "Unknown") if move_number % 2 == 1 else headers.get("Black", "Unknown"),
                        "Color": "White" if move_number % 2 == 1 else "Black",
                        "Blunder Move": node.board().san(next_node.move),
                        "Better Move": better_move,
                        "Comment": comment,
                        "Evaluation Before": eval_score_prev,
                        "Evaluation After": eval_score,
                        "Evaluation Difference": eval_diff,
                        "Position Before Blunder": before_blunder,
                        "Position After Blunder": after_blunder,
                    }
                    blunders.append(blunder_info)

                node = next_node

    return blunders

def process_pgn_files_parallel(pgn_directory, num_workers=4):
    pgn_files = [os.path.join(pgn_directory, file) for file in os.listdir(pgn_directory) if file.endswith(".pgn")]
    all_blunders = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(extract_blunders, pgn_file): pgn_file for pgn_file in pgn_files}

        for future in as_completed(futures):
            pgn_file = futures[future]
            try:
                blunders = future.result()
                all_blunders.extend(blunders)
            except Exception as e:
                print(f"Error processing {pgn_file}: {e}")

    return all_blunders

def save_to_json(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    pgn_directory_path = "analysis_pgns"
    json_output_path = "blunders.json"

    all_blunders = process_pgn_files_parallel(pgn_directory_path)
    save_to_json(all_blunders, json_output_path)
    print(f"Blunders have been saved to {json_output_path}")