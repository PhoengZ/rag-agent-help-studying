import os
import typer
from dotenv import load_dotenv

# Load dot env first before any other imports to populate environment variables
load_dotenv()

app = typer.Typer(help="🚀 Antigravity Agentic RAG CLI Tool")

@app.command()
def sync():
    """Sync and update PDF/text/markdown documents incrementally to local ChromaDB."""
    typer.secho("🔄 Scanning and updating documents...", fg=typer.colors.CYAN, bold=True)
    import sync_manager
    try:
        sync_manager.sync_all_documents()
    except Exception as e:
        typer.secho(f"❌ Error during sync: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

@app.command()
def start():
    """Start the interactive agentic RAG prompt session."""
    typer.secho("🤖 Welcome to Antigravity Agentic RAG CLI!", fg=typer.colors.CYAN, bold=True)
    
    # Pre-flight check: Verify Typhoon API Key
    api_key = os.getenv("TYPHOON_API_KEY")
    if not api_key or api_key == "your_typhoon_api_key_here":
        typer.secho("\n❌ Error: TYPHOON_API_KEY is not set or is using the placeholder value.", fg=typer.colors.RED, err=True)
        typer.echo("Please set the TYPHOON_API_KEY in your '.env' file.", err=True)
        raise typer.Exit(code=1)

    typer.echo("Connecting to local database and preparing Typhoon LLM router...")

    try:
        import query_engine
        router_engine = query_engine.build_agentic_router_engine()
    except ValueError as val_err:
        typer.secho(f"\n⚠️ Setup Alert: {val_err}", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"\n❌ Initialization Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho("\n✨ RAG Agent is ready! (Type 'exit' or 'quit' to close the session)\n", fg=typer.colors.GREEN, bold=True)

    while True:
        try:
            query = typer.prompt("❓ Question")
        except typer.Abort:
            typer.secho("\n👋 Goodbye!", fg=typer.colors.YELLOW)
            break

        if query.lower().strip() in ["exit", "quit"]:
            typer.secho("👋 Goodbye!", fg=typer.colors.YELLOW)
            break

        if not query.strip():
            continue

        typer.secho("🤖 Thinking and routing through document collections...", fg=typer.colors.BLUE)
        
        try:
            response = router_engine.query(query)
            typer.secho("\n" + "="*60, fg=typer.colors.CYAN)
            typer.secho(f"✨ Answer:\n{response}", fg=typer.colors.MAGENTA, bold=True)
            typer.secho("="*60 + "\n", fg=typer.colors.CYAN)
        except Exception as e:
            typer.secho(f"❌ Error compiling query response: {e}\n", fg=typer.colors.RED, err=True)

if __name__ == "__main__":
    app()
