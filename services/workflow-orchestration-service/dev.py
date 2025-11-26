"""
Development helper script for Workflow Orchestration Service
Quick commands for common development tasks
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd: str, description: str):
    """Run a shell command"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"$ {cmd}\n")
    
    result = subprocess.run(cmd, shell=True, cwd=Path(__file__).parent)
    return result.returncode == 0


def main():
    """Main menu"""
    print("""
╔════════════════════════════════════════════════════════════╗
║   Workflow Orchestration Service - Development Helper     ║
╚════════════════════════════════════════════════════════════╝

Select an option:

  1. Initialize database
  2. Start service (local)
  3. Start service (Docker)
  4. Run tests
  5. Run example usage
  6. Check service health
  7. View logs (Docker)
  8. Stop service (Docker)
  9. Rebuild Docker image
  10. Database verification
  11. Drop database tables (⚠️  CAUTION)
  
  0. Exit
""")
    
    choice = input("Enter choice (0-11): ").strip()
    
    if choice == "1":
        run_command("python init_db.py init", "Initializing database")
    
    elif choice == "2":
        print("\n✨ Starting service locally...")
        print("📝 Make sure .env file is configured!")
        print("🌐 Service will be available at http://localhost:8007")
        print("📚 API docs at http://localhost:8007/docs\n")
        run_command("python main.py", "Starting local service")
    
    elif choice == "3":
        run_command(
            "docker-compose up -d workflow-orchestration-service",
            "Starting Docker service"
        )
        print("\n✅ Service started!")
        print("🌐 Access at http://localhost:8107")
        print("📚 API docs at http://localhost:8107/docs")
    
    elif choice == "4":
        print("\n📋 Running tests...")
        # Try basic test first
        if run_command("python test_service.py", "Running basic tests"):
            print("\n✅ Basic tests passed!")
            
            # Ask if want to run full pytest
            full_test = input("\nRun full pytest suite? (y/n): ").lower()
            if full_test == 'y':
                run_command("pytest test_service.py -v", "Running full test suite")
    
    elif choice == "5":
        run_command("python example_usage.py", "Running usage examples")
    
    elif choice == "6":
        print("\n🔍 Checking service health...")
        try:
            import httpx
            import asyncio
            
            async def check():
                async with httpx.AsyncClient() as client:
                    # Try local first
                    try:
                        response = await client.get("http://localhost:8007/health", timeout=2.0)
                        print("✅ Local service (port 8007): HEALTHY")
                        print(f"   {response.json()}")
                    except:
                        print("❌ Local service (port 8007): NOT RUNNING")
                    
                    # Try Docker
                    try:
                        response = await client.get("http://localhost:8107/health", timeout=2.0)
                        print("✅ Docker service (port 8107): HEALTHY")
                        print(f"   {response.json()}")
                    except:
                        print("❌ Docker service (port 8107): NOT RUNNING")
            
            asyncio.run(check())
        except ImportError:
            print("❌ httpx not installed. Run: pip install httpx")
    
    elif choice == "7":
        run_command(
            "docker-compose logs -f --tail=100 workflow-orchestration-service",
            "Viewing Docker logs"
        )
    
    elif choice == "8":
        run_command(
            "docker-compose stop workflow-orchestration-service",
            "Stopping Docker service"
        )
    
    elif choice == "9":
        run_command(
            "docker-compose build workflow-orchestration-service",
            "Rebuilding Docker image"
        )
        print("\n✅ Image rebuilt! Start with option 3.")
    
    elif choice == "10":
        run_command("python init_db.py verify", "Verifying database")
    
    elif choice == "11":
        print("\n⚠️  WARNING: This will DELETE all data!")
        confirm = input("Type 'DELETE' to confirm: ")
        if confirm == "DELETE":
            run_command("python init_db.py drop", "Dropping tables")
        else:
            print("Cancelled.")
    
    elif choice == "0":
        print("\n👋 Goodbye!")
        return
    
    else:
        print("\n❌ Invalid choice!")
    
    # Ask to continue
    input("\n\nPress Enter to continue...")
    main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
