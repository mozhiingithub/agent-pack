# AI 双工协作操作手册

> 本手册是 solution.md 的操作版。
> **第一部分**只写人的操作步骤，日常照此执行即可；**第二部分**是人 / AI / 脚本的完整流程，需要查细节时再看。
> 给 AI 加载的对应规范见 `agent-pack/`（AGENTS.md + skills），与场景一一对应。

## 通用约定（先读一遍，后文不再重复）

- 所有场景 spec 先行（spec-coding 不变）；
- AI 的每个写操作（合 main、删分支、打 tag）必须先汇报"实测通过 + diff 校验为空"，人确认后才执行；
- **人对 AI 下指令时带上技能名**（如"按 feat-workflow ……"），这是触发正确操作规范的方式。前提是 `AGENTS.md` 已放在仓库根目录并被 agent 自动加载——新会话首次使用或不确定加载与否时，第一句话先说："**先读 AGENTS.md**"；
- 人需要动手的环境动作只有三种：拷包、解压并执行 `import.sh`、在 latest 上实测——具体是：zip 拷到内网仓库一级目录 → 右键"解压到当前位置" → Git Bash 执行 `./import.sh`（零配置，成功后自动清理包文件）；
- 执行 `import.sh` 时本地仓库处于任何分支都可以——脚本自带现场保护与恢复，不需要先切分支；
- 内网执行环境是 Windows 个人电脑 + Git Bash，装了 git 即可，无需 jq 等任何其他工具（临时工作区用 `mktemp -d`，Git Bash 自动映射到 Windows 临时目录）；
- Windows 两个已知坑：路径过长报错 → 执行一次 `git config --global core.longpaths true`；清理工作区失败 → 多半是文件被编辑器/杀软占用，关闭后 `git worktree prune` 清理即可。

---

# 第一部分：人的操作清单

**每日开工**

1. 对 AI 说："**开工，按 AGENTS.md 开工引导执行，并把 main 同步进在途分支**"；
2. 与同事 5 分钟互通"今天动哪些模块"，重叠则人工错开。

**新功能**

1. 对 AI 说："**按 feat-workflow 开发新需求：……（需求描述），先出 spec**"；
2. 审 spec：拆分粒度（≤3~5 天/单元）、触及模块声明、"部署影响"一节；
3. 对 AI 说："**按 sync-package 出 sync 包**" → 拷 zip 到内网仓库一级目录 → "解压到当前位置" → Git Bash 执行 `./import.sh`（零配置）；
4. 若脚本提示 configImpact 待办 → 追加 `[config]` commit 后重新部署 latest；
5. latest 实测：有问题 → 带完整日志对 AI 说"**按 iteration-round 继续改，别换分支**"，回到第 3 步；
6. 通过 → 对 AI 说："**实测通过，按 merge-and-close 收尾，先汇报等我确认**"；
7. 看 AI 汇报（实测通过 + diff 为空 + 拟写的 commit message）→ 确认；
8. 拷 close 包入内网仓库一级目录，同样"解压到当前位置"后执行 → 确认对账通过。完成。

**修 bug**

1. 在 latest/stable 上复现确认（main 上的 bug 才走这条线）；
2. 对 AI 说："**按 fix-workflow 处理。现象：…… 复现步骤：…… 日志：……**"；
3. 之后与"新功能"第 3~8 步完全相同（出包 → 实测 → 迭代 → 确认合并 → close 包）。

**重构**

1. 群内公告"X 模块重构窗口（约 N 天）"；
2. 对 AI 说："**按 refactor-guardrails 执行重构，窗口已公告，先拆切片 spec**"；
3. 每个切片按"新功能"流程完整走一遍。

**发布 / 回滚**

- 发布：按 checklist 确认本批全部实测通过 → 对 AI 说"**按 merge-and-close 打 tag 发布**" → 部署 stable 到该 tag；
- 回滚：重新部署上一个 stable tag，秒级完成，代码配置一起回滚。

**分支清理**

- 合并完成后：人零操作（AI 当场删、close 包自动清内网分支）；
- 废弃分支：拍板后对 AI 说"**归档废弃 <分支名>**"；
- 每周：对 AI 说"**做分支卫生检查**"，对列出的超期分支逐个拍板（继续 / 合并 / 归档删）。

**网络故障**

- 不用做任何事（脚本自动重试、挂起）；恢复后对 AI 说"**网络恢复了，继续**"；
- 公司提供代理时：对 AI 说"**网络走代理 http://ip:port，记到 .sync-state/proxy，探活确认**"；要取消说"**取消代理**"。该配置只对 git 命令生效（等效逐条命令加前缀），不是全局代理，不影响其他程序联网；代理失效时脚本会自动直连兜底并提示取消。

**import.sh 执行失败**

