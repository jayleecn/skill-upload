---
name: skill-upload
description: Pack local directories or GitHub repositories into zip files and upload to Cloudflare R2 for backup and distribution.
trigger: |
  Use when user mentions upload to R2, backup to Cloudflare, package skill, zip and upload, GitHub to R2.
  Also trigger on commands: /upload setup, /upload local, /upload github.
---

# Skill Upload - 技能打包上传到 R2

把技能目录打包成 zip，上传到 Cloudflare R2 存储，方便分发和备份。

## 🚀 快速开始

**第一次使用？** 直接输入：
```
/upload setup
```

然后编辑配置文件 `~/.skill-upload/.env`，填入你的 R2 凭证。

## 🔧 配置要求

| 配置项 | 用途 | 获取方式 |
|--------|------|----------|
| `R2_ACCESS_KEY_ID` | R2 访问密钥 | Cloudflare R2 管理后台 |
| `R2_SECRET_ACCESS_KEY` | R2 密钥 | 同上 |
| `R2_ENDPOINT` | R2 API 端点 | 同上 |
| `R2_BUCKET` | 存储桶名称 | 同上 |
| `R2_PUBLIC_URL` | 公开访问 URL | 可选，用于生成下载链接 |

**获取方式：**
1. 登录 Cloudflare 控制台 → R2
2. 创建/选择存储桶
3. 左侧「管理 R2 API 令牌」
4. 创建 API 令牌，复制密钥信息

## 📋 命令列表

### `/upload setup` - 初始化配置

创建配置文件和白名单模板：
```
/upload setup
```

然后编辑 `~/.skill-upload/.env` 填入你的凭证。

---

### `/upload auto` - 自动同步白名单（核心功能）

管理自动同步白名单。只有白名单中的仓库才会被自动同步。

**查看白名单：**
```
/upload auto list
```

**添加到白名单：**
```
/upload auto add ~/.agents/skills/mp-editor
/upload auto add https://github.com/user/repo
```

**从白名单移除：**
```
/upload auto remove mp-editor
```

**手动同步白名单：**
```
/upload auto sync
```

---

### `/upload local <目录>` - 上传本地目录

把本地技能目录打包上传到 R2：
```
/upload local ~/.agents/skills/mp-editor
```

**参数：**
- `-k, --key`: 自定义 R2 中的对象 key（默认: `jayleecn/{dirname}.zip`）
- `-c, --clean`: 上传后删除本地 zip 文件

---

### `/upload github <URL>` - 上传 GitHub 仓库

直接从 GitHub 下载仓库并上传到 R2：
```
/upload github https://github.com/jayleecn/mp-editor
```

**参数：**
- `-b, --branch`: 指定分支（默认: 仓库默认分支）
- `-k, --key`: 自定义 R2 中的对象 key
- `-c, --clean`: 上传后删除本地 zip 文件

---

## 💡 自动化工作流

### 场景：GitHub push 后自动同步到 R2

在你的主 skill 仓库执行 `git push` 后，AI 会检测到并提示：

> "该仓库在白名单中，需要同步到 R2 吗？"

确认后自动执行：
```bash
/upload auto sync
```

或只同步单个：
```bash
/upload local ~/.agents/skills/mp-editor
```

**白名单配置位置：** `~/.skill-upload/auto-sync.json`

---

## 🔧 技术说明

### 实现特点

- **零外部依赖**: 使用 Python 标准库实现 AWS Signature V4 签名
- **支持两种来源**: 本地目录（支持 git archive）或 GitHub 仓库
- **自动打包**: 自动检测 `.git` 目录，使用 git archive 生成干净的 zip

### 文件结构

```
skill-upload/
├── src/
│   ├── main.py          # CLI 入口
│   ├── r2_uploader.py   # R2 上传（AWS Signature V4）
│   └── packager.py      # 打包模块
├── SKILL.md             # 本文件
├── README.md            # 使用说明
└── .env.example         # 配置模板
```
