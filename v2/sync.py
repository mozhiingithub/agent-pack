#!/usr/bin/env python3
"""
v2 同步工具：GitHub 全量 zip → 内网仓库分支完整覆盖

用法:
  python3 sync.py <zip文件> --branch <分支名> --message "变更描述"
           [--base <基线分支>] [--push] [--repo <仓库路径>]

放置约定（同级目录）:
  <目录>/
  ├── <内网仓库>/     （git 仓库，--repo 省略时自动识别，唯一才自动）
  ├── sync.py         （本工具，不受 git 管控）
  ├── sync.ini        （参数文件：声明主分支名）
  ├── sync.ignore     （忽略清单：内网专属、不与外网同步的路径）
  └── *.zip           （GitHub 网页下载的全量包）

语义: 将 zip 内容完整覆盖目标分支（含删除 zip 中不存在的文件），
      忽略清单中的路径一律不动；随后以变更描述提交一个 commit。
      外网独有提交记录不复制（v2 放弃提交记录一致性，换取确定性）。
"""
import argparse
import fnmatch
import io
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# Windows 中文区域（GBK）下：subprocess 若用 text=True 会按 GBK 解码 git 的 UTF-8 输出而崩溃。
# 统一改为手动 UTF-8 解码（errors="replace"），并把脚本自身输出固定为 UTF-8。
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import configparser
except ImportError:  # noqa
    configparser = None


