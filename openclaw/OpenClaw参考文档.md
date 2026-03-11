# OpenClaw安装

```text
@Author: Weist
@OpenClaw Version: 2026.3.2 (85377a2)
@Platform: Windows10
```

本文通过 **NodeJs** 安装 **OpenClaw** ，官方要求Node版本大于等于22，可自行安装Node最新版本，Node相关安装教程查看网上教程或AI给出。
由于版本、环境、作者理解等原因，可能造成事实错漏，如有异常，请自行检查情况。

- 官方文档：https://docs.openclaw.ai/zh-CN
- Skills：https://clawhub.ai/

## 安装流程

1. 使用 **Win + R** 键开启CMD指令框【或其它启动方式】，以管理员身份启动。
2. 输入 **npm install -g openclaw@latest** ，进行OpenClaw的安装，等待安装完成。
3. 输入 **openclaw onboard** ，会输出版本信息、提示和安全警告，
4. 接下来安装流程，**中文括号内的信息是提示**。

### CMD指令框流程

- I understand this is personal-by-default and shared/multi-user use requires lock-down. Continue?
    - Yes
- Onboarding mode【选择模式】
    - Manual
- What do you want to set up?
    - Local gateway (this machine)
- Workspace directory【选择工作空间，建议不要选择默认】
    - *:\******\openclaw\workspace【自己创建的文件夹路径】
- Model/auth provider【模型选择，接下来的流程不同模型可能不一样】
    - MiniMax
- MiniMax auth method【选择版本，根据拥有的API key选择】
    - MiniMax M2.5
- How do you want to provide this API key?
    - Paste API key now【选择粘贴key】
- Enter MiniMax API key
    - sk-api-*******************************************************
- Default model【疑似会影响首选模型】
    - Keep current (minimax/MiniMax-M2.5)
- Gateway port【UI网关端口号，因为现在安全性不足，本地使用时要慎重】
    - 18789【默认端口号】
- Gateway bind
    - Loopback (127.0.0.1) 【本地调试选择这个】
- Gateway auth【网关访问方式】
    - Token
- Tailscale exposure【是否曝露】
    - Off
- Gateway token (blank to generate) 【生成token】
- Channel status【会展示各种聊天方式及其配置条件】
- Configure chat channels now?【是否现在配置交流方式，不配置可以选No】
    - Yes
- Select a channel【选择交流频道】
    - Slack (Socket Mode)
- Slack bot display name (used for manifest)
    - OpenClaw
