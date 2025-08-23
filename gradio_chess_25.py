import gradio as gr
import chess
import chess.svg
import chess.pgn
import cairosvg
from PIL import Image
import io
import os
import json
import time
from stockfish import Stockfish
from google import genai
from google.genai import types

# Constants
DEFAULT_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
DEFAULT_BOARD_SIZE = 800
BOARD_SQUARES = 8
STOCKFISH_MOVE_DELAY = 2.5  # Seconds between Stockfish moves
GEMINI_MOVE_DELAY = 2.5  # Seconds between Gemini moves
STOCKFISH_ELO = 800  # Initial ELO setting
LLM_MOVE_DELAY = 5.0  # Seconds between LLM moves (for free tier rate limits)
MAX_LLM_RETRIES = 10  # Maximum retries for LLM move generation
MAX_TOKENS = 16000 # Maximum number of tokens including input, thinking, output, etc... 
# MODEL_ID = "gemini-1.5-pro" # Gemini model string identifier - no thinking
# MODEL_ID = "gemini-1.5-flash" # Gemini model string identifier - no thinking
# MODEL_ID = "gemini-2.0-flash" # Gemini model string identifier - no thinking
MODEL_ID = "gemini-2.5-pro-preview-05-06" # Gemini model string identifier
MODEL_ID = "gemini-2.5-flash-preview-05-20" # Gemini model string identifier
THINKING_BUDGET = 12000 # Max thinking tokens to use

# Rate limit configurations
GEMINI_FREE_TIER_RPM = 10  # Requests per minute on free tier
GEMINI_PAID_TIER_RPM = 150  # Requests per minute on paid tier

# Chess Grandmaster System Instruction
CHESS_GRANDMASTER_PERSONA_SI = """You are a world-class chess grandmaster with decades of experience in competitive chess. Your expertise includes:

- Deep understanding of opening theory, middlegame strategy, and endgame technique
- Exceptional tactical vision and positional understanding
- Knowledge of chess history and famous games
- Awareness of psychological aspects of chess competition
- Understanding of time management in tournament play

Key strategic principles you follow:
- Always look for the most forcing moves first (checks, captures, threats)
- Consider piece coordination and pawn structure
- Evaluate king safety as a top priority
- Think about piece activity and space advantage
- Plan several moves ahead while remaining flexible

Important rules you must remember:
- The 3-fold repetition rule allows claiming a draw if the same position occurs three times with the same player to move, same castling rights, and same en passant possibilities
- Always consider if your opponent can force a repetition or if you should seek one in difficult positions
- In winning positions, avoid unnecessary repetitions unless they lead to a better continuation
- In losing positions, look for repetition opportunities to secure a draw

CRITICAL CONSTRAINT:
- You MUST choose from the legal moves provided in the prompt
- Your move must be exactly as shown in the legal moves list
- Do not suggest moves that are not in the legal moves list

Your move predictions should be:
- In standard algebraic notation (SAN) format (e.g., Nf3, Bxe5, O-O, Qh5+)
- The single best move you would play in a tournament game
- Based on sound chess principles and concrete calculation
- Considering both tactics and strategy

Respond with only the move in SAN notation, nothing else."""

# CHESS_GRANDMASTER_PERSONA_SI = """You are a world-class chess grandmaster with decades of experience in competitive chess.

# CRITICAL CONSTRAINT:
# - You MUST choose from the legal moves provided in the prompt
# - Your move must be exactly as shown in the legal moves list
# - Do not suggest moves that are not in the legal moves list"""

# CHESS_GRANDMASTER_PERSONA_SI = """You are Magnus Carlsen-level chess grandmaster with 2800+ rating and decades of tournament experience. You think like the world's elite players, combining deep calculation with intuitive pattern recognition.

# CHESS PHILOSOPHY & APPROACH

# Opening Principles:
# - Control the center with pawns and pieces (e4, d4, Nf3, Nc3)
# - Develop pieces toward the center before moving the same piece twice
# - Castle early for king safety (usually within first 10 moves)
# - Don't bring the queen out too early (avoid early queen attacks)
# - Connect your rooks by completing development

# Middlegame Mastery:
# - Always look for forcing moves first: Checks, captures, threats
# - Evaluate pawn structure: Passed pawns, weak squares, pawn chains
# - Piece activity over material: An active rook beats a passive queen
# - King safety is paramount: Never compromise without concrete compensation
# - Create weaknesses in opponent's position, then exploit them systematically
# - Time is a resource: Use it for critical decisions, not routine moves

# Endgame Technique:
# - Activate your king - it becomes a powerful piece in the endgame
# - Passed pawns must be pushed - they tie down opponent's pieces
# - Rook endgames: Rook behind passed pawns, cut off the enemy king
# - Opposition in king and pawn endings - gain space and zugzwang
# - Know theoretical positions: Basic mates, key pawn endings, rook vs pawn

# TACTICAL VISION
# - Pin, fork, skewer - look for these in every position
# - Deflection and decoy - remove defenders of key squares/pieces
# - Double attacks - attack two things at once
# - Discovered attacks - move one piece to unleash another
# - Zwischenzug (in-between moves) - unexpected intermediate moves
# - Sacrifice calculation: Only sacrifice with concrete, calculable advantage

# POSITIONAL UNDERSTANDING
# - Weak squares: Holes in pawn structure that can't be defended by pawns
# - Piece coordination: Make pieces work together, avoid "loose pieces"
# - Pawn majorities: Create and advance them, especially on the queenside
# - Bishop vs Knight: Bishops better in open positions, knights in closed
# - Good vs bad bishops: Evaluate based on pawn structure

# PSYCHOLOGICAL ASPECTS
# - Maintain objectivity: Don't get attached to "pretty" moves if they're unsound
# - Calculate concrete variations: Avoid wishful thinking, verify everything
# - Practical decisions: Sometimes the "second best" move is easier to play
# - Time pressure: Have a move hierarchy (forcing moves → improving moves → waiting moves)
# - Opponent modeling: Consider their style, rating, time situation

# CRITICAL CONSTRAINTS

# MANDATORY RULE:
# You MUST choose from the legal moves provided in the prompt. Never suggest moves not in the legal moves list.

# Response Format:
# - Output only the move in standard algebraic notation (SAN)
# - No explanations unless specifically requested
# - No analysis in move-only requests
# - Examples: Nf3, Bxe5, O-O, Qh5+, exd6

# Calculation Method:
# 1. Scan for forcing moves: Checks, captures, threats (2-3 moves deep minimum)
# 2. Evaluate candidate moves: Usually 3-5 serious options
# 3. Calculate key variations: Go deeper on critical lines (5-7 moves)
# 4. Assess resulting positions: Material, activity, king safety, pawn structure
# 5. Choose the move: Based on concrete evaluation, not general principles

# TOURNAMENT MINDSET

# Move Selection Priority:
# 1. Forced winning sequences (mate, material gain)
# 2. Strong positional moves that improve your position
# 3. Solid moves that maintain equality
# 4. Avoid blunders at all costs

# Time Management Philosophy:
# - Use time on critical positions: Opening transitions, tactical positions, endgames
# - Play quickly when obvious: Simple developing moves, forced sequences
# - Calculate once, decide: Don't second-guess good moves

# ADVANCED CONCEPTS

# Strategic Themes:
# - Minority attack: b5-b4 against queenside pawn majority
# - Exchange sacrifices: Rook for bishop+knight for activity
# - Positional sacrifices: Material for long-term compensation
# - Piece blockades: Using pieces to stop dangerous pawns

# Pattern Recognition:
# - Typical sacrifices: Bxh7+, Nxf7, Rxh7+, f4-f5 attacks
# - Mating patterns: Back rank, smothered mate, queen and bishop attacks
# - Endgame patterns: Lucena, Philidor, basic opposition

# EXAMPLE DECISION TREE

# Position Analysis Process:
# 1. Is there a tactical shot? (Checks/captures/threats)
# 2. What is the pawn structure telling me? (Where to play)
# 3. Which pieces need improvement? (Worst placed piece principle)
# 4. What is my opponent's plan? (Prevention vs execution)
# 5. Is this a critical moment? (Use more time if yes)

# GRANDMASTER TEMPERAMENT

# You are calm, precise, and confident. You've seen thousands of positions and patterns. You don't get excited by "tricks" but respect sound, principled play. You calculate concretely and trust your evaluation. You play the position, not the opponent's rating.

# When given a position, you analyze like a world champion: systematically, deeply, and with unwavering focus on finding the objectively best move from the provided legal options.

# CRITICAL CONSTRAINT:
# - You MUST choose from the legal moves provided in the prompt
# - Your move must be exactly as shown in the legal moves list
# - Do not suggest moves that are not in the legal moves list"""

CHESS_GRANDMASTER_PERSONA_SI = """"""

def get_gemini_api_key():
    """Get Gemini API key from environment"""
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("WARNING: GOOGLE_API_KEY not found in environment variables")
        print("Set it with: export GOOGLE_API_KEY='your-api-key-here'")
    return api_key

def initialize_gemini():
    """Initialize Gemini client"""
    api_key = get_gemini_api_key()
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            print("✅ Gemini API initialized successfully")
            return client
        except Exception as e:
            print(f"❌ Failed to initialize Gemini API: {e}")
            return None
    return None

# Initialize Gemini
GEMINI_CLIENT = initialize_gemini()

# Stockfish setup with environment detection
def get_stockfish_path():
    """Get the appropriate Stockfish path based on environment"""
    env_path = os.environ.get('STOCKFISH_PATH')
    if env_path and os.path.exists(env_path):
        return env_path
    
    common_paths = [
        '/usr/games/stockfish',  # Ubuntu/Debian
        '/usr/local/bin/stockfish',  # Homebrew
        '/opt/homebrew/bin/stockfish',  # Homebrew M1 Mac
        'stockfish',  # System PATH
    ]
    
    for path in common_paths:
        try:
            if os.path.exists(path):
                return path
        except:
            continue
    
    return 'stockfish'

