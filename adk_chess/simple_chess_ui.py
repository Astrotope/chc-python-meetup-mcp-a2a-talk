#!/usr/bin/env python3
"""
Simple Chess UI - Gradio interface for ADK Chess Orchestrator
"""

import asyncio
import threading
import time
import uuid
from typing import Optional
import json
import os

import gradio as gr
import chess
import chess.svg
from PIL import Image
import io
from dotenv import load_dotenv

# Load environment variables from local .env file
load_dotenv(".env")

try:
    import cairosvg
    SVG_AVAILABLE = True
except ImportError:
    print("cairosvg not available - using fallback board display")
    SVG_AVAILABLE = False

from google.adk.runners import InMemoryRunner
from google.genai import types
from orchestrator_agent.agent import root_agent
from chess_game_manager import ChessGameManager
import logging
import warnings

warnings.filterwarnings("ignore", message=".*\[EXPERIMENTAL\].*", category=UserWarning)

logger = logging.getLogger(__name__)
log_level = getattr(logging, os.getenv('ADK_LOG_LEVEL', 'WARNING').upper())
logging.basicConfig(level=log_level)

# Suppress INFO logging
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_adk").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("google.adk").setLevel(logging.WARNING)
logging.getLogger("google.genai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Constants
DEFAULT_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
BOARD_SIZE = 800
APP_NAME = "simple_chess_ui"
USER_ID = "ui_user"
SESSION_ID = "chess_ui_session"

def create_default_browser_session():
    """Create minimal browser session data"""
    return {
        'browser_id': f"browser_{str(uuid.uuid4())[:8]}",
        'current_game_id': None,  # Link to active game
        'user_preferences': {
            'dark_mode': False
        }
    }

class SimpleChessUI:
    """Simple chess UI manager"""

    def __init__(self):
        # ADK setup
        self.runner = InMemoryRunner(
            app_name=APP_NAME,
            agent=root_agent
        )
        self.session = None
        self.current_fen = DEFAULT_FEN
        self.last_move = None
        self.game_active = False
        self.last_update = time.time()

    async def initialize_session(self, browser_session=None):
        """Initialize ADK session with browser session ID"""
        if not self.session:
            # Include browser session ID in initial state if provided
            initial_state = {}
            if browser_session and 'browser_id' in browser_session:
                initial_state["browser_session_id"] = browser_session['browser_id']
                print(f"🔗 Initializing ADK session with browser ID: {browser_session['browser_id']}")

            self.session = await self.runner.session_service.create_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID,
                state=initial_state
            )
        return self.session

    def svg_to_png(self, svg_string: str) -> Image.Image:
        """Convert SVG chess board to PNG image"""
        if SVG_AVAILABLE:
            try:
                png_data = cairosvg.svg2png(
                    bytestring=svg_string.encode('utf-8'),
                    output_width=BOARD_SIZE,
                    output_height=BOARD_SIZE
                )
                image = Image.open(io.BytesIO(png_data))

                # Force RGBA mode to preserve transparency
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')

                return image
            except Exception as e:
                print(f"SVG conversion error: {e}")

        # Fallback: create simple placeholder
        img = Image.new('RGB', (BOARD_SIZE, BOARD_SIZE), color='lightgray')
        return img

    def get_board_image_from_session(self, browser_session: dict) -> Image.Image:
        """Generate board image from browser session data"""
        if not browser_session or 'browser_id' not in browser_session:
            return self.get_board_image()

        # Get game state from game manager
        game_manager = ChessGameManager.get_for_browser(browser_session['browser_id'])
        current_fen = game_manager.get_fen()

        # Get last move for highlighting
        move_history = game_manager.move_history()
        last_move = move_history[-1] if move_history else None

        return self.get_board_image(current_fen, last_move)

    def get_board_image(self, fen: str = None, last_move: str = None) -> Image.Image:
        """Generate chess board image from FEN with enhanced styling"""
        if fen is None:
            fen = self.current_fen

        try:
            board = chess.Board(fen)
            square_size = BOARD_SIZE // 8
            actual_board_size = square_size * 8

            fill = {}
            arrows = []
            lastmove_obj = None

            # Add last move highlighting if provided
            if last_move and len(last_move) >= 4:
                try:
                    lastmove_obj = chess.Move.from_uci(last_move)
                    to_square = lastmove_obj.to_square
                    from_square = lastmove_obj.from_square

                    # Show attacks from the destination square
                    fill = dict.fromkeys(board.attacks(to_square), "#ff0000aa")

                    # Add last move highlighting
                    fill[from_square] = "#fdd90dac"  # From square
                    fill[to_square] = "#fdd90dac"    # To square

                    # Add arrow for last move
                    arrows = [chess.svg.Arrow(from_square, to_square, color="#2fac104d")]

                except (ValueError, chess.InvalidMoveError) as e:
                    print(f"Invalid UCI move '{last_move}': {e}")
                    lastmove_obj = None
                    fill = {}
                    arrows = []

            svg_data = chess.svg.board(
                board=board,
                fill=fill,
                arrows=arrows,
                colors={
                    'margin': '#30ac10',
                    'square light': '#8ec1ef',
                    'square dark': '#eeefe7',
                },
                size=actual_board_size,
                lastmove=lastmove_obj
            )

            return self.svg_to_png(svg_data)
        except Exception as e:
            print(f"Error generating board image: {e}")
            return Image.new('RGB', (BOARD_SIZE, BOARD_SIZE), color='lightgray')

    async def send_begin_command(self, browser_session=None):
        """Send 'begin' command to orchestrator agent"""
        print("🎮 Sending 'begin' command to orchestrator...")
        try:
            await self.initialize_session(browser_session)

            content = types.Content(
                role="user",
                parts=[types.Part(text="begin")]
            )

            # Send command to orchestrator (this will start automated gameplay)
            async for event in self.runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=content
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(f"🎮 Orchestrator response: {part.text[:100]}...")

            self.game_active = True
            print("🎮 Game started! Orchestrator will play automatically.")

        except Exception as e:
            error_msg = f"❌ Error starting game: {e}"
            print(error_msg)
            return error_msg

    async def update_board_state(self, browser_session=None):
        """Update board state from browser-scoped ChessGameManager"""
        try:
            if not browser_session or 'browser_id' not in browser_session:
                print("⚠️ No browser session available for board update")
                return

            # Get the browser-scoped game manager instance
            game_manager = ChessGameManager.get_for_browser(browser_session['browser_id'])
            new_fen = game_manager.get_fen()

            if new_fen != self.current_fen:
                print(f"🔄 Board updated: {new_fen}")
                # Get the last move from move history
                move_history = game_manager.move_history()
                if move_history:
                    self.last_move = move_history[-1]
                else:
                    self.last_move = None

                self.current_fen = new_fen
                self.last_update = time.time()

        except Exception as e:
            print(f"⚠️ Error updating board state: {e}")

