# 安装指南

本 Skill 是一个**纯文本目录**（`SKILL.md` + `references/` + `scripts/` + `assets/`），
不含可执行二进制、不联网、不写用户目录之外的任何文件——安装即复制，风险极低。

---

## 方式一：一键脚本

### Linux / macOS / Git Bash

```bash
curl -fsSL https://raw.githubusercontent.com/Yym11345/zhanggong-yanyu-skill/main/install.sh | bash
```

可选参数：

```bash
bash install.sh --project          # 装到当前项目 ./.workbuddy/skills/zhanggong（团队共享）
bash install.sh --target ~/skills/zhanggong   # 自定义目录
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/Yym11345/zhanggong-yanyu-skill/main/install.ps1 | iex
```

可选参数：

```powershell
.\install.ps1 -Project
.\install.ps1 -Target "$HOME\skills\zhanggong"
```

> 脚本会**自动备份**已有版本为 `<目标>.bak.<时间戳>`，不会静默覆盖你的修改。

---

## 方式二：手动复制（推荐先看这个）

本质只有一句话：**把整个目录放到目标 agent 的 skills 目录**。

```bash
git clone https://github.com/Yym11345/zhanggong-yanyu-skill.git
cp -r zhanggong-yanyu-skill ~/.workbuddy/skills/zhanggong
```

Windows：

```powershell
git clone https://github.com/Yym11345/zhanggong-yanyu-skill.git
Copy-Item -Recurse zhanggong-yanyu-skill "$HOME\.workbuddy\skills\zhanggong"
```

---

## 各平台安装位置

| 平台 | 路径 | 是否支持目录级 Skill | 备注 |
|---|---|---|---|
| **WorkBuddy** | `~/.workbuddy/skills/zhanggong/` | ✅ 原生 | 装完重启会话即可触发 |
| **Claude Code** | `~/.claude/skills/zhanggong/` | ✅ 原生 | 项目内可用 `.claude/skills/zhanggong/` |
| **Cursor** | `.cursor/rules/zhanggong.mdc` | ⚠️ 需转换 | 见下方「非目录式平台」 |
| **Windsurf** | `.windsurf/rules/zhanggong.md` | ⚠️ 需转换 | 同上 |
| **Cline / Roo Code** | `.clinerules/zhanggong.md` | ⚠️ 需转换 | 同上 |
| **ChatGPT** | 自定义 GPT → Knowledge 上传 | ⚠️ 需转换 | 见下方「非目录式平台」 |
| **豆包 Doubao** | 智能体平台 → 知识库 | ⚠️ 需转换 | 见下方「非目录式平台」 |
| **ZCode** | 平台自定义知识库 | ⚠️ 需转换 | 见下方「非目录式平台」 |
| **Hermes / 通用 Agent** | `~/.hermes/skills/zhanggong/` | ✅ 目录级 | 同 WorkBuddy 约定 |

---

## 非目录式平台（ChatGPT / 豆包 / ZCode / Cursor 等）

这些平台不读「skill 目录」，只吃**一段提示词 + 若干知识文件**。有两种做法：

### 做法 A：单文件模式（轻量）

把 `SKILL.md` 全文粘贴进系统提示词/知识库，再按需追加 `references/` 里的文件。

对话开始时发送：

```
【角色】按下方规则解题，规则不可违背。

<SKILL.md 全文>

（需要时再追加：references/00-考场速查.md、references/01-中心理解-总纲与流程.md、
 references/04-中心理解-排除干扰项.md、references/02-中心理解-关系与功能.md、
 references/03-中心理解-同义替换与主题词.md）
```

### 做法 B：完整知识库模式（推荐，效果最接近原生）

1. 新建一个「知识库 / Knowledge」，把整个 `references/` 目录里的 22 个 `.md` **逐个上传**
   （ChatGPT 知识库、豆包知识库都支持多文件）
2. 再单独上传 `SKILL.md` 作为核心指令
3. 知识库检索设为「按需检索」，避免每次全量塞进上下文

> **注意**：这类平台的知识库是**向量检索**，会漏掉细节。若要求零失误，
> 用做法 A 的单文件模式并按题型手动追加对应 reference 更稳。

---

## 目录式平台的最小可用配置

装好后 `SKILL.md` 的 frontmatter 会自动被各 agent 识别：

```yaml
---
name: zhanggong
description: 行测言语理解与表达（六题型）的解题教练……触发词：行测、言语理解、中心理解……
agent_created: true
---
```

**名称必须是 hyphen-case**（只用小写字母、数字、连字符）——`zhanggong_skill` 会被校验器拒绝。

---

## 验证安装

```bash
# 1. 目录结构
ls ~/.workbuddy/skills/zhanggong/
# 应看到：SKILL.md  README.md  references/  scripts/  assets/

# 2. frontmatter 合法
head -5 ~/.workbuddy/skills/zhanggong/SKILL.md

# 3. 知识库完整（应为 22）
ls ~/.workbuddy/skills/zhanggong/references/ | wc -l

# 4. 卡片页数自检（需要 Python3 + Chromium）
python ~/.workbuddy/skills/zhanggong/scripts/verify_card.py --check-pages
# 期望输出：HTML .sheet 数 == PDF 实测页数 ✓ 一致
```

**功能自测**：给 agent 贴一道带 ABCD 选项的言语题，问「这道题怎么解」。
若回答里出现了「第一步·寻找重点 / 第二步·同义替换 / 第三步·排除干扰项」的结构，
说明 skill 已正确加载。

---

## 卸载

```bash
rm -rf ~/.workbuddy/skills/zhanggong
```

Windows：

```powershell
Remove-Item -Recurse -Force "$HOME\.workbuddy\skills\zhanggong"
```

---

## 常见问题

**Q：装了但 agent 不触发？**
A：检查 `SKILL.md` 的 frontmatter 是否完整（`---` 包裹、含 `name:` 与 `description:`）；
描述里的触发词是否覆盖用户的说法。也可能是会话未重载——重启会话再试。

**Q：回答太啰嗦／太简短？**
A：直接说「用三步走」（默认 60 秒流）或「按速记卡方式完整拆解」（五步，含句级标注与选项逐项判定）。

**Q：能改吗？**
A：可以，MIT 协议。`references/00-17` 由 `scripts/extract_card.py` 从速记卡生成，
改速记卡后重跑脚本即可；`18-20` 是可直接编辑的示范与风格库。
