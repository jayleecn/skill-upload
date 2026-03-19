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
        return

    env_dir.mkdir(parents=True, exist_ok=True)

    template = """# Cloudflare R2 Configuration
R2_ACCESS_KEY_ID=your_access_key_here
R2_SECRET_ACCESS_KEY=your_secret_key_here
R2_ENDPOINT=https://your-account.r2.cloudflarestorage.com
R2_BUCKET=your_bucket_name
R2_PUBLIC_URL=https://your-public-url.r2.dev
"""

    with open(env_file, 'w') as f:
        f.write(template)

    print(f"✅ Config template created: {env_file}")
    print("Please edit this file with your R2 credentials.")


def cmd_upload_local(args):
    """Upload local directory."""
    # Validate source
    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        print(f"❌ Source not found: {args.source}")
        return 1

    # Package
    print(f"📦 Packaging: {source}")
    try:
        zip_path = Packager.from_local(str(source))
        print(f"   Created: {zip_path}")
    except Exception as e:
        print(f"❌ Packaging failed: {e}")
        return 1

    # Determine key
    key = args.key or f"skills/{source.name}.zip"

    # Upload
    print(f"☁️  Uploading to R2: {key}")
    try:
        uploader = get_uploader()
        result = uploader.upload(zip_path, key)

        if result['success']:
            print(f"✅ Upload successful!")
            print(f"   Size: {result['size']:,} bytes")
            if 'url' in result:
                print(f"   URL: {result['url']}")
        else:
            print(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
            return 1
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return 1

    # Cleanup if requested
    if args.clean:
        os.remove(zip_path)
        print(f"🗑️  Cleaned up: {zip_path}")

    return 0


def cmd_upload_github(args):
    """Upload GitHub repository."""
    repo_url = args.url

    # Get repo info
    print(f"📋 Fetching repo info...")
    info = Packager.get_github_info(repo_url)
    if 'error' in info:
        print(f"❌ Failed to get repo info: {info['error']}")
        return 1

    repo_name = info['name']
    branch = info.get('default_branch', 'main')
    print(f"   Repo: {repo_name}")
    print(f"   Branch: {branch}")

    # Download
    print(f"📦 Downloading from GitHub...")
    try:
        zip_path = Packager.from_github(repo_url, branch=args.branch or branch)
        print(f"   Downloaded: {zip_path}")
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return 1

    # Determine key
    key = args.key or f"skills/{repo_name}.zip"

    # Upload
    print(f"☁️  Uploading to R2: {key}")
    try:
        uploader = get_uploader()
        result = uploader.upload(zip_path, key)

        if result['success']:
            print(f"✅ Upload successful!")
            print(f"   Size: {result['size']:,} bytes")
            if 'url' in result:
                print(f"   URL: {result['url']}")
        else:
            print(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
            return 1
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return 1

    # Cleanup if requested
    if args.clean:
        os.remove(zip_path)
        print(f"🗑️  Cleaned up: {zip_path}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Skill Upload - Pack and upload to Cloudflare R2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  /upload setup                           初始化配置
  /upload local ~/skills/my-skill         上传本地目录
  /upload github https://github.com/user/repo  上传GitHub仓库
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="创建配置文件模板")
    setup_parser.set_defaults(func=cmd_setup)

    # Local upload command
    local_parser = subparsers.add_parser("local", help="上传本地目录")
    local_parser.add_argument("source", help="本地目录路径")
    local_parser.add_argument("-k", "--key", help="R2 中的对象 key (默认: skills/{name}.zip)")
    local_parser.add_argument("-c", "--clean", action="store_true", help="上传后删除本地 zip")
    local_parser.set_defaults(func=cmd_upload_local)

    # GitHub upload command
    github_parser = subparsers.add_parser("github", help="上传 GitHub 仓库")
    github_parser.add_argument("url", help="GitHub 仓库 URL")
    github_parser.add_argument("-b", "--branch", help="分支名 (默认: 仓库默认分支)")
    github_parser.add_argument("-k", "--key", help="R2 中的对象 key (默认: skills/{repo}.zip)")
    github_parser.add_argument("-c", "--clean", action="store_true", help="上传后删除本地 zip")
    github_parser.set_defaults(func=cmd_upload_github)

    args = parser.parse_args()

    # Load environment
    load_env()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