def initialize_stockfish():
    """Initialize Stockfish engine with optimal settings"""
    try:
        stockfish_path = get_stockfish_path()
        print(f"DEBUG: Initializing Stockfish at path: {stockfish_path}")
        
        stockfish = Stockfish(
            path=stockfish_path,
            depth=1,
            parameters={
                "Threads": 2,
                "Hash": 256,
                "Minimum Thinking Time": 100,
                "UCI_LimitStrength": "true",
                "UCI_Elo": STOCKFISH_ELO,
            }
        )
        
        print(f"DEBUG: Stockfish setting are: {json.dumps(stockfish.get_parameters())}")
        
        # Test the engine
        stockfish.set_fen_position(DEFAULT_FEN)
        test_move = stockfish.get_best_move()
        if test_move:
            print("DEBUG: Stockfish initialized successfully")
            print(f"⚙️  Engine settings: Threads=2, Hash=256MB, ELO=1500")
            return stockfish
        else:
            print("DEBUG: Stockfish test failed")
            return None
            
    except Exception as e:
        print(f"DEBUG: Stockfish initialization failed: {e}")
        return None

# Global Stockfish instance
STOCKFISH = initialize_stockfish()

def create_default_session():
    """Create default session data"""
    return {
        'current_fen': DEFAULT_FEN,
        'starting_fen': DEFAULT_FEN,
        'move_history': [],
        'last_move': '',
        'white_player': 'LLM (Gemini)',
        'black_player': 'Stockfish',
        'stockfish_elo': STOCKFISH_ELO,
        'game_over': False,
        'game_result': '',
        'auto_play_active': False,
        'auto_play_timer': None,
        'gemini_paid_tier': True,
        'rate_limit_active': False,
        'rate_limit_message': '',
        'last_rate_limit_delay': None,
        'failed_moves': [],
        'user_preferences': {
            'dark_mode': False,
            'board_size': DEFAULT_BOARD_SIZE,
            'auto_update': True
        }
    }

def get_move_delay_for_session(session_data):
    """Get appropriate move delay based on current player types and API limits"""
    # Check if we're in a rate limit situation
    if session_data.get('rate_limit_active'):
        rate_limit_delay = session_data.get('last_rate_limit_delay', 63)
        print(f"DEBUG: Rate limit active, using {rate_limit_delay}s delay")
        return rate_limit_delay
    
    current_fen = session_data.get('current_fen', DEFAULT_FEN)
    board = chess.Board(current_fen)
    
    # Check what type of player is about to move
    if board.turn == chess.WHITE:
        current_player = session_data.get('white_player', 'Human')
    else:
        current_player = session_data.get('black_player', 'Human')
    
    # Return appropriate delay based on player type
    if current_player == 'LLM (Gemini)':
        # Use longer delay for LLM to respect rate limits
        if session_data.get('gemini_paid_tier', False):
            # Paid tier: 150 RPM = allow ~2.0 seconds with retry buffer
            return GEMINI_MOVE_DELAY
        else:
            # Free tier: 10 RPM = need ~6 seconds with retry buffer
            return LLM_MOVE_DELAY
    else:
        # Stockfish or Human - use faster timing
        return STOCKFISH_MOVE_DELAY

def detect_gemini_rate_limit_error(error_msg):
    """Detect if error is due to rate limiting"""
    if isinstance(error_msg, str):
        return ("429" in error_msg or 
                "RESOURCE_EXHAUSTED" in error_msg or 
                "quota" in error_msg.lower() or
                "rate limit" in error_msg.lower())
    return False

def get_retry_delay_from_error(error_msg):
    """Extract retry delay from Gemini error message, with minimum 60s"""
    try:
        if "retryDelay" in str(error_msg):
            # Try to extract the retry delay (e.g., "51s")
            import re
            match = re.search(r"retryDelay.*?(\d+)s", str(error_msg))
            if match:
                suggested_delay = int(match.group(1))
                # Add 5% tolerance and minimum 60 seconds
                return max(60, int(suggested_delay * 1.05))
    except:
        pass
    return 63  # Default: 60 seconds + 5% tolerance

def create_next_move_prediction_prompt(session_data):
    """Create enhanced prompt with legal moves and better structure"""
    current_fen = session_data.get('current_fen', DEFAULT_FEN)
    move_history = session_data.get('move_history', [])
    
    # Get current board state and legal moves
    try:
        board = chess.Board(current_fen)
        current_player = "White" if board.turn == chess.WHITE else "Black"
        
        # Get legal moves in SAN notation
        legal_moves_san = []
        for move in board.legal_moves:
            legal_moves_san.append(board.san(move))
        legal_moves_san.sort()  # Sort for consistency
        
        # Check for check status
        check_status = " (in check)" if board.is_check() else ""
        
    except Exception as e:
        print(f"ERROR: Invalid FEN in prompt creation: {e}")
        return "Invalid chess position - cannot generate prompt"
    
    prompt_parts = []
    
    # Clear, direct instruction
    prompt_parts.append(f"You are a chess player with decades of experience. Choose the best move for {current_player}{check_status}.")
    prompt_parts.append("")
    # Clear final instructions
    prompt_parts.append("INSTRUCTIONS:")
    prompt_parts.append("1. Predict the next best move that will result in winning the game")
    prompt_parts.append("2. ONLY suggest moves that are not blocked by other pieces (check CURRENT PIECE PLACEMENT). AVOID rook moves, that may be blocked by other pieces.")
    prompt_parts.append("3. Respond with ONLY the move notation - no explanation")
    prompt_parts.append("")
    prompt_parts.append("IMPORTANT: The move must be in short algebraic notation (SAN notation)")
    prompt_parts.append("")
    
    # Show complete move history for context (if exists)
    if move_history:
        prompt_parts.append("COMPLETE MOVE HISTORY:")
        
        # Format all moves as numbered pairs for full context
        pgn_moves = []
        for i in range(0, len(move_history), 2):
            move_num = (i // 2) + 1
            white_move = move_history[i]
            black_move = move_history[i + 1] if i + 1 < len(move_history) else ""
            
            if black_move:
                pgn_moves.append(f"{move_num}. {white_move} {black_move}")
            else:
                pgn_moves.append(f"{move_num}. {white_move}")
        
        # Split into lines of reasonable length
        history_text = " ".join(pgn_moves)
        max_line_length = 80
        lines = []
        current_line = ""
        
        for move in pgn_moves:
            if len(current_line + " " + move) <= max_line_length:
                current_line += (" " + move) if current_line else move
            else:
                if current_line:
                    lines.append(current_line)
                current_line = move
        if current_line:
            lines.append(current_line)
            
        for line in lines:
            prompt_parts.append(line)
        prompt_parts.append("")

    # # CRITICAL: Show all legal moves to prevent illegal move generation
    # prompt_parts.append("LEGAL MOVES YOU CAN CHOOSE FROM:")
    # # Display moves in groups of 10 for readability
    # moves_per_line = 10
    # for i in range(0, len(legal_moves_san), moves_per_line):
    #     line_moves = legal_moves_san[i:i + moves_per_line]
    #     prompt_parts.append(" ".join(line_moves))
    # prompt_parts.append("")
    
    # Position information
    prompt_parts.append("CURRENT PIECE PLACEMENT:")
    prompt_parts.append(f"FEN: {current_fen}")
    prompt_parts.append("")
        
    # Check if there are any failed moves to avoid
    failed_moves = session_data.get('failed_moves', [])
    if failed_moves and len(failed_moves) > 0:
        # Format with reasons: "Rd2 (illegal move), Nxe4 (invalid syntax)"
        failed_descriptions = [f"{move} ({reason})" for move, reason in failed_moves]
        prompt_parts.append(f"DO NOT choose these moves (already tried): {', '.join(failed_descriptions)}")
        prompt_parts.append("")

        
    prompt_parts.append("")
    prompt_parts.append("Your move:")
    
    return "\n".join(prompt_parts)

def get_prediction_temperature(move_count):
    """Get temperature based on move count - simplified"""
    return 0.8 if move_count <= 4 else 0.0

def get_gemini_move(session_data, retry_temperature=None):
    """Get a chess move from Gemini LLM with full debug output"""
    if not GEMINI_CLIENT:
        print("DEBUG: Gemini not available")
        return None, None  # Return move, rate_limit_delay
    
    try:
        # Create the prompt
        prompt = create_next_move_prediction_prompt(session_data)
        
        # FULL DEBUG OUTPUT - show complete prompt
        print("=" * 80)
        print("DEBUG: FULL GEMINI PROMPT:")
        print("=" * 80)
        print(prompt)
        print("=" * 80)
        
        # Determine temperature
        move_count = len(session_data.get('move_history', []))
        if retry_temperature is not None:
            temperature = retry_temperature
            print(f"DEBUG: Using retry temperature: {temperature}")
        else:
            temperature = get_prediction_temperature(move_count)
            print(f"DEBUG: Using normal temperature: {temperature} (move {move_count})")
        
        client = genai.Client(
            vertexai=True,
            project="argon-works-458421-c3",
            location="global",
        )
      
        # Generate content using API
        response = GEMINI_CLIENT.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are a chess grandmaster. Always choose from the legal moves provided.",
                thinking_config=types.ThinkingConfig(thinking_budget=THINKING_BUDGET),
                max_output_tokens=MAX_TOKENS,  # Keep response short to avoid explanations
                temperature=temperature
            )
        )
        
        print(f"DEBUG: Gemini raw response: '{response}'")
        
        # Check response validity
        if not response or not hasattr(response, 'text') or not response.text:
            print("DEBUG: Gemini returned empty or invalid response")
            return None, None
        
        prediction = response.text.strip()
        # print(f"DEBUG: Gemini raw response: '{prediction}'")
        
        return prediction, None  # No rate limit delay
        
    except Exception as e:
        error_msg = str(e)
        print(f"DEBUG: Gemini API error: {error_msg}")
        
        # Check if it's a rate limit error
        if detect_gemini_rate_limit_error(error_msg):
            retry_delay = get_retry_delay_from_error(error_msg)
            print(f"DEBUG: Rate limit detected. Required retry delay: {retry_delay}s")
            return None, retry_delay  # Return rate limit delay
        
        return None, None
    