def die(msg):
    print(f"[sync] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def log(msg):
    print(f"[sync] {msg}")


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    stdout = r.stdout.decode("utf-8", errors="replace") if r.stdout else ""
    stderr = r.stderr.decode("utf-8", errors="replace") if r.stderr else ""
    r = subprocess.CompletedProcess(r.args, r.returncode, stdout, stderr)
    if check and r.returncode != 0:
        die(f"git {' '.join(args)} 失败: {r.stderr.strip()}")
    return r


def out(repo, *args):
    return git(repo, *args).stdout.strip()


def load_ignore(path):
    pats = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                pats.append(line)
    return pats


def is_ignored(rel, pats):
    for p in pats:
        if p.endswith("/"):
            if rel == p[:-1] or rel.startswith(p):
                return True
        elif rel == p or fnmatch.fnmatch(rel, p):
            return True
    return False


def collect_protected(repo, pats):
    """把忽略清单展开为实际存在的路径集合（支持目录前缀、确切路径、文件名 glob）。"""
    found = set()
    for p in pats:
        if p.endswith("/"):
            d = repo / p[:-1]
            if d.exists():
                found.add(d)
        else:
            direct = repo / p
            if direct.exists():
                found.add(direct)
            else:
                for hit in repo.rglob("*"):
                    if ".git" in hit.parts:
                        continue
                    rel = hit.relative_to(repo).as_posix()
                    if fnmatch.fnmatch(rel, p):
                        found.add(hit)
    return found


def git_ignored(repo):
    """仓库 .gitignore 覆盖的本地未跟踪路径（用 git 自己的引擎，语义不走样）。"""
    r = git(repo, "ls-files", "--others", "--ignored", "--exclude-standard",
            "--directory", "-z")
    if not r.stdout:
        return set()
    return {repo / p.rstrip("/") for p in r.stdout.split("\0") if p}


def main():
    ap = argparse.ArgumentParser(description="v2 同步工具：GitHub 全量 zip → 内网仓库分支完整覆盖")
    ap.add_argument("zipfile", help="GitHub 网页下载的全量 zip 包")
    ap.add_argument("-b", "--branch", required=True, help="目标分支（不存在则新建）")
    ap.add_argument("-m", "--message", required=True, help="变更描述（一句话）")
    ap.add_argument("--base", help="新建分支的基线分支；缺省用 sync.ini 的主分支")
    ap.add_argument("--push", action="store_true", help="完成后推送到 origin（网络问题由人处置）")
    ap.add_argument("--repo", help="内网仓库路径；缺省自动识别同级目录下唯一的 git 仓库")
    args = ap.parse_args()

    tool_dir = Path(__file__).resolve().parent

    # ---------- 参数文件与忽略清单 ----------
    main_branch = "main"
    repo_name = None
    inifile = tool_dir / "sync.ini"
    if inifile.exists() and configparser:
        ini = configparser.ConfigParser()
        ini.read(inifile, encoding="utf-8")
        main_branch = ini.get("sync", "main_branch", fallback="main")
        repo_name = ini.get("sync", "repo", fallback=None) or None
    pats = load_ignore(tool_dir / "sync.ignore")

    # ---------- 定位仓库：--repo > sync.ini repo 项 > 自动识别（唯一时） ----------
    if args.repo:
        repo = Path(args.repo).resolve()
        (repo / ".git").is_dir() or die(f"不是 git 仓库: {repo}")
    elif repo_name:
        repo = (tool_dir / repo_name).resolve()
        (repo / ".git").is_dir() or die(f"sync.ini 指定的 repo 不存在或不是 git 仓库: {repo}")
    else:
        cands = [d for d in tool_dir.iterdir() if d.is_dir() and (d / ".git").exists()]
        if len(cands) != 1:
            die("同级目录下 git 仓库不唯一或不存在：请在 sync.ini 的 repo 项指定，或用 --repo。候选: "
                + (", ".join(d.name for d in cands) or "无候选"))
        repo = cands[0]
    log(f"内网仓库: {repo}")
    log(f"主分支: {main_branch}；忽略规则 {len(pats)} 条")

    zipsrc = Path(args.zipfile).resolve()
    zipsrc.is_file() or die(f"全量包不存在: {zipsrc}")

    # ---------- 前置校验 ----------
    if out(repo, "status", "--porcelain"):
        die("工作区不干净：请先提交或清理（工具不替人保存现场）")
    if git(repo, "var", "GIT_COMMITTER_IDENT", check=False).returncode != 0:
        die('未配置 git 提交者身份：git config --global user.name "名字" 及 user.email "邮箱"')

    cur = out(repo, "branch", "--show-current")
    branch_exists = git(repo, "rev-parse", "--verify", f"refs/heads/{args.branch}",
                        check=False).returncode == 0

    try:
        # ---------- 建/切分支 ----------
        if not branch_exists:
            base = args.base or main_branch
            if git(repo, "rev-parse", "--verify", f"refs/heads/{base}",
                   check=False).returncode != 0:
                die(f"基线分支不存在: {base}（用 --base 指定，或在 sync.ini 声明主分支）")
            git(repo, "checkout", "-b", args.branch, base)
            log(f"已从 {base} 新建分支 {args.branch}")
        else:
            git(repo, "checkout", args.branch)
        old_head = out(repo, "rev-parse", "HEAD")

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            # zip 先复制到临时目录（防止 zip 位于仓库内被自身覆盖）
            tmpzip = td / "pkg.zip"
            shutil.copy2(zipsrc, tmpzip)
            with zipfile.ZipFile(tmpzip) as z:
                if any(n.split("/")[0] == ".git" for n in z.namelist()):
                    die("全量包内含 .git，拒收")
                infos = z.infolist()
                z.extractall(td)
            roots = [p for p in td.iterdir() if p.name != "pkg.zip"]
            src = roots[0] if len(roots) == 1 and roots[0].is_dir() else td
            # zipfile 不恢复 unix 权限位：记录可执行文件，复制后补回（否则 git 报 mode 变化）
            prefix = (roots[0].name + "/") if src is roots[0] else ""
            execs = {i.filename[len(prefix):] for i in infos
                     if i.filename.startswith(prefix) and (i.external_attr >> 16) & 0o111}

            # ---------- 保护集合：sync.ignore ∪ 仓库 .gitignore ----------
            protected = {p.resolve() for p in (collect_protected(repo, pats) | git_ignored(repo))}
            log(f"保护路径 {len(protected)} 个（sync.ignore + 仓库 .gitignore）")

            def is_protected(path):
                rp = path.resolve()
                return any(rp == pr or pr in rp.parents for pr in protected)

            # ---------- 完整覆盖：按保护集合逐文件删除（除 .git）→ 复制 ----------
            for entry in sorted(repo.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if ".git" in entry.parts or is_protected(entry):
                    continue
                if entry.is_file() or entry.is_symlink():
                    entry.unlink()
                elif entry.is_dir():
                    try:
                        entry.rmdir()  # 仅删已清空的目录；含保护内容的目录自动保留
                    except OSError:
                        pass
            copied = 0
            for f in src.rglob("*"):
                if f.is_dir():
                    continue
                rel = f.relative_to(src).as_posix()
                if is_ignored(rel, pats) or is_protected(repo / rel):
                    continue
                dst = repo / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                if rel in execs:
                    dst.chmod(0o755)
                copied += 1

        # ---------- 提交 ----------
        git(repo, "add", "-A")
        # 防呆：若全量包缺 .gitignore（不规范包），被忽略的本地产物会被 add -A 纳入，逐一出栈
        for pr in protected:
            git(repo, "reset", "-q", "--", str(pr.relative_to(repo)), check=False)
        if not out(repo, "diff", "--cached", "--shortstat"):
            log("无内容变更，无需提交（分支已与全量包一致）")
        else:
            git(repo, "commit", "-m", f"[sync] {args.branch}: {args.message}")
            log(f"已提交: {out(repo, 'log', '-1', '--format=%h %s')}（覆盖文件 {copied} 个）")
            log("变更统计: " + out(repo, "diff", "--shortstat", f"{old_head}..HEAD"))

        # ---------- 可选推送 ----------
        if args.push:
            r = git(repo, "push", "origin", args.branch, check=False)
            if r.returncode != 0:
                die(f"推送失败（v2 原则：网络问题由人处置）。可稍后手动执行: git push origin {args.branch}\n{r.stderr.strip()}")
            log(f"已推送 origin {args.branch}")

        print("\n========== SUCCESS ==========\n")
    finally:
        if cur and cur != args.branch:
            git(repo, "checkout", cur, check=False)


if __name__ == "__main__":
    main()
