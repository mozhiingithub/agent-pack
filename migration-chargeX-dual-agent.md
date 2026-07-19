# chargeX_fault_platform 引入双工协作模式改造方案

> 性质：预研文档，暂不动工。触发条件：agent-pack 在试运行项目（agent-pack-test）上稳定运行、机制成熟后再启动。
> 约束：不破坏 chargeX 现有 spec-coding 与 superpowers 体系；双工协作内核（分支纪律、迭代验证环、内外网同步包、人对写操作确认）完整落地。
> 依据文档：`solution.md`、`handbook.md`、`agent-pack/`（含 `skills/superpowers/` vendored 副本）。

## 一、现状盘点（改造起点）

| 维度 | chargeX 现状 | 与双工机制的关系 |
| --- | --- | --- |
| spec 体系 | `docs/product-specs` + `docs/exec-plans`（active/completed）+ `docs/PLANS.md` 索引 | 结构完全兼容，只需补两个字段（见第五节） |
| 技能 | `.claude/skills/superpowers/` 14 个 | 6 个保留、4 个改造或弃用、4 个可留作参考（见第二节） |
| 分支 | 在 `mjw` 个人分支上工作，GitHub 单仓库 | 需先归并主干，再立 main 保护（见第六节） |
| 检查命令 | 已有"验证命令速查"（ast 语法、vue-tsc、pytest、npm test） | 直接作为 `.checks-ok` 产生器（见第七节） |
| 部署 | `deploy/`（docker-compose、helm、pack.sh/unpack.sh） | pack.sh 管部署制品，同步包管代码，职责切分（见第四节） |
| AGENTS.md | 220 行：知识库导航、文档规则、superpowers 产物落位、运行与测试、工作方式 | 保留主体，插入三块新内容（见第三节） |
| 内外网 | 尚未分离（单 GitHub 仓库） | 需新建内网仓库（Gitee）与 latest/stable 双实例 |

## 二、引入的 skill 清单与冲突裁决

### 从 agent-pack 引入（8 个）

`feat-workflow`、`fix-workflow`、`iteration-round`、`sync-package`、`merge-and-close`、`refactor-guardrails`、`network-safe-git`，以及 vendor 版 `superpowers/`（6 个：brainstorming、writing-plans、executing-plans、test-driven-development、systematic-debugging、verification-before-completion——chargeX 已有同源副本，可直接对齐版本）。

### 与现有 14 个 superpowers 技能的裁决表

| 现有技能 | 裁决 | 理由 |
| --- | --- | --- |
| brainstorming / writing-plans / executing-plans / test-driven-development / systematic-debugging / verification-before-completion | **保留** | 与双工机制同构，已 vendor 进 agent-pack；只需把"问用户"类交互改为批量提问，产物落位沿用现有规则 |
| finishing-a-development-branch | **弃用，以 merge-and-close 替代** | 其"push 建 PR、四选项"假设在线 GitHub 与单人连续执行；双工收尾必须是 squash + 人确认 + close 包 |
| using-git-worktrees | **保留但降级为参考** | import.sh 已内建 worktree 契约；该技能可用于 agent 本地开发隔离，不与内网流程叠加 |
| subagent-driven-development | **弃用（拓扑冲突）** | 同会话派 implementer、连续执行不问人，与"开发/修复各一个独立 agent + 人确认写操作"冲突 |
| dispatching-parallel-agents | **改造为只读并行调查** | 与"一个分支同一时刻只有一方在改"冲突；保留其独立失败域调查用法，禁止并行改码 |
| requesting-code-review / receiving-code-review | **保留（第二阶段再启用）** | 可改造成跨 agent 互审协议（review-package 随同步包走），首轮迁移不启用 |
| writing-skills / using-superpowers | **保留** | 体系元技能，无冲突 |

冲突总原则写入 AGENTS.md：**双工铁律优先于 superpowers 技能条款**；superpowers 的"连续执行"在该项目降级为"任务内连续、写操作必停"。

## 三、AGENTS.md 改造方案（逐节）

现有 220 行主体**全部保留**，做"三块新增、两处修改"。

### 新增 A：角色与模式（放在文件最前）

```markdown
## 角色与双工模式

- 两条工作线：开发线（feat/*）与修复线（fix/*），各有自己的 agent，你是其中之一。
- main 是唯一事实来源：不直接承载开发提交，只接收验证通过的分支合入。
- 内外网双仓：外网 GitHub 开发，内网 Gitee 部署；代码只能经同步包单向流动（外网→内网）。
```

### 新增 B：铁律（紧随其后，含指令触发表）

直接移植 agent-pack/AGENTS.md 的铁律 1~7（分支纪律、单分支单负责人、写操作人确认、网络走 safe-git、commit message 规范、spec 两层先行、机制修复不搭车），并将**指令触发表**与现有 superpowers 技能合并为一张表：

| 短语 | 流程 |
| --- | --- |
| "开工…同步 main" | 开工引导（读本文 + PLANS.md + git log + merge main 进在途分支） |
| "按 feat-workflow…" | agent-pack/skills/feat-workflow |
| "按 fix-workflow…" | agent-pack/skills/fix-workflow |
| "brainstorm / 写 plan" | superpowers/brainstorming → writing-plans（产物落位按现有规则） |
| "按 sync-package / merge-and-close / iteration-round…" | 对应 agent-pack skill |