def parse_ambiguous_move(board, move_text):
    """
    Enhanced move parsing that handles ambiguous SAN notation like "Rxa6"
    by trying all possible disambiguations
    """
    try:
        # First try normal parsing
        return board.parse_san(move_text)
    except ValueError as e:
        print(f"DEBUG: Normal SAN parsing failed for '{move_text}': {e}")
        
        # If normal parsing fails, try to resolve ambiguity
        if not move_text or len(move_text) < 2:
            raise e
        
        # Extract piece type and target square
        piece_char = move_text[0] if move_text[0] in 'KQRBN' else ''
        
        # Handle different move formats
        if 'x' in move_text:
            # Capture move like "Rxa6"
            parts = move_text.split('x')
            if len(parts) == 2:
                piece_part = parts[0]
                target_square = parts[1]
                
                # Try to find all legal moves that match this pattern
                legal_moves = []
                for move in board.legal_moves:
                    move_san = board.san(move)
                    # Check if this move matches the pattern
                    if (target_square in move_san and 
                        'x' in move_san and 
                        piece_part in move_san):
                        legal_moves.append(move)
                
                if len(legal_moves) == 1:
                    print(f"DEBUG: Resolved ambiguous '{move_text}' to {board.san(legal_moves[0])}")
                    return legal_moves[0]
                elif len(legal_moves) > 1:
                    # Multiple possibilities - try the first one
                    print(f"DEBUG: Multiple matches for '{move_text}', using {board.san(legal_moves[0])}")
                    return legal_moves[0]
        
        else:
            # Non-capture move like "Rf6"
            target_square = move_text[-2:] if len(move_text) >= 2 else move_text
            
            legal_moves = []
            for move in board.legal_moves:
                move_san = board.san(move)
                if (target_square in move_san and 
                    piece_char and piece_char in move_san and
                    'x' not in move_san):
                    legal_moves.append(move)
            
            if len(legal_moves) == 1:
                print(f"DEBUG: Resolved ambiguous '{move_text}' to {board.san(legal_moves[0])}")
                return legal_moves[0]
            elif len(legal_moves) > 1:
                print(f"DEBUG: Multiple matches for '{move_text}', using {board.san(legal_moves[0])}")
                return legal_moves[0]
        
        # If we couldn't resolve it, raise the original error
        raise e
    
def create_thinking_prompt(session_data):
    """Create a thinking/reflection prompt for the LLM"""
    current_fen = session_data.get('current_fen', DEFAULT_FEN)
    move_history = session_data.get('move_history', [])
    
    try:
        board = chess.Board(current_fen)
        current_player = "White" if board.turn == chess.WHITE else "Black"
        check_status = " (in check)" if board.is_check() else ""
    except Exception as e:
        print(f"ERROR: Invalid FEN in thinking prompt creation: {e}")
        return "Invalid chess position - cannot generate thinking prompt"
    
    prompt_parts = []
    
    # Show complete move history for context (if exists)
    if move_history:
        prompt_parts.append("COMPLETE MOVE HISTORY:")
        
        # Format all moves as numbered pairs for full context
        pgn_moves = []
        for i in range(0, len(move_history), 2):
            move_num = (i // 2) + 1
            white_move = move_history[i]
            black_move = move_history[i + 1] if i + 1 < len(move_history) else ""
            
            if black_move:
                pgn_moves.append(f"{move_num}. {white_move} {black_move}")
            else:
                pgn_moves.append(f"{move_num}. {white_move}")
        
        # Split into lines of reasonable length
        history_text = " ".join(pgn_moves)
        max_line_length = 80
        lines = []
        current_line = ""
        
        for move in pgn_moves:
            if len(current_line + " " + move) <= max_line_length:
                current_line += (" " + move) if current_line else move
            else:
                if current_line:
                    lines.append(current_line)
                current_line = move
        if current_line:
            lines.append(current_line)
            
        for line in lines:
            prompt_parts.append(line)
        prompt_parts.append("")
    else:
        prompt_parts.append("GAME START - No moves yet")
        prompt_parts.append("")
    
    # Position information
    prompt_parts.append("CURRENT PIECE PLACEMENT:")
    prompt_parts.append(f"FEN: {current_fen}")
    prompt_parts.append("")
    
    # Board layout information
    prompt_parts.append("CURRENT BOARD LAYOUT:")
    prompt_parts.append("")                  
    prompt_parts.append(f"{chess.Board(current_fen).__str__()}")
    prompt_parts.append("")
    
    # Thinking instructions
    prompt_parts.append(f"Before deciding on the next move for {current_player}{check_status}, you can reflect on your current situation, write down notes, and evaluate.")
    prompt_parts.append("Here are a few recommendations that you can follow to make a better move decision:")
    prompt_parts.append("- Shortlist the most valuable next moves")
    prompt_parts.append("- Consider how they affect the situation")
    prompt_parts.append("- What could be the next moves from your opponent in each case")
    prompt_parts.append("- Is there any strategy fitting the situation and your choice of moves")
    prompt_parts.append("- Rerank the shortlisted moves based on the previous steps")
    prompt_parts.append("")
    
    # Check if there are any failed moves to avoid
    failed_moves = session_data.get('failed_moves', [])
    if failed_moves and len(failed_moves) > 0:
        # Format with reasons: "Rd2 (illegal move), Nxe4 (invalid syntax)"
        failed_descriptions = [f"{move} ({reason})" for move, reason in failed_moves]
        prompt_parts.append(f"IMPORTANT - DO NOT consider these moves (already tried and failed): {', '.join(failed_descriptions)}")
        prompt_parts.append("")
    
    # Ask for reflection
    prompt_parts.append("Provide your analysis and reflection:")
    
    return "\n".join(prompt_parts)

def get_gemini_thinking(session_data, max_retries=MAX_LLM_RETRIES):
    """Get thinking/reflection from Gemini LLM with retries and temperature increase"""
    if not GEMINI_CLIENT:
        print("DEBUG: Gemini not available for thinking")
        return None
    
    # Create the thinking prompt once
    thinking_prompt = create_thinking_prompt(session_data)
    
    print("=" * 80)
    print("DEBUG: GEMINI THINKING PROMPT:")
    print("=" * 80)
    print(thinking_prompt)
    print("=" * 80)
    
    for attempt in range(max_retries):
        print(f"DEBUG: Gemini thinking attempt {attempt + 1}/{max_retries}")
        
        try:
            # Determine temperature - start higher for thinking, increase on retries
            if attempt == 0:
                thinking_temperature = 0.7  # Start with creative temperature for thinking
            else:
                thinking_temperature = min(2.0, 0.7 + (attempt * 0.15))  # Increase for variety
                print(f"DEBUG: Thinking retry {attempt + 1} - using temperature {thinking_temperature}")
            
            # Generate thinking content using the same client structure as your code
            response = GEMINI_CLIENT.models.generate_content(
                model=MODEL_ID,
                contents=thinking_prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are a chess grandmaster analyzing the position. Provide thoughtful analysis and reflection about the current position and potential moves.",
                    max_output_tokens=MAX_TOKENS,
                    thinking_config=types.ThinkingConfig(thinking_budget=THINKING_BUDGET),
                    temperature=thinking_temperature
                )
            )
            
            print(f"DEBUG: Gemini raw response: '{response}'")
            
            # Extract text using the same approach as your move function
            thinking_text = None
            
            # First try the simple approach that your move function uses
            if hasattr(response, 'text') and response.text:
                thinking_text = response.text.strip()
            else:
                # If that fails, try extracting from the complex structure
                try:
                    if hasattr(response, 'candidates') and response.candidates and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts and len(candidate.content.parts) > 0:
                                part = candidate.content.parts[0]
                                if hasattr(part, 'text') and part.text:
                                    thinking_text = part.text.strip()
                except Exception as extract_error:
                    print(f"DEBUG: Error extracting text from response on attempt {attempt + 1}: {extract_error}")
            
            # Check if we got valid thinking text
            if not thinking_text or thinking_text.strip() == "":
                print(f"DEBUG: Gemini thinking returned empty or invalid response on attempt {attempt + 1}")
                continue  # This will retry with higher temperature
            
            print(f"DEBUG: Gemini raw response: '{thinking_text}'")
            
            # If we got a response, return it
            if thinking_text:
                # print("=" * 80)
                # print("DEBUG: GEMINI THINKING RESPONSE:")
                # print("=" * 80)
                # print(thinking_text)
                # print("=" * 80)
                return thinking_text
            else:
                # print(f"DEBUG: Empty thinking text on attempt {attempt + 1}")
                continue
            
        except Exception as e:
            error_msg = str(e)
            print(f"DEBUG: Gemini thinking error on attempt {attempt + 1}: {error_msg}")
            
            # Check if it's a rate limit error - if so, stop retrying and return None
            # The main move function will handle the rate limit
            if detect_gemini_rate_limit_error(error_msg):
                print(f"DEBUG: Rate limit hit during thinking, stopping thinking retries")
                return None
            
            # For other errors, continue to next attempt
            continue
    
    print("DEBUG: All thinking attempts failed, proceeding without reflection")
    return None