- Slack socket mode
  - tokens【这里会提示你Slack的配置模式，实际情况会有所不同，此时可以直接跳转[SlackApp 创建与配置](#slackapp-创建与配置)】
- How do you want to provide this Slack bot token?
    - Enter Slack bot token
- Enter Slack bot token (xoxb-...)【此处输入机器人token】
    - xoxb-*******************************
- How do you want to provide this Slack app token?
    - Enter Slack app token
- Enter Slack app token (xapp-...)
    - xapp-1-*****************************
- Configure Slack channels access?
    - Yes
- Slack channels access【频道关联】
    - Allowlist (recommended)【白名单模式，只有在名单内的Slack频道才能使用，防止滥用】
- Slack channels allowlist (comma-separated)
    - C0********【这个是频道ID，在频道信息最下面。频道名称实际也行，建议使用ID】
- Slack channels
- Select a channel
    - Finished
- Selected channels
- Configure DM access policies now? (default: pairing)【是配置成员访问策略】
    - Yes
- Slack DM access
- Slack DM policy
    - Pairing (recommended)
- Updated ~\.openclaw\openclaw.json【该路径是核心配置文件，要记住这个路径，Windows下使用需要转换路径】
- Workspace OK: D:\software\openclaw\workspace
- Sessions OK: ~\.openclaw\agents\main\sessions【该路径是交流配置目录，Windows下使用需要转换路径】
- Skills status
- Configure skills now? (recommended)【配置Skills，会影响智能体使用的技能，不配置可以跳过】
- Install missing skill dependencies【安装依赖】
    - Skip for now【依据所需配置】
- Set GOOGLE_PLACES_API_KEY for goplaces?
    - No
- Set GEMINI_API_KEY for nano-banana-pro?
    - No
- Set NOTION_API_KEY for notion?
    - No
- Set OPENAI_API_KEY for openai-image-gen?
    - No
- Set OPENAI_API_KEY for openai-whisper-api?
    - No
- Set ELEVENLABS_API_KEY for sag?
    - No
- Hooks【影响智能体自动化】
- Enable hooks?【多选】
    - command-logger
    - session-memory
- Hooks Configured
- Config overwrite：***********\.openclaw\openclaw.json【配置本地化的路径】
- Install Gateway service (recommended)
    - Yes
- Gateway service runtime
    - Node (recommended)
- Gateway service install failed.【此处笔者自动安装失败了，影响不大】
- Gateway【失败信息】
- Gateway【提示信息：PowerShell重新安装流程，笔者电脑的PowerShell无法执行脚本，因此也无法使用】
- Health check failed：******【gateway失败信息】
- Health check help
- Optional apps
- Control UI【浏览器访问面板地址】
- Workspace backup
- Security
- Enable zsh shell completion for openclaw?
    - No
- Dashboard ready【访问浏览器地址包含token，需要在启动**gateway**服务才能使用】
- Web search【智能体是否能够使用浏览器搜索（联网请求？）】
- What now
- Onboarding complete. Dashboard opened; keep that tab to control OpenClaw.【OpenCLaw配置完成】

```text
PS1：如果 Gateway service 失败，可以启动一个CMD指令框，输入 openclaw gateway 启动服务。
PS2：在 Gateway service 启动状态下，在浏览器访问带token的地址，如果正常展示面板，那么基本配置无误。
PS3：在不使用的情况下，建议关闭Gateway service。
``` 

### 指令

- **openclaw status** - 状态检查
- **openclaw gateway** - 启用gateway服务
- **openclaw help** - 提示

## SlackApp 创建与配置

1. 首先访问 **https://api.slack.com/apps** ，点击 **Create New App**。
2. 选择 ***[From scratch](#from-scratch)*** 或 ***[From a manifest](#from-a-manifest)***。
3. 输入App名称，选择工作空间，点击创建App，进入配置界面。
4. 拿到两个token后，在OpenClaw的配置Slack的步骤使用。

### From scratch

按照下述流程配置。

- Socket Mode
    - Enable Socket Mode
        - 输入Token Name
        - 点击Generate
        - 复制并记录Token(xapp-1-************)
        - Done
- OAuth & Permissions
    - 机器人令牌权限
        - app_mentions:read
        - chat:write
        - groups:read
        - calls:read
- Enable Events
    - ON
- Install App
    - Install to ***
        - 点击后会进入一个新的界面
        - 新界面会展示机器人所有的权限
        - 点击 **允许** 创建成功
        - 页面重定向会生成Bot User OAuth Token (xoxb-*********************)
        - 记录该token

### From a manifest

OpenClaw 生成的配置文件，该配置文件给予的权限非常多，建议按需使用。若是对配置不熟悉，建议使用
**[From scratch](#from-scratch)**，以免造成损失。

```json
{
  "display_information": {
    "name": "OpenClaw",
    "description": "OpenClaw connector for OpenClaw"
  },
  "features": {
    "bot_user": {
      "display_name": "OpenClaw",
      "always_online": false
    },
    "app_home": {
      "messages_tab_enabled": true,
      "messages_tab_read_only_enabled": false
    },
    "slash_commands": [
      {
        "command": "/openclaw",
        "description": "Send a message to OpenClaw",
        "should_escape": false
      }
    ]
  },
  "oauth_config": {
    "scopes": {
      "bot": [
        "chat:write",
        "channels:history",
        "channels:read",
        "groups:history",
        "im:history",
        "mpim:history",
        "users:read",
        "app_mentions:read",
        "reactions:read",
        "reactions:write",
        "pins:read",
        "pins:write",
        "emoji:read",
        "commands",
        "files:read",
        "files:write"
      ]
    }
  },
  "settings": {
    "socket_mode_enabled": true,
    "event_subscriptions": {
      "bot_events": [
        "app_mention",
        "message.channels",
        "message.groups",
        "message.im",
        "message.mpim",
        "reaction_added",
        "reaction_removed",
        "member_joined_channel",
        "member_left_channel",
        "channel_rename",
        "pin_added",
        "pin_removed"
      ]
    }
  }
} 
```

按照下述流程配置（未实验）。

- Basic Information
    - App-Level Tokens
        - Add Scope
            - connections:write
        - 输入token name
        - Generate
        - 记录该token
- Install App
    - Install to ***
        - 点击后会进入一个新的界面
        - 新界面会展示机器人所有的权限
        - 点击 **允许** 创建成功
        - 页面重定向会生成Bot User OAuth Token (xoxb-*********************)
        - 记录该token

### Slack 操作

1. 进入Openclaw配置(Slack channels allowlist)许可的频道。
2. 输入 **/** ，点击***将应用添加至此频道***，将上面创建的***机器人应用***添加进来。
3. 输入 ***@机器人应用 !status***，如果出现自检信息则是成功。
4. 如果上述操作不成功，可以访问配置机器人的网址，检查之前的权限流程以及基于的机器人权限是否充足，进行Slack层面的配置。
5. 如果仍然无反应，可以查看以下的 ***[频道](#频道)***中的[Slack](#slack),进行OpenClaw层面的配置。

## OpenClaw 面板操作

```text
1. 输入带Token的地址，成功访问后OpenClaw会记录特征，后续就不再需要这样登录了，因此不要泄露Token。
2. 界面右上角会显示OpenClaw的版本、健康状态和界面风格。
3. 版本、健康为绿色时为最新和正常状态。
4. 当面板操作出现异常，如某些界面按钮无响应，建议检查版本是否是最新。
5. 如果要更新操作，不要点击面板上的更新，在指令框输入 npm install -g openclaw@latest 做更新操作。
```

### 聊天

```text
用于快速干预的直接网关聊天会话。
```

1. 该界面可以跟智能体(AI)聊天，或进行OpenClaw的调试，此界面的智能体是对OpenClaw有“**感知**”的。
2. 聊天界面右上角显示当前正在使用聊天，包含[频道](#频道)如Slack使用的聊天，可以进行切换操作查看运行记录。
3. 在该界面下会展示智能体所有的操作流程，[频道](#频道)的聊天一般只返回执行结果。
4. 如果需要智能体遗忘“记忆”，点击右下角的 ***NewSession*** 应该就可以操作。
5. 如果涉及智能体的改变，如[代理](#代理agent)、[技能](#技能skills)、[配置](#配置)的改变，应当需要重启网关(Gateway)
   ，这个行为可以人为，也可以智能体自执行(需要在[代理](#代理agent)中的Tools中的gateway授权启用)。

### 概览

```text
网关状态、入口点和快速健康读取。
```

本地调试可以不用调整。

### 频道

```text
管理频道和设置。
```

#### Slack

在这个界面可以修改Token、增加频道许可等操作，以下列举几个重要操作的标签名称。

- Channels - Slack界面频道权限修改
    - Add Entry - 增加频道
        - 修改 **custom-x** 为**频道代码**
        - 进行授权
- Group Policy - Slack频道策略
    - open - 开放
    - disabled - 禁止
    - allowlist - 白名单
- Mode - 交互模式
- Require Mention - 提及交互，是否在频道中@应用进行响应

进行操作之后记得保存，该操作会修改 **openclaw.json** 文件。

### 实例

```text
来自已连接客户端和节点的在线信号。
```

### 会话

```text
检查活动会话并调整每个会话的默认设置。
```

在这个界面可以查看各个实例消耗的Token，以及对实例进行操作。

### 使用情况

```text
详细了解智能体在各个模型、时间段的花费情况。
```

### 定时任务

```text
安排唤醒和重复的代理运行。
```

该操作可能会消耗大量Token，如果登录的使用的Token泄露，可能会造成信息泄露，慎用。

### 代理(agent)

```text
管理代理工作区、工具和身份。
```

每个代理可以视为一名“员工”，在这个界面可以调整员工的权限，并且查看员工的任务执行情况。

- Overview - 工作区路径和身份元数据
- Files - 扮演的角色、身份和工具指南（可以视为另一种类型的Skills）
- Tools - 每个工具的覆盖设置，可以使用快速配置，慎用 **Full**。
    - Files - 文件操作权限（智能体会写入代码到文件中）
        - read
        - write
        - edit
    - Runtime - 执行文件
        - exec - shell指令
        - process - 后台进程操作
    - Web - 网页操作（会操作浏览器）
        - web_search - 网络搜索
        - web_fetch - 内容捕捉
    - Memory - 记忆
        - memory_search - 记忆搜索
        - memory_get - 读取记忆文件（Files的MEMORY.md？）
    - Sessions - 会话管理
    - UI - 浏览器操作
    - Messaging - 发送消息
    - Automation
        - cron - 任务配置
        - gateway - 网关操控
        - Nodes - 节点操作
    - Agents - 查询代理
        - agents_list - 代理列表
    - Media - 媒体相关
- Skills - 单独设置技能，受到[技能](#技能skills)的强管理
    - Workspace Skills - 工作区技能，一般需要自己安装
        - 显示技能名称
        - 显示技能介绍
        - 显示技能工作区
        - 显示节能状态
    - Built-in Skills - OpenClaw 自带技能
- Channels - [频道](#频道)相关信息展示
- Cron Jobs - [定时任务](#定时任务)相关信息展示

### 技能(Skills)

```text
管理技能可用性和 API 密钥注入。
```

1. 此处的管理是全局性、强制性的。
2. 访问 **https://clawhub.ai/** 查看社区上传的技能。
3. 指令框安装指令 **npx clawhub@latest install skill**。
4. 工作区安装直接将技能文件夹拖入 **~\openclaw\workspace\skills** 下。
5. 进行技能的操作后可以让智能体自检，如果搜索不到，重启网关。

- Workspace Skills - 工作区技能，一般需要自己安装
    - 显示技能名称
    - 显示技能介绍
    - 显示技能工作区
    - 显示节能状态
- Built-in Skills - OpenClaw 自带技能

### 节点

```text
配对设备、功能和命令公开。
```

### 配置

```text
安全地编辑 ~/.openclaw/openclaw.json。
```

### 调试

```text
网关快照、事件和手动 RPC 调用。
```

### 日志

```text
网关文件日志的实时追踪。
```

## 技能(Skill) 创建

1. 访问 **https://docs.openclaw.ai/zh-CN/tools/creating-skills** 可以查看相关文档。
2. 技能的文件格式是MarkDown格式，因此描述方式可以通过强调、列举、代码块等操作进行描述。
3. 技能的本质上是教AI如何进行操作，将一系列操作流程细分，使用自然语言进行任务、行为进行抽象描述，但是每种操作细节描述一定要精确，上下文语义不能有冲突。
4. 技能使用过程可以理解成一个事件，事件有开头、过程、结尾三个阶段，每个阶段又可以拆分若干个细节。


