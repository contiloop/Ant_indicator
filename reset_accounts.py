#!/usr/bin/env python3
"""
Account Reset Script
Reset trader accounts to initial state and clean up related data.
"""

import sys
from pathlib import Path
import argparse

# Add project root path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.accounts.accounts import Account
from src.trading.database import clear_analyzed_videos


def reset_trader_account(trader_name: str, strategy: str = None):
    """Reset specific trader account"""
    try:
        account = Account.get(trader_name)
        
        print(f"📊 Status before reset:")
        print(f"   - Account: {account.name}")
        print(f"   - Balance: ${account.balance:.2f}")
        print(f"   - Holdings: {account.holdings}")
        print(f"   - Transactions: {len(account.transactions)} trades")
        
        # Reset account
        reset_strategy = strategy or "YouTuber-based AI investment strategy"
        account.reset(reset_strategy)
        
        print(f"\n✅ Account reset completed:")
        print(f"   - Balance: ${account.balance:.2f}")
        print(f"   - Strategy: {account.strategy}")
        print(f"   - Holdings: {account.holdings}")
        print(f"   - Transactions: cleared")
        
        return True
        
    except Exception as e:
        print(f"❌ Account reset failed: {e}")
        return False


def reset_analyzed_videos(trader_name: str = None):
    """Reset analyzed video records"""
    try:
        if trader_name:
            clear_analyzed_videos(trader_name)
            print(f"✅ {trader_name} video analysis records cleared")
        else:
            clear_analyzed_videos()
            print("✅ All video analysis records cleared")
        return True
    except Exception as e:
        print(f"❌ Video analysis records reset failed: {e}")
        return False


def reset_memory_db(trader_name: str = None):
    """Reset memory DB (Researcher's knowledge graph)"""
    try:
        memory_dir = Path("./memory")
        
        if trader_name:
            # Delete specific trader's memory DB only
            memory_file = memory_dir / f"{trader_name}.db"
            if memory_file.exists():
                memory_file.unlink()
                print(f"✅ {trader_name} memory DB deleted: {memory_file}")
            else:
                print(f"ℹ️  {trader_name} memory DB not found: {memory_file}")
        else:
            # Delete all memory DBs
            if memory_dir.exists():
                deleted_count = 0
                for db_file in memory_dir.glob("*.db"):
                    db_file.unlink()
                    print(f"✅ Memory DB deleted: {db_file}")
                    deleted_count += 1
                
                if deleted_count == 0:
                    print("ℹ️  No memory DBs to delete")
                else:
                    print(f"✅ Total {deleted_count} memory DBs deleted")
            else:
                print("ℹ️  Memory directory does not exist")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory DB reset failed: {e}")
        return False


def list_memory_dbs():
    """List memory DB files"""
    try:
        memory_dir = Path("./memory")
        if memory_dir.exists():
            db_files = list(memory_dir.glob("*.db"))
            if db_files:
                print("💾 Current memory DBs:")
                for db_file in db_files:
                    size_mb = db_file.stat().st_size / (1024 * 1024)
                    print(f"   - {db_file.name}: {size_mb:.2f}MB")
            else:
                print("💾 No memory DBs found")
        else:
            print("💾 Memory directory not found")
    except Exception as e:
        print(f"❌ Memory DB listing failed: {e}")


def list_traders():
    """List current registered traders"""
    try:
        import sqlite3
        conn = sqlite3.connect("accounts.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM accounts")
        traders = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if traders:
            print("📋 Current registered traders:")
            for trader in traders:
                account = Account.get(trader)
                print(f"   - {trader}: ${account.balance:.2f}, {len(account.holdings)} stocks")
        else:
            print("📋 No traders registered")
            
    except Exception as e:
        print(f"❌ Trader listing failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Reset trader accounts and data")
    parser.add_argument("--trader", "-t", type=str, help="Trader name to reset")
    parser.add_argument("--strategy", "-s", type=str, help="Investment strategy to set")
    parser.add_argument("--videos", "-v", action="store_true", help="Also reset video analysis records")
    parser.add_argument("--memory", "-m", action="store_true", help="Also reset memory DB")
    parser.add_argument("--all", "-a", action="store_true", help="Reset account + videos + memory all")
    parser.add_argument("--all-videos", action="store_true", help="Reset all traders' video analysis records")
    parser.add_argument("--all-memory", action="store_true", help="Reset all memory DBs")
    parser.add_argument("--list", "-l", action="store_true", help="List current traders")
    parser.add_argument("--list-memory", action="store_true", help="List memory DB files")
    
    args = parser.parse_args()
    
    print("🔄 Trader Account and Data Reset Tool")
    print("-" * 50)
    
    # List operations
    if args.list:
        list_traders()
        return
    
    if args.list_memory:
        list_memory_dbs()
        return
    
    # Global reset operations
    if args.all_videos:
        if input("⚠️  Delete all traders' video analysis records? (y/N): ").lower() == 'y':
            reset_analyzed_videos()
        return
    
    if args.all_memory:
        if input("⚠️  Delete all memory DBs? (y/N): ").lower() == 'y':
            reset_memory_db()
        return
    
    # Specific trader reset
    if args.trader:
        trader_name = args.trader
        
        # Account reset confirmation
        if input(f"⚠️  Reset '{trader_name}' account? (y/N): ").lower() == 'y':
            success = reset_trader_account(trader_name, args.strategy)
            
            # Additional data reset
            if success:
                # --all option: reset all data
                if args.all:
                    print(f"\n🔄 Resetting all data for {trader_name}...")
                    reset_analyzed_videos(trader_name)
                    reset_memory_db(trader_name)
                else:
                    # Individual options
                    if args.videos:
                        if input(f"⚠️  Also delete '{trader_name}' video analysis records? (y/N): ").lower() == 'y':
                            reset_analyzed_videos(trader_name)
                    
                    if args.memory:
                        if input(f"⚠️  Also delete '{trader_name}' memory DB? (y/N): ").lower() == 'y':
                            reset_memory_db(trader_name)
        
    else:
        print("Usage:")
        print("  python reset_accounts.py --list                    # List traders")
        print("  python reset_accounts.py --list-memory             # List memory DBs")
        print("  python reset_accounts.py -t trader_name            # Reset specific trader account")
        print("  python reset_accounts.py -t trader_name -v         # Reset account + videos")
        print("  python reset_accounts.py -t trader_name -m         # Reset account + memory")
        print("  python reset_accounts.py -t trader_name -a         # Reset account + videos + memory")
        print("  python reset_accounts.py --all-videos              # Reset all video records")
        print("  python reset_accounts.py --all-memory              # Reset all memory DBs")


if __name__ == "__main__":
    main()