- 照脚本输出的提示操作（如"先执行 sync-main-NNN 包"），不手工修仓库；
- 提示解决不了 → 把完整日志发给 AI："**诊断原因，不要改包、不要绕过**"。

---

# 第二部分：完整流程（人 / AI / 脚本）

## 场景 0：每日开工（两人各自执行）

【人】对 AI 说："**开工，按 AGENTS.md 开工引导执行，并把 main 同步进在途分支**"。

1. 【AI】开工引导：读 `AGENTS.md` → 读相关 spec → `git log --oneline main -20` + `git diff <基点>..main --stat`，需要细节再 `git show`；
2. 【AI】（仅开发线）把 main merge 进自己的 feat 分支；
3. 【人】两人 5 分钟互通"今天动哪些模块"，重叠则人工错开。

## 场景 1：新功能开发（主开发 + 开发 agent）

启动：【人】对 AI 说："**按 feat-workflow 开发新需求：……（需求描述），先出 spec。**"

1. 【AI】产出 spec（技能：feat-workflow），必须含：触及的既有模块、"部署影响"一节；
2. 【人】审 spec：拆分成 ≤3~5 天可独立交付的单元，一个单元一条分支；
3. 【AI】从最新 main 建 `feat/<功能>` 并推送（技能：feat-workflow）；
4. 【AI】开发，本地检查全绿（技能：feat-workflow）；
5. 【人】对 AI 说："**按 sync-package 出 sync 包**" → 【AI】出包并原样转述脚本输出（技能：sync-package）；
6. 【人】拷 zip 到内网仓库一级目录，"解压到当前位置"，执行 `import.sh`（零配置）；
7. 【脚本】自动建/更新内网同名分支 → 校验 → 触发 latest 部署；若有 configImpact 待办 → 【人】据待办在内网分支追加 `[config]` commit 后重新部署；
8. 【人】在 latest 实测：
   - 有问题 → 转场景 3（迭代轮）；
   - 通过 → 继续；
9. 【人】对 AI 说："**再 merge 一次 main，有变化就再出一版包**" → 【AI】merge 并按需重新出包（技能：feat-workflow → sync-package）；若有新合入，重复步骤 6~8 一轮；
10. 【人】对 AI 说："**实测通过，按 merge-and-close 收尾，先汇报等我确认**"；
11. 【AI】最后校验并汇报"实测通过 + diff 为空 + 拟写的 commit message"（技能：merge-and-close）→【人】确认 →【AI】squash 合入外网 main → push → 删外网 feat 分支 → 出 close 包（技能：merge-and-close → sync-package）；
12. 【人】拷 close 包入内网仓库一级目录，解压执行 `import.sh`；
13. 【脚本】内网同名分支合入内网 main → 对账 → 删内网分支 → 输出结果；
14. 【人】确认对账通过；【AI】更新 spec 状态为"已合入"。

## 场景 2：修复 bug（主修复 + 修复 agent）

> 前提：bug 必须在 main 上可复现（latest/stable 上确认）。feat 分支内的问题不叫 bug，见场景 3。

启动：【人】对 AI 说："**main 上有个 bug，按 fix-workflow 处理。现象：…… 复现步骤：…… 日志：……**"

1. 【AI】判定类型（技能：fix-workflow）：局部缺陷直接修；设计性缺陷 →【人】裁定是否派回原开发者（流程不变，执行人换）；
2. 【AI】spec 写四要素（现象、根因、方案、影响面），从最新 main 建 `fix/<bug>`；
3. 【AI】修复 + 外网检查全绿；
4. 【人】对 AI 说："**按 sync-package 出 sync 包**"，后续同步、实测、迭代、合并、对账同场景 1 的步骤 6~13；
5. 【AI】失败案例回流：把该 bug 场景转化为外网可跑的回归测试，随本分支或下一变更合入（技能：fix-workflow）。

## 场景 3：内网实测发现问题（迭代轮，fix/feat 通用）

【人】对 AI 说："**实测失败，按 iteration-round 继续改，别换分支。复现步骤：…… 完整日志：…… 截图：……**"

1. 【AI】读日志定位，信息不够先向人要（技能：iteration-round）；
2. 【AI】在**同一分支**上修改 → 本地检查全绿 → 生成新序号 sync 包（技能：iteration-round → sync-package）；
3. 【人】拷入 → `import.sh` → latest 部署 → 再测；
4. 循环直到通过，回到场景 1/2 的合并步骤。

此场景的铁律：不新建分支、不碰 main、不换一个 agent 接手。

## 场景 4：重构/简化类需求（主开发 + 开发 agent）

启动：【人】先群内公告"X 模块重构窗口（约 N 天）"，再对 AI 说："**按 refactor-guardrails 执行重构，窗口已公告，先把需求拆成切片 spec。**"