def create_next_move_prediction_prompt_with_reflection(session_data, reflection_text):
    """Enhanced version of your existing prompt creation function that includes reflection"""
    current_fen = session_data.get('current_fen', DEFAULT_FEN)
    move_history = session_data.get('move_history', [])
    
    # Get current board state and legal moves
    try:
        board = chess.Board(current_fen)
        current_player = "White" if board.turn == chess.WHITE else "Black"
        
        # Get legal moves in SAN notation
        legal_moves_san = []
        for move in board.legal_moves:
            legal_moves_san.append(board.san(move))
        legal_moves_san.sort()  # Sort for consistency
        
        # Check for check status
        check_status = " (in check)" if board.is_check() else ""
        
    except Exception as e:
        print(f"ERROR: Invalid FEN in prompt creation: {e}")
        return "Invalid chess position - cannot generate prompt"
    
    prompt_parts = []
    
    # Clear, direct instruction
    prompt_parts.append(f"You are a chess player with decades of experience. Choose the best move for {current_player}{check_status}.")
    prompt_parts.append("")
    
    # Include the reflection from the thinking step
    if reflection_text and reflection_text.strip():
        prompt_parts.append("REFLECTION:")
        # Add the reflection text, properly formatted
        reflection_lines = reflection_text.strip().split('\n')
        for line in reflection_lines:
            prompt_parts.append(line)
        prompt_parts.append("")
    
    # Clear final instructions
    prompt_parts.append("INSTRUCTIONS:")
    prompt_parts.append("1. Predict the next best move that will result in winning the game")
    prompt_parts.append("2. ONLY suggest moves that are not blocked by other pieces (check CURRENT PIECE PLACEMENT). AVOID rook moves, that may be blocked by other pieces.")
    prompt_parts.append("3. Respond with ONLY the move notation - no explanation")
    prompt_parts.append("")
    prompt_parts.append("IMPORTANT: The move must be in short algebraic notation (SAN notation)")
    prompt_parts.append("")
    
    # Show complete move history for context (if exists)
    if move_history:
        prompt_parts.append("COMPLETE MOVE HISTORY:")
        
        # Format all moves as numbered pairs for full context
        pgn_moves = []
        for i in range(0, len(move_history), 2):
            move_num = (i // 2) + 1
            white_move = move_history[i]
            black_move = move_history[i + 1] if i + 1 < len(move_history) else ""
            
            if black_move:
                pgn_moves.append(f"{move_num}. {white_move} {black_move}")
            else:
                pgn_moves.append(f"{move_num}. {white_move}")
        
        # Split into lines of reasonable length
        history_text = " ".join(pgn_moves)
        max_line_length = 80
        lines = []
        current_line = ""
        
        for move in pgn_moves:
            if len(current_line + " " + move) <= max_line_length:
                current_line += (" " + move) if current_line else move
            else:
                if current_line:
                    lines.append(current_line)
                current_line = move
        if current_line:
            lines.append(current_line)
            
        for line in lines:
            prompt_parts.append(line)
        prompt_parts.append("")

    # Position information
    prompt_parts.append("CURRENT PIECE PLACEMENT:")
    prompt_parts.append(f"FEN: {current_fen}")
    prompt_parts.append("")
        
    # Check if there are any failed moves to avoid
    failed_moves = session_data.get('failed_moves', [])
    if failed_moves and len(failed_moves) > 0:
        # Format with reasons: "Rd2 (illegal move), Nxe4 (invalid syntax)"
        failed_descriptions = [f"{move} ({reason})" for move, reason in failed_moves]
        prompt_parts.append(f"DO NOT choose these moves (already tried): {', '.join(failed_descriptions)}")
        prompt_parts.append("")

    prompt_parts.append("")
    prompt_parts.append("Your move:")
    
    return "\n".join(prompt_parts)

# Modified version of your existing get_gemini_move function
def get_gemini_move_with_thinking(session_data, retry_temperature=None):
    """Enhanced version of your get_gemini_move function that includes thinking step"""
    if not GEMINI_CLIENT:
        print("DEBUG: Gemini not available")
        return None, None  # Return move, rate_limit_delay
    
    try:
        # Step 1: Get thinking/reflection (new step)
        thinking_text = get_gemini_thinking(session_data)
        if thinking_text is None:
            print("DEBUG: Could not get thinking from Gemini, proceeding without reflection")
            thinking_text = ""
        
        # Step 2: Create the move prediction prompt with reflection
        if thinking_text:
            prompt = create_next_move_prediction_prompt_with_reflection(session_data, thinking_text)
        else:
            # Fallback to your original prompt if thinking failed
            prompt = create_next_move_prediction_prompt(session_data)
        
        # FULL DEBUG OUTPUT - show complete prompt
        print("=" * 80)
        print("DEBUG: FULL GEMINI MOVE PROMPT (WITH REFLECTION):")
        print("=" * 80)
        print(prompt)
        print("=" * 80)
        
        # Determine temperature (using your existing logic)
        move_count = len(session_data.get('move_history', []))
        if retry_temperature is not None:
            temperature = retry_temperature
            print(f"DEBUG: Using retry temperature: {temperature}")
        else:
            temperature = get_prediction_temperature(move_count)
            print(f"DEBUG: Using normal temperature: {temperature} (move {move_count})")
        
        # Your existing client setup (I noticed you have an unused client creation)
        # Generate content using API (same as your existing code)
        response = GEMINI_CLIENT.models.generate_content(
            model="gemini-2.5-flash-preview-05-20",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are a chess grandmaster. Always choose from the legal moves provided.",
                max_output_tokens=16000,  # Keep response short to avoid explanations
                temperature=temperature
            )
        )
        
        print(f"DEBUG: Gemini raw response: '{response}'")
        
        # Check response validity (same as your existing code)
        if not response or not hasattr(response, 'text') or not response.text:
            print("DEBUG: Gemini returned empty or invalid response")
            return None, None
        
        prediction = response.text.strip()
        # print(f"DEBUG: Gemini raw response: '{prediction}'")
        
        return prediction, None  # No rate limit delay
        
    except Exception as e:
        error_msg = str(e)
        print(f"DEBUG: Gemini API error: {error_msg}")
        
        # Check if it's a rate limit error (using your existing function)
        if detect_gemini_rate_limit_error(error_msg):
            retry_delay = get_retry_delay_from_error(error_msg)
            print(f"DEBUG: Rate limit detected. Required retry delay: {retry_delay}s")
            return None, retry_delay  # Return rate limit delay
        
        return None, None

    
# Simplified validate_and_get_gemini_move function (replace lines 427-562)
def validate_and_get_gemini_move(session_data):
    """Hybrid validation - simple but robust move extraction with SAN disambiguation"""
    
    # Initialize failed_moves if it doesn't exist OR if it's not a list
    if 'failed_moves' not in session_data or not isinstance(session_data['failed_moves'], list):
        session_data['failed_moves'] = []
    
    for attempt in range(MAX_LLM_RETRIES):
        print(f"DEBUG: Gemini move attempt {attempt + 1}/{MAX_LLM_RETRIES}")
        
        # Determine retry temperature for variety
        retry_temp = None
        if attempt > 0:
            retry_temp = min(2.0, 0.5 + (attempt * 0.15))
            print(f"DEBUG: Retry {attempt} - using temperature {retry_temp}")
        
        # Get move from Gemini
        move_text, rate_limit_delay = get_gemini_move_with_thinking(session_data, retry_temperature=retry_temp)
        
        # Handle rate limit
        if rate_limit_delay is not None:
            print(f"DEBUG: Rate limit hit, stopping retries. Required wait: {rate_limit_delay}s")
            session_data['rate_limit_active'] = True
            session_data['rate_limit_message'] = f"⏳ Gemini rate limit hit. Waiting {rate_limit_delay} seconds for reset..."
            session_data['last_rate_limit_delay'] = rate_limit_delay
            return None
        
        if not move_text:
            print(f"DEBUG: No response from Gemini on attempt {attempt + 1}")
            continue
        
        # ENHANCED MOVE EXTRACTION: Handle both SAN and LAN notation
        import re
        chess_move_pattern = r'([KQRBN]?[a-h][1-8][-x][a-h][1-8](?:=[QRBN])?[+#]?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?|O-O(?:-O)?[+#]?)'
        potential_moves = re.findall(chess_move_pattern, move_text)
        
        if potential_moves:
            # Take the first chess-like move found
            cleaned_move = potential_moves[0]
            print(f"DEBUG: Regex found chess move: '{cleaned_move}'")
        else:
            # Fallback: take first word and hope for the best
            words = move_text.strip().split()
            if words:
                cleaned_move = words[0]
                print(f"DEBUG: Fallback to first word: '{cleaned_move}'")
            else:
                print(f"DEBUG: Empty response on attempt {attempt + 1}")
                continue
        
        # ENHANCED VALIDATION: Handle SAN disambiguation
        try:
            board = chess.Board(session_data.get('current_fen', DEFAULT_FEN))
            move = board.parse_san(cleaned_move)
            proper_san = board.san(move)  # Get canonical disambiguated SAN
            
            print(f"DEBUG: ✅ SUCCESS - '{cleaned_move}' → '{proper_san}' (UCI: {move.uci()})")
            
            # Clear rate limit state AND failed moves on success
            session_data.pop('rate_limit_active', None)
            session_data.pop('rate_limit_message', None)
            session_data.pop('last_rate_limit_delay', None)
            session_data['failed_moves'] = []  # Clear failed moves on success
            
            return proper_san
            
        except chess.AmbiguousMoveError as e:
            print(f"DEBUG: ❌ AMBIGUOUS MOVE - '{cleaned_move}': {e}")
            
            # Try to find all legal moves that could match this ambiguous move
            board = chess.Board(session_data.get('current_fen', DEFAULT_FEN))
            possible_moves = []
            target_square = None
            
            # Extract the target square from the ambiguous move (e.g., "Rd1" -> "d1")
            target_match = re.search(r'([a-h][1-8])', cleaned_move)
            if target_match:
                target_square = target_match.group(1)
            
            # Find all legal moves that could match
            for legal_move in board.legal_moves:
                legal_san = board.san(legal_move)
                # Check if this move goes to the same target square
                if target_square and target_square in legal_san:
                    # Additional check: same piece type if specified
                    piece_match = re.match(r'^([KQRBN])', cleaned_move)
                    if piece_match:
                        piece_type = piece_match.group(1)
                        if legal_san.startswith(piece_type):
                            possible_moves.append(legal_san)
                    else:
                        # Pawn move
                        if not re.match(r'^[KQRBN]', legal_san):
                            possible_moves.append(legal_san)
            
            if len(possible_moves) == 1:
                # Found exactly one matching move - use it!
                resolved_move = possible_moves[0]
                print(f"DEBUG: ✅ RESOLVED AMBIGUITY - '{cleaned_move}' → '{resolved_move}'")
                
                # Clear success state
                session_data.pop('rate_limit_active', None)
                session_data.pop('rate_limit_message', None) 
                session_data.pop('last_rate_limit_delay', None)
                session_data['failed_moves'] = []
                
                return resolved_move
            else:
                # Still ambiguous or no matches
                error_msg = f"ambiguous move - options: {possible_moves}" if possible_moves else "ambiguous move - no clear options"
                if cleaned_move not in [item[0] for item in session_data['failed_moves']]:
                    session_data['failed_moves'].append((cleaned_move, error_msg))
            
        except chess.InvalidMoveError as e:
            print(f"DEBUG: ❌ INVALID SYNTAX - '{cleaned_move}': {e}")
            if cleaned_move not in [item[0] for item in session_data['failed_moves']]:
                session_data['failed_moves'].append((cleaned_move, "invalid syntax"))
            
        except chess.IllegalMoveError as e:
            print(f"DEBUG: ❌ ILLEGAL MOVE - '{cleaned_move}': {e}")
            if cleaned_move not in [item[0] for item in session_data['failed_moves']]:
                session_data['failed_moves'].append((cleaned_move, "illegal move"))
            
        except Exception as e:
            print(f"DEBUG: ❌ OTHER ERROR - '{cleaned_move}': {e}")
            if cleaned_move not in [item[0] for item in session_data['failed_moves']]:
                session_data['failed_moves'].append((cleaned_move, "other error"))
    
    print("DEBUG: All attempts failed")
    return None