# Global UI instance
chess_ui = SimpleChessUI()

# Gradio Interface Functions
def start_game(browser_session):
    """Start button handler"""
    print("🟢 Start button pressed!")

    # Initialize browser session if needed
    if not browser_session:
        browser_session = create_default_browser_session()
    elif 'browser_id' not in browser_session:
        browser_session['browser_id'] = f"browser_{str(uuid.uuid4())[:8]}"

    # Mark game as active in browser session
    browser_session['game_active'] = True

    # Start orchestrator in background thread so it doesn't block the UI
    def run_orchestrator():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(chess_ui.send_begin_command(browser_session))
        except Exception as e:
            print(f"Orchestrator error: {e}")
            browser_session['game_active'] = False
        finally:
            loop.close()

    # Start orchestrator in background
    threading.Thread(target=run_orchestrator, daemon=True).start()

    # Return immediately with active button state
    board_image = chess_ui.get_board_image_from_session(browser_session)
    return browser_session, board_image, "Game Started! Orchestrator playing automatically...", gr.update(interactive=False, value="🔄 Game Running...")

def update_board(browser_session):
    """Periodic board update"""
    if not browser_session:
        browser_session = create_default_browser_session()

    # Update board state from browser session
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(chess_ui.update_board_state(browser_session))
    finally:
        loop.close()

    # Check if game ended
    if browser_session.get('browser_id'):
        game_manager = ChessGameManager.get_for_browser(browser_session['browser_id'])
        if game_manager.is_gameover():
            browser_session['game_active'] = False
        elif chess_ui.game_active and 'game_active' not in browser_session:
            # If orchestrator is active but session doesn't reflect it, set it
            browser_session['game_active'] = True

    # Get board image from session
    board_image = chess_ui.get_board_image_from_session(browser_session)

    # Return current board image and status
    status = f"FEN: {chess_ui.current_fen}"
    if chess_ui.last_move:
        status += f" | Last move: {chess_ui.last_move}"
    if chess_ui.game_active:
        status += f" | Updated: {time.time() - chess_ui.last_update:.1f}s ago"

    # Return button state based on game activity - check both session and global state
    game_active = browser_session.get('game_active', False) or chess_ui.game_active
    if game_active:
        button_update = gr.update(interactive=False, value="🔄 Game Running...")
    else:
        button_update = gr.update(interactive=True, value="🟢 Start Game")
    
    return browser_session, board_image, status, button_update

