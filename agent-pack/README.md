# agent-pack：AI 操作规范包（示例）

把 `solution.md` / `handbook.md` 中的规范固化为 agent 可加载的指令文件，避免所有规则靠人口头转述。

## 内容

- `AGENTS.md`：仓库级强制规范 + 开工引导，两个 agent（开发/修复）共用；
- `skills/`：分场景操作技能，与 handbook.md 的场景一一对应；
- `templates/`：`export_package.sh` / `import.sh` / `safe-git.sh` 参考骨架，分固定区（不得修改）与可变区（按项目实现），AI 生成脚本必须以此为底。三者分工：export 在外网出包；import 随包下发、内置重试（包自包含，不依赖内网仓库已有 `tools/`）；safe-git 供 agent 与人日常网络操作。`templates/githooks/pre-push` 为裸推拦截钩子（`git config core.hooksPath .githooks` 启用）。

## 部署

1. `AGENTS.md` → 拷贝到项目仓库根目录；
2. `skills/*` → 拷贝到 agent 的技能目录（按所用工具的约定路径，如 `.agents/skills/`）；
3. 实现 `tools/` 下的配套脚本（`export_package.sh` / `import.sh` / safe-git 包装函数），本包只含规范，不含脚本实现；
4. 规范变更时三处同步：`solution.md`（权威解释）、`handbook.md`（人读）、`agent-pack/`（AI 读）。

## 仓库目录约定（tools/ 是项目仓库的普通一部分）

```
<项目仓库>/
├── AGENTS.md                  # 本包根文件
├── .githooks/pre-push         # 裸推拦截钩子（git config core.hooksPath .githooks）
├── tools/
│   ├── export_package.sh      # 出包脚本（基于 templates 骨架生成）
│   ├── safe-git.sh            # agent/人的网络操作包装
│   └── templates/import.sh    # 出包时拷入同步包的 import.sh 模板
├── docs/                      # spec 结构（exec-plans 等）
└── .sync-state/               # seq / 上一状态 hash / outbox——机器本地状态，必须加入 .gitignore
```

- `tools/` 随正常代码同步进入内网，不是外部依赖；
- `.sync-state/` 是各机器自己的状态（外网出包机、内网执行机各自一份），**不能进 git**，否则两侧序号互相污染；
- `import.sh` 不依赖 `tools/`（重试内置、包自包含），所以即使 `tools/` 尚未同步到内网，首包也能正常执行。

## 老项目接入（已按 docs/ 结构适配）

本项目 spec 结构为 `docs/`（`product-specs` / `design-docs` / `exec-plans{active,completed}` / `generated` / `references`），本包已按此适配。

老仓库没有 `tools/`、钩子、AGENTS.md 等任何基础设施，用一次性脚手架铺好：

```bash
bash agent-pack/templates/bootstrap.sh <项目仓库根目录>
```

脚本幂等（已存在的文件跳过不覆盖，`--force` 才覆盖），自动完成：拷贝 tools/ 脚本与 import 模板、安装 `.githooks/pre-push` 并设置 `core.hooksPath`、`.gitignore` 补 `.sync-state/` 与 `outbox/`、落地 AGENTS.md 与 skills、检查 Git Bash 必备命令、检查 exec-plan 模板是否含"部署影响"。之后手工做四件事：填两个脚本的可变区、（若已有 AGENTS.md）手工合并、提交、拿一个小 bug 全流程试跑。

其余适配要点：

- 分支 ↔ spec 映射：`feat|fix/<名>` ↔ `docs/exec-plans/active/<名>.md`（见 `templates/export_package.sh` 可变区 `SPEC_FILE`）；执行计划是干活用的 spec；
- spec 两层：**新需求先 product-spec 后 exec-plan**，exec-plan 须注明来源需求；fix 类只写 exec-plan（四要素），不需要 product-spec；
- spec 状态：用 `active/` ↔ `completed/` 目录移动表达，合入 main 后由 merge-and-close 流程 `git mv` 归档，比状态字段更清爽；
- 接口契约集中在 `docs/design-docs/`，双方 agent 必读；
- 需求层（`docs/product-specs/`）与执行层（exec-plans）一对多：一个大需求拆成多个执行计划，正好对应"功能拆小单元分批合入"；
- exec-plan 模板必须含"部署影响"一节（export 脚本硬性检查项）；存量计划不强制回填，被新工作触及时顺手补上。

其他项目若结构不同，硬性要求只有内容层面四条：分支与 spec 一一对应且映射可机械判定；含"部署影响"节与状态表达；接口变化有固定记录处；经人确认后才动工。

## 技能清单

| 技能 | 触发场景 |
| --- | --- |
| `feat-workflow` | 开发新功能 |
| `fix-workflow` | 修复 main 上的 bug |
| `iteration-round` | 内网实测失败后的迭代 |
| `sync-package` | 生成内网同步包 |
| `merge-and-close` | 合入 main、打 tag、删分支、close 包 |
| `refactor-guardrails` | 重构/简化类需求 |
| `network-safe-git` | 一切 git 网络操作及失败处理 |