def update_stockfish_settings(elo_rating):
    """Update Stockfish engine settings using ELO only"""
    if STOCKFISH:
        try:
            STOCKFISH.set_elo_rating(elo_rating)
            print(f"DEBUG: Updated Stockfish ELO: {elo_rating}")
            return True
        except Exception as e:
            print(f"DEBUG: Failed to update Stockfish settings: {e}")
            return False
    return False

def get_stockfish_move(fen_position):
    """Get best move from Stockfish for current position"""
    if not STOCKFISH:
        print("DEBUG: Stockfish not available")
        return None
    
    try:
        STOCKFISH.set_fen_position(fen_position)
        best_move = STOCKFISH.get_best_move()
        print(f"DEBUG: Stockfish suggests: {best_move}")
        return best_move
    except Exception as e:
        print(f"DEBUG: Stockfish move generation failed: {e}")
        return None

def validate_move_with_stockfish(fen_position, move):
    """Validate a move using Stockfish"""
    if not STOCKFISH:
        return True  # Fallback to chess library validation
    
    try:
        STOCKFISH.set_fen_position(fen_position)
        return STOCKFISH.is_move_correct(move)
    except Exception as e:
        print(f"DEBUG: Stockfish move validation failed: {e}")
        return True

def create_chess_board_image(
    fen: str = DEFAULT_FEN,
    board_size: int = DEFAULT_BOARD_SIZE,
    last_move: str = None
):
    """Returns either PIL Image on success or error string on failure"""
    try:
        board = chess.Board(fen)
        square_size = board_size // BOARD_SQUARES
        actual_board_size = square_size * BOARD_SQUARES
        
        fill = {}
        arrows = []
        lastmove_obj = None
        
        if last_move and len(last_move) >= 4:
            try:
                lastmove_obj = chess.Move.from_uci(last_move)
                to_square = lastmove_obj.to_square
                from_square = lastmove_obj.from_square
                
                print(f"DEBUG: last move UCI {last_move}")
                print(f"DEBUG: to_square: {to_square}, from_square: {from_square}")
                
                # Show attacks from the destination square
                fill = dict.fromkeys(board.attacks(to_square), "#ff0000aa")
                
                # Add last move highlighting
                fill[from_square] = "#fdd90dac"  # From square
                fill[to_square] = "#fdd90dac"    # To square
                
                # Add arrow for last move (light green version of #30ac10)
                arrows = [chess.svg.Arrow(from_square, to_square, color="#2fac104d")]
                
                print(f"DEBUG: fill: {fill}")
                print(f"DEBUG: arrows: {arrows}")
                
            except (ValueError, chess.InvalidMoveError) as e:
                print(f"DEBUG: Invalid UCI move '{last_move}': {e}")
                lastmove_obj = None
                fill = {}
                arrows = []

        svg_data = chess.svg.board(
            board=board,
            fill=fill,
            arrows=arrows,
            colors={
                'margin':'#30ac10',
                'square light': '#8ec1ef',
                'square dark': '#eeefe7',
            },
            size=actual_board_size,
            lastmove=lastmove_obj
        )
        
        # # Create SVG with last move highlighting
        # svg_data = chess.svg.board(
        #     board=board, 
        #     size=actual_board_size,
        #     lastmove=chess.Move.from_uci(last_move) if last_move and len(last_move) >= 4 else None
        # )
        
        png_data = cairosvg.svg2png(
            bytestring=svg_data.encode('utf-8'),
            output_width=actual_board_size,
            output_height=actual_board_size
        )
        image = Image.open(io.BytesIO(png_data))
        
        # Force RGBA mode to preserve transparency
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
    
        return image
    except ValueError as e:
        return f"Invalid FEN notation: {e}"
    except Exception as e:
        return f"Error creating chess board: {e}"
    
def format_outcome_message(outcome, halfmove_clock):
    """Format outcome into user-friendly message"""
    termination = outcome.termination
    winner = outcome.winner
    
    if termination == chess.Termination.CHECKMATE:
        winner_name = "White" if winner == chess.WHITE else "Black"
        return f"🏆 Game Over - {winner_name} wins by checkmate!"
    elif termination == chess.Termination.STALEMATE:
        return "🤝 Game Over - Draw by stalemate!"
    elif termination == chess.Termination.INSUFFICIENT_MATERIAL:
        return "🤝 Game Over - Draw by insufficient material!"
    elif termination == chess.Termination.SEVENTYFIVE_MOVES:
        return f"🤝 Game Over - Draw by 75-move rule! (Clock: {halfmove_clock})"
    elif termination == chess.Termination.FIVEFOLD_REPETITION:
        return "🤝 Game Over - Draw by 5-fold repetition!"
    elif termination == chess.Termination.FIFTY_MOVES:
        return f"🤝 Game Over - Draw by 50-move rule! (Clock: {halfmove_clock})"
    elif termination == chess.Termination.THREEFOLD_REPETITION:
        return "🤝 Game Over - Draw by 3-fold repetition!"
    else:
        return f"🤝 Game Over - {termination.name.lower().replace('_', ' ')}"

def get_game_status(board):
    """Simplified version using only the outcome() method"""
    
    # Check with automatic rules only
    outcome = board.outcome()
    if outcome:
        return True, format_outcome_message(outcome, board.halfmove_clock)
    
    # Check with claimable draws
    outcome_with_claims = board.outcome(claim_draw=True)
    if outcome_with_claims:
        return True, format_outcome_message(outcome_with_claims, board.halfmove_clock)
    
    # Game ongoing
    turn = "White" if board.turn == chess.WHITE else "Black"
    move_count = board.fullmove_number
    
    if board.is_check():
        return False, f"⚠️ {turn} to move (in check) - Move {(move_count//2)+1}"
    else:
        return False, f"▶️ {turn} to move - Move {(move_count//2)+1}"

def generate_pgn_from_moves(move_history, starting_fen=DEFAULT_FEN):
    """Generate PGN from the current game's move history"""
    try:
        # Create a new board and game
        board = chess.Board(starting_fen)
        game = chess.pgn.Game()
        
        # Set basic headers
        game.headers["Event"] = "Chess App Game"
        game.headers["Site"] = "Local Chess App"
        game.headers["Date"] = "2025.06.04"
        game.headers["Round"] = "1"
        game.headers["White"] = "Player"
        game.headers["Black"] = "Player"
        game.headers["Result"] = "*"
        
        # If starting from a custom position, set the FEN header
        if starting_fen != DEFAULT_FEN:
            game.headers["FEN"] = starting_fen
            game.headers["SetUp"] = "1"
        
        # Add moves to the game
        node = game
        for move_san in move_history:
            move = board.parse_san(move_san)
            board.push(move)
            node = node.add_variation(move)
        
        # Return PGN string
        return str(game)
    except Exception as e:
        return f"Error generating PGN: {str(e)}"

def load_game_from_pgn(pgn_text):
    """Load a game from PGN text and return FEN, move history, and status"""
    try:
        # Parse PGN
        pgn_io = io.StringIO(pgn_text.strip())
        game = chess.pgn.read_game(pgn_io)
        
        if game is None:
            return None, [], None, "No valid game found in PGN"
        
        # Get starting position
        starting_fen = DEFAULT_FEN
        if "FEN" in game.headers:
            starting_fen = game.headers["FEN"]
        
        # Play through the moves to get final position and move list
        board = game.board()
        move_history = []
        
        for move in game.mainline_moves():
            # Convert to SAN for our move history
            move_san = board.san(move)
            move_history.append(move_san)
            board.push(move)
        
        final_fen = board.fen()
        return final_fen, move_history, starting_fen, f"Loaded game with {len(move_history)} moves"
        
    except Exception as e:
        return None, [], None, f"Error loading PGN: {str(e)}"

def get_lan_move_history_from_session(session_data):
    """Convert stored SAN move history to LAN for display"""
    try:
        move_history = session_data.get('move_history', [])
        starting_fen = session_data.get('starting_fen', DEFAULT_FEN)
        
        # print(f"DEBUG LAN: Processing move_history: {move_history}")
        # print(f"DEBUG LAN: Starting FEN: {starting_fen}")
        
        if not move_history:
            return 'No moves yet'
        
        # Replay moves to get LAN notation
        board = chess.Board(starting_fen)
        lan_moves = []
        
        for i, move_san in enumerate(move_history):
            try:
                # print(f"DEBUG LAN: Processing move {i+1}: '{move_san}'")
                move = board.parse_san(move_san)
                lan = board.lan(move)
                # print(f"DEBUG LAN: Converted '{move_san}' to LAN: '{lan}'")
                lan_moves.append(lan)
                board.push(move)
            except Exception as e:
                # If we can't parse a move, keep the original
                # print(f"DEBUG LAN: Error converting '{move_san}' to LAN: {e}")
                lan_moves.append(f"{move_san}(?)")
        
        result = ', '.join(lan_moves)
        # print(f"DEBUG LAN: Final LAN result: {result}")
        return result
        
    except Exception as e:
        # print(f"DEBUG LAN: Major error converting to LAN: {e}")
        # Fallback to original move history
        move_history = session_data.get('move_history', [])
        return ', '.join(move_history) if move_history else 'No moves yet'

def get_turn_from_fen(fen):
    """Extract whose turn it is from FEN notation"""
    try:
        board = chess.Board(fen)
        game_over, status = get_game_status(board)
        return status
    except:
        return "Unknown turn"

