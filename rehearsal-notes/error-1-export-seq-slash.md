 出包失败，按 sync-package 规范停止，原文转述 stderr：                                                                                                                                                                    
                                                                                                                                                                                                                            
   ```                                                                                                                                                                                                                      
     tools/export_package.sh: line 100: .sync-state/seq-feat/add-message-timestamp: No such file or directory                                                                                                               
   ```                                                                                                                                                                                                                      
                                                                                                                                                                                                                            
   根因诊断（只读排查，未动任何东西）：                                                                                                                                                                                     
   • tools/export_package.sh:41 把分支名直接拼进状态文件路径：SEQ_FILE="$STATE_DIR/seq-$BRANCH"。我们的分支名都带 /（feat/*、fix/*），路径变成 .sync-state/seq-feat/add-message-timestamp——中间目录 seq-feat/ 从未被创建；  
   • 第 42-43 行读文件能容忍不存在，但第 100 行 echo "$SEQ" > "$SEQ_FILE" 写文件时直接失败。即：该脚本对任何带 / 的分支名（也就是所有标准分支）出包必败，属 main 上可复现的 bug；                                           
   • 修法很简单（如第 40 行 mkdir -p 时加上状态文件父目录，或对分支名做 / 转义），但失败点在脚本的固定区，按规范需你确认结构变更并同步 agent-pack 上游模板（本仓库 tools/templates/ 只有 import.sh，没有 export 骨架副本）。
                                                                                                                                                                                                                            
   现场状态：工作区干净；失败残留 outbox/sync-feat/add-message-timestamp-1{,.tar}（序号未记账，.sync-state/ 无 seq 文件；修复后重跑会因 rm -rf 自动清理残留）；分支开发与推送均不受影响。                                   
 ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Todo
   ✓ 建 feat/add-message-timestamp 分支并推远端
   ✓ 开发 web/app.js + web/style.css
   ✓ 本地检查全绿（check.sh + node --check）
   ● 按 sync-package 出包交内网实测
   ○ 实测通过后按 merge-and-close 收尾
   … +1 more (1 done) · ctrl+t to expand
 ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  question
 
   脚本修复    Submit 
 
  ? export_package.sh 对带 / 的分支名必败，如何推进？
 
   → [1] 走 fix-workflow 修脚本 (Recommended)
         按修复线流程开 fix/export-package-seq 分支修脚本（根因 spec + 修复 + 回归测试），修完回来重新出包；固定区变更会请你过目
     [2] 人来修，我等
         我暂停在本步，等你或修复线 agent 修好脚本后，说一声我重新跑 export_package.sh
     [3] 其他方案
         你有其他处理意见（如临时改分支命名约定，不推荐）
     [4] Other
 
   ↑↓ select  1-4 / ↵ choose  ←/→/tab switch  esc cancel