1. 【AI】拆成 1~2 天/片的切片，每片 spec 声明"对外行为不变"（技能：refactor-guardrails）；
2. 每片按场景 1 完整走一遍（分支 → 同步 → 实测 → 合并）；
3. 【AI】验收红线：既有测试原样全绿；要改行为就拆成独立 feat/fix 分支单独走；
4. 窗口内出紧急 bug → 修复优先走场景 2，【AI】当天把 main merge 进重构分支吸收后继续。

## 场景 5：发布 stable 与回滚

发布：

1. 【人】在 latest 上按 checklist 确认本批 commit 全部实测通过；
2. 【人】对 AI 说："**按 merge-and-close 打 tag 发布**" → 【AI】打 tag（message 写本批摘要）→ 原子推送（技能：merge-and-close）；
3. 【流水线/人】将 stable 部署到该 tag（代码与 `deploy-intranet/` 配置随 tag 一起固化）。

回滚：

4. 【人】决定回滚 → 重新部署上一个 stable tag 即可，秒级完成，代码配置一起回滚，不需要改任何代码；
5. 【AI】事后把故障场景沉淀为外网可跑的回归测试（技能：fix-workflow 的失败案例回流）。

## 场景 6：分支清理

- 合并完成：【AI】当场删本地+远程分支（squash 合并用 `git branch -D`）（技能：merge-and-close）；
- 决定废弃：【人】拍板后对 AI 说："**归档废弃 <分支>**" →【AI】在 spec/issue 记录 commit hash、废弃原因、可复用片段 → 删；
- 每周卫生检查：【人】对 AI 说："**做分支卫生检查**" →【AI】列出存活超 7 天的分支 →【人】逐个决定：继续迭代 / 尽快合并 / 归档删除；
- 内网临时分支：close 包执行时自动删，人不干预。

禁止删除：迭代验证环中的分支、未合并未归档的分支、被未关闭 spec/issue 引用的分支。

## 场景 7：网络故障（GitHub/Gitee 访问失败）

AI 自动按 network-safe-git 处理，人基本无需操作：

1. push/fetch 失败：【脚本】自动按 5s/15s/45s/2m/5m 退避重试，最多 5 次；永久错误立即报告，不重试；
2. 仍不通：【脚本】挂起进 outbox，【AI】报告"已挂起，恢复后自动续做"；
3. 网络恢复后，【人】只需对 AI 说："**网络恢复了，继续**"（技能：network-safe-git，续做幂等）；
4. 长时间不通：【人】安排做不依赖网络的工作（本地开发、写 spec、跑本地检查）；
5. 铁律：AI 不得因一次 push 失败就重做整个合并流程，也不得绕过包装脚本裸推。

## 场景 8：import.sh 执行失败

1. 【脚本】自动还原到执行前状态，输出失败原因和下一步提示；
2. 【人】按提示操作（如"main 同步落后，请先执行 sync-main-NNN 包"），不手工修仓库；
3. 提示无法解决：【人】对 AI 说："**import.sh 执行失败，日志如下，诊断原因，不要改包、不要绕过**" →【AI】给出处置方案，人再执行。

---

## 一页速查：谁干什么 + 怎么触发

| 角色 | 职责 |
| --- | --- |
| 【人】 | 定需求、审 spec、拷包、执行 import.sh、latest 实测、写操作前确认、发布/回滚/废弃的决策、带技能名下指令 |
| 【AI】 | 写 spec、写代码、本地检查、建/合/删分支、打 tag、出同步包、对账汇报、回归测试沉淀 |
| 【脚本】 | 出包、导入、建内网分支、校验、对账、触发部署、重试、挂起续做、失败还原 |

| 场景 | 人对 AI 说 | 对应技能 |
| --- | --- | --- |
| 每日开工 | "开工，按 AGENTS.md 开工引导执行，并把 main 同步进在途分支" | AGENTS.md 开工引导 |
| 新功能 | "按 feat-workflow 开发……" | feat-workflow |
| 修 bug | "按 fix-workflow 处理……" | fix-workflow |
| 实测失败 | "按 iteration-round 继续改，别换分支" | iteration-round |
| 出同步包 | "按 sync-package 出 sync 包" | sync-package |
| 合并收尾/发布 | "按 merge-and-close 收尾，先汇报等我确认" | merge-and-close |
| 重构 | "按 refactor-guardrails 执行，窗口已公告" | refactor-guardrails |
| 网络恢复 | "网络恢复了，继续" | network-safe-git |
| 使用代理 | "网络走代理 http://…，记到 .sync-state/proxy" | network-safe-git |

分工一句话：人做决策和搬运，AI 做开发和操作，脚本做重复和校验。
