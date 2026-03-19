# Skill Upload · 技能打包上传到 R2

> 把技能目录打包成 zip，上传到 Cloudflare R2 存储，方便分发和备份。

---

## 🚀 快速开始

### 1. 安装配置

运行初始化命令：
```
/upload setup
```

然后编辑配置文件 `~/.skill-upload/.env`：
```bash
# Cloudflare R2 Configuration
R2_ACCESS_KEY_ID=your_access_key_here
R2_SECRET_ACCESS_KEY=your_secret_key_here
R2_ENDPOINT=https://your-account.r2.cloudflarestorage.com
R2_BUCKET=your_bucket_name
R2_PUBLIC_URL=https://github.23201.com
```

**获取 R2 凭证：**
1. 登录 [Cloudflare 控制台](https://dash.cloudflare.com/) → R2
2. 创建存储桶（或选择已有）
3. 左侧「管理 R2 API 令牌」→ 创建 API 令牌
4. 复制密钥信息到 `.env` 文件

---

## 📝 使用方法

### 上传本地目录

把本地技能目录打包上传到 R2：
```
/upload local ~/skills/mp-editor
```

**自定义对象 key：**
```
/upload local ~/skills/mp-editor -k backup/mp-editor-v2.zip
```

**上传后自动清理：**
```
/upload local ~/skills/mp-editor -c
```

---

### 上传 GitHub 仓库

直接从 GitHub 下载并上传：
```
/upload github https://github.com/jayleecn/mp-editor
```

**指定分支：**
```
/upload github https://github.com/jayleecn/mp-editor -b develop
```

---

## 🤖 自动同步白名单

白名单机制用于控制哪些仓库会在 git push 后自动提示同步到 R2。

### 查看白名单
```
/upload auto list
```

### 添加到白名单
```
/upload auto add ~/.agents/skills/mp-editor
/upload auto add https://github.com/jayleecn/mp-editor
```

### 从白名单移除
```
/upload auto remove mp-editor
```

### 手动同步白名单所有仓库
```
/upload auto sync
```

**白名单配置文件**：`~/.skill-upload/auto-sync.json`

---

## 💡 自动化工作流

### 场景：GitHub push 后自动备份到 R2

1. 先把仓库加入白名单：
```
/upload auto add ~/.agents/skills/mp-editor
```

2. 每次 git push 后，运行同步命令：
```
/upload auto sync
```

### 场景：一次性上传本地目录

直接上传本地目录（不在白名单也可以）：
```
/upload local ~/.agents/skills/mp-editor
```

---

## 🔧 技术特点

| 特性 | 说明 |
|------|------|
| **零外部依赖** | 纯 Python 标准库实现 AWS Signature V4 |
| **支持 git archive** | 自动检测 git 仓库，生成干净的 zip（不含 .git）|
| **双来源支持** | 本地目录 或 GitHub 仓库 |
| **自动 key 生成** | 智能生成默认的对象 key |

---

## 📄 License

MIT
