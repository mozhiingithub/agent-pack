24599@mo MINGW64 /d/coding/2026/agent-pack-test (main)
$ unzip sync-feat-add-message-timestamp-3.zip 
Archive:  sync-feat-add-message-timestamp-3.zip
  inflating: files.txt               
  inflating: import.sh               
  inflating: manifest.sh             
 extracting: message.txt             
   creating: payload/
  inflating: payload/0001-feat-exec-plans-spec.patch  
  inflating: payload/0002-feat-message-board.patch  
  inflating: payload/0003-fix-tools-export_package.sh.patch  
  inflating: payload/0004-fix-tools-quotePath-ls-remote-safe-git-configImpact.patch  
  inflating: payload/0005-fix-tools-zip-import.sh.patch  

24599@mo MINGW64 /d/coding/2026/agent-pack-test (main)
$ bash import.sh 
[import] 16:00:26 内网仓库: D:/coding/2026/agent-pack-test
Applying: feat(exec-plans): 消息时间戳执行计划补充 spec 细节
Applying: feat(message-board): 列表消息显示发布时间
Applying: fix(tools): export_package.sh 分支名含 / 时出包必败。
Applying: fix(tools): 同步上游模板复盘修订（quotePath 硬阻断绕过、ls-remote 走 safe-git、configImpact 归一化、提交者身份预检）。
Applying: fix(tools): 同步上游模板——zip 平铺打包 + import.sh 零配置自动定位仓库。
[import] ERROR: commit 校验失败

24599@mo MINGW64 /d/coding/2026/agent-pack-test (main)