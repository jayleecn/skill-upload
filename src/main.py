#!/usr/bin/env python3
"""
Skill Upload - Pack and upload skills to Cloudflare R2.

CLI for packaging local directories or GitHub repos and uploading to R2.
"""
import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from packager import Packager
from r2_uploader import R2Uploader
from autosync import (
    get_whitelist, add_to_whitelist, remove_from_whitelist,
    list_whitelist, is_in_whitelist, init_whitelist_with_defaults
)


def load_env():
    """Load environment variables from ~/.skill-upload/.env"""
    env_path = Path.home() / ".skill-upload" / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip().strip('"').strip("'")


def get_uploader() -> R2Uploader:
    """Create R2 uploader from environment."""
    required = ['R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_ENDPOINT', 'R2_BUCKET']
    missing = [k for k in required if not os.getenv(k)]

    if missing:
        raise ValueError(f"Missing R2 config: {', '.join(missing)}. Run: /upload setup")

    return R2Uploader(
        access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        endpoint=os.getenv('R2_ENDPOINT'),
        bucket=os.getenv('R2_BUCKET'),
        public_url=os.getenv('R2_PUBLIC_URL')
    )


def cmd_setup(args):
    """Setup command: create config file."""
    env_dir = Path.home() / ".skill-upload"
    env_file = env_dir / ".env"

    if env_file.exists():
        print(f"Config already exists: {env_file}")
    else:
        env_dir.mkdir(parents=True, exist_ok=True)

        template = """# Cloudflare R2 Configuration
R2_ACCESS_KEY_ID=your_access_key_here
R2_SECRET_ACCESS_KEY=your_secret_key_here
R2_ENDPOINT=https://your-account.r2.cloudflarestorage.com
R2_BUCKET=your_bucket_name
R2_PUBLIC_URL=https://github.23201.com
"""

        with open(env_file, 'w') as f:
            f.write(template)

        print(f"✅ Config template created: {env_file}")
        print("Please edit this file with your R2 credentials.")

    # Also init whitelist
    init_whitelist_with_defaults()
    whitelist_file = env_dir / "auto-sync.json"
    print(f"✅ Auto-sync whitelist initialized: {whitelist_file}")


def do_upload_local(source: str, key: Optional[str] = None, clean: bool = False) -> dict:
    """Internal: upload local directory and return result."""
    src_path = Path(source).expanduser().resolve()
    if not src_path.exists():
        return {"success": False, "error": f"Source not found: {source}"}

    # Package
    try:
        zip_path = Packager.from_local(str(src_path))
    except Exception as e:
        return {"success": False, "error": f"Packaging failed: {e}"}

    # Determine key
    actual_key = key or f"jayleecn/{src_path.name}.zip"

    # Upload
    try:
        uploader = get_uploader()
        result = uploader.upload(zip_path, actual_key)
    except Exception as e:
        return {"success": False, "error": f"Upload failed: {e}"}

    # Cleanup
    if clean:
        os.remove(zip_path)

    return result


def do_upload_github(repo_url: str, branch: Optional[str] = None, key: Optional[str] = None, clean: bool = False) -> dict:
    """Internal: upload GitHub repo and return result."""
    # Get repo info
    info = Packager.get_github_info(repo_url)
    if 'error' in info:
        return {"success": False, "error": f"Failed to get repo info: {info['error']}"}

    repo_name = info['name']
    actual_branch = branch or info.get('default_branch', 'main')

    # Download
    try:
        zip_path = Packager.from_github(repo_url, branch=actual_branch)
    except Exception as e:
        return {"success": False, "error": f"Download failed: {e}"}

    # Determine key
    actual_key = key or f"jayleecn/{repo_name}.zip"

    # Upload
    try:
        uploader = get_uploader()
        result = uploader.upload(zip_path, actual_key)
    except Exception as e:
        return {"success": False, "error": f"Upload failed: {e}"}

    # Cleanup
    if clean:
        os.remove(zip_path)

    return result


def cmd_upload_local(args):
    """Upload local directory."""
    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        print(f"❌ Source not found: {args.source}")
        return 1

    print(f"📦 Packaging: {source}")
    result = do_upload_local(str(source), args.key, args.clean)

    if result.get('success'):
        print(f"✅ Upload successful!")
        print(f"   Size: {result['size']:,} bytes")
        if 'url' in result:
            print(f"   URL: {result['url']}")
        return 0
    else:
        print(f"❌ {result.get('error', 'Unknown error')}")
        return 1


def cmd_upload_github(args):
    """Upload GitHub repository."""
    print(f"📋 Fetching repo info...")
    result = do_upload_github(args.url, args.branch, args.key, args.clean)

    if result.get('success'):
        print(f"✅ Upload successful!")
        print(f"   Size: {result['size']:,} bytes")
        if 'url' in result:
            print(f"   URL: {result['url']}")
        return 0
    else:
        print(f"❌ {result.get('error', 'Unknown error')}")
        return 1


def cmd_auto_add(args):
    """Add path to auto-sync whitelist."""
    path = args.path

    # Validate path
    expanded = Path(path).expanduser().resolve()
    if expanded.exists() and expanded.is_dir():
        # Local directory
        if add_to_whitelist(str(expanded)):
            print(f"✅ Added to whitelist: {expanded}")
        else:
            print(f"⚠️  Already in whitelist: {expanded}")
    elif 'github.com' in path:
        # GitHub URL
        if add_to_whitelist(path):
            print(f"✅ Added to whitelist: {path}")
        else:
            print(f"⚠️  Already in whitelist: {path}")
    else:
        print(f"❌ Path not found: {path}")
        return 1

    return 0