def get_initial_display(browser_session):
    """Get initial board display"""
    if not browser_session:
        browser_session = create_default_browser_session()

    board_image = chess_ui.get_board_image_from_session(browser_session)
    
    # Check if game is active to set correct button state
    game_active = browser_session.get('game_active', False)
    if game_active:
        button_update = gr.update(interactive=False, value="🔄 Game Running...")
    else:
        button_update = gr.update(interactive=True, value="🟢 Start Game")
    
    return browser_session, board_image, f"Ready to start | FEN: {chess_ui.current_fen}", button_update

def toggle_theme_and_save(session_data):
    """Toggle theme and save to session"""
    if session_data is None:
        session_data = {}
    if 'user_preferences' not in session_data:
        session_data['user_preferences'] = {}

    # Toggle dark mode
    current_dark = session_data['user_preferences'].get('dark_mode', False)
    session_data['user_preferences']['dark_mode'] = not current_dark

    print(f"🎨 Theme toggled to: {'Dark' if not current_dark else 'Light'} mode")
    return session_data

# Create Gradio Interface
def create_interface():
    """Create the enhanced chess interface"""

    with gr.Blocks(theme=gr.themes.Soft(), title="Enhanced Chess UI") as demo:

        gr.Markdown("# ♟️ Enhanced ADK Chess Interface")
        gr.Markdown("Watch the AI agents play chess with move highlighting and attack visualization!")

        # Browser session state for theme persistence and game linking
        browser_session = gr.BrowserState(create_default_browser_session())

        # Sidebar with theme toggle
        with gr.Sidebar(open=False):
            toggle_dark = gr.Button("🌙 Dark Mode", variant="secondary", elem_id="theme-toggle")

        with gr.Row():
            # Left column - Chess board display (80% width)
            with gr.Column(scale=4):
                gr.Markdown("### Chess Board")

                # Display board as image with proper container sizing
                initial_board = chess_ui.get_board_image(last_move=chess_ui.last_move)

                board_image = gr.Image(
                    value=initial_board,
                    label="Chess Board",
                    show_label=False,
                    container=True,
                    width="100%"
                )

                # Start Button
                start_btn = gr.Button("🟢 Start Game", variant="primary", size="lg")

            # Right column - Game info
            with gr.Column(scale=1):
                gr.Markdown("### Game Status")

                # Status Display
                status_display = gr.Textbox(
                    label="Current State",
                    interactive=False,
                    lines=4,
                    placeholder="Game status will appear here..."
                )

                gr.Markdown("### Game Legend")
                gr.Markdown("""
                - **Yellow squares**: Last move (from/to)
                - **Red squares**: Squares attacked by last moved piece
                - **Green arrow**: Last move direction
                - **Auto-refresh**: Updates every second during gameplay
                """)

        # Event handlers
        start_btn.click(
            fn=start_game,
            inputs=[browser_session],
            outputs=[browser_session, board_image, status_display, start_btn]
        )

        # Initialize theme on load
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
        ).then(
            fn=get_initial_display,
            inputs=[browser_session],
            outputs=[browser_session, board_image, status_display, start_btn]
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

        # Set up periodic refresh for board updates
        timer = gr.Timer(1.0)  # Update every 1 second
        timer.tick(
            fn=update_board,
            inputs=[browser_session],
            outputs=[browser_session, board_image, status_display, start_btn]
        )

    return demo

if __name__ == "__main__":
    print("🎮 Starting Enhanced Chess UI...")
    print("🔧 Creating Gradio interface...")
    demo = create_interface()
    print("✅ Gradio interface created successfully")

    # Get port from environment or use default
    port = int(os.getenv("GRADIO_PORT", 7865))
    print(f"🚀 Launching Gradio on 0.0.0.0:{port}")

    demo.launch(
        server_name="0.0.0.0",  # Bind to all interfaces for Docker compatibility
        server_port=port,
        share=False,
        debug=True
    )
    print("✅ Gradio launched successfully")
