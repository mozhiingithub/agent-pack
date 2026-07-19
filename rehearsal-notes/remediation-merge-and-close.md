# merge-and-close 机制整改清单（试运行第一轮）

> 来源：`agent-pack-test` 双工协作试运行，首个练习需求 `add-message-timestamp` 的完整交付轮。
> 整理：开发线 agent；读者：agent-pack 机制开发方。
> 环境：外网 GitHub（https→SSH）、内网为同机模拟仓库 + Gitee（https→SSH），出包脚本 v4/模板 import.sh v7 世代。
> 范围：本轮 merge-and-close 暴露的全部机制问题。需求本身已闭环（内网手动 close，对账通过）。

## 结论摘要

- 需求 `add-message-timestamp` 已闭环：外网 main `1317bbe`，内网 main `3bd4821`，双侧分支已删、执行计划已归档。
- 本轮暴露机制问题共 10 项未决（P1×4、P2×3、P3×3），均在内网实测中原样复现，非推测。
- 其中 **P1-1（close 包幂等误杀）为流程阻断级硬伤**：现行模板下 close 流程从未真正跑通过。
- 另附已决项 10 条（机制方本轮已修，备查防回归）。

---

## 一、未决项

### P1-1　幂等检查不区分包类型，close 包必被误杀【流程阻断】

- **现象**：内网执行 close 包 #6，输出 `已是最新（feat/add-message-timestamp 内容与本包一致），无副作用退出`，squash 合 main、对账、删分支、清理一步未执行。
- **根因**：`agent-pack/templates/import.sh` 固定区 4（幂等，约 L82-85）在类型分派**之前**执行，判据为 `分支 tree == TREE_HASH`。而 close 包的 `TREE_HASH` 按构造就等于分支最终 tree（export 固定区 3 `TREE=$(git rev-parse "$BRANCH^{tree}")`），即 close 包的**正常前置状态必然命中幂等早退**。
- **影响**：现行模板下 close 流程在标准序列中**永远无法执行**；报错文案"已是最新"还会误导执行人以为已完成。
- **建议**：
  1. 幂等检查改为类型感知：sync 维持现判据；close 的"已完成"应判 main 侧状态——`main` 排除保护路径后的 tree == `TREE_HASH` 且分支已删除；
  2. close 路径此前零覆盖，建议补端到端测试（sync→close 全链，见末节测试矩阵）。
- **复现**：任意分支走完 sync 后出 close 包，内网执行 import.sh，必现。

### P1-2　`net()` 未设 `GIT_TERMINAL_PROMPT=0`，鉴权缺失时交互挂起

- **现象**：内网执行 sync 包 #5，`git am` 完成后推送 Gitee 时弹出 `Username for 'https://gitee.com':`，用户名输入后进入不回显的密码提示，执行人误判为"卡死"，连按 `^C` 中断。
- **根因**：import.sh 固定区 1 `net()`（约 L26-50）内 `timeout 60 git "$@"` 未屏蔽交互提示。脚本的设计语义是"失败即还原、恢复后重跑"，但交互挂起使失败路径永远走不到，把人逼成中断源。
- **影响**：形成**半完成态**——本地分支已被 `git am` 推进（`b950a5d`）、远端未推、`trap` 还原被二次 `^C` 打断未完整执行。该状态下脚本无法自愈（见 P1-3）。
- **建议**：`net()` 内置 `GIT_TERMINAL_PROMPT=0`，鉴权问题立即死于明确文案（"未配置凭据，请配置后重新执行本包"），进入既有的失败还原路径。

### P1-3　幂等早退不确认远端 tip，半完成态无法自愈

- **现象**：P1-2 的半完成态下重新执行 import.sh，输出 `已是最新` 退出；实际 Gitee 远端分支仍停在旧值（`e80054e`），推送欠账被永久跳过。
- **根因**：固定区 4 幂等判据只比**本地**分支 tree，不查远端。脚本其余路径（sync 正常流）有 `ls-remote` 远端确认（约 L134-136），唯独早退路径没有。
- **建议**：早退前增加远端比对：`ls-remote origin "$BRANCH"` 的 tip 与本地分支 tip 一致才允许"无副作用退出"；不一致则继续走推送+远端确认流程。与 P1-1 的类型感知改造可同处落地。

### P1-4　worktree 方案与"与执行时所在分支无关"契约系统性冲突（三处）

- **现象**：sync 包 #5 首次执行报 `fatal: 'feat/add-message-timestamp' is already used by worktree at '<内网仓库>'`——内网主工作区正检出着该分支（实测时人工 checkout，属高频场景）。
- **根因与三处缺口**（import.sh 固定区 6，约 L108-150）：
  1. **sync**：`git worktree add "$WT" "$BRANCH"`，目标分支被任一工作区检出即失败；
  2. **close**：`git worktree add "$WT" "$MAIN_BRANCH"`，人坐在 main 上执行 close 必失败（本次靠改用 detached 操作避开）；
  3. **close**：`git branch -D "$BRANCH" || true`，分支被占用时**静默失败**，分支残留无人知晓。
- **影响**：契约宣称"与所在分支无关"，实际要求人执行前先 `git checkout --detach`——恰恰是最容易被踩的一步；两包连跑时还会互相矛盾（#5 要求不占 feat，#6 要求不占 main）。
- **建议**：内部实现改为 `git worktree add --detach "$WT" <ref>` + 事后 `git update-ref`（真正与现场无关）；或前置统一检测并输出可执行文案（"请先执行 git checkout --detach 再运行本包"）。