def cmd_auto_remove(args):
    """Remove path from auto-sync whitelist."""
    if remove_from_whitelist(args.path):
        print(f"✅ Removed from whitelist: {args.path}")
        return 0
    else:
        print(f"❌ Not found in whitelist: {args.path}")
        return 1


def cmd_auto_list(args):
    """List auto-sync whitelist."""
    whitelist = list_whitelist()

    if not whitelist:
        print("📝 Auto-sync whitelist is empty.")
        print("   Use '/upload auto-add <path>' to add.")
        return 0

    print(f"📝 Auto-sync whitelist ({len(whitelist)} items):")
    print("-" * 50)
    for i, item in enumerate(whitelist, 1):
        print(f"{i}. {item}")
    print("-" * 50)
    print("\n这些仓库在 push 后会自动提示同步到 R2。")

    return 0


def cmd_auto_sync(args):
    """Sync all whitelisted repositories to R2."""
    whitelist = list_whitelist()

    if not whitelist:
        print("📝 Auto-sync whitelist is empty.")
        return 0

    print(f"🔄 Syncing {len(whitelist)} repositories to R2...\n")

    success_count = 0
    failed = []

    for item in whitelist:
        print(f"📦 Processing: {item}")

        if 'github.com' in item:
            # GitHub URL
            result = do_upload_github(item, clean=True)
        else:
            # Local directory
            result = do_upload_local(item, clean=True)

        if result.get('success'):
            print(f"   ✅ Done - {result.get('url', 'OK')}")
            success_count += 1
        else:
            print(f"   ❌ Failed - {result.get('error', 'Unknown')}")
            failed.append(item)

        print()

    # Summary
    print("-" * 50)
    print(f"Sync complete: {success_count}/{len(whitelist)} succeeded")

    if failed:
        print(f"\n❌ Failed ({len(failed)}):")
        for item in failed:
            print(f"   - {item}")
        return 1

    return 0


def check_and_prompt_sync(repo_path: str) -> Optional[dict]:
    """
    Check if a path is in whitelist and return sync info.
    This is called by the AI assistant to check if sync should be prompted.

    Args:
        repo_path: Path to the repository

    Returns:
        dict with sync info if in whitelist, None otherwise
    """
    if is_in_whitelist(repo_path):
        return {
            "in_whitelist": True,
            "path": repo_path,
            "message": f"This repository ({repo_path}) is in the auto-sync whitelist.",
            "suggested_action": "Run '/upload auto-sync' to sync to R2"
        }
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Skill Upload - Pack and upload to Cloudflare R2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  /upload setup                           初始化配置

  /upload local ~/skills/my-skill         上传本地目录
  /upload github https://github.com/user/repo  上传GitHub仓库

  /upload auto-add ~/skills/my-skill      添加到自动同步白名单
  /upload auto-remove my-skill            从白名单移除
  /upload auto-list                       查看白名单
  /upload auto-sync                       同步白名单所有仓库
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="创建配置文件模板")
    setup_parser.set_defaults(func=cmd_setup)

    # Local upload command
    local_parser = subparsers.add_parser("local", help="上传本地目录")
    local_parser.add_argument("source", help="本地目录路径")
    local_parser.add_argument("-k", "--key", help="R2 中的对象 key (默认: jayleecn/{name}.zip)")
    local_parser.add_argument("-c", "--clean", action="store_true", help="上传后删除本地 zip")
    local_parser.set_defaults(func=cmd_upload_local)

    # GitHub upload command
    github_parser = subparsers.add_parser("github", help="上传 GitHub 仓库")
    github_parser.add_argument("url", help="GitHub 仓库 URL")
    github_parser.add_argument("-b", "--branch", help="分支名 (默认: 仓库默认分支)")
    github_parser.add_argument("-k", "--key", help="R2 中的对象 key (默认: jayleecn/{repo}.zip)")
    github_parser.add_argument("-c", "--clean", action="store_true", help="上传后删除本地 zip")
    github_parser.set_defaults(func=cmd_upload_github)

    # Auto commands
    auto_parser = subparsers.add_parser("auto", help="自动同步管理")
    auto_subparsers = auto_parser.add_subparsers(dest="auto_command", help="自动同步命令")

    # auto add
    auto_add_parser = auto_subparsers.add_parser("add", help="添加到白名单")
    auto_add_parser.add_argument("path", help="本地目录路径或 GitHub URL")
    auto_add_parser.set_defaults(func=cmd_auto_add)

    # auto remove
    auto_remove_parser = auto_subparsers.add_parser("remove", help="从白名单移除")
    auto_remove_parser.add_argument("path", help="路径或名称")
    auto_remove_parser.set_defaults(func=cmd_auto_remove)

    # auto list
    auto_list_parser = auto_subparsers.add_parser("list", help="查看白名单")
    auto_list_parser.set_defaults(func=cmd_auto_list)

    # auto sync
    auto_sync_parser = auto_subparsers.add_parser("sync", help="同步白名单所有仓库")
    auto_sync_parser.set_defaults(func=cmd_auto_sync)

    args = parser.parse_args()

    # Load environment
    load_env()

    if not args.command:
        parser.print_help()
        return 1

    # Handle auto subcommands
    if args.command == "auto" and not args.auto_command:
        auto_parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