def update_board_from_fen(fen_input, session_data):
    """Update chess board display from FEN input and save to session"""
    if not fen_input.strip():
        fen_input = DEFAULT_FEN
    
    result = create_chess_board_image(fen_input, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
    
    # Update session with new FEN and clear move history since FEN has no history
    session_data['current_fen'] = fen_input
    session_data['starting_fen'] = fen_input  # Set this as the new starting position
    session_data['move_history'] = []  # Clear move history
    session_data['last_move'] = ''     # Clear last move
    session_data['game_over'] = False  # Reset game over status
    session_data['game_result'] = ''   # Clear game result
    
    if isinstance(result, str):
        print(f"Invalid FEN: {result}")
        return None, session_data
    else:
        return result, session_data

def update_from_pgn(pgn_text, session_data):
    """Update board and session from PGN input"""
    if not pgn_text.strip():
        print("Please enter PGN text")
        return session_data, None, session_data.get('current_fen', DEFAULT_FEN)
    
    final_fen, move_history, starting_fen, status = load_game_from_pgn(pgn_text)
    
    if final_fen is None:
        print(status)
        current_fen = session_data.get('current_fen', DEFAULT_FEN)
        result = create_chess_board_image(current_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
        return session_data, result, current_fen
    
    # Update session with loaded game
    session_data['current_fen'] = final_fen
    session_data['move_history'] = move_history
    session_data['starting_fen'] = starting_fen or DEFAULT_FEN
    session_data['last_move'] = ''  # No specific last move from PGN
    session_data['game_over'] = False  # Reset game status
    session_data['game_result'] = ''
    
    # Create board image
    result = create_chess_board_image(final_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
    if isinstance(result, str):
        print(f"Error creating board: {result}")
        return session_data, None, final_fen
    else:
        print(status)
        return session_data, result, final_fen

def should_stockfish_move(session_data):
    """Check if Stockfish should make the next move"""
    if session_data.get('game_over', False):
        return False
        
    current_fen = session_data.get('current_fen', DEFAULT_FEN)
    board = chess.Board(current_fen)
    
    if board.turn == chess.WHITE:
        return session_data.get('white_player') == 'Stockfish'
    else:
        return session_data.get('black_player') == 'Stockfish'

def should_llm_move(session_data):
    """Check if LLM should make the next move"""
    if session_data.get('game_over', False):
        return False
        
    current_fen = session_data.get('current_fen', DEFAULT_FEN)
    board = chess.Board(current_fen)
    
    if board.turn == chess.WHITE:
        return session_data.get('white_player') == 'LLM (Gemini)'
    else:
        return session_data.get('black_player') == 'LLM (Gemini)'

def should_ai_move(session_data):
    """Check if any AI (Stockfish or LLM) should make the next move"""
    return should_stockfish_move(session_data) or should_llm_move(session_data)

def make_move_with_session(session_data, move_san):
    """Make a move on the chess board and update session"""
    print(f"DEBUG: Attempting move '{move_san}'")
    
    # Check if game is over
    if session_data.get('game_over', False):
        print("DEBUG: Game is already over")
        current_fen = session_data.get('current_fen', DEFAULT_FEN)
        board_image = create_chess_board_image(current_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
        return session_data, board_image, current_fen
    
    current_fen = session_data.get('current_fen', DEFAULT_FEN)
    current_board_result = create_chess_board_image(current_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
    current_board_image = current_board_result if not isinstance(current_board_result, str) else None
    
    if not move_san.strip():
        print("DEBUG: Empty move")
        return session_data, current_board_image, current_fen
        
    try:
        board = chess.Board(current_fen)
        print(f"DEBUG: Board created, attempting to parse '{move_san}'")
        
        # Parse the move (accepts SAN, LAN, UCI, etc.)
        move = board.parse_san(move_san)
        print(f"DEBUG: Move parsed successfully: {move}")
        
        # Validate with Stockfish if available
        if not validate_move_with_stockfish(current_fen, move.uci()):
            print("DEBUG: Stockfish validation failed")
            return session_data, current_board_image, current_fen
        
        # Get the standardized SAN notation BEFORE making the move
        standardized_san = board.san(move)
        print(f"DEBUG: Standardized SAN: {standardized_san}")
        
        board.push(move)
        new_fen = board.fen()
        print(f"DEBUG: Move executed, new FEN: {new_fen}")
        
        # Update session data with standardized SAN
        session_data['current_fen'] = new_fen
        session_data['move_history'].append(standardized_san)
        session_data['last_move'] = move.uci()
        
        # Check game status
        game_over, status = get_game_status(board)
        session_data['game_over'] = game_over
        session_data['game_result'] = status if game_over else ''
        
        result = create_chess_board_image(new_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE), move.uci())
        
        if isinstance(result, str):
            print(f"DEBUG: Board image creation failed: {result}")
            return session_data, current_board_image, current_fen
        else:
            print("DEBUG: Move completed successfully")
            return session_data, result, new_fen
            
    except ValueError as e:
        print(f"DEBUG: ValueError caught: {e}")
        return session_data, current_board_image, current_fen
    except Exception as e:
        print(f"DEBUG: Exception caught: {type(e).__name__}: {e}")
        return session_data, current_board_image, current_fen

def make_stockfish_move(session_data):
    """Make a Stockfish move automatically"""
    if not should_stockfish_move(session_data) or session_data.get('game_over', False):
        current_fen = session_data.get('current_fen', DEFAULT_FEN)
        board_image = create_chess_board_image(current_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
        return session_data, board_image, current_fen
    
    current_fen = session_data.get('current_fen', DEFAULT_FEN)
    stockfish_move = get_stockfish_move(current_fen)
    
    if stockfish_move:
        print(f"DEBUG: Executing Stockfish move: {stockfish_move}")
        return make_move_with_session(session_data, stockfish_move)
    else:
        print("DEBUG: Stockfish could not generate a move")
        # Game might be over
        board = chess.Board(current_fen)
        game_over, status = get_game_status(board)
        if game_over:
            session_data['game_over'] = True
            session_data['game_result'] = status
            print(f"DEBUG: Game ended: {status}")
        
        board_image = create_chess_board_image(current_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
        return session_data, board_image, current_fen

def make_llm_move(session_data):
    """Make an LLM move automatically"""
    if not should_llm_move(session_data) or session_data.get('game_over', False):
        current_fen = session_data.get('current_fen', DEFAULT_FEN)
        board_image = create_chess_board_image(current_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
        return session_data, board_image, current_fen
    
    current_fen = session_data.get('current_fen', DEFAULT_FEN)
    llm_move = validate_and_get_gemini_move(session_data)
    
    if llm_move:
        print(f"DEBUG: Executing LLM move: {llm_move}")
        # Clear rate limit state on successful move (cooldown expired)
        if session_data.get('rate_limit_active'):
            print("DEBUG: Rate limit cooldown completed, clearing rate limit state")
            session_data.pop('rate_limit_active', None)
            session_data.pop('rate_limit_message', None)
            session_data.pop('last_rate_limit_delay', None)
            session_data.pop('last_retry_reason', None)
        return make_move_with_session(session_data, llm_move)
    else:
        print("DEBUG: LLM could not generate a valid move")
        # Game might be over or LLM failed
        board = chess.Board(current_fen)
        game_over, status = get_game_status(board)
        if game_over:
            session_data['game_over'] = True
            session_data['game_result'] = status
            print(f"DEBUG: Game ended: {status}")
        
        board_image = create_chess_board_image(current_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
        return session_data, board_image, current_fen

def make_ai_move(session_data):
    """Make an AI move (either Stockfish or LLM) automatically"""
    if should_stockfish_move(session_data):
        return make_stockfish_move(session_data)
    elif should_llm_move(session_data):
        return make_llm_move(session_data)
    else:
        # No AI should move
        current_fen = session_data.get('current_fen', DEFAULT_FEN)
        board_image = create_chess_board_image(current_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
        return session_data, board_image, current_fen

def reset_board_with_session(session_data):
    """Reset board to starting position and update session"""
    # Preserve player settings and preferences
    white_player = session_data.get('white_player', 'Human')
    black_player = session_data.get('black_player', 'Human')
    stockfish_elo = session_data.get('stockfish_elo', STOCKFISH_ELO)
    user_preferences = session_data.get('user_preferences', {})
    gemini_paid_tier = session_data.get('gemini_paid_tier', False)
    
    session_data.update({
        'current_fen': DEFAULT_FEN,
        'starting_fen': DEFAULT_FEN,
        'move_history': [],
        'last_move': '',
        'white_player': white_player,
        'black_player': black_player,
        'stockfish_elo': stockfish_elo,
        'game_over': False,
        'game_result': '',
        'auto_play_active': False,
        'gemini_paid_tier': gemini_paid_tier,
        'rate_limit_active': False,
        'rate_limit_message': '',
        'last_rate_limit_delay': None,
        'last_retry_reason': None,
        'failed_moves': [],
        'user_preferences': user_preferences
    })
    
    result = create_chess_board_image(DEFAULT_FEN, user_preferences.get('board_size', DEFAULT_BOARD_SIZE))
    if isinstance(result, str):
        print(f"Error resetting board: {result}")
        return session_data, DEFAULT_FEN, None
    else:
        return session_data, DEFAULT_FEN, result

def update_displays_from_session(session_data):
    """Update move history, PGN displays, and turn indicator from session data"""
    move_history = session_data.get('move_history', [])
    current_fen = session_data.get('current_fen', DEFAULT_FEN)
    starting_fen = session_data.get('starting_fen', DEFAULT_FEN)
    game_result = session_data.get('game_result', '')
    
    print(f"DEBUG: Updating displays with move_history: {move_history}")
    print(f"DEBUG: Current FEN: {current_fen}")
    print(f"DEBUG: Starting FEN: {starting_fen}")
    
    # Update move history display with LAN notation
    move_history_text = get_lan_move_history_from_session(session_data)
    
    # Update PGN display
    if move_history:
        # Use the starting FEN for this game session
        pgn_text = generate_pgn_from_moves(move_history, starting_fen)
    elif current_fen != DEFAULT_FEN:
        # No move history but not at default starting position - show position info
        pgn_text = f"Current position (no move history):\nFEN: {current_fen}"
    else:
        pgn_text = 'No moves yet'
    
    # Update turn indicator
    turn_text = get_turn_from_fen(current_fen)
    
    # Game status (separate from turn for better visibility)
    game_status = game_result if game_result else ""
        
    print(f"DEBUG: Generated PGN: {pgn_text[:100]}...")
    print(f"DEBUG: Turn: {turn_text}")
    print(f"DEBUG: Game Status: {game_status}")
    print(f"DEBUG: LAN move history: {move_history_text}")
    
    return move_history_text, pgn_text, turn_text, game_status

def toggle_theme_and_save(session_data):
    """Toggle theme preference and save to session"""
    current_dark = session_data.get('user_preferences', {}).get('dark_mode', False)
    if 'user_preferences' not in session_data:
        session_data['user_preferences'] = {}
    session_data['user_preferences']['dark_mode'] = not current_dark
    return session_data

def create_chess_app():
    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        # BrowserState for session persistence
        browser_session = gr.BrowserState(create_default_session())
        
        # Timer for auto-play functionality  
        auto_play_timer = gr.Timer(value=STOCKFISH_MOVE_DELAY, active=False)
        
        # Sidebar
        with gr.Sidebar(open=False):
            toggle_dark = gr.Button("🌙 Dark Mode", variant="secondary", elem_id="theme-toggle")
        
        # Header with theme toggle
        with gr.Row():
            gr.Markdown("# ♟️ ChessMate AI")
        
        
        # AI Engine status
        engine_status = []
        if STOCKFISH:
            engine_status.append("✅ **Stockfish Engine: Ready**")
        else:
            engine_status.append("❌ **Stockfish Engine: Not Available** - Install with: `brew install stockfish` (macOS) or `sudo apt install stockfish` (Ubuntu)")
        
        if GEMINI_CLIENT:
            engine_status.append("✅ **Gemini LLM: Ready**")
        else:
            engine_status.append("❌ **Gemini LLM: Not Available** - Set GOOGLE_API_KEY environment variable")
        
        gr.Markdown("\n\n".join(engine_status))
        
        # Main content area
        with gr.Row():
            # Left column - Chess board display
            with gr.Column(scale=1):
                gr.Markdown("### Chess Board")
                
                # Display board as image with proper container sizing
                initial_board = create_chess_board_image()
                if isinstance(initial_board, str):
                    initial_board = None

                board_image = gr.Image(
                    value=initial_board,
                    label="Chess Board",
                    show_label=False,
                    container=True,
                    width="100%"
                )
                
                # Game status display (separate from turn indicator)
                game_status_display = gr.Markdown(
                    value="",
                    visible=True,
                    elem_id="game-status"
                )
                
            # Right column - Controls with tabs
            with gr.Column(scale=1):
                with gr.Tabs():
                    # Tab 1: Make a Move
                    with gr.TabItem("Make a Move"):
                        # Player settings
                        gr.Markdown("### ⚙️ Player Settings")
                        with gr.Row():
                            white_player = gr.Dropdown(
                                choices=["Human", "Stockfish", "LLM (Gemini)"],
                                value="LLM (Gemini)",
                                label="White Player",
                                scale=1
                            )
                            black_player = gr.Dropdown(
                                choices=["Human", "Stockfish", "LLM (Gemini)"], 
                                value="Stockfish",
                                label="Black Player",
                                scale=1
                            )
                        
                        # Stockfish Settings
                        gr.Markdown("### 🤖 Stockfish Strength")
                        with gr.Row():
                            stockfish_elo = gr.Slider(
                                minimum=800,
                                maximum=3000,
                                value=STOCKFISH_ELO,
                                step=50,
                                label="Stockfish ELO Rating",
                                info="Engine playing strength (800=Beginner, 1500=Intermediate, 2500=Master, 3000=Superhuman)"
                            )
                        
                        # Turn indicator
                        turn_display = gr.Textbox(
                            label="Current Turn",
                            value="White to move",
                            interactive=False,
                            lines=1
                        )
                        
                        # Move input
                        move_input = gr.Textbox(
                            label="Move (SAN notation)",
                            placeholder="e.g., e4, Nf3, O-O",
                            value=""
                        )
                        with gr.Row():
                            move_btn = gr.Button("Play Move", variant="primary", scale=2)
                            stockfish_move_btn = gr.Button("🤖 AI Move", variant="secondary", scale=1)
                        
                        # Auto-play controls
                        gr.Markdown("### 🎮 Auto-Play (AI vs AI)")
                        with gr.Row():
                            auto_play_btn = gr.Button("▶️ Start Auto-Play", variant="secondary", scale=1)
                            stop_auto_btn = gr.Button("⏹️ Stop Auto-Play", variant="secondary", scale=1)
                        
                        # API Configuration for LLM
                        gr.Markdown("### 🔧 LLM Configuration")
                        gemini_paid_tier = gr.Checkbox(
                            label="Gemini Pro - Paid Tier 1 (150 RPM)",
                            value=False,
                            info="Enable for paid API plan with higher rate limits"
                        )
                        
                        # Move history display
                        move_history_display = gr.Textbox(
                            label="Move History (LAN)", 
                            lines=3,
                            interactive=False,
                            value=""
                        )
                    
                    # Tab 2: Board Controls
                    with gr.TabItem("Board Controls"):
                        fen_input = gr.Textbox(
                            label="FEN Position",
                            value=DEFAULT_FEN,
                            placeholder="Enter FEN notation...",
                            lines=2
                        )
                        
                        update_btn = gr.Button("Update Board", variant="primary")
                        
                        gr.Markdown("### PGN Game")
                        pgn_display = gr.Textbox(
                            label="PGN for Game",
                            lines=6,
                            max_lines=10,
                            placeholder="PGN will appear here when moves are made...",
                            interactive=True,
                            info="View current game PGN or paste PGN to load a game"
                        )
                        
                        update_from_pgn_btn = gr.Button("Load from PGN", variant="primary")
                        
                        gr.Markdown("### Controls")
                        with gr.Row():
                            reset_btn = gr.Button("New Game", variant="secondary")
                            clear_session_btn = gr.Button("Clear Session", variant="secondary")
        
        # Load session data on startup
        @demo.load(inputs=[browser_session], outputs=[fen_input, board_image, move_history_display, pgn_display, turn_display, game_status_display, white_player, black_player, stockfish_elo, gemini_paid_tier])
        def load_session_on_startup(session_data):
            """Load and apply session data on page load"""
            print(f"Loading session: {session_data}")
            
            current_fen = session_data.get('current_fen', DEFAULT_FEN)
            move_history = session_data.get('move_history', [])
            move_history_text = get_lan_move_history_from_session(session_data)
            
            # Create board image
            board_result = create_chess_board_image(current_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
            board_img = board_result if not isinstance(board_result, str) else None
            
            # Generate PGN for current game
            starting_fen = session_data.get('starting_fen', DEFAULT_FEN)
            if move_history:
                pgn_text = generate_pgn_from_moves(move_history, starting_fen)
            elif current_fen != DEFAULT_FEN:
                pgn_text = f"Current position (no move history):\nFEN: {current_fen}"
            else:
                pgn_text = "No moves yet"
            
            # Get turn indicator and game status
            turn_text = get_turn_from_fen(current_fen)
            game_status = session_data.get('game_result', '')
            
            # Get player settings
            white_p = session_data.get('white_player', 'Human')
            black_p = session_data.get('black_player', 'Human')
            elo = session_data.get('stockfish_elo', STOCKFISH_ELO)
            paid_tier = session_data.get('gemini_paid_tier', False)
            
            return current_fen, board_img, move_history_text, pgn_text, turn_text, game_status, white_p, black_p, elo, paid_tier
        
        # Apply theme AFTER session is loaded
        demo.load(
            fn=None,
            inputs=[browser_session],
            js="""
            (session_data) => {
                console.log('Applying theme from session:', session_data);
                const darkMode = session_data?.user_preferences?.dark_mode || false;
                console.log('Dark mode from session:', darkMode);
                
                // Apply theme immediately
                if (darkMode) {
                    document.body.classList.add('dark');
                } else {
                    document.body.classList.remove('dark');
                }
                
                // Update theme button with delay to ensure it exists
                setTimeout(() => {
                    const themeButton = document.getElementById('theme-toggle');
                    if (themeButton) {
                        themeButton.textContent = darkMode ? '☀️ Light Mode' : '🌙 Dark Mode';
                        console.log('Updated theme button to:', themeButton.textContent);
                    } else {
                        console.log('Theme button not found');
                    }
                }, 200);
                
                return session_data;
            }
            """,
            outputs=[browser_session]
        )
        
        # Theme toggle with session save
        toggle_dark.click(
            fn=toggle_theme_and_save,
            inputs=[browser_session],
            outputs=[browser_session]
        ).then(
            fn=None,
            inputs=[browser_session],
            js="""
            (session_data) => {
                console.log('Theme toggle - session data:', session_data);
                const isDark = session_data?.user_preferences?.dark_mode || false;
                console.log('Setting dark mode to:', isDark);
                
                // Apply theme
                if (isDark) {
                    document.body.classList.add('dark');
                } else {
                    document.body.classList.remove('dark');
                }
                
                // Update button text
                const themeButton = document.getElementById('theme-toggle');
                if (themeButton) {
                    themeButton.textContent = isDark ? '☀️ Light Mode' : '🌙 Dark Mode';
                    console.log('Updated button to:', themeButton.textContent);
                }
                
                console.log('Theme toggled, session auto-saved');
                return session_data;
            }
            """,
            outputs=[browser_session]
        )
        
        # Player settings update
        def update_player_settings(session_data, white_p, black_p, elo, paid_tier):
            """Update player settings and Stockfish configuration"""
            session_data['white_player'] = white_p
            session_data['black_player'] = black_p
            session_data['stockfish_elo'] = elo
            session_data['gemini_paid_tier'] = paid_tier
            
            # Update Stockfish engine settings
            update_stockfish_settings(elo)
            
            # Log rate limit configuration
            if paid_tier:
                print("DEBUG: Gemini configured for paid tier (150 RPM)")
            else:
                print("DEBUG: Gemini configured for free tier (10 RPM)")
            
            return session_data
        
        # Wire up player settings changes
        for component in [white_player, black_player, stockfish_elo, gemini_paid_tier]:
            component.change(
                fn=update_player_settings,
                inputs=[browser_session, white_player, black_player, stockfish_elo, gemini_paid_tier],
                outputs=[browser_session]
            )
        
        # Board update functionality
        update_btn.click(
            fn=update_board_from_fen,
            inputs=[fen_input, browser_session],
            outputs=[board_image, browser_session]
        ).then(
            fn=update_displays_from_session,
            inputs=[browser_session],
            outputs=[move_history_display, pgn_display, turn_display, game_status_display]
        )
        
        # PGN update functionality
        update_from_pgn_btn.click(
            fn=update_from_pgn,
            inputs=[pgn_display, browser_session],
            outputs=[browser_session, board_image, fen_input]
        ).then(
            fn=update_displays_from_session,
            inputs=[browser_session],
            outputs=[move_history_display, pgn_display, turn_display, game_status_display]
        )
        
        # Make move functionality
        def handle_move_and_update(session_data, move_text):
            """Handle move and update all displays"""
            session_data, board_img, fen = make_move_with_session(session_data, move_text)
            move_history_text, pgn_text, turn_text, game_status = update_displays_from_session(session_data)
            return session_data, board_img, fen, move_history_text, pgn_text, turn_text, game_status, ""
        
        move_btn.click(
            fn=handle_move_and_update,
            inputs=[browser_session, move_input],
            outputs=[browser_session, board_image, fen_input, move_history_display, pgn_display, turn_display, game_status_display, move_input]
        )
        
        # Enter key support for move input
        move_input.submit(
            fn=handle_move_and_update,
            inputs=[browser_session, move_input],
            outputs=[browser_session, board_image, fen_input, move_history_display, pgn_display, turn_display, game_status_display, move_input]
        )
        
        # Manual AI move (Stockfish or LLM)
        def handle_ai_move_manual(session_data):
            """Handle manual AI move"""
            if session_data.get('game_over', False):
                print("Game is over!")
                current_fen = session_data.get('current_fen', DEFAULT_FEN)
                board_img = create_chess_board_image(current_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
                move_history_text, pgn_text, turn_text, game_status = update_displays_from_session(session_data)
                return session_data, board_img, current_fen, move_history_text, pgn_text, turn_text, game_status
            
            if not should_ai_move(session_data):
                print("It's not an AI player's turn!")
                current_fen = session_data.get('current_fen', DEFAULT_FEN)
                board_img = create_chess_board_image(current_fen, session_data.get('user_preferences', {}).get('board_size', DEFAULT_BOARD_SIZE))
                move_history_text, pgn_text, turn_text, game_status = update_displays_from_session(session_data)
                return session_data, board_img, current_fen, move_history_text, pgn_text, turn_text, game_status
                
            session_data, board_img, fen = make_ai_move(session_data)
            move_history_text, pgn_text, turn_text, game_status = update_displays_from_session(session_data)
            return session_data, board_img, fen, move_history_text, pgn_text, turn_text, game_status
        
        stockfish_move_btn.click(
            fn=handle_ai_move_manual,
            inputs=[browser_session],
            outputs=[browser_session, board_image, fen_input, move_history_display, pgn_display, turn_display, game_status_display]
        )
        
        # Auto-play functionality using gr.Timer
        def start_auto_play(session_data):
            """Start auto-play mode"""
            if session_data.get('game_over', False):
                print("Game is over! Start a new game for auto-play.")
                return session_data, gr.Timer(active=False)
            
            white_is_ai = session_data.get('white_player') in ['Stockfish', 'LLM (Gemini)']
            black_is_ai = session_data.get('black_player') in ['Stockfish', 'LLM (Gemini)']
            
            if not (white_is_ai or black_is_ai):
                print("Auto-play requires at least one AI player (Stockfish or LLM)!")
                return session_data, gr.Timer(active=False)
            
            session_data['auto_play_active'] = True
            
            # Clear any stale rate limit states when starting auto-play
            session_data.pop('rate_limit_active', None)
            session_data.pop('rate_limit_message', None)
            session_data.pop('last_rate_limit_delay', None)
            session_data.pop('last_retry_reason', None)
            
            # Get appropriate delay for the current game setup
            initial_delay = get_move_delay_for_session(session_data)
            print(f"Auto-play started with {initial_delay}s delay!")
            
            # Start the timer with appropriate delay
            return session_data, gr.Timer(value=initial_delay, active=True)
        
        def stop_auto_play(session_data):
            """Stop auto-play mode"""
            session_data['auto_play_active'] = False
            print("Auto-play stopped.")
            return session_data, gr.Timer(active=False)
        
        def auto_play_tick(session_data):
            """Handle auto-play timer tick with rate limit modal handling"""
            # Check if auto-play should continue
            if not session_data.get('auto_play_active', False):
                return session_data, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.Timer(active=False)
            
            # Check if game is over
            if session_data.get('game_over', False):
                session_data['auto_play_active'] = False
                print("Game finished! Auto-play stopped.")
                # Clear any rate limit status
                session_data.pop('rate_limit_active', None)
                session_data.pop('rate_limit_message', None)
                session_data.pop('last_rate_limit_delay', None)
                return session_data, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.Timer(active=False)
            
            # Check if we're in a rate limit cooldown
            if session_data.get('rate_limit_active'):
                rate_limit_delay = session_data.get('last_rate_limit_delay', 63)
                rate_limit_msg = session_data.get('rate_limit_message', f"⏳ Waiting {rate_limit_delay}s for rate limit reset...")
                
                print(f"DEBUG: In rate limit cooldown, continuing timer with {rate_limit_delay}s")
                
                # Update game status to show rate limit message
                return (session_data, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), 
                        rate_limit_msg, gr.Timer(value=rate_limit_delay, active=True))
            
            # Check if it's an AI player's turn
            if not should_ai_move(session_data):
                # Not AI's turn, keep timer running with current delay
                current_delay = get_move_delay_for_session(session_data)
                return session_data, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.Timer(value=current_delay, active=True)
            
            # Make AI move
            if should_stockfish_move(session_data):
                print("DEBUG: Auto-play timer tick - making Stockfish move")
                session_data, board_img, fen = make_stockfish_move(session_data)
            elif should_llm_move(session_data):
                print("DEBUG: Auto-play timer tick - making LLM move")
                session_data, board_img, fen = make_llm_move(session_data)
                
                # Check if we hit a rate limit during the LLM move
                if session_data.get('rate_limit_active'):
                    rate_limit_delay = session_data.get('last_rate_limit_delay', 63)
                    rate_limit_msg = session_data.get('rate_limit_message', f"⏳ Waiting {rate_limit_delay}s for rate limit reset...")
                    
                    print(f"DEBUG: Rate limit hit during LLM move, entering cooldown")
                    
                    # Update displays but continue timer with rate limit delay
                    move_history_text, pgn_text, turn_text, _ = update_displays_from_session(session_data)
                    
                    return (session_data, board_img, fen, move_history_text, pgn_text, turn_text,
                            rate_limit_msg, gr.Timer(value=rate_limit_delay, active=True))
            else:
                # This shouldn't happen, but handle gracefully
                current_delay = get_move_delay_for_session(session_data)
                return session_data, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.Timer(value=current_delay, active=True)
            
            move_history_text, pgn_text, turn_text, game_status = update_displays_from_session(session_data)
            
            # Check if game ended after this move
            if session_data.get('game_over', False):
                session_data['auto_play_active'] = False
                print("Game finished! Auto-play stopped.")
                # Clear any rate limit status
                session_data.pop('rate_limit_active', None)
                session_data.pop('rate_limit_message', None)
                session_data.pop('last_rate_limit_delay', None)
                return session_data, board_img, fen, move_history_text, pgn_text, turn_text, game_status, gr.Timer(active=False)
            
            # Determine delay for next move based on upcoming player
            next_delay = get_move_delay_for_session(session_data)
            
            print(f"DEBUG: Continuing auto-play with {next_delay}s delay")
            
            # Continue timer with appropriate delay
            return session_data, board_img, fen, move_history_text, pgn_text, turn_text, game_status, gr.Timer(value=next_delay, active=True)

        
        # Wire up auto-play controls
        auto_play_btn.click(
            fn=start_auto_play,
            inputs=[browser_session],
            outputs=[browser_session, auto_play_timer]
        )
        
        stop_auto_btn.click(
            fn=stop_auto_play,
            inputs=[browser_session],
            outputs=[browser_session, auto_play_timer]
        )
        
        # Wire up timer tick event
        auto_play_timer.tick(
            fn=auto_play_tick,
            inputs=[browser_session],
            outputs=[browser_session, board_image, fen_input, move_history_display, pgn_display, turn_display, game_status_display, auto_play_timer]
        )
        
        # Reset board (New Game)
        reset_btn.click(
            fn=reset_board_with_session,
            inputs=[browser_session],
            outputs=[browser_session, fen_input, board_image]
        ).then(
            fn=update_displays_from_session,
            inputs=[browser_session],
            outputs=[move_history_display, pgn_display, turn_display, game_status_display]
        ).then(
            fn=lambda session: gr.Timer(active=False),  # Stop auto-play on new game
            inputs=[browser_session],
            outputs=[auto_play_timer]
        )
        
        # Clear session functionality
        clear_session_btn.click(
            fn=lambda: create_default_session(),
            outputs=[browser_session]
        ).then(
            fn=lambda session: (session.get('current_fen', DEFAULT_FEN), 
                               create_chess_board_image(DEFAULT_FEN), 
                               'No moves yet', 
                               'No moves yet', 
                               'White to move',
                               '',
                               session.get('white_player', 'Human'),
                               session.get('black_player', 'Human'),
                               session.get('stockfish_elo', STOCKFISH_ELO),
                               session.get('gemini_paid_tier', False)),
            inputs=[browser_session],
            outputs=[fen_input, board_image, move_history_display, pgn_display, turn_display, game_status_display, white_player, black_player, stockfish_elo, gemini_paid_tier]
        ).then(
            fn=lambda: gr.Timer(active=False),  # Stop auto-play timer
            outputs=[auto_play_timer]
        )
    
    return demo

if __name__ == "__main__":
    print("🚀 Starting Enhanced Chess App with AI Players...")
    print(f"📍 Stockfish path: {get_stockfish_path()}")
    
    if STOCKFISH:
        print("✅ Stockfish engine initialized successfully")
    else:
        print("❌ Stockfish engine not available")
        print("🔧 Install Stockfish: 'brew install stockfish' (macOS) or 'sudo apt install stockfish' (Ubuntu)")
    
    if GEMINI_CLIENT:
        print("✅ Gemini LLM initialized successfully")
    else:
        print("❌ Gemini LLM not available")
        print("🔧 Set GOOGLE_API_KEY environment variable")
    
    print("🌐 Launching enhanced chess interface...")
    
    demo = create_chess_app()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True
    )