### 新增 C：目录与边界约定

- `docs/exec-plans/active/`、`docs/product-specs/`、`docs/PLANS.md` 沿用现有落位规则；
- `deploy-intranet/`（内网专属部署配置目录，占位名，实际可复用 `deploy/` 的内网侧变体）只存在于内网仓库；
- 同步包约定：zip 平铺、解压到内网仓库一级目录、执行 `import.sh`（零配置）。

### 修改 1：文档使用规则

第 1 条"先入口，再深入"后追加：**开工引导固定动作**（读 PLANS.md → `git log --oneline main -20` → `git diff <基点>..main --stat`），与现有渐进式披露规则合并，不另起一节。

### 修改 2：工作方式

在"注释和 git commit 一律用中文"后追加 commit message 规范：`type(scope): 摘要`，type ∈ `feat` / `fix` / `refactor` / `config`；fix 正文写根因。与现有中文要求合并。

## 四、tools/ 与基础设施落地

1. 用 `agent-pack/templates/bootstrap.sh` 改造版一次性铺设：`tools/export_package.sh`、`tools/safe-git.sh`、`tools/templates/import.sh`、`.githooks/pre-push`、`.agents/skills/`。chargeX 已有 `scripts/`（api/db/demo），tools/ 与 scripts/ 并存：scripts/ 管业务工具，tools/ 管协作机制。
2. **deploy/ 与同步包的关系**：`deploy/pack.sh`/`unpack.sh` 是部署制品打包（镜像、配置），同步包是**代码变更**的跨网传输，两者不替代——内网拿到代码后仍走现有 deploy 流程部署 latest。改造点仅为：`deploy/` 中内网专属配置（helm values、nginx 配置）归入保护路径清单，同步包永不触碰。
3. `.gitignore` 补 `.sync-state/`、`outbox/`；pre-push 钩子启用（`git config core.hooksPath .githooks`）。

## 五、spec 两层规则的落地（改动最小）

chargeX 的产物落位规则已兼容，只需两处补强：

1. exec-plan 模板补两节："**来源需求**"（指向 product-specs 文件）与"**部署影响**"（export 脚本硬性检查项，无则写"无"）；存量 exec-plan 不强制回填，被新工作触及时补上；
2. `docs/PLANS.md` 增加"分支"列（计划 ↔ feat/fix 分支对应关系），替代 agent-pack 的 SPEC_FILE 单文件映射难以覆盖的多计划并行场景。

## 六、分支模型与内外网同步

1. **先归并主干**：`mjw` 个人分支的工作归并回 main（或确认以某分支为主干并更名），此后 main 受保护（禁 force push、仅维护者可推）；
2. 此后新工作一律 `feat/*`、`fix/*` 短分支，规则同 agent-pack（每日 merge main、合并方向单向、删除规范）；
3. 新建内网仓库（Gitee）：首个 main 同步包为全量基线导入；latest/stable 双实例按现有 deploy 流程各挂一份；
4. 迭代验证环、main 同步包、close 包流程与试运行项目完全一致，不再重复设计。

## 七、外网检查门槛（复用现有验证命令）

`tools/check.sh` 直接封装 AGENTS.md 现有"验证命令速查"：

```bash
python3 -c "import ast; ..."   # 后端语法（受影响文件）
cd frontend && npx vue-tsc --noEmit
pytest tests/ -x -q
cd frontend && npm test
touch .checks-ok               # 全绿后写标记（export 前置校验要求 24h 内有效）
```

失败案例回流规则不变：内网实测发现的问题，优先转化为上述四项中可外网执行的用例。

## 八、迁移步骤（三阶段）

| 阶段 | 内容 | 验收 |
| --- | --- | --- |
| 1. 准备（1 周） | 归并主干、main 保护、bootstrap 铺 tools/、exec-plan 模板补两节、AGENTS.md 按第三节改造 | bootstrap 自检通过；agent 读新 AGENTS.md 能正确触发指令表 |
| 2. 试运行（2 周） | 选一个小需求走 feat 全流程 + 一个小 bug 走 fix 全流程 + 一次 main 同步；期间 superpowers 流程照用，观察冲突点 | 三条链路各闭环一次；失败案例全部回流 |
| 3. 推广 | 废弃 finishing-a-development-branch 与 SDD；视情况启用跨 agent 互审 | 连续两周无机制类事故 |

回退方案：机制文件全部在 `tools/`、`.agents/`、`.githooks/`、AGENTS.md 新增块中，删除即恢复原状，不影响业务代码与 spec 库。

## 九、风险与对策

| 风险 | 对策 |
| --- | --- |
| superpowers"连续执行"习惯 vs 人确认停顿 | AGENTS.md 写明双工铁律优先；agent 首周易违规，人盯写操作汇报点 |
| chargeX 检查链较重（pytest+npm test）拖慢迭代轮 | check.sh 支持只跑受影响范围（可变区），但标记有效期不变 |
| 内网仓库不存在（全新） | 首个 main 包为全量基线；import.sh 的 main 引导路径已支持 |
| 分支归并期与在途工作冲突 | 归并窗口内冻结新分支，先清在途 |
| 模型分级不可控 | 放弃，退化为人启动会话时的选型建议 |