### P2-5　`trap` 在 SIGINT 下还原不完整

- **现象**：P1-2 中执行人连按两次 `^C`，`on_exit` 的 worktree 清理/`update-ref` 被打断，分支引用停留在推进后的值。
- **建议**：`on_exit` 入口先 `trap '' INT TERM`，保证还原段原子执行完。

### P2-6　close 出包与 push main 存在隐式时序耦合

- **现象**：export 固定区 4 close 校验要求 `git diff origin/main <branch>` 为空。外网 main 若先推了机制修复 commit（本轮 `6033768`、`9a418d4`），其内容不在分支上，diff 非空，close 包出不来——本轮靠人工排序（先出 close 再推 main）才通过。
- **建议**：把"先出 close 包、后推 main 机制修复"写入 merge-and-close skill 步骤；或由脚本识别 diff 全落在机制路径（`tools/`、`.agents/`）时给出明确提示而非笼统报错。

### P2-7　幂等早退不清理包文件

- **现象**：已成功应用（或被误杀）的包，其解压文件（manifest/files/payload 等）残留在内网仓库目录，本轮出现两次，靠人工清理。
- **建议**：判定"已是最新"（含远端确认，见 P1-3）后同样执行固定区 8 的清理。

### P3-8　成功/失败不易辨认，日志不落盘

- **现象**：`已还原 ...` 与成功输出视觉上接近，执行人曾把失败误读为成功（#5 第一次）；向开发方反馈靠手工复制终端，易截断。
- **建议**：脚本结尾打印醒目 `SUCCESS`/`FAIL` 横幅 + 下一步提示；全程 `tee` 落一份日志文件到包同目录。

### P3-9　handbook 应建议内网仓库使用 SSH remote

- **现象**：内网仓库初始为 `https://gitee.com/...`，无凭据帮手时推送必挂（P1-2 的土壤）。改为 `git@gitee.com:...` 后问题消失。
- **建议**：handbook/环境约定一节写明"内网仓库 remote 一律 SSH"；import.sh 可在前置检查中识别 https remote 给出提示。

### P3-10　机制修复 commit 直接落在在途交付分支（流程类）

- **现象**：本轮 4 个机制修复 commit 由人直接提交到 `feat/add-message-timestamp`，造成"被合并的不是被实测的"（tree 与最近 sync 包不一致）、prev-commit 需手工补登、close 前置校验被触发等一连串补救。
- **建议**：机制修复走 main 或独立 fix 分支（修复线纪律），交付分支只承载需求改动；若必须随分支带修复，应在 merge-and-close 前置检查中显式豁免并记录。

---

## 二、已决项（本轮机制方已修复，备查防回归）

| 缺陷 | 修复 commit | 说明 |
| --- | --- | --- |
| 分支名含 `/` 状态文件路径未转义，出包必败 | `33d32c5` | SAFE_BRANCH 转义，git 操作仍用原始名 |
| 保护路径硬阻断可被非 ASCII 文件名绕过 | `fb81151` | 统一 `core.quotePath=false`（实测可绕过：`deploy-intranet/中文.txt` 被 C 引用转义后 `^` 锚点失效） |
| files.txt 非 ASCII 路径转义致导入校验必败 | `fb81151` | 同上，一并修复 |
| export 的 ls-remote 裸网络操作 | `fb81151` | 改走 safe-git.sh（重试/代理） |
| configImpact 把 spec 占位"无"误报为部署影响 | `fb81151` | 归一化（无/空白/none 视为无影响） |
| import.sh 缺 git 身份预检 | `fb81151` | `git var GIT_COMMITTER_IDENT` 预检 + 指引 |
| 跨机 commit hash 不可比（git am 改写 committer） | `b8685cc` | 幂等/连续/逐文件/对账全部改 tree/blob hash |
| import.sh 需手改 REPO 路径 | `acbcb2d` | 零配置自动定位仓库 + 成功后自清 |
| sync 全量重放续包必败 | `6033768` | 增量出包（prev-commit 定 RANGE_BASE）+ merge-and-close 前置检查 |
| main 同步机制缺失 | `9a418d4` | main 豁免 spec 检查、close 播种基线、main 引导新建 |

---

## 三、建议的验证要求（修复回归用）

最小测试矩阵（内网环境可用本机双目录模拟）：

1. **sync 首包**：全新分支 → 导入成功 → tree 一致 → 包文件自清；
2. **sync 续包**：分支已存在 → 增量 patch → 链式校验通过；
3. **close 全链**：sync 到位后出 close → 合 main → 对账通过 → 分支双删（P1-1 修复的验收）；
4. **半完成态注入**：推送前中断 → 重跑 → 远端确认补齐而非误报"已是最新"（P1-3 验收）；
5. **分支占用矩阵**：主工作区分别检出 目标分支 / main / detached 三种现场，sync 与 close 各跑一遍（P1-4 验收）；
6. **无凭据环境**：清空 credential helper，确认脚本快速死于明确文案而非挂起（P1-2 验收）。

## 附：本轮关键哈希对照

- 外网 main：`8e07d8d`（squash）→ `9a418d4`（机制修复）→ `1317bbe`（归档）；
- 内网 main：`3bd4821`（手动 close 的 squash，message 同 `8e07d8d`）；
- 交付分支最终 tree（双侧一致）：`4daf361a5a29eba4b794292febfbd1741b4ad7da`；
- 内网重放分支 tip：`b950a5d`（对应外网 `668126e`，committer 差异致 hash 不同，tree 相同